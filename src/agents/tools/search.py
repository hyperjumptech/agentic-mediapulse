from agents.tools.serper import format_results, serper

_RECENCY = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m"}


def search(query: str, kind: str = "news", gl: str = "", hl: str = "", recency: str = "week") -> str:
    """Search for the query and return titles, URLs, and snippets.

    kind is 'news' (default, recent articles) or 'web' (general results). gl/hl are the
    Serper country/language codes that localize results to the subject's home market.
    recency limits results by age: 'day' (last 24h), 'week' (default), 'month', or '' for any time.
    """
    endpoint = "news" if kind == "news" else "search"

    return format_results(serper(endpoint, query, gl, hl, _RECENCY.get(recency, "")))
