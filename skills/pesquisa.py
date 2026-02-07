import requests
from bs4 import BeautifulSoup

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _buscar_ddg_lite(query: str, max_results: int = 5) -> str:
    url = "https://lite.duckduckgo.com/lite/"
    headers = {"User-Agent": _USER_AGENT}
    try:
        response = requests.get(url, params={"q": query}, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return f"Erro ao acessar DuckDuckGo Lite: {str(e)}"

    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", rel="nofollow", limit=max_results * 2)

    formatted_output = [f"Resultados para: '{query}' (fallback DDG Lite)\n"]
    count = 0

    for link in links:
        title = link.get_text(strip=True)
        href = link.get("href", "")
        if not title or not href:
            continue

        count += 1
        formatted_output.append(
            f"{count}. {title}\n"
            f"   URL: {href}\n"
            f"   Resumo: Resumo indisponivel (DDG Lite)\n"
        )
        if count >= max_results:
            break

    if count == 0:
        return "Nenhum resultado valido extraido do DuckDuckGo Lite."

    return "\n".join(formatted_output)


def pesquisar_web(query: str, max_results: int = 5) -> str:
    """
    Realiza uma busca na web utilizando a versÃ£o HTML do DuckDuckGo via scraping manual.
    Esta abordagem Ã© mais robusta contra bloqueios de bibliotecas automatizadas.

    Args:
        query (str): O termo de busca.
        max_results (int, optional): O nÃºmero mÃ¡ximo de resultados. PadrÃ£o 5.

    Returns:
        str: Resultados formatados com TÃ­tulo, URL e Resumo.
    """
    url = 'https://html.duckduckgo.com/html/'
    data = {'q': query}
    # Headers simulando um navegador real para evitar bloqueio
    headers = {
        'User-Agent': _USER_AGENT,
        'Referer': 'https://html.duckduckgo.com/',
        'Origin': 'https://html.duckduckgo.com',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(url, data=data, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        formatted_output = [f"Resultados para: '{query}'\n"]

        # Encontra os blocos de resultado
        # Estrutura comum do DDG HTML: div.result
        results_divs = soup.find_all('div', class_='result', limit=max_results)

        if not results_divs:
            # Fallback: Tenta achar apenas os links se a estrutura mudou
            links = soup.find_all('a', class_='result__a', limit=max_results)
            if not links:
                if "No results" in response.text:
                    return f"Nenhum resultado encontrado para: '{query}'."
                if "captcha" in response.text.lower() or "verify" in response.text.lower():
                    return _buscar_ddg_lite(query, max_results=max_results)
                return "Erro: Estrutura da pÃ¡gina desconhecida ou bloqueio (Captcha)."

        count = 0
        for div in results_divs:
            # TÃ­tulo e Link
            link_tag = div.find('a', class_='result__a')
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            href = link_tag.get('href', '')

            # Snippet
            snippet_tag = div.find('a', class_='result__snippet')
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else "Resumo indisponivel"

            count += 1
            formatted_output.append(
                f"{count}. {title}\n"
                f"   URL: {href}\n"
                f"   Resumo: {snippet}\n"
            )

            if count >= max_results:
                break

        if count == 0:
            # Caso tenha achado divs mas nÃ£o links (estranho, mas possÃ­vel)
            return _buscar_ddg_lite(query, max_results=max_results)

        return "\n".join(formatted_output)

    except Exception as e:
        return f"Erro ao realizar pesquisa na web: {str(e)}"
