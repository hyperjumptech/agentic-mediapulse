import os

import httpx


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
