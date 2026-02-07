import sys
import os
import atexit
import importlib.util
import inspect
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any, Tuple
from dotenv import load_dotenv

from skills.util_comuns import (
    LOG_DIR,
    SKILLS_DIR,
    cleanup_processos
)
from skills.cerebro import gemini_cli_raw
from skills.codex_cli import executar_codex_cli, executar_codex_cli_raw

# --- CONFIGURACAO DE VERSAO ---
VERSION = "0.4.1"
UPDATE_DATE = "2026-02-07"

# --- SETUP INICIAL ---
load_dotenv()

# --- HARDENING: ENCODING ---
if sys.stdout and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass
if sys.stderr and sys.stderr.encoding != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

# --- CONFIGURACAO ---
ROUTER_MODE = os.getenv("ROUTER_MODE", "rules").lower()
ROUTER_MODE = ROUTER_MODE if ROUTER_MODE in {"rules", "llm", "hybrid"} else "rules"
HISTORY_TURNS = int(os.getenv("HISTORY_TURNS", "8"))
HISTORY_MAX_CHARS = int(os.getenv("HISTORY_MAX_CHARS", "2000"))
SUMMARY_MAX_CHARS = int(os.getenv("SUMMARY_MAX_CHARS", "4000"))
CODEX_SANDBOX = os.getenv("CODEX_SANDBOX", "workspace-write")
CODEX_TIMEOUT = int(os.getenv("CODEX_TIMEOUT", "900"))
CODEX_MODEL = os.getenv("CODEX_MODEL", "")
SLASH_ROUTE = os.getenv("SLASH_ROUTE", "auto").lower()
SLASH_ROUTE = SLASH_ROUTE if SLASH_ROUTE in {"auto", "gemini", "codex"} else "auto"

SKILLS_ALLOWLIST = {
    s.strip() for s in os.getenv(
        "SKILLS_ALLOWLIST",
        "sistema,memoria,cerebro,codex_cli"
    ).split(",") if s.strip()
}

if not os.getenv("GEMINI_API_KEY"):
    print("Aviso: GEMINI_API_KEY nao encontrada. Chamadas ao Gemini CLI podem falhar.")

# --- GESTAO DE DIRETORIOS E SKILLS ---
def ensure_skills_dir() -> None:
    """Garante que a pasta skills existe e e um pacote Python."""
    if not SKILLS_DIR.exists():
        SKILLS_DIR.mkdir(parents=True)
        print("Diretorio 'skills' criado.")

    init_file = SKILLS_DIR / "__init__.py"
    if not init_file.exists():
        init_file.touch()


def carregar_ferramentas_dinamicas() -> List[Callable]:
    """
    Carrega ferramentas dinamicamente da pasta skills/.
    Critérios: funcoes com docstrings e type hints.
    Aplica allowlist: apenas infra (sistema, memoria, cerebro, codex_cli).
    """
    ensure_skills_dir()
    dynamic_tools: List[Callable] = []

    print(f"Buscando skills em {SKILLS_DIR.resolve()} (allowlist: {sorted(SKILLS_ALLOWLIST)})")

    for py_file in SKILLS_DIR.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name == "util_comuns.py":
            continue
        if py_file.stem not in SKILLS_ALLOWLIST:
            continue

        module_name = f"skills.{py_file.stem}"
        try:
            if module_name in sys.modules:
                mod = importlib.reload(sys.modules[module_name])
            else:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = mod
                    spec.loader.exec_module(mod)
                else:
                    continue

            for name, func in inspect.getmembers(mod, inspect.isfunction):
                if func.__module__ == module_name:
                    if func.__doc__ and func.__annotations__:
                        dynamic_tools.append(func)
                        print(f"  + Skill carregada: {name} ({module_name})")
        except Exception as e:
            print(f"  Falha ao carregar {py_file.name}: {e}")

    return dynamic_tools


def _parse_direct_tool_call(msg: str) -> Optional[tuple[str, Dict[str, Any]]]:
    """
    Detecta pedidos diretos do tipo "Use a skill X ..." para executar localmente.
    """
    if not msg:
        return None
    pattern = (
        r"(?i)\b(use a skill|use the skill|use a tool|use a ferramenta|"
        r"use a habilidade|use o skill|use a skill)\s+([a-zA-Z0-9_]+)"
    )
    match = re.search(pattern, msg)
    if not match:
        return None
    tool_name = match.group(2)
    args: Dict[str, Any] = {}
    args_match = re.search(r"(?i)\bargs?\b", msg)
    if args_match:
        start = msg.find("{", args_match.end())
        end = msg.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                args = json.loads(msg[start:end + 1])
            except json.JSONDecodeError:
                args = {}

    if not args:
        texto_match = re.search(r"(?i)\b(texto|text)\s*['\"]([^'\"]+)['\"]", msg)
        if texto_match:
            args["texto"] = texto_match.group(2)
    return tool_name, args


# --- CLEANUP ---
atexit.register(cleanup_processos)


def rotacionar_logs(dias_retencao: int = 3) -> None:
    agora = datetime.now()
    removidos = 0
    for log_file in LOG_DIR.glob("*.txt"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if agora - mtime > timedelta(days=dias_retencao):
                log_file.unlink()
                removidos += 1
        except:
            pass
    if removidos:
        print(f"{removidos} logs antigos removidos.")


# --- SEGURANCA ---
def forcar_workdir_seguro() -> None:
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    os.chdir(script_dir)
    if r"windows\system32" in script_dir.lower():
        sys.exit("CRITICO: execucao bloqueada em System32.")


forcar_workdir_seguro()


# --- ROTEADOR ---
EXEC_KEYWORDS = [
    "implementar", "codar", "corrigir", "bug", "teste", "testes",
    "rodar", "executar", "build", "deploy", "refator",
    "arquivo", "editar", "modificar", "patch", "diff", "commit",
    "git", "pip", "npm", "docker", "pytest", "unit test", "stacktrace"
]

FILE_EXT_RE = re.compile(r"\b[\w\-/\\\\]+\.(py|js|ts|md|yml|yaml|json|toml|txt|ini|cfg)\b", re.IGNORECASE)


def _looks_like_execution(msg: str) -> bool:
    text = msg.lower()
    if "```" in text:
        return True
    if any(k in text for k in EXEC_KEYWORDS):
        return True
    if re.search(r"\b(run|execute|rodar|exec|compilar)\b", text):
        return True
    if FILE_EXT_RE.search(text):
        return True
    return False


def _route_rules(msg: str) -> Optional[str]:
    if _looks_like_execution(msg):
        return "codex"
    return None


def _route_llm(msg: str) -> Optional[str]:
    prompt = (
        "Classifique a mensagem do usuario como GEMINI (pensar) ou CODEX (executar). "
        "Responda APENAS com GEMINI ou CODEX.\n\n"
        f"MENSAGEM:\n{msg}\n"
    )
    try:
        output = gemini_cli_raw(prompt)
    except Exception:
        return None
    if not output:
        return None
    lowered = output.strip().lower()
    if lowered.startswith("erro") or "falha" in lowered:
        return None
    upper = output.strip().upper()
    if "CODEX" in upper:
        return "codex"
    if "GEMINI" in upper:
        return "gemini"
    return None


def escolher_rota(msg: str) -> str:
    rule_choice = _route_rules(msg)
    if ROUTER_MODE == "rules":
        return rule_choice or "gemini"
    if ROUTER_MODE == "llm":
        llm_choice = _route_llm(msg)
        return llm_choice or rule_choice or "gemini"
    if ROUTER_MODE == "hybrid":
        if rule_choice:
            return rule_choice
        llm_choice = _route_llm(msg)
        return llm_choice or "gemini"
    return rule_choice or "gemini"


# --- HISTORICO E CONTEXTO ---
def _trim_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n[...TRUNCADO...]"


def _merge_summary(summary: str, overflow: List[Dict[str, str]]) -> str:
    lines = []
    if summary:
        lines.append(summary)
    for item in overflow:
        role = item.get("role", "unknown").upper()
        content = item.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    combined = "\n".join(lines)
    if len(combined) > SUMMARY_MAX_CHARS:
        combined = combined[-SUMMARY_MAX_CHARS:]
    return combined


def _rollup_history(history: List[Dict[str, str]], summary: str) -> Tuple[List[Dict[str, str]], str]:
    max_items = HISTORY_TURNS * 2
    if len(history) <= max_items:
        return history, summary
    overflow = history[:-max_items]
    summary = _merge_summary(summary, overflow)
    return history[-max_items:], summary


def _format_history(history: List[Dict[str, str]]) -> str:
    lines = []
    for item in history:
        role = item.get("role", "unknown").upper()
        content = item.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_context(history: List[Dict[str, str]], summary: str) -> str:
    parts = []
    if summary:
        parts.append(f"RESUMO:\n{summary}")
    if history:
        parts.append(f"ULTIMOS TURNOS:\n{_format_history(history)}")
    return "\n\n".join(parts)


def _build_gemini_prompt(msg: str, history: List[Dict[str, str]], summary: str) -> str:
    context = _build_context(history, summary)
    if context:
        return f"{context}\n\nUSUARIO:\n{msg}"
    return msg


def _extract_codex_final(report: str) -> str:
    marker = "FINAL MESSAGE:"
    if marker not in report:
        return report
    tail = report.split(marker, 1)[1]
    for sep in ["\n\nSTDOUT:", "\n\nSTDERR:", "\n\nLOGS:"]:
        if sep in tail:
            tail = tail.split(sep, 1)[0]
    return tail.strip()


# --- BOOTSTRAP ---
rotacionar_logs()
print(f"JARVIS V{VERSION} ONLINE. Logs em: {LOG_DIR.resolve()}")
ensure_skills_dir()

TODAS_FERRAMENTAS = carregar_ferramentas_dinamicas()
TOOL_MAP = {func.__name__: func for func in TODAS_FERRAMENTAS}

if "verificar_codex_cli" in TOOL_MAP:
    try:
        print(TOOL_MAP["verificar_codex_cli"]())
    except Exception as e:
        print(f"Codex CLI check failed: {e}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    history: List[Dict[str, str]] = []
    summary_text = ""

    while True:
        try:
            msg = input("\nCMD: ")
            if msg.strip().lower() in ["exit", "sair", "quit"]:
                break

            direto = _parse_direct_tool_call(msg)
            if direto:
                tool_name, tool_args = direto
                if tool_name in TOOL_MAP:
                    try:
                        result = TOOL_MAP[tool_name](**tool_args)
                        print(f"[BOT] {result}")
                    except Exception as e:
                        print(f"[ERROR] Erro ao executar {tool_name}: {e}")
                else:
                    print(f"[WARN] Skill {tool_name} nao encontrada.")
                continue

            route = escolher_rota(msg)

            if msg.lstrip().startswith("/"):
                if SLASH_ROUTE in {"gemini", "codex"}:
                    route = SLASH_ROUTE
                if route == "codex":
                    result = executar_codex_cli_raw(
                        prompt=msg,
                        sandbox=CODEX_SANDBOX,
                        timeout_segundos=CODEX_TIMEOUT,
                        modelo=CODEX_MODEL
                    )
                else:
                    result = gemini_cli_raw(msg)
            else:
                if route == "codex":
                    context = _build_context(history, summary_text)
                    result = executar_codex_cli(
                        tarefa=msg,
                        contexto=context,
                        sandbox=CODEX_SANDBOX,
                        timeout_segundos=CODEX_TIMEOUT,
                        modelo=CODEX_MODEL
                    )
                else:
                    prompt = _build_gemini_prompt(msg, history, summary_text)
                    result = gemini_cli_raw(prompt)

            print(f"BOT ({route}): {result}")

            history.append({"role": "user", "content": _trim_text(msg, HISTORY_MAX_CHARS)})
            if route == "codex":
                assistant_text = _extract_codex_final(result)
            else:
                assistant_text = result
            history.append({"role": "assistant", "content": _trim_text(assistant_text, HISTORY_MAX_CHARS)})
            history, summary_text = _rollup_history(history, summary_text)

        except KeyboardInterrupt:
            break
        except EOFError:
            break
        except Exception as e:
            print(f"ERRO: {e}")
