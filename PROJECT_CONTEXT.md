# PROJECT CONTEXT: JARVIS ECOSYSTEM (V3.6)
**Date:** 2026-02-01 | **Architecture:** Orchestrator (Hand) + Intelligence (Brain-CLI)

## 1. Overview
O projeto evoluiu para uma arquitetura de **Fábrica de Software Autônoma**.
- **Jarvis (Hand):** Script Python (`jarvis_v3.6.py`) que atua como **Orquestrador Síncrono**. Ele não "pensa", apenas executa ordens. Possui um Loop Manual de Ferramentas sem limites de execução.
- **Gemini CLI (Brain):** Motor de raciocínio profundo. Recebe contexto, processa e retorna comandos estruturados em **JSON** para a Mão executar.
- **Objetivo:** Permitir fluxos de trabalho infinitos, recursivos (Cérebros chamando Cérebros) e especializados (Arquiteto -> Dev -> QA).

## 2. Directory Structure
- `/`: Raiz do projeto.
- `/jarvis_logs/`: Auditoria completa. Cada raciocínio gera um par `_input.txt` (Prompt) e `_output.txt` (Resposta JSON/Texto).
- `/venv/`: Ambiente virtual Python.

## 3. Core Components
- `jarvis_v3.6.py` [CORE]:
    - **Loop Manual:** Substituiu o `automatic_function_calling` do SDK para remover o limite de 10 chamadas.
    - **Protocolo Síncrono:** Aguarda o término do processo CLI antes de agir, garantindo consistência.
    - **JSON Parsing:** Detecta blocos `{"tool": ...}` na resposta do Brain e executa via `TOOL_MAP`.
    - **Tools:** `escrever_arquivo` (Preferencial), `ler_arquivo`, `executar_comando_terminal`, `listar_estrutura_projeto`, `iniciar_raciocinio` (Recursivo).

## 4. Protocols & Standards
- **Brain-Hand Protocol:**
    - O Brain **NUNCA** executa comandos shell (ex: `echo ... > file`) para criar arquivos complexos.
    - O Brain **SEMPRE** envia um JSON: `{"tool": "escrever_arquivo", "args": {...}}`.
    - O Hand executa cegamente.
- **Factory Mode (Methodology):**
    - **Phase 1 (Architect):** Gera Specs/Docs em Markdown.
    - **Phase 2 (Coder):** Lê Specs e gera Código.
    - **Phase 3 (QA):** Lê Código e gera Testes.

## 5. Data Flow (The Loop)
1. **User Input** -> Jarvis (Hand).
2. **Hand** -> Repassa integralmente para `iniciar_raciocinio` (Brain).
3. **Brain** -> Pensa -> Retorna JSON `{"tool": "..."}`.
4. **Hand** -> Detecta JSON -> Executa Tool -> Envia resultado de volta ao Brain.
5. **Repeat** -> O ciclo continua indefinidamente até o Brain decidir parar e responder texto ao usuário.

## 6. Dependencies
- `google-genai`: SDK v1.0+ (Client).
- `subprocess`: Ponte para o CLI.
- **Runtime:** Python 3.12+.

## 7. Security
- **Sandboxing:** `validate_path` impede acesso fora da raiz.
- **Hardening:** Prompt do Brain instruído a não usar shell tricks frágeis.