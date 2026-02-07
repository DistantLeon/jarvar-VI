import asyncio
import requests
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _fallback_request(url: str, tipo_extracao: str) -> str:
    headers = {"User-Agent": _USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return f"âŒ Fallback HTTP falhou para {url}: {str(e)}"

    if tipo_extracao == "raw_html":
        return response.text

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = " ".join(soup.get_text(" ", strip=True).split())
    if len(text) > 40000:
        text = f"{text[:40000]}\n\n[...CONTEUDO TRUNCADO (Total: {len(text)} chars)...]"
    if title:
        return f"# {title}\n\n{text}"
    return text


def navegar_web(url: str, tipo_extracao: str = "markdown") -> str:
    """
    Acessa uma URL, renderiza o JS e retorna o conteÃºdo principal.
    Args:
        url: O endereÃ§o web completo.
        tipo_extracao: 'markdown' (padrÃ£o) ou 'raw_html'.
    Returns:
        Texto contendo o conteÃºdo da pÃ¡gina ou mensagem de erro.
    """
    async def _run_crawler():
        # Inicializa o crawler com modo verbose para logs (opcional)
        # O crawl4ai gerencia o ciclo de vida do navegador internamente no context manager
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=url)

            if not result.success:
                fallback = _fallback_request(url, tipo_extracao)
                return (
                    f"âŒ Falha ao acessar {url}: {result.error_message}\n\n"
                    f"{fallback}"
                )

            if tipo_extracao == "raw_html":
                return result.html

            # Retorna o markdown.
            # Trunca se for muito grande para evitar estourar limites de contexto
            # O limite de 40k caracteres Ã© razoÃ¡vel para processamento posterior
            conteudo = result.markdown
            if len(conteudo) > 40000:
                return f"{conteudo[:40000]}\n\n[...CONTEUDO TRUNCADO (Total: {len(conteudo)} chars)...]"
            return conteudo

    try:
        # asyncio.run() cria um novo event loop, executa a corrotina e fecha o loop.
        # Isso Ã© seguro pois jarvis.py Ã© sÃ­ncrono e nÃ£o tem um loop rodando na main thread.
        return asyncio.run(_run_crawler())
    except Exception as e:
        fallback = _fallback_request(url, tipo_extracao)
        return f"âŒ Erro sistemico ao navegar: {str(e)}\n\n{fallback}"
