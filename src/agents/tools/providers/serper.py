import os

import httpx

_RECENCY = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m"}


def serper(endpoint: str, query: str, gl: str, hl: str, tbs: str = "") -> list[dict]:
    body = {"q": query}

    if gl:
        body["gl"] = gl

    if hl:
        body["hl"] = hl

    if tbs:
        body["tbs"] = tbs

    response = httpx.post(
        f"https://google.serper.dev/{endpoint}",
        headers={"X-API-KEY": os.environ["SERPER_API_KEY"]},
        json=body,
        timeout=30.0,
    )
    response.raise_for_status()

    return response.json().get("news" if endpoint == "news" else "organic", [])


def search(query: str, kind: str, gl: str, hl: str, recency: str) -> list[dict]:
    """Adapter: map the unified search call onto Serper's news/web endpoints."""
    endpoint = "news" if kind == "news" else "search"

    return serper(endpoint, query, gl, hl, _RECENCY.get(recency, ""))


def fetch(url: str) -> str:
    """Adapter: scrape readable text for `url` via Serper, raising on HTTP error."""
    response = httpx.post(
        "https://scrape.serper.dev",
        headers={"X-API-KEY": os.environ["SERPER_API_KEY"]},
        json={"url": url},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    return data.get("text") or data.get("markdown") or ""
