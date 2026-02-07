import os
import subprocess
import uuid
from pathlib import Path
from typing import List

from skills.util_comuns import PROCESSOS_ATIVOS, PROCESSOS_LOCK, LOG_DIR

_MAX_OUTPUT_CHARS = 20000


def _truncate(text: str, max_chars: int = _MAX_OUTPUT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[...TRUNCATED. TOTAL {len(text)} CHARS...]"


def _codex_command_candidates() -> List[str]:
    if os.name == "nt":
        return ["codex.cmd", "codex"]
    return ["codex"]


def _build_codex_prompt(tarefa: str, contexto: str) -> str:
    sections = [
        "You are Codex CLI acting as an execution specialist for Jarvis.",
        "Perform the task in this repository, run commands when needed, and edit files directly.",
        "Return a concise final report with: changed files, commands executed, and outcome.",
        f"PRIMARY TASK:\n{tarefa.strip()}",
    ]
    if contexto.strip():
        sections.append(f"EXTRA CONTEXT:\n{contexto.strip()}")
    return "\n\n".join(sections)


def descrever_capacidades_codex() -> str:
    """
    Tool: Retorna um resumo operacional das capacidades do Codex CLI para delegacao.
    """
    return (
        "Codex CLI (delegated executor) capabilities:\n"
        "- Edits files directly in the current repository.\n"
        "- Runs terminal commands, tests, and build steps.\n"
        "- Applies multi-file code changes with reasoning over local context.\n"
        "- Can run in fresh non-interactive sessions via 'codex exec'.\n"
        "- For this integration, each delegation starts a new session by default,\n"
        "  which resets Codex context window while Gemini keeps orchestration context."
    )


def verificar_codex_cli() -> str:
    """
    Tool: Verifica disponibilidade do Codex CLI e retorna a versao detectada.
    """
    for command in _codex_command_candidates():
        try:
            result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            output = (result.stdout or result.stderr).strip()
            if result.returncode == 0 and output:
                return f"Codex CLI online: {output}"
            return f"Codex CLI command found ({command}) but returned exit {result.returncode}."
        except FileNotFoundError:
            continue
        except Exception as exc:
            return f"Codex CLI check failed: {exc}"
    return "Codex CLI not found in PATH."


def _run_codex_cli(
    prompt: str,
    sandbox: str = "workspace-write",
    timeout_segundos: int = 900,
    modelo: str = "",
) -> str:
    sandboxes_validos = {"read-only", "workspace-write", "danger-full-access"}
    if sandbox not in sandboxes_validos:
        return (
            "Sandbox invalido. Use um destes valores: "
            "read-only, workspace-write, danger-full-access."
        )

    if not prompt or not prompt.strip():
        return "O prompt para o Codex nao pode estar vazio."

    timeout_segundos = max(30, min(int(timeout_segundos), 3600))
    rid = str(uuid.uuid4())

    input_log = LOG_DIR / f"{rid}_codex_input.txt"
    output_log = LOG_DIR / f"{rid}_codex_output.txt"
    last_message_log = LOG_DIR / f"{rid}_codex_last_message.txt"
    input_log.write_text(prompt, encoding="utf-8")

    proc = None
    command_used = ""

    for command in _codex_command_candidates():
        cmd = [
            command,
            "exec",
            "--full-auto",
            "--sandbox",
            sandbox,
            "--color",
            "never",
            "-C",
            str(Path.cwd()),
            "--output-last-message",
            str(last_message_log),
            "-",
        ]
        if modelo.strip():
            cmd[2:2] = ["--model", modelo.strip()]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=os.environ.copy(),
            )
            command_used = command
            break
        except FileNotFoundError:
            continue
        except Exception as exc:
            return f"Falha ao iniciar Codex CLI: {exc}"

    if proc is None:
        return "Codex CLI nao encontrado no PATH (tentativas: codex/codex.cmd)."

    with PROCESSOS_LOCK:
        PROCESSOS_ATIVOS[rid] = {"proc": proc, "type": "codex_exec"}

    try:
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout_segundos)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        with PROCESSOS_LOCK:
            PROCESSOS_ATIVOS.pop(rid, None)
        timeout_report = (
            f"Codex CLI timeout apos {timeout_segundos}s.\n\n"
            f"STDOUT:\n{_truncate((stdout or '').strip())}\n\n"
            f"STDERR:\n{_truncate((stderr or '').strip())}"
        )
        output_log.write_text(timeout_report, encoding="utf-8")
        return timeout_report
    finally:
        with PROCESSOS_LOCK:
            PROCESSOS_ATIVOS.pop(rid, None)

    stdout_clean = (stdout or "").strip()
    stderr_clean = (stderr or "").strip()
    final_message = ""

    if last_message_log.exists():
        try:
            final_message = last_message_log.read_text(encoding="utf-8").strip()
        except Exception:
            final_message = ""

    report_parts = []
    if proc.returncode == 0:
        report_parts.append(f"Codex CLI execution finished successfully via '{command_used}'.")
    else:
        report_parts.append(f"Codex CLI failed with exit code {proc.returncode}.")

    if final_message:
        report_parts.append(f"FINAL MESSAGE:\n{_truncate(final_message)}")
    if stdout_clean:
        report_parts.append(f"STDOUT:\n{_truncate(stdout_clean)}")
    if stderr_clean:
        report_parts.append(f"STDERR:\n{_truncate(stderr_clean)}")

    if len(report_parts) == 1:
        report_parts.append("Codex returned no output.")

    report_parts.append(
        f"LOGS: input={input_log.name}, output={output_log.name}, last={last_message_log.name}"
    )

    final_report = "\n\n".join(report_parts)
    output_log.write_text(final_report, encoding="utf-8")
    return final_report


def executar_codex_cli(
    tarefa: str,
    contexto: str = "",
    sandbox: str = "workspace-write",
    timeout_segundos: int = 900,
    modelo: str = "",
) -> str:
    """
    Tool: Delega uma tarefa para o Codex CLI em modo nao interativo (sessao nova por chamada).
    Args:
        tarefa: Objetivo principal para o Codex executar.
        contexto: Contexto adicional e restricoes.
        sandbox: read-only, workspace-write, ou danger-full-access.
        timeout_segundos: Timeout total da execucao.
        modelo: Modelo opcional para o Codex CLI (ex: gpt-5-codex).
    """
    if not tarefa or not tarefa.strip():
        return "A tarefa para o Codex nao pode estar vazia."
    prompt = _build_codex_prompt(tarefa, contexto)
    return _run_codex_cli(
        prompt=prompt,
        sandbox=sandbox,
        timeout_segundos=timeout_segundos,
        modelo=modelo,
    )


def executar_codex_cli_raw(
    prompt: str,
    sandbox: str = "workspace-write",
    timeout_segundos: int = 900,
    modelo: str = "",
) -> str:
    """
    Tool: Executa o Codex CLI com prompt bruto (pass-through), sem preambulo.
    Args:
        prompt: Texto bruto a ser enviado ao Codex CLI.
        sandbox: read-only, workspace-write, ou danger-full-access.
        timeout_segundos: Timeout total da execucao.
        modelo: Modelo opcional para o Codex CLI (ex: gpt-5-codex).
    """
    return _run_codex_cli(
        prompt=prompt,
        sandbox=sandbox,
        timeout_segundos=timeout_segundos,
        modelo=modelo,
    )
