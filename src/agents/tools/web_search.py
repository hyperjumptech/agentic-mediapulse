from agents.tools.providers import Provider, dispatch, exa, serper, tavily

SEARCH_PROVIDERS = [
    Provider("serper", "SERPER_API_KEY", serper.search),
    Provider("exa", "EXA_API_KEY", exa.search),
    Provider("tavily", "TAVILY_API_KEY", tavily.search),
]


def format_results(results: list[dict]) -> str:
    if not results:
        return "No results found."

    blocks = []

    for item in results[:10]:
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        date = item.get("date", "")
        blocks.append(f"{title}\n{link}\n{date} {snippet}".strip())

    return "\n\n".join(blocks)


def web_search(query: str, kind: str = "news", gl: str = "", hl: str = "", recency: str = "week") -> str:
    """Search for the query and return titles, URLs, and snippets.

    kind is 'news' (default, recent articles) or 'web' (general results). gl/hl are the
    country/language codes that localize results to the subject's home market.
    recency limits results by age: 'day' (last 24h), 'week' (default), 'month', or '' for any time.
    """
    results = dispatch("search", SEARCH_PROVIDERS, lambda fn: fn(query, kind, gl, hl, recency), accept=bool)

    return format_results(results)
