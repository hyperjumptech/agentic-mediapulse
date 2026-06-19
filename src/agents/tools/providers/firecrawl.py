import os

import httpx


def fetch(url: str) -> str:
    """Adapter: Firecrawl scrape for `url` as markdown, raising on HTTP error."""
    response = httpx.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {os.environ['FIRECRAWL_API_KEY']}"},
        json={"url": url, "formats": ["markdown"]},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json().get("data", {})

    return data.get("markdown", "") or ""
