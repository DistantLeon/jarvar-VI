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
import importlib.util
import inspect
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- CONFIGURAÇÃO DE VERSÃO ---
VERSION = "3.7.0" # Bumped for Dynamic Skills
UPDATE_DATE = "2026-02-02"

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
SKILLS_DIR = Path("skills")
LOG_DIR.mkdir(parents=True, exist_ok=True)

if not API_KEY:
    sys.exit("❌ ERRO CRÍTICO: Variável GEMINI_API_KEY não encontrada no .env")

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    sys.exit(f"❌ Erro ao iniciar Client: {e}")

# --- GESTÃO DE PROCESSOS (THREAD-SAFE) ---
PROCESSOS_LOCK = threading.Lock()
PROCESSOS_ATIVOS: Dict[str, Dict] = {} 
CEREBROS_ATIVOS: Dict[str, Any] = {}
CEREBROS_LOCK = threading.Lock()

# --- GESTÃO DE DIRETÓRIOS E SKILLS ---
def ensure_skills_dir():
    """Garante que a pasta skills existe e é um pacote Python."""
    if not SKILLS_DIR.exists():
        SKILLS_DIR.mkdir(parents=True)
        print("📁 Diretório 'skills' criado.")
    
    init_file = SKILLS_DIR / "__init__.py"
    if not init_file.exists():
        init_file.touch()

def carregar_ferramentas_dinamicas() -> List[Callable]:
    """
    Carrega ferramentas dinamicamente da pasta skills/.
    Critérios: Funções com docstrings e Type Hints.
    """
    ensure_skills_dir()
    dynamic_tools = []
    
    print(f"🔍 Buscando skills em {SKILLS_DIR.resolve()}...")
    
    for py_file in SKILLS_DIR.glob("*.py"):
        if py_file.name.startswith("_"): continue
        
        module_name = py_file.stem
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod # Registra no sys.modules
                spec.loader.exec_module(mod)
                
                # Introspecção para encontrar funções válidas
                for name, func in inspect.getmembers(mod, inspect.isfunction):
                    if func.__module__ == module_name: # Apenas funções definidas no arquivo
                        if func.__doc__ and func.__annotations__:
                            dynamic_tools.append(func)
                            print(f"   + Skill carregada: {name}")
        except Exception as e:
            print(f"   ⚠️ Falha ao carregar {py_file.name}: {e}")
            
    return dynamic_tools

# --- CLEANUP ---
def cleanup_processos():
    """Garante encerramento recursivo e total de processos órfãos."""
    with PROCESSOS_LOCK:
        if not PROCESSOS_ATIVOS: return
        print(f"\n🧹 [SYSTEM] Encerrando {len(PROCESSOS_ATIVOS)} processos e subprocessos...")
        for pid_str, dados in list(PROCESSOS_ATIVOS.items()):
            try:
                proc = dados["proc"]
                if proc.poll() is None: 
                    proc.terminate()
                    try: proc.wait(timeout=2)
                    except: proc.kill()
                print(f"🛑 PID {pid_str} ({dados.get('type', 'cmd')}) encerrado.")
            except: pass
        PROCESSOS_ATIVOS.clear()

atexit.register(cleanup_processos)

def rotacionar_logs(dias_retencao: int = 3):
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
        # Permite acesso a subpastas
        if project_root not in target_path.parents and project_root != target_path:
            return None
        return target_path
    except: return None

def forcar_workdir_seguro():
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    os.chdir(script_dir)
    if r"windows\system32" in script_dir.lower():
        sys.exit("❌ CRÍTICO: Execução bloqueada em System32.")

forcar_workdir_seguro()

# --- REGISTRO DE FERRAMENTAS BASE ---
FERRAMENTAS_BASE = []
def tool(func: Callable):
    FERRAMENTAS_BASE.append(func)
    return func

def _get_project_structure(caminho: str = ".") -> str:
    p = validate_path(caminho)
    if not p: return "❌ Erro path."
    ignorar = {'.git', 'venv', '__pycache__', '.vscode', 'node_modules', 'jarvis_logs', '__init__.py'}
    res = []
    for root, dirs, files in os.walk(str(p)):
        dirs[:] = [d for d in dirs if d not in ignorar]
        level = root.replace(str(p), '').count(os.sep)
        indent = ' ' * 4 * level
        res.append(f"{indent}📂 {os.path.basename(root)}/")
        for f in files: 
            if f.endswith('.py') or f.endswith('.md') or f.endswith('.txt') or f.endswith('.json'):
                res.append(f"{indent}    📄 {f}")
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
def criar_skill(nome_funcao: str, codigo_python: str, descricao: str) -> str:
    """
    META-TOOL: Cria uma nova habilidade (tool) Python dinamicamente.
    Args:
        nome_funcao: Nome da função (ex: 'calcular_hash').
        codigo_python: Código fonte completo (deve incluir imports).
        descricao: Descrição do propósito da ferramenta.
    """
    # 1. Sanitização básica
    nome_safe = "".join([c for c in nome_funcao if c.isalnum() or c == "_"])
    if not nome_safe: return "❌ Nome de função inválido."
    
    file_path = SKILLS_DIR / f"{nome_safe}.py"
    
    # 2. Salvar arquivo
    try:
        ensure_skills_dir()
        file_path.write_text(codigo_python, encoding='utf-8')
        print(f"✨ NOVA SKILL CRIADA: {nome_safe}")
        return f"✅ Skill '{nome_safe}' criada em {file_path}. RECARREGAMENTO_SOLICITADO."
    except Exception as e:
        return f"❌ Erro ao criar skill: {e}"

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
- `criar_skill(nome_funcao, codigo_python, descricao)` -> USE ISSO PARA EXPANDIR O SISTEMA.
</audience_context>

<protocol>
1. YOU HAVE TOOLS. Use them via JSON commands.
2. TO EXECUTE: Output a JSON block. The Hand will parse and run it.
   Format: {{'tool': 'function_name', 'args': {{ ... }}}}
3. DO NOT output conversational text if you can output a command. Action over words.
4. FILE CREATION: ALWAYS use `escrever_arquivo`. DO NOT use shell redirection (>) or `python -c` to write files. It is fragile.
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

# --- CHAT LIFECYCLE ---
def iniciar_sessao_chat(ferramentas: List[Callable], history: List = []):
    """
    Cria ou recria a sessão de chat com as ferramentas especificadas.
    Preserva o histórico se fornecido.
    """
    try:
        # Mescla ferramentas base + dinâmicas
        return client.chats.create(
            model=MODELO_ESCOLHIDO,
            history=history,
            config={
                'tools': ferramentas,
                'automatic_function_calling': {'disable': True}, 
                'system_instruction': f"""
# IDENTIDADE: JARVIS V{VERSION} (Dynamic Orchestrator)
Você é o "HAND" (Executor/Ponte). Sua função é conectar o Usuário ao "BRAIN".

# MEMÓRIA PERSISTENTE (DOSSIER)
Você tem acesso a uma Memória Persistente em `/memoria`.
- SEMPRE consulte `user_preferences` no início de uma sessão se precisar saber sobre o usuário.
- Use `memorizar` para salvar fatos importantes (decisões de projeto, gostos/desgostos do usuário).
- Use `consultar_memoria` antes de dizer que não sabe algo sobre o passado.
- Use `listar_topicos` para ver o que você já sabe.

# DINÂMICA DE SKILLS (IMPORTANTE)
Você tem acesso a ferramentas NATIVAS (File I/O, Terminal) e DINÂMICAS (Skills).
Seu sistema permite que você CRIE suas próprias ferramentas usando `criar_skill`.
Se o BRAIN solicitar a criação de uma ferramenta, use `criar_skill` imediatamente.

# PROTOCOLO
1. **PASSTHROUGH:** Encaminhe mensagens do usuário para `iniciar_raciocinio`.
2. **EXECUÇÃO:** Execute as ferramentas solicitadas pelo Brain (JSON) ou por você mesmo.
3. **RESPOSTA:** Repasse a resposta textual final.
"""
            }
        )
    except Exception as e:
        sys.exit(f"❌ Falha ao iniciar chat: {e}")

# --- BOOTSTRAP (GLOBAL SCOPE FOR IMPORTS) ---
rotacionar_logs()
print(f"🔌 JARVIS V{VERSION} ONLINE. Logs em: {LOG_DIR.resolve()}")
ensure_skills_dir()

# Carregamento Inicial
FERRAMENTAS_DINAMICAS = carregar_ferramentas_dinamicas()
TODAS_FERRAMENTAS = FERRAMENTAS_BASE + FERRAMENTAS_DINAMICAS
TOOL_MAP = {func.__name__: func for func in TODAS_FERRAMENTAS}

# --- MAIN EXECUTION (ONLY IF RUN DIRECTLY) ---
if __name__ == "__main__":
    chat = iniciar_sessao_chat(TODAS_FERRAMENTAS)

    # --- MAIN LOOP ---
    while True:
        try:
            msg = input("\n👤 CMD: ")
            if msg.strip().lower() in ["exit", "sair", "quit"]:
                break
            
            # Envia mensagem inicial
            response = chat.send_message(msg)
            
            reload_needed = False
            
            # Loop de Ferramentas
            while response.function_calls:
                parts = []
                print(f"🤖: [Executando {len(response.function_calls)} ferramentas...]")
                
                for fc in response.function_calls:
                    fn_name = fc.name
                    fn_args = fc.args
                    
                    # Execução
                    if fn_name in TOOL_MAP:
                        try:
                            result = TOOL_MAP[fn_name](**fn_args)
                            # Verifica flag de recarregamento
                            if fn_name == "criar_skill" and "RECARREGAMENTO_SOLICITADO" in str(result):
                                reload_needed = True
                        except Exception as e:
                            result = f"Error: {e}"
                    else:
                        result = f"Error: Tool '{fn_name}' not found."
                    
                    # Resposta da ferramenta
                    parts.append(types.Part.from_function_response(
                        name=fn_name,
                        response={"result": result}
                    ))
                
                # Envia resultados de volta (completa o turno atual)
                response = chat.send_message(parts)

            # Exibe resposta final
            if response.text:
                print(f"🤖: {response.text}")

            # HOT RELOAD (Se necessário, ocorre APÓS o turno completo para manter consistência)
            if reload_needed:
                print("\n♻️  [SYSTEM] Nova skill detectada. Recarregando Matrix...")
                FERRAMENTAS_DINAMICAS = carregar_ferramentas_dinamicas()
                TODAS_FERRAMENTAS = FERRAMENTAS_BASE + FERRAMENTAS_DINAMICAS
                TOOL_MAP = {func.__name__: func for func in TODAS_FERRAMENTAS}
                
                # Preserva histórico e recria sessão
                historico_atual = chat.history
                chat = iniciar_sessao_chat(TODAS_FERRAMENTAS, history=historico_atual)
                print("🚀 Sistema atualizado com sucesso. Próxima interação terá novas skills.")

        except KeyboardInterrupt:
            break
        except EOFError:
            break
        except Exception as e:
            print(f"⚠️ ERRO: {e}")