# Project Requirements

## Core Dependencies (Jarvis System)
Essas bibliotecas são essenciais para o funcionamento do orquestrador `jarvis.py` (v3.7+).

- **Python 3.12+**
- **google-genai**: SDK para comunicação com o modelo Gemini 2.0 Flash.
- **python-dotenv**: Carregamento de credenciais (`.env`).
- **pydantic**: Validação de dados (usado internamente pelo SDK).

## Web Arm Dependencies (Navegação) [NOVO]
Essenciais para a funcionalidade de navegação e leitura de páginas web (`skills/navegacao.py`).

- **crawl4ai**: Framework de crawling assíncrono que converte HTML/JS em Markdown limpo.
- **playwright**: Motor de automação de browser (usado pelo crawl4ai).
  *Nota:* Requer instalação de binários do sistema: `playwright install chromium`.

## Dynamic Skills Dependencies
O sistema de skills nativo utiliza bibliotecas padrão do Python, mas skills criadas podem requerer pacotes extras.

- **importlib**: (Stdlib) Carregamento dinâmico.
- **inspect**: (Stdlib) Introspecção de código.

## Environment Setup
1. Crie o arquivo `.env`:
   ```env
   GEMINI_API_KEY=sua_chave_aqui
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Verifique o Gemini CLI:
   Certifique-se de que o comando `gemini` está acessível no PATH para funcionamento do Brain.
