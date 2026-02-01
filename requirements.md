# Project Requirements

## Core Dependencies (Jarvis System)
Essas bibliotecas são essenciais para o funcionamento do orquestrador `jarvis_v3.6.py`.

- **Python 3.12+**
- **google-genai**: SDK para comunicação com o modelo Gemini 2.0 Flash.
- **python-dotenv**: Carregamento de credenciais (`.env`).
- **pydantic**: Validação de dados.

## Factory Mode Dependencies (Generated Apps)
Bibliotecas recomendadas para os softwares gerados pelo Jarvis (como visto no Desafio 5).

- **fastapi**: Framework web moderno.
- **uvicorn**: Servidor ASGI.
- **requests**: Para testes de integração.
- **pytest**: Framework de testes.

## Environment Setup
1. Crie o arquivo `.env`:
   ```env
   GEMINI_API_KEY=sua_chave_aqui
   ```
2. Instale as dependências:
   ```bash
   pip install google-genai python-dotenv fastapi uvicorn requests pytest
   ```
3. Verifique o Gemini CLI:
   Certifique-se de que o comando `gemini` está acessível no PATH.
