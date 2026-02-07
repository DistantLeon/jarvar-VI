import uuid
import os
import re
import subprocess
from pathlib import Path
from skills.util_comuns import (
    PROCESSOS_LOCK,
    PROCESSOS_ATIVOS,
    LOG_DIR,
    get_project_structure
)


def _comando_direto_por_texto(query: str) -> str | None:
    """
    Detecta pedidos diretos do tipo "Use a skill X ..." e devolve JSON executavel.
    """
    if not query:
        return None

    pattern = (
        r"(?i)\b(use a skill|use the skill|use a tool|use a ferramenta|"
        r"use a habilidade|use o skill|use a skill)\s+([a-zA-Z0-9_]+)"
    )
    match = re.search(pattern, query)
    if not match:
        return None

    tool_name = match.group(2)
    args = {}

    texto_match = re.search(r"(?i)\b(texto|text)\s*['\"]([^'\"]+)['\"]", query)
    if texto_match:
        args["texto"] = texto_match.group(2)

    return (
        "```json\n"
        "{\n"
        f"  \"tool\": \"{tool_name}\",\n"
        f"  \"args\": {args}\n"
        "}\n"
        "```"
    )


def _executar_gemini_cli(prompt: str, rid: str, proc_type: str) -> str:
    input_log = LOG_DIR / f"{rid}_input.txt"
    output_log = LOG_DIR / f"{rid}_output.txt"
    input_log.write_text(prompt, encoding="utf-8")

    # ==================================================================================
    # CRITICAL ARCHITECTURAL COMPONENT: GEMINI CLI SUBPROCESS
    #
    # DO NOT REPLACE THIS BLOCK WITH DIRECT SDK CALLS (google.genai).
    # ==================================================================================

    command = ["gemini"]
    if os.name == "nt":
        command = ["gemini.cmd"]

    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=os.environ.copy()
    )

    with PROCESSOS_LOCK:
        PROCESSOS_ATIVOS[rid] = {"proc": proc, "type": proc_type}

    stdout, stderr = proc.communicate(input=prompt)

    with PROCESSOS_LOCK:
        PROCESSOS_ATIVOS.pop(rid, None)

    if proc.returncode != 0:
        return f"Erro no Gemini CLI: {stderr or f'Exit {proc.returncode}'}"

    output_log.write_text(stdout.strip(), encoding="utf-8")
    return stdout.strip()


def gemini_cli_raw(prompt: str) -> str:
    """
    Tool: Executa o Gemini CLI com prompt bruto (pass-through), sem protocolo JSON.
    """
    rid = str(uuid.uuid4())
    print(f"\n[BRAIN] Gemini raw: {rid}")
    try:
        output = _executar_gemini_cli(prompt=prompt, rid=rid, proc_type="brain_raw")
        print(f"[BRAIN] Gemini raw concluido: {rid}")
        return output
    except Exception as e:
        return f"Falha critica no Gemini CLI: {e}"


def iniciar_raciocinio(query: str, context_level: str = "none") -> str:
    """Tool: Inicia raciocinio profundo e aguarda a conclusao (Sincrono via Gemini CLI)."""
    rid = str(uuid.uuid4())
    print(f"\n[BRAIN] Processando: {rid} (Context: {context_level})")
    comando_direto = _comando_direto_por_texto(query)
    if comando_direto:
        return comando_direto

    ctx = ""
    if context_level == "full":
        ctx = f"PROJECT STRUCTURE:\n{get_project_structure()}"
    elif context_level == "medium":
        ctx = f"FILES: {[f.name for f in Path('.').iterdir() if f.is_file()][:50]}"

    # --- INJECAO DINAMICA DE SKILLS ---
    def _listar_skills_disponiveis() -> str:
        """Le os arquivos em skills/ e gera um resumo para o Brain."""
        resumo = []
        try:
            skill_files = list(Path("skills").glob("*.py"))
            for f in skill_files:
                if f.name.startswith("_") or f.name == "util_comuns.py":
                    continue

                # Leitura simplificada para extrair defs
                try:
                    content = f.read_text(encoding="utf-8")
                    import ast
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if not node.name.startswith("_") and ast.get_docstring(node):
                                doc = ast.get_docstring(node).split("\n")[0]
                                resumo.append(f"- {node.name}(...): {doc} (em {f.name})")
                except:
                    pass
        except Exception as e:
            return f"Error listing skills: {e}"
        return "\n".join(resumo)

    try:
        skills_summary = _listar_skills_disponiveis()

        sys_inst = f"""
<system_identity>
You are the BRAIN (High-Level Logic Core) of the Jarvis Ecosystem.
You operate in a sandbox with NO direct OS access.
You control an EXECUTOR AGENT (The Hand) who has full system access and a suite of specialized Python tools.
</system_identity>

<audience_context>
Your output is NOT read by a human. It is read by another LLM (The Hand).
The Hand is dumb but obedient. It will execute exactly what you command in JSON.
</audience_context>

<available_tools>
The Hand has the following tools loaded and ready to use.
PREFER using these tools over raw shell commands whenever possible:

{skills_summary}

SPECIAL TOOL: `executar_codex_cli(tarefa, contexto, sandbox, timeout_segundos, modelo)`
- Use this for code-heavy execution: multi-file edits, refactors, test/debug loops, and terminal-heavy implementation.
- Each call creates a NEW Codex session via `codex exec` (fresh context window every call).
- You (Gemini) are the ORCHESTRATOR. Keep global plan/context on your side and pass focused instructions to Codex.

SPECIAL TOOL: `criar_skill(nome, codigo, descricao)`
- Use this if a capability does NOT exist in the loaded tools.
- The Hand will hot-reload and the new tool will be available in the next turn.
</available_tools>

<protocol>
0. ONE-SHOT TOOLING: You only get ONE tool call per Brain turn. Choose the final action, not exploration.
1. THINK FIRST: Analyze the user's objective and choose the best tool strategy.
2. ORCHESTRATE WITH CODEX WHEN NEEDED.
3. JSON EXECUTION: To execute a tool, output a JSON block inside markdown code fences.
4. STRICT OUTPUT: If you want to execute a tool: output ONLY the JSON block.
5. DIRECT TOOL REQUESTS: If the user asks to run a specific tool, call it directly.
6. FILE OPS: ALWAYS use escrever_arquivo to create files.
</protocol>

{ctx}

<objective>
{query}
</objective>
"""

        output = _executar_gemini_cli(prompt=sys_inst, rid=rid, proc_type="brain_sync")
        if output.startswith("Erro no Gemini CLI"):
            return output
        print(f"[BRAIN] {rid} Concluido.")
        return f"CONCLUSAO DO CEREBRO (Log: {LOG_DIR / f'{rid}_output.txt'}):\n\n{output}"

    except Exception as e:
        print(f"DEBUG EXCEPTION: {e}")
        return f"Falha critica no Cerebro: {e}"
