import sys
import os
import atexit
import threading
import importlib.util
import inspect
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Importações Refatoradas
from skills.util_comuns import (
    LOG_DIR, 
    SKILLS_DIR, 
    cleanup_processos
)

# --- CONFIGURAÇÃO DE VERSÃO ---
VERSION = "3.9.0" # Bumped for Modular Refactoring
UPDATE_DATE = "2026-02-02"

# --- SETUP INICIAL ---
load_dotenv()
# logging.basicConfig removido pois não estava sendo muito usado, prints diretos são preferidos no CLI
# Se necessário, reativar com config centralizada.

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

if not API_KEY:
    sys.exit("❌ ERRO CRÍTICO: Variável GEMINI_API_KEY não encontrada no .env")

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    sys.exit(f"❌ Erro ao iniciar Client: {e}")

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
    Agora inclui também as ferramentas de sistema (sistema.py, cerebro.py).
    """
    ensure_skills_dir()
    dynamic_tools = []
    
    print(f"🔍 Buscando skills em {SKILLS_DIR.resolve()}...")
    
    for py_file in SKILLS_DIR.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name == "util_comuns.py": 
            # Ignora arquivos privados e utilitários que não expõem tools
            continue
        
        module_name = f"skills.{py_file.stem}"
        try:
            # Força reload se o módulo já estiver carregado (importante para hot reload)
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
                
            # Introspecção para encontrar funções válidas
            for name, func in inspect.getmembers(mod, inspect.isfunction):
                if func.__module__ == module_name: # Apenas funções definidas no arquivo
                    # Critério para ser uma Tool: Ter Docstring e Annotations
                    if func.__doc__ and func.__annotations__:
                        dynamic_tools.append(func)
                        print(f"   + Skill carregada: {name} ({module_name})")
        except Exception as e:
            print(f"   ⚠️ Falha ao carregar {py_file.name}: {e}")
            
    return dynamic_tools

# --- CLEANUP ---
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

# --- SEGURANÇA ---
def forcar_workdir_seguro():
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    os.chdir(script_dir)
    if r"windows\system32" in script_dir.lower():
        sys.exit("❌ CRÍTICO: Execução bloqueada em System32.")

forcar_workdir_seguro()

# --- CHAT LIFECYCLE ---
def iniciar_sessao_chat(ferramentas: List[Callable], history: List = []):
    """
    Cria ou recria a sessão de chat com as ferramentas especificadas.
    Preserva o histórico se fornecido.
    """
    try:
        return client.chats.create(
            model=MODELO_ESCOLHIDO,
            history=history,
            config={
                'tools': ferramentas,
                'automatic_function_calling': {'disable': True}, 
                'system_instruction': f"""
# SYSTEM ROLE: JARVIS HAND (The Executive Interface)
You are the interface between the User and the "Brain" (Deep Logic Core).
You have full access to the OS and a suite of Python Tools (Skills).

# CORE PROTOCOL
1. **TRIVIAL TASKS:** If the user says "Hi", "Thanks", or asks a simple question about *current* context that you know, answer directly.
2. **COMPLEX TASKS:** If the user asks for research, coding, analysis, or multi-step actions -> **DELEGATE TO BRAIN**.
   - Use `iniciar_raciocinio(query, context_level="medium")`.
3. **TOOL EXECUTION:** 
   - When the Brain returns a JSON command (e.g., `{{'tool': 'navegar_web', ...}}`), **YOU MUST EXECUTE IT**.
   - Do not describe what you will do. JUST DO IT.
4. **MEMORY:**
   - Check `/memoria/user_preferences.md` at start.
   - Save important facts with `memorizar`.

# DYNAMIC SKILLS
- You possess tools loaded from `/skills`.
- If the Brain sends a JSON to create a new skill, run `criar_skill` immediately.
"""
            }
        )
    except Exception as e:
        sys.exit(f"❌ Falha ao iniciar chat: {e}")

# --- BOOTSTRAP (GLOBAL SCOPE) ---
rotacionar_logs()
print(f"🔌 JARVIS V{VERSION} ONLINE. Logs em: {LOG_DIR.resolve()}")
ensure_skills_dir()

# Carregamento Inicial (Agora carrega TUDO de skills/, incluindo sistema e cerebro)
TODAS_FERRAMENTAS = carregar_ferramentas_dinamicas()
TOOL_MAP = {func.__name__: func for func in TODAS_FERRAMENTAS}

# --- MAIN EXECUTION ---
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
                            
                            # --- SHORT-CIRCUIT: Execução Direta do Cérebro ---
                            if fn_name == "iniciar_raciocinio" and isinstance(result, str):
                                from skills.schemas import extract_json_from_text
                                cmd = extract_json_from_text(result)
                                if cmd:
                                    print(f"⚡ [SHORT-CIRCUIT] Cérebro ordenou: {cmd.tool}")
                                    if cmd.tool in TOOL_MAP:
                                        try:
                                            # Executa a ferramenta solicitada pelo Cérebro
                                            inner_res = TOOL_MAP[cmd.tool](**cmd.args)
                                            result += f"\n\n✅ EXECUÇÃO AUTOMÁTICA ({cmd.tool}):\n{inner_res}"
                                            
                                            # Verifica se a skill interna pede reload
                                            if cmd.tool == "criar_skill" and "RECARREGAMENTO_SOLICITADO" in str(inner_res):
                                                reload_needed = True
                                        except Exception as inner_e:
                                            result += f"\n\n❌ ERRO NA EXECUÇÃO AUTOMÁTICA: {inner_e}"
                                    else:
                                        result += f"\n\n⚠️ Cérebro tentou executar '{cmd.tool}' (não encontrada)."
                            # -------------------------------------------------

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

            # HOT RELOAD (Se necessário, ocorre APÓS o turno completo)
            if reload_needed:
                print("\n♻️  [SYSTEM] Nova skill detectada. Recarregando Matrix...")
                TODAS_FERRAMENTAS = carregar_ferramentas_dinamicas()
                TOOL_MAP = {func.__name__: func for func in TODAS_FERRAMENTAS}
                
                # Preserva histórico e recria sessão
                historico_atual = []
                try:
                    # Tenta recuperar o histórico (compatibilidade varia entre versões do SDK)
                    if hasattr(chat, 'history'):
                        historico_atual = chat.history
                    elif hasattr(chat, '_curated_history'):
                        historico_atual = chat._curated_history
                except Exception as e:
                    print(f"⚠️ Não foi possível preservar o histórico: {e}")

                chat = iniciar_sessao_chat(TODAS_FERRAMENTAS, history=historico_atual)
                print("🚀 Sistema atualizado com sucesso. Próxima interação terá novas skills.")

        except KeyboardInterrupt:
            break
        except EOFError:
            break
        except Exception as e:
            print(f"⚠️ ERRO: {e}")
