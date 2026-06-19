import os

import httpx


def search(query: str, kind: str, gl: str, hl: str, recency: str) -> list[dict]:
    """Adapter: Tavily search, mapped to the Serper result shape."""
    body = {"query": query, "max_results": 10, "topic": "news" if kind == "news" else "general"}

    if recency in ("day", "week", "month"):
        body["time_range"] = recency

    response = httpx.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
        json=body,
        timeout=30.0,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    return [
        {
            "title": item.get("title", ""),
            "link": item.get("url", ""),
            "snippet": " ".join((item.get("content") or "").split())[:300],
            "date": item.get("published_date", "") or "",
        }
        for item in results
    ]


def fetch(url: str) -> str:
    """Adapter: Tavily extract for `url`, raising on HTTP error."""
    response = httpx.post(
        "https://api.tavily.com/extract",
        headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
        json={"urls": [url]},
        timeout=30.0,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    return results[0].get("raw_content", "") if results else ""
