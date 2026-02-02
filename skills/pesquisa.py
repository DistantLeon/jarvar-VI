import requests
from bs4 import BeautifulSoup

def pesquisar_web(query: str, max_results: int = 5) -> str:
    """
    Realiza uma busca na web utilizando a versão HTML do DuckDuckGo via scraping manual.
    Esta abordagem é mais robusta contra bloqueios de bibliotecas automatizadas.

    Args:
        query (str): O termo de busca.
        max_results (int, optional): O número máximo de resultados. Padrão 5.

    Returns:
        str: Resultados formatados com Título, URL e Resumo.
    """
    url = 'https://html.duckduckgo.com/html/'
    data = {'q': query}
    # Headers simulando um navegador real para evitar bloqueio
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
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
                return "Erro: Estrutura da página desconhecida ou bloqueio (Captcha)."

        count = 0
        for div in results_divs:
            # Título e Link
            link_tag = div.find('a', class_='result__a')
            if not link_tag:
                continue
                
            title = link_tag.get_text(strip=True)
            href = link_tag.get('href', '')
            
            # Snippet
            snippet_tag = div.find('a', class_='result__snippet')
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else "Resumo indisponível"
            
            count += 1
            formatted_output.append(
                f"{count}. {title}\n"
                f"   URL: {href}\n"
                f"   Resumo: {snippet}\n"
            )
            
            if count >= max_results:
                break
        
        if count == 0:
            # Caso tenha achado divs mas não links (estranho, mas possível)
             return "Nenhum resultado válido extraído da página."

        return "\n".join(formatted_output)

    except Exception as e:
        return f"Erro ao realizar pesquisa na web: {str(e)}"