from agents.tools.providers import AllProvidersFailed, Provider, diffbot, dispatch, exa, firecrawl, serper, tavily

FETCH_PROVIDERS = [
    Provider("serper", "SERPER_API_KEY", serper.fetch),
    Provider("exa", "EXA_API_KEY", exa.fetch),
    Provider("tavily", "TAVILY_API_KEY", tavily.fetch),
    Provider("firecrawl", "FIRECRAWL_API_KEY", firecrawl.fetch),
    Provider("diffbot", "DIFFBOT_API_KEY", diffbot.fetch),
]


def _nonempty(value: str) -> bool:
    return bool(value and value.strip())


def web_fetch(url: str) -> str:
    """Fetch a web page by URL and return its readable text content."""
    if not url.startswith("http"):
        return "Not a fetchable URL — pass a full http(s) article link."

    try:
        text = dispatch("fetch", FETCH_PROVIDERS, lambda fn: fn(url), accept=_nonempty)
    except AllProvidersFailed:
        return f"Could not fetch this URL; summarize from the candidate's title and snippet instead: {url}"

    return text[:6000] if text else "No content."
