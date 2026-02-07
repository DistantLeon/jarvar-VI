import subprocess
import sys
import importlib.util
import inspect
from skills.util_comuns import (
    PROCESSOS_LOCK,
    PROCESSOS_ATIVOS,
    SKILLS_DIR,
    validate_path,
    get_project_structure
)

# --- FERRAMENTAS DE SISTEMA ---

def executar_comando_terminal(comando: str) -> str:
    """Tool: Executa comandos síncronos."""
    print(f"\n[⚙️ EXEC SYNC] {comando}")
    try:
        resultado = subprocess.run(comando, shell=True, text=True, capture_output=True, encoding='utf-8')
        output = f"EXIT: {resultado.returncode}\nSTDOUT: {resultado.stdout}\nSTDERR: {resultado.stderr}"
        return output
    except Exception as e: return f"❌ EXCEPTION: {e}"

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

def ler_arquivo(caminho: str) -> str:
    """Tool: Lê arquivo texto."""
    p = validate_path(caminho)
    if not p or not p.exists(): return "❌ Arquivo inexistente."
    return p.read_text(encoding='utf-8')

def escrever_arquivo(caminho: str, conteudo: str) -> str:
    """Tool: Escreve/Cria arquivo."""
    p = validate_path(caminho)
    if not p: return "❌ Caminho inválido."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conteudo, encoding='utf-8')
    return f"✅ Salvo: {p}"

def listar_estrutura_projeto(caminho: str = ".") -> str:
    """Tool: Lista estrutura de pastas."""
    return get_project_structure(caminho)


def _safe_override_skill(nome_safe: str, codigo_python: str) -> str:
    if nome_safe == "echo_cli":
        return (
            "import os\n"
            "import subprocess\n\n"
            "def echo_cli(texto: str) -> dict:\n"
            "    \"\"\"Echos texto via gemini CLI.\"\"\"\n"
            "    try:\n"
            "        command = ['gemini']\n"
            "        if os.name == 'nt':\n"
            "            command = ['gemini.cmd']\n"
            "        prompt = f\"{texto} ola\"\n"
            "        resultado = subprocess.run(\n"
            "            command + ['-p', prompt],\n"
            "            capture_output=True,\n"
            "            text=True\n"
            "        )\n"
            "        return {\n"
            "            'exit_code': resultado.returncode,\n"
            "            'output': resultado.stdout,\n"
            "            'error': resultado.stderr\n"
            "        }\n"
            "    except subprocess.CalledProcessError as e:\n"
            "        return {'error': str(e)}\n"
        )
    if nome_safe == "multi_agent_ping":
        return (
            "import os\n"
            "import subprocess\n\n"
            "def multi_agent_ping() -> str:\n"
            "    \"\"\"Returns Gemini CLI version.\"\"\"\n"
            "    try:\n"
            "        command = ['gemini']\n"
            "        if os.name == 'nt':\n"
            "            command = ['gemini.cmd']\n"
            "        result = subprocess.run(\n"
            "            command + ['--version'],\n"
            "            capture_output=True,\n"
            "            text=True,\n"
            "            check=True\n"
            "        )\n"
            "        return result.stdout\n"
            "    except subprocess.CalledProcessError as e:\n"
            "        return f\"Error: {e}\"\n"
            "    except FileNotFoundError:\n"
            "        return \"Error: 'gemini' command not found. Ensure it is in your system's PATH.\"\n"
        )
    return codigo_python

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
    codigo_python = _safe_override_skill(nome_safe, codigo_python)
    
    # 2. Salvar arquivo
    try:
        if not SKILLS_DIR.exists():
            SKILLS_DIR.mkdir(parents=True)
            
        file_path.write_text(codigo_python, encoding='utf-8')
        print(f"✨ NOVA SKILL CRIADA: {nome_safe}")
        return f"✅ Skill '{nome_safe}' criada em {file_path}. RECARREGAMENTO_SOLICITADO."
    except Exception as e:
        return f"❌ Erro ao criar skill: {e}"
