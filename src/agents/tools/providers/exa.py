import os
from datetime import datetime, timedelta, timezone

import httpx

_RECENCY_DAYS = {"day": 1, "week": 7, "month": 30}


def _start_date(recency: str) -> str | None:
    days = _RECENCY_DAYS.get(recency)

    if not days:
        return None

    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def search(query: str, kind: str, gl: str, hl: str, recency: str) -> list[dict]:
    """Adapter: Exa neural/keyword search, mapped to the Serper result shape."""
    body = {"query": query, "numResults": 10, "type": "auto", "contents": {"text": {"maxCharacters": 500}}}

    if kind == "news":
        body["category"] = "news"

    start_date = _start_date(recency)

    if start_date:
        body["startPublishedDate"] = start_date

    response = httpx.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": os.environ["EXA_API_KEY"]},
        json=body,
        timeout=30.0,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    return [
        {
            "title": item.get("title", ""),
            "link": item.get("url", ""),
            "snippet": " ".join((item.get("text") or "").split())[:300],
            "date": item.get("publishedDate", "") or "",
        }
        for item in results
    ]


def fetch(url: str) -> str:
    """Adapter: Exa page contents for `url`, raising on HTTP error."""
    response = httpx.post(
        "https://api.exa.ai/contents",
        headers={"x-api-key": os.environ["EXA_API_KEY"]},
        json={"urls": [url], "text": True},
        timeout=30.0,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    return results[0].get("text", "") if results else ""
