# Tool Refector

## Policy Update (2026-02-07)
Jarvis version: **0.4.1**.
O Jarvis agora trata os **CLIs (Gemini/Codex)** como fonte primaria de tools.
As skills locais ficam restritas a infraestrutura (sistema, memoria, cerebro, codex_cli).
Comandos iniciados por `/` sao repassados diretamente ao CLI escolhido.

Isso reduz duplicacao de tools e mantem o uso das tools nativas dos CLIs.

## Legacy Notes: Web Tools
O projeto possui ferramentas web em `skills/pesquisa.py` e `skills/navegacao.py`,
mas elas **nao sao carregadas por padrao** (fora da allowlist).

### Web Search Tool Description
The project provides a web search capability via the dynamic skill `skills/pesquisa.py`. It performs a search using DuckDuckGo’s HTML endpoint and parses results with BeautifulSoup. To reduce blocks, it sets a realistic User-Agent and includes a fallback to DuckDuckGo Lite when the HTML endpoint appears to be blocked (for example captcha/verify responses or unexpected HTML structure). The tool returns a formatted list of titles, URLs, and snippets. This is a lightweight, scraping-based approach intended for quick, non‑API searches.

The project also includes a web navigation tool `skills/navegacao.py` (“Web Arm”). It uses `crawl4ai` (Playwright) to fetch and render pages. When Playwright fails, it falls back to a simple HTTP GET + BeautifulSoup parse, returning either raw HTML or a text summary with title.

### Problem Found
During test runs, the web search and navigation features failed to return results consistently.
- `pesquisar_web` sometimes failed with “estrutura desconhecida ou bloqueio (Captcha)” from DuckDuckGo.
- `navegar_web` failed with `net::ERR_NAME_NOT_RESOLVED` when trying to access `https://example.com`, which indicates DNS resolution/network access issues in the execution environment.

### Attempts to Fix
1. Added a DuckDuckGo Lite fallback to `skills/pesquisa.py`.
   - When the HTML endpoint is blocked (captcha/verify), the tool retries using `https://lite.duckduckgo.com/lite/`.
   - Updated User‑Agent to a more recent browser string.

2. Added HTTP fallback for web navigation in `skills/navegacao.py`.
   - If Playwright/crawl4ai fails, it performs a direct HTTP GET using `requests` and parses content with BeautifulSoup.
   - This provides a degraded but usable response when headless browser navigation fails.

### Diagnosis
The core issue is environment-level network/DNS restrictions, not only tool logic.
- `ERR_NAME_NOT_RESOLVED` indicates DNS resolution failure, which prevents access even to well‑known domains.
- Scraping endpoints can return captcha/verify pages that break HTML parsing.
- The fallback logic improves resilience, but cannot bypass DNS/network blocks.

In short: the tool code is now more robust, but successful web search and navigation still depend on network access and DNS resolution in the runtime environment.
