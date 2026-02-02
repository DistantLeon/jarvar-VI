import os
import sys
import threading
from pathlib import Path
from typing import Dict, Optional, Any

# --- CONFIGURAÇÃO ---
# Recriamos as constantes aqui para serem usadas pelos módulos
LOG_DIR = Path("jarvis_logs")
SKILLS_DIR = Path("skills")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- GESTÃO DE PROCESSOS (THREAD-SAFE) ---
PROCESSOS_LOCK = threading.Lock()
PROCESSOS_ATIVOS: Dict[str, Dict] = {}

# --- FUNÇÕES UTILITÁRIAS ---
def validate_path(path_str: str) -> Optional[Path]:
    """Valida se o caminho está dentro da raiz do projeto para segurança."""
    try:
        project_root = Path.cwd().resolve()
        target_path = (project_root / path_str).resolve()
        # Permite acesso a subpastas
        if project_root not in target_path.parents and project_root != target_path:
            return None
        return target_path
    except: return None

def get_project_structure(caminho: str = ".") -> str:
    """Retorna a árvore de arquivos do projeto."""
    p = validate_path(caminho)
    if not p: return "❌ Erro path."
    ignorar = {'.git', 'venv', '__pycache__', '.vscode', 'node_modules', 'jarvis_logs', '__init__.py', 'workspace_output'}
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
