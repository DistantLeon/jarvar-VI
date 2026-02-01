import sys
import os
import subprocess
import json
import time
import shlex
import logging
import atexit
import signal
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- CONFIGURAÇÃO DE VERSÃO ---
VERSION = "3.6.0"
UPDATE_DATE = "2026-02-01"

# --- SETUP INICIAL ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- HARDENING: ENCODING ---
if sys.stdout and sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass
if sys.stderr and sys.stderr.encoding != 'utf-8':
    try: sys.stderr.reconfigure(encoding='utf-8')
    except: pass

# --- CONFIGURAÇÃO ---
MODELO_ESCOLHIDO = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
API_KEY = os.getenv("GEMINI_API_KEY")
LOG_DIR = Path("jarvis_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

if not API_KEY:
    sys.exit("❌ ERRO CRÍTICO: Variável GEMINI_API_KEY não encontrada no .env")

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    sys.exit(f"❌ Erro ao iniciar Client: {e}")

# --- GESTÃO DE PROCESSOS (THREAD-SAFE) ---
PROCESSOS_LOCK = threading.Lock()
PROCESSOS_ATIVOS: Dict[str, Dict] = {} # Inclui processos de background e subprocessos de raciocínio
CEREBROS_ATIVOS: Dict[str, Any] = {}
CEREBROS_LOCK = threading.Lock()

# --- ESTRUTURA 2: GERENCIAMENTO DE CICLO DE VIDA ---
def cleanup_processos():
    """Garante encerramento recursivo e total de processos órfãos."""
    with PROCESSOS_LOCK:
        if not PROCESSOS_ATIVOS: return
        print(f"\n🧹 [SYSTEM] Encerrando {len(PROCESSOS_ATIVOS)} processos e subprocessos...")
        for pid_str, dados in list(PROCESSOS_ATIVOS.items()):
            try:
                proc = dados["proc"]
                if proc.poll() is None: # Se ainda rodando
                    proc.terminate()
                    try: proc.wait(timeout=2)
                    except: proc.kill()
                print(f"🛑 PID {pid_str} ({dados.get('type', 'cmd')}) encerrado.")
            except: pass
        PROCESSOS_ATIVOS.clear()

atexit.register(cleanup_processos)

def rotacionar_logs(dias_retencao: int = 3):
    """Remove logs mais antigos que o limite especificado."""
    print(f"♻️  [SYSTEM] Rotacionando logs (Retenção: {dias_retencao} dias)...")
    agora = datetime.now()
    removidos = 0
    for log_file in LOG_DIR.glob("*.txt"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if agora - mtime > timedelta(days=dias_retencao):
                log_file.unlink()
                removidos += 1
        except: pass
    if removidos: print(f"🧹 {removidos} logs antigos removidos.")

# --- PROTOCOLO DE SEGURANÇA ---
def validate_path(path_str: str) -> Optional[Path]:
    try:
        project_root = Path.cwd().resolve()
        target_path = (project_root / path_str).resolve()
        if project_root not in target_path.parents and project_root != target_path:
            return None
        return target_path
    except: return None

def forcar_workdir_seguro():
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    os.chdir(script_dir)
    if "windows\system32" in script_dir.lower():
        sys.exit("❌ CRÍTICO: Execução bloqueada em System32.")

forcar_workdir_seguro()

# --- REGISTRO DE FERRAMENTAS ---
FERRAMENTAS_REGISTRADAS = []
def tool(func: Callable):
    FERRAMENTAS_REGISTRADAS.append(func)
    return func

def _get_project_structure(caminho: str = ".") -> str:
    p = validate_path(caminho)
    if not p: return "❌ Erro path."
    ignorar = {'.git', 'venv', '__pycache__', '.vscode', 'node_modules', 'jarvis_logs'}
    res = []
    for root, dirs, files in os.walk(str(p)):
        dirs[:] = [d for d in dirs if d not in ignorar]
        level = root.replace(str(p), '').count(os.sep)
        indent = ' ' * 4 * level
        res.append(f"{indent}📂 {os.path.basename(root)}/")
        for f in files: res.append(f"{indent}    📄 {f}")
        if len(res) > 300: break
    return "\n".join(res)

@tool
def executar_comando_terminal(comando: str) -> str:
    """Tool: Executa comandos síncronos."""
    print(f"\n[⚙️ EXEC SYNC] {comando}")
    try:
        resultado = subprocess.run(comando, shell=True, text=True, capture_output=True, encoding='utf-8')
        output = f"EXIT: {resultado.returncode}\nSTDOUT: {resultado.stdout}\nSTDERR: {resultado.stderr}"
        return output
    except Exception as e: return f"❌ EXCEPTION: {e}"

@tool
def executar_processo_background(comando: str) -> str:
    """Tool: Inicia processos de longa duração."""
    print(f"\n[🚀 START ASYNC] {comando}")
    try:
        proc = subprocess.Popen(comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        pid = str(proc.pid)
        with PROCESSOS_LOCK:
            PROCESSOS_ATIVOS[pid] = {"proc": proc, "cmd": comando, "type": "background"}
        return f"✅ PID {pid} iniciado."
    except Exception as e: return f"❌ ERRO: {e}"

@tool
def ler_arquivo(caminho: str) -> str:
    """Tool: Lê arquivo texto."""
    p = validate_path(caminho)
    if not p or not p.exists(): return "❌ Arquivo inexistente."
    return p.read_text(encoding='utf-8')

@tool
def escrever_arquivo(caminho: str, conteudo: str) -> str:
    """Tool: Escreve/Cria arquivo."""
    p = validate_path(caminho)
    if not p: return "❌ Caminho inválido."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conteudo, encoding='utf-8')
    return f"✅ Salvo: {p}"

@tool
def listar_estrutura_projeto(caminho: str = ".") -> str:
    """Tool: Lista estrutura de pastas."""
    return _get_project_structure(caminho)

@tool
def iniciar_raciocinio(user_query: str, context_level: str = "none") -> str:
    """Tool: Inicia raciocínio profundo e aguarda a conclusão (Síncrono)."""
    rid = str(uuid.uuid4())
    print(f"\n[🧠 BRAIN] Processando: {rid} (Context: {context_level})")
    
    ctx = ""
    if context_level == "full": ctx = f"PROJECT STRUCTURE:\n{_get_project_structure()}"
    elif context_level == "medium": ctx = f"FILES: {[f.name for f in Path('.').iterdir() if f.is_file()][:50]}"
    
    sys_inst = f"""
<system_identity>
You are the BRAIN (High-Level Logic Core). 
You are running in a sandbox with NO direct OS access. 
However, you control an EXECUTOR AGENT (The Hand) who has full system access.
</system_identity>

<audience_context>
Your output is NOT read by a human. It is read by another LLM (The Hand).
The Hand is dumb but obedient. It has these tools:
- `escrever_arquivo(path, content)`
- `executar_comando_terminal(command)`
- `ler_arquivo(path)`
</audience_context>

<protocol>
1. YOU HAVE TOOLS. Use them via JSON commands.
2. TO EXECUTE: Output a JSON block. The Hand will parse and run it.
   Format: {{"tool": "function_name", "args": {{ ... }}}}
   Available Tools:
   - {{"tool": "escrever_arquivo", "args": {{"caminho": "path", "conteudo": "content"}}}}
   - {{"tool": "executar_comando_terminal", "args": {{"comando": "cmd"}}}}
   - {{"tool": "ler_arquivo", "args": {{"caminho": "path"}}}}
3. DO NOT output conversational text if you can output a command. Action over words.
4. FILE CREATION: ALWAYS use `escrever_arquivo`. DO NOT use shell redirection (>) or `python -c` to write files. It is fragile.
5. DELEGATION: {{"tool": "iniciar_raciocinio", "args": {{"user_query": "...", "context_level": "medium"}}}}
</protocol>

{ctx}

<objective>
{user_query}
</objective>
"""

    input_log = LOG_DIR / f"{rid}_input.txt"
    output_log = LOG_DIR / f"{rid}_output.txt"
    
    try:
        input_log.write_text(sys_inst, encoding='utf-8')
        
        log_path_safe = f'\"{input_log.absolute()}\"'
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

# --- BOOTSTRAP ---
rotacionar_logs()
print(f"🔌 JARVIS V{VERSION} ONLINE. Logs em: {LOG_DIR.resolve()}")

# Mapeamento de Ferramentas para Execução Manual
TOOL_MAP = {func.__name__: func for func in FERRAMENTAS_REGISTRADAS}

try:
    # AFC Desabilitado para controle manual (Loop Infinito permitido)
    chat = client.chats.create(
        model=MODELO_ESCOLHIDO,
        config={
            'tools': FERRAMENTAS_REGISTRADAS,
            'automatic_function_calling': {'disable': True}, 
            'system_instruction': f"""
# IDENTIDADE: JARVIS V{VERSION} (Orchestrator Mode)
Você é o "HAND" (Executor/Ponte). Sua única função é conectar o Usuário ao "BRAIN" (Gemini CLI).

# PROTOCOLO DE CONEXÃO (CRÍTICO)
1. **PASSTHROUGH INTEGRAL:** Toda e qualquer mensagem do usuário deve ser encaminhada ao Cérebro via `iniciar_raciocinio`.
2. **FLUXO SÍNCRONO:** A ferramenta `iniciar_raciocinio` agora aguarda e retorna a resposta completa.
   - Chame `iniciar_raciocinio`.
   - Receba a resposta imediata.
   - **EXECUÇÃO:** Se a resposta contiver JSON (ex: {{"tool": ...}}), EXECUTE A FERRAMENTA IMEDIATAMENTE.
3. **RESPOSTA:** Repasse a resposta textual do Cérebro ao usuário.

# FERRAMENTAS EXECUTIVAS
- Use `listar_estrutura_projeto` e `ler_arquivo` para alimentar o contexto do Cérebro.
- Use `escrever_arquivo` e `executar_comando_terminal` APENAS sob orientação explícita do Cérebro.
- Se o Cérebro pedir para "falar com o outro cérebro", inicie um novo processo de raciocínio com o contexto necessário.
"""
        }
    )
except Exception as e: sys.exit(f"❌ Falha chat: {e}")

# --- MAIN LOOP (MANUAL TOOL EXECUTION) ---
while True:
    try:
        msg = input("\n👤 CMD: ")
        if msg.strip().lower() in ["exit", "sair", "quit"]:
            break
        
        # Envia mensagem inicial
        response = chat.send_message(msg)
        
        # Loop de Ferramentas (Sem limite hardcoded)
        while response.function_calls:
            parts = []
            print(f"🤖: [Executando {len(response.function_calls)} ferramentas...]")
            
            for fc in response.function_calls:
                fn_name = fc.name
                fn_args = fc.args
                
                if fn_name in TOOL_MAP:
                    try:
                        # Executa a função
                        result = TOOL_MAP[fn_name](**fn_args)
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = f"Error: Tool '{fn_name}' not found."
                
                # Cria a resposta da ferramenta
                parts.append(types.Part.from_function_response(
                    name=fn_name,
                    response={"result": result}
                ))
            
            # Envia os resultados de volta para o modelo
            response = chat.send_message(parts)

        # Exibe resposta final (Texto)
        if response.text:
            print(f"🤖: {response.text}")

    except KeyboardInterrupt:
        break
    except EOFError:
        break
    except Exception as e:
        print(f"⚠️ ERRO: {e}")
