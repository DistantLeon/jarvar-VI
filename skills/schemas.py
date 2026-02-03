import re
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

class BrainCommand(BaseModel):
    """Estrutura rígida para comandos executáveis do Cérebro."""
    tool: str = Field(..., description="Nome exato da função/skill a ser executada")
    args: Dict[str, Any] = Field(default_factory=dict, description="Argumentos da função")

def extract_json_from_text(text: str) -> Optional[BrainCommand]:
    """
    Tenta extrair e validar um BrainCommand de um texto.
    Suporta blocos ```json ... ``` ou JSON puro.
    """
    text = text.strip()
    
    # 1. Tenta encontrar bloco de código JSON
    pattern = r"```json\s*(\{.*?\})\s*```"
    match = re.search(pattern, text, re.DOTALL)
    
    json_str = ""
    if match:
        json_str = match.group(1)
    elif text.startswith("{") and text.endswith("}"):
        # Tenta assumir que o texto inteiro é JSON
        json_str = text
    else:
        # Tenta encontrar o primeiro { e o último }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            json_str = text[start:end+1]
    
    if not json_str:
        return None

    try:
        data = json.loads(json_str)
        return BrainCommand(**data)
    except (json.JSONDecodeError, ValidationError):
        return None
