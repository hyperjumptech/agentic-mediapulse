import os

import httpx


def web_fetch(url: str) -> str:
    """Fetch a web page by URL and return its readable text content."""
    if not url.startswith("http"):
        return "Not a fetchable URL — pass a full http(s) article link."

    try:
        response = httpx.post(
            "https://scrape.serper.dev",
            headers={"X-API-KEY": os.environ["SERPER_API_KEY"]},
            json={"url": url},
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return f"Could not fetch this URL; summarize from the candidate's title and snippet instead: {url}"

    data = response.json()
    text = data.get("text") or data.get("markdown") or ""

    return text[:6000] if text else "No content."
