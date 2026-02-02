# Jarvis Dynamic Skills

Este diretório contém as ferramentas (skills) carregadas dinamicamente pelo Jarvis. Cada arquivo `.py` aqui é importado e suas funções expostas ao Agente.

## Ferramentas Disponíveis

### 1. Pesquisa Web (`pesquisa.py`)
Realiza buscas no Google e DuckDuckGo para encontrar informações atualizadas.
- **Função Principal:** `pesquisar_web(query: str, max_results: int = 5) -> str`
- **Retorno:** Lista formatada com Título, URL e Resumo (Snippet) dos resultados.
- **Robustez:** Usa scraping manual do DuckDuckGo HTML para evitar bloqueios de API. Faz fallback para Google se necessário.

### 2. Inteligência de Vídeo (`youtube.py`)
Baixa e processa transcrições (legendas) de vídeos do YouTube.
- **Função Principal:** `ler_transcricao_youtube(url_video: str) -> str`
- **Retorno:** Texto completo da legenda (concatenação de segmentos).
- **Suporte:** Legendas manuais e automáticas em Português e Inglês.
- **Tecnologia:** Baseado em `yt-dlp` (suporta quase todos os vídeos).

### 3. Manipulação de Imagem (`imagem.py`)
Utilitários básicos para conversão e redimensionamento de imagens.
- **Função Principal:** `converter_imagem(caminho_entrada: str, formato_saida: str = "png", redimensionar_fator: float = 1.0) -> str`
- **Retorno:** Caminho absoluto do novo arquivo de imagem.
- **Tecnologia:** `Pillow` (PIL) com filtro de alta qualidade (Lanczos).

### 4. Navegação Web (`navegacao.py`) - *Existente*
Acesso headless a páginas web para leitura de conteúdo.
- **Função Principal:** `navegar_web(url: str)`

### 5. Memória Persistente (`memoria.py`)
Sistema de leitura e escrita em arquivos Markdown na pasta `/memoria`.
- **Funções:** `memorizar`, `consultar_memoria`, `listar_topicos`.

### 6. Ferramentas de Sistema (`sistema.py`)
Interface com o sistema operacional e gerenciamento de arquivos.
- **Funções:** `ler_arquivo`, `escrever_arquivo`, `executar_comando_terminal`, `listar_estrutura_projeto`, `criar_skill` (Meta-Tool).

### 7. Core de Raciocínio (`cerebro.py`)
Permite delegar tarefas complexas para o motor de lógica profunda.
- **Função Principal:** `iniciar_raciocinio(query: str, context_level: str = "medium")`.
Para criar uma nova skill:
1. Crie um arquivo `.py` nesta pasta.
2. Defina funções com **Type Hints** e **Docstrings** claras.
3. O Jarvis importará automaticamente no próximo ciclo de reload.
