# PROJECT CONTEXT: JARVIS ECOSYSTEM (V0.4.1)
**Date:** 2026-02-07 | **Architecture:** Router (Hand) + Brain-CLI (Gemini) + Executor-CLI (Codex) + Infra Skills + Persistent Memory

## 1. Overview
O projeto evoluiu para uma arquitetura onde **os CLIs sao a fonte primaria de tools**.
As skills locais ficam apenas para infraestrutura (IO, memoria, bridges).
- **Jarvis (Hand/Router):** Script Python (`jarvis.py`) que atua como **roteador automatico**.
- **Gemini CLI (Brain):** Motor de raciocinio profundo, executado via subprocesso isolado.
- **Codex CLI (Executor):** Executor especializado para tarefas de codigo e automacao.
- **Infra Skills:** Apenas ferramentas essenciais (sistema, memoria, cerebro, codex_cli).
- **Persistent Memory (Dossier):** Arquivos Markdown para retencao de longo prazo.

## 2. Directory Structure
- `/`: Raiz do projeto.
- `/jarvis_logs/`: Auditoria completa do Brain e do Codex (inputs/outputs).
- `/memoria/`: Armazenamento de conhecimento persistente (arquivos .md).
- `/skills/`: Repositorio de ferramentas dinamicas (infra only por allowlist).
- `/tests/`: Scripts de testes e cenarios de execucao.
- `/venv/`: Ambiente virtual Python.

## 3. Core Components
- `jarvis.py` (v0.4.1):
  - **Router:** Decide automaticamente entre Gemini (pensar) e Codex (executar).
  - **Pass-through `/`:** Comandos iniciados por `/` sao repassados ao CLI escolhido.
  - **Skills Allowlist:** Carrega apenas `sistema`, `memoria`, `cerebro`, `codex_cli`.
  - **History + Summary:** Mantem contexto da sessao e injeta nos prompts.

- `skills/cerebro.py` (Brain Bridge):
  - **Architecture:** Executa o `gemini` CLI via `subprocess` nativo.
  - **Functions:** `gemini_cli_raw` (pass-through) e `iniciar_raciocinio` (legado JSON).
  - **CRITICAL:** A separacao via CLI e vital. **Nao substituir por SDK.**

- `skills/codex_cli.py` (Executor Bridge):
  - **Purpose:** Ponte para o Codex CLI (`codex exec`).
  - **Functions:** `executar_codex_cli` (com preambulo) e `executar_codex_cli_raw` (pass-through).
  - **Logs:** Entrada e saida salvas em `jarvis_logs/`.

- `skills/memoria.py` (Dossier):
  - **Funcoes:** `memorizar`, `consultar_memoria`, `listar_topicos`.

- `skills/sistema.py` (Infra):
  - **Funcoes:** `ler_arquivo`, `escrever_arquivo`, `executar_comando_terminal`, `listar_estrutura_projeto`, `criar_skill`.

## 4. Protocols & Standards
- **Router Protocol:**
  - Roteamento automatico com heuristicas (e opcional LLM via `ROUTER_MODE=hybrid|llm`).
  - Gemini = pensamento/contexto longo. Codex = execucao/codigo.
- **CLI Tools First:**
  - As tools built-in dos CLIs sao a referencia primaria.
  - Skills locais ficam restritas a infraestrutura.
- **Security Protocol:**
  - **Non-Root Execution:** Container roda com usuario `jarvis` (UID 1000).
  - **Sandboxing:** `validate_path` impede acesso fora da raiz.

## 5. Data Flow (The Loop)
1. **User Input** -> Jarvis Router.
2. **Router** -> Decide Gemini CLI ou Codex CLI.
3. **CLI** -> Responde diretamente (texto/tools nativas).
4. **Jarvis** -> Exibe resposta e atualiza contexto local.

## 6. Dependencies
- **Core:** `python-dotenv`, `pydantic`.
- **Runtime:** Python 3.12+.
- **CLIs (System):** `gemini` CLI, `codex` CLI.

## 7. Security
- **Docker:** Usuario `jarvis` configurado. Volumes montados com permissoes ajustadas.
