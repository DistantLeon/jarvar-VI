# PROJECT CONTEXT: JARVIS ECOSYSTEM (V3.9.1)
**Date:** 2026-02-03 | **Architecture:** Orchestrator (Hand) + Intelligence (Brain-CLI) + Dynamic Skills (Meta) + Web Arm + Media Suite + Persistent Memory

## 1. Overview
O projeto evoluiu para uma arquitetura de **Fábrica de Software Autônoma com Capacidade de Auto-Expansão, Navegação Web, Processamento Multimídia e Memória Persistente**.
- **Jarvis (Hand):** Script Python (`jarvis.py`) que atua como **Orquestrador Síncrono com Hot Reload**.
- **Gemini CLI (Brain):** Motor de raciocínio profundo (Brain) executado via subprocesso isolado.
- **Dynamic Skills:** Sistema que permite ao Jarvis criar, salvar e carregar novas ferramentas Python em tempo de execução sem reiniciar o processo.
- **Web Arm:** Capacidade headless de navegar, renderizar JS e ler a web.
- **Persistent Memory (Dossier):** Sistema de arquivos Markdown para retenção de longo prazo (preferências, contexto de projeto).

## 2. Directory Structure
- `/`: Raiz do projeto.
- `/jarvis_logs/`: Auditoria completa do Brain (Inputs/Outputs).
- `/memoria/`: [NOVO] Armazenamento de conhecimento persistente (Arquivos .md).
- `/skills/`: Repositório de ferramentas dinâmicas (Navegação, Memória, etc).
- `/web_arm_tests/`: Testes automatizados da capacidade de navegação.
- `/venv/`: Ambiente virtual Python.

## 3. Core Components
- `jarvis.py` (v3.9.1):
    - **Hot Reloading:** Detecta criação de novas skills e recarrega a "memória" de funções do modelo preservando o histórico do chat.
    - **Short-Circuit Execution:** Intercepta comandos JSON retornados pelo Brain e os executa imediatamente na mesma iteração, eliminando alucinações da Hand.
    - **Meta-Tool (`criar_skill`):** Permite que o Jarvis escreva código Python para expandir suas próprias capacidades.
    - **Dynamic Loader:** Importa módulos da pasta `/skills` automaticamente via `importlib` com resolução de nomes robusta (`skills.modulo`).

- `skills/cerebro.py` (The Bridge):
    - **Architecture:** Executa o `gemini` CLI via `subprocess` nativo.
    - **Protocol:** Envia contexto via STDIN (evitando limites de shell e problemas de encoding).
    - **CRITICAL:** A separação via CLI é vital para a arquitetura multi-agente. **NÃO SUBSTITUIR POR SDK.**
    - **Logs:** Auditoria completa em `jarvis_logs/` antes e depois do processamento.

- `skills/schemas.py` (Guardrails):
    - **Lib:** `pydantic`.
    - **Função:** Define a estrutura rígida `BrainCommand` (tool + args).
    - **Parser:** `extract_json_from_text` garante que apenas JSONs válidos acionem ferramentas.

- `skills/navegacao.py` (Web Arm):
    - **Lib:** `crawl4ai` (Baseada em Playwright).
    - **Função:** `navegar_web(url, tipo_extracao)`.

- `skills/memoria.py` (Dossier):
    - **Funções:** `memorizar(conteudo, topico)`, `consultar_memoria(topico)`.

## 4. Protocols & Standards
- **Meta-Programming Protocol:**
    - Se o Brain identificar uma tarefa repetitiva ou complexa que falta no arsenal, ele deve instruir a criação de uma Skill.
- **Brain-Hand Protocol:**
    - Brain pensa -> JSON Estruturado (` ```json ... ``` `) -> Hand valida (Pydantic) -> Executa (Short-Circuit).
- **Security Protocol:**
    - **Non-Root Execution:** Container roda com usuário `jarvis` (UID 1000).
    - **Input Sanitization:** JSONs são validados antes da execução.
    - **Sandboxing:** `validate_path` impede acesso fora da raiz.

## 5. Data Flow (The Loop)
1. **User Input** -> Jarvis (Hand).
2. **Hand** -> Repassa para `iniciar_raciocinio` (Brain) via CLI Subprocess.
3. **Brain** -> Retorna estratégia ou comando JSON.
4. **Hand** -> 
    - Se JSON: Executa ferramenta imediatamente (Short-Circuit) e anexa resultado.
    - Se Texto: Exibe ao usuário.

## 6. Dependencies
- **Core:** `pydantic`, `python-dotenv`, `google-genai` (apenas p/ Hand), `gemini-cli` (Sistema).
- **Web Arm:** `crawl4ai`, `playwright` (Requires `playwright install chromium`).
- **Media:** `yt-dlp` (Video), `Pillow` (Image).
- **Runtime:** Python 3.12+.

## 7. Security
- **Docker:** Usuário `jarvis` configurado. Volumes montados com permissões ajustadas.
- **Web:** `navegar_web` roda em contexto seguro (Chromium sandbox).