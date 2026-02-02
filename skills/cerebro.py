import uuid
import os
import subprocess
from pathlib import Path
from skills.util_comuns import (
    PROCESSOS_LOCK,
    PROCESSOS_ATIVOS,
    LOG_DIR,
    get_project_structure
)

def iniciar_raciocinio(query: str, context_level: str = "none") -> str:
    """Tool: Inicia raciocínio profundo e aguarda a conclusão (Síncrono)."""
    rid = str(uuid.uuid4())
    print(f"\n[🧠 BRAIN] Processando: {rid} (Context: {context_level})")
    
    ctx = ""
    if context_level == "full": ctx = f"PROJECT STRUCTURE:\n{get_project_structure()}"
    elif context_level == "medium": ctx = f"FILES: {[f.name for f in Path('.').iterdir() if f.is_file()][:50]}"
    
    # --- INJEÇÃO DINÂMICA DE SKILLS ---
    def _listar_skills_disponiveis() -> str:
        """Lê os arquivos em skills/ e gera um resumo para o Brain."""
        resumo = []
        try:
            skill_files = list(Path("skills").glob("*.py"))
            for f in skill_files:
                if f.name.startswith("_") or f.name == "util_comuns.py": continue
                
                # Leitura simplificada para extrair defs
                try:
                    content = f.read_text(encoding="utf-8")
                    import ast
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if not node.name.startswith("_") and ast.get_docstring(node):
                                doc = ast.get_docstring(node).split('\\n')[0]
                                resumo.append(f"- {node.name}(...): {doc} (em {f.name})")
                except: pass
        except Exception as e:
            return f"Error listing skills: {e}"
        return "\\n".join(resumo)

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

SPECIAL TOOL: `criar_skill(nome, codigo, descricao)`
- Use this if you need a capability that does NOT exist in the list above.
- The Hand will hot-reload and the new tool will be available in the next turn.
</available_tools>

<protocol>
1. **THINK FIRST:** Analyze the user's objective. Check if an existing tool fits.
2. **JSON COMMANDS:** To execute a tool, output a SINGLE JSON block.
   Format: {{'tool': 'function_name', 'args': {{ 'arg1': 'value' }} }}
3. **NO CHATTER:** Do not output conversational text if you are outputting a command.
4. **FILE OPS:** ALWAYS use `escrever_arquivo` to create files. NEVER use `echo > file` or `python -c write`.
</protocol>

{ctx}

<objective>
{query}
</objective>
"""

    input_log = LOG_DIR / f"{rid}_input.txt"
    output_log = LOG_DIR / f"{rid}_output.txt"
    
    try:
        input_log.write_text(sys_inst, encoding='utf-8')
        
        log_path_safe = f'\"{input_log.absolute()}\"' # Escaped quotes for the shell command
        cmd = f"type {log_path_safe} | gemini" if os.name == "nt" else f"cat {log_path_safe} | gemini"

        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8"
        )
        
        with PROCESSOS_LOCK:
            PROCESSOS_ATIVOS[rid] = {"proc": proc, "type": "brain_sync"}
        
        stdout, stderr = proc.communicate()
        
        with PROCESSOS_LOCK: PROCESSOS_ATIVOS.pop(rid, None)

        if proc.returncode != 0: 
            return f"❌ Erro no Cérebro: {stderr or f'Exit {proc.returncode}'}"
            
        output_log.write_text(stdout.strip(), encoding='utf-8')
        print(f"[🧠 BRAIN] {rid} Concluído.")
        return f"✅ CONCLUSÃO DO CÉREBRO (Log: {output_log}):\n\n{stdout.strip()}"
        
    except Exception as e:
        return f"❌ Falha crítica no Cérebro: {e}"
