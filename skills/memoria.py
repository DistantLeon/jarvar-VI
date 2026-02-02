import os
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Define the memory directory relative to the current working directory
MEMORIA_DIR = Path("memoria")

def _validate_memoria_path(filename: str) -> Optional[Path]:
    """
    Validates that the filename results in a path inside the memoria directory.
    """
    try:
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        if not filename.endswith(".md"):
            filename += ".md"
        
        target_path = (MEMORIA_DIR / filename).resolve()
        memoria_abs = MEMORIA_DIR.resolve()
        
        # Ensure target is within memoria directory
        if memoria_abs not in target_path.parents:
            return None
            
        return target_path
    except Exception:
        return None

def memorizar(conteudo: str, topico: str = "geral") -> str:
    """
    Salva uma informação na memória persistente. 
    
    Args:
        conteudo: O texto a ser memorizado.
        topico: O nome do arquivo (tópico) onde salvar. Padrão: "geral".
    
    Returns:
        Mensagem de sucesso ou erro.
    """
    path = _validate_memoria_path(topico)
    if not path:
        return f"❌ Erro: Tópico '{topico}' inválido."
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n### {timestamp}\n{conteudo}\n"
    
    try:
        if not MEMORIA_DIR.exists():
            MEMORIA_DIR.mkdir(parents=True)
            
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
            
        return f"✅ Informação salva em 'memoria/{path.name}'."
    except Exception as e:
        return f"❌ Erro ao salvar memória: {e}"

def consultar_memoria(topico: str) -> str:
    """
    Lê o conteúdo de um tópico da memória.
    
    Args:
        topico: O nome do arquivo (tópico) a ser lido.
    
    Returns:
        O conteúdo do arquivo ou mensagem de erro se não existir.
    """
    path = _validate_memoria_path(topico)
    if not path:
        return f"❌ Erro: Tópico '{topico}' inválido."
        
    if not path.exists():
        return f"ℹ️ Nenhuma memória encontrada para o tópico '{topico}'."
        
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ Erro ao ler memória: {e}"

def listar_topicos() -> str:
    """
    Lista todos os tópicos (arquivos) disponíveis na memória.
    
    Returns:
        Lista de tópicos encontrados.
    """
    if not MEMORIA_DIR.exists():
        return "ℹ️ O diretório de memória ainda não existe."
        
    try:
        files = list(MEMORIA_DIR.glob("*.md"))
        if not files:
            return "ℹ️ Nenhum tópico encontrado na memória."
            
        topicos = [f.stem for f in files]
        return f"📂 Tópicos de Memória:\n" + "\n".join([f"- {t}" for t in topicos])
    except Exception as e:
        return f"❌ Erro ao listar tópicos: {e}"
