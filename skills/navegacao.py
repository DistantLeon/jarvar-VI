import asyncio
from crawl4ai import AsyncWebCrawler

def navegar_web(url: str, tipo_extracao: str = "markdown") -> str:
    """
    Acessa uma URL, renderiza o JS e retorna o conteúdo principal.
    Args:
        url: O endereço web completo.
        tipo_extracao: 'markdown' (padrão) ou 'raw_html'.
    Returns:
        Texto contendo o conteúdo da página ou mensagem de erro.
    """
    async def _run_crawler():
        # Inicializa o crawler com modo verbose para logs (opcional)
        # O crawl4ai gerencia o ciclo de vida do navegador internamente no context manager
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=url)
            
            if not result.success:
                return f"❌ Falha ao acessar {url}: {result.error_message}"
            
            if tipo_extracao == "raw_html":
                return result.html
            
            # Retorna o markdown.
            # Trunca se for muito grande para evitar estourar limites de contexto
            # O limite de 40k caracteres é razoável para processamento posterior
            conteudo = result.markdown
            if len(conteudo) > 40000:
                return f"{conteudo[:40000]}\n\n[...CONTEUDO TRUNCADO (Total: {len(conteudo)} chars)...]"
            return conteudo

    try:
        # asyncio.run() cria um novo event loop, executa a corrotina e fecha o loop.
        # Isso é seguro pois jarvis.py é síncrono e não tem um loop rodando na main thread.
        return asyncio.run(_run_crawler())
    except Exception as e:
        return f"❌ Erro sistemico ao navegar: {str(e)}"