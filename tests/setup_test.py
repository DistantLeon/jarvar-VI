# Test Scenario: Full Capability Check
# 1. Image dummy creation
import requests
from PIL import Image

img = Image.new('RGB', (60, 30), color = 'red')
img.save('tests/run_001/dummy.png')

# 2. Input script for Jarvis
# Scenario:
# - Check memory (Memory)
# - Search web (Web Research + Brain)
# - Navigate (Web Navigation)
# - Create a skill (Meta)
# - Use created skill (Multi-CLI simulation via shell)

inputs = [
    "Verifique se tenho preferencias salvas na memoria sobre o projeto.",
    "Pesquise 'Python 3.13 features' e me diga a principal.",
    "Acesse 'https://example.com' e me diga o titulo da pagina.",
    "Converta a imagem 'tests/run_001/dummy.png' para JPG.",
    "Crie uma skill chamada 'multi_agent_ping' que executa o comando 'gemini --version' no terminal e retorna o output. Quero testar se consigo invocar outro CLI.",
    "Use a skill multi_agent_ping e me mostre a versao.",
    "sair"
]

with open('tests/run_001/input_script.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(inputs))
