import os

import httpx


def fetch(url: str) -> str:
    """Adapter: Diffbot article extraction for `url`, raising on HTTP error."""
    response = httpx.get(
        "https://api.diffbot.com/v3/article",
        params={"token": os.environ["DIFFBOT_API_KEY"], "url": url},
        timeout=30.0,
    )
    response.raise_for_status()
    objects = response.json().get("objects", [])

    return objects[0].get("text", "") if objects else ""
