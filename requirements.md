# Project Requirements (Jarvis 4.0)

## Core Dependencies (Jarvis System)
Bibliotecas essenciais para o orquestrador `jarvis.py`.
- **Python 3.12+**
- **google-genai**: SDK para comunicacao com o modelo Gemini.
- **python-dotenv**: Carregamento de credenciais (`.env`).
- **pydantic**: Validacao de dados e schemas.

## Brain / Executor CLIs (System)
Ferramentas de CLI que precisam estar no PATH do sistema:
- **gemini**: CLI do Brain (orquestrador via subprocess).
- **codex**: CLI do Executor (delegacao via `codex exec`).

## Web Arm Dependencies (Navegacao)
- **crawl4ai**: Crawling assincrono (Playwright).
- **playwright**: Motor de automacao do browser.
  - Requer: `playwright install chromium`
- **requests** + **beautifulsoup4**: Fallback HTTP quando Playwright falha.

## Media
- **yt-dlp**: Transcricao e metadata de video.
- **Pillow**: Conversao e redimensionamento de imagens.

## Optional / Infra
- **fastapi**, **uvicorn**: Somente se voce for expor o Jarvis como API.
- **pytest**: Testes locais.

## Install
```bash
pip install -r requirements.txt
playwright install chromium
```

## Environment Setup
Crie o arquivo `.env`:
```env
GEMINI_API_KEY=sua_chave_aqui
```

## Notes
- O Brain utiliza o Gemini CLI via subprocess, nao substituir por SDK.
- O Codex roda em sessoes novas por chamada (`codex exec`).
