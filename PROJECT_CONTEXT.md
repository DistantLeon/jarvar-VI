# PROJECT CONTEXT: JARVIS ECOSYSTEM (V3.9)
**Date:** 2026-02-02 | **Architecture:** Orchestrator (Hand) + Intelligence (Brain-CLI) + Dynamic Skills (Meta) + Web Arm + Media Suite + Persistent Memory

## 1. Overview
O projeto evoluiu para uma arquitetura de **Fábrica de Software Autônoma com Capacidade de Auto-Expansão, Navegação Web, Processamento Multimídia e Memória Persistente**.
- **Jarvis (Hand):** Script Python (`jarvis.py`) que atua como **Orquestrador Síncrono com Hot Reload**.
- **Gemini CLI (Brain):** Motor de raciocínio profundo (Brain).
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
- `jarvis.py` (v3.9.0):
    - **Hot Reloading:** Detecta criação de novas skills e recarrega a "memória" de funções do modelo preservando o histórico do chat.
    - **Meta-Tool (`criar_skill`):** Permite que o Jarvis escreva código Python para expandir suas próprias capacidades.
    - **Dynamic Loader:** Importa módulos da pasta `/skills` automaticamente via `importlib`.
    - **Tools Nativas:** `escrever_arquivo`, `ler_arquivo`, `executar_comando_terminal`, `listar_estrutura_projeto`, `iniciar_raciocinio`, `criar_skill`.

- `skills/navegacao.py` (Web Arm):
    - **Lib:** `crawl4ai` (Baseada em Playwright).
    - **Função:** `navegar_web(url, tipo_extracao)`.
    - **Saída:** Markdown limpo e otimizado para LLMs.
    - **Recursos:** Renderização de JavaScript, contorno de bloqueios simples, truncamento de conteúdo seguro (40k chars).

- `skills/memoria.py` (Dossier):
    - **Lib:** Standard Python (`pathlib`, `glob`).
    - **Funções:** `memorizar(conteudo, topico)`, `consultar_memoria(topico)`, `listar_topicos()`.
    - **Propósito:** Evitar "amnésia" entre sessões salvando fatos em `/memoria`.

- `skills/pesquisa.py` (Search Engine):
    - **Lib:** `requests`, `bs4` (Scraping Manual Robust).
    - **Função:** `pesquisar_web(query)`.
    - **Estratégia:** Rotação de user-agents e parsing direto do HTML do DuckDuckGo. Fallback para Google.

- `skills/youtube.py` (Video Intel):
    - **Lib:** `yt-dlp`.
    - **Função:** `ler_transcricao_youtube(url)`.
    - **Recursos:** Baixa legendas (PT/EN) sem baixar vídeo. Suporta auto-subs.

- `skills/imagem.py` (Media Ops):
    - **Lib:** `Pillow`.
    - **Função:** `converter_imagem(path, fmt, scale)`.

## 4. Protocols & Standards
- **Meta-Programming Protocol:**
    - Se o Brain identificar uma tarefa repetitiva ou complexa que falta no arsenal, ele deve instruir a criação de uma Skill.
- **Brain-Hand Protocol:**
    - Brain pensa -> JSON -> Hand executa.
- **Web Research Protocol:**
    - Para acessar URLs: Use `navegar_web`.
    - O retorno é Markdown. O Brain deve ler o Markdown e sintetizar a resposta.
- **Memory Protocol:**
    - Início de Sessão: Consultar `memoria/user_preferences.md` (se existir).
    - Fato Novo: Usar `memorizar` para salvar decisões arquiteturais ou preferências.
    - Dúvida: Usar `consultar_memoria` antes de alucinar ou perguntar novamente.

## 5. Data Flow (The Loop)
1. **User Input** -> Jarvis (Hand).
2. **Hand** -> Repassa para `iniciar_raciocinio` (Brain) OU executa ferramenta direta (Ex: `navegar_web`).
3. **Brain** -> Retorna estratégia, conteúdo processado ou pedido de nova skill.
4. **Hand** -> Executa e retorna feedback.

## 6. Dependencies
- **Core:** `google-genai`, `python-dotenv`, `requests`, `beautifulsoup4`.
- **Web Arm:** `crawl4ai`, `playwright` (Requires `playwright install chromium`).
- **Media:** `yt-dlp` (Video), `Pillow` (Image).
- **Runtime:** Python 3.12+.

## 7. Security
- **Sandboxing:** `validate_path` impede acesso fora da raiz.
- **Web:** `navegar_web` roda em contexto seguro (Chromium sandbox) e trunca saídas gigantes.