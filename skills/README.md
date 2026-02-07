# Jarvis Dynamic Skills (Infra Only)

Este diretorio contem as ferramentas (skills) carregadas dinamicamente pelo Jarvis.
A politica atual e **infra only**: apenas skills essenciais permanecem ativas.
As tools principais passam a ser as tools built-in dos CLIs (Gemini/Codex).

## Skills Ativas (Allowlist)

### 1. Ferramentas de Sistema (`sistema.py`)
Interface com o sistema operacional e gerenciamento de arquivos.
- **Funcoes:** `ler_arquivo`, `escrever_arquivo`, `executar_comando_terminal`, `listar_estrutura_projeto`, `criar_skill`.

### 2. Memoria Persistente (`memoria.py`)
Sistema de leitura e escrita em arquivos Markdown na pasta `/memoria`.
- **Funcoes:** `memorizar`, `consultar_memoria`, `listar_topicos`.

### 3. Core de Raciocinio (`cerebro.py`)
Orquestrador via Gemini CLI.
- **Funcoes:** `iniciar_raciocinio`, `gemini_cli_raw`.

### 4. Codex CLI (`codex_cli.py`)
Executor especializado para tarefas de codigo e automacao via Codex CLI.
- **Funcoes:** `executar_codex_cli`, `executar_codex_cli_raw`, `verificar_codex_cli`, `descrever_capacidades_codex`.

## Observacao
Outras skills (web, imagem, youtube, etc.) permanecem no diretorio,
mas **nao sao carregadas** por padrao. Para ativa-las, ajuste `SKILLS_ALLOWLIST`
ou a variavel de ambiente `SKILLS_ALLOWLIST`.
