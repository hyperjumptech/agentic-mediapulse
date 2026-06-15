import importlib

import httpx
import pytest

# Import via importlib: agents/tools/__init__.py re-exports `search` and `web_fetch`
# as names on the package, which would shadow the submodules under `import ... as`.
search_module = importlib.import_module("agents.tools.search")
serper_module = importlib.import_module("agents.tools.serper")
web_fetch_module = importlib.import_module("agents.tools.web_fetch")


class FakeResponse:
    def __init__(self, payload, *, raise_error=False):
        self._payload = payload
        self._raise_error = raise_error

    def raise_for_status(self):
        if self._raise_error:
            raise httpx.HTTPStatusError("boom", request=None, response=None)

    def json(self):
        return self._payload


def test_format_results_empty():
    assert serper_module.format_results([]) == "No results found."


def test_format_results_builds_blocks():
    results = [
        {"title": "T1", "link": "https://a.com/1", "snippet": "s1", "date": "2024"},
        {"title": "T2", "link": "https://a.com/2", "snippet": "s2", "date": ""},
    ]
    out = serper_module.format_results(results)
    assert "T1\nhttps://a.com/1\n2024 s1" in out
    assert "\n\n" in out  # blocks separated by a blank line


def test_format_results_caps_at_ten():
    results = [{"title": f"T{index}", "link": f"https://a.com/{index}"} for index in range(15)]
    out = serper_module.format_results(results)
    assert out.count("https://a.com/") == 10


def test_serper_news_endpoint_reads_news_key(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["body"] = json
        return FakeResponse({"news": [{"title": "N"}], "organic": [{"title": "O"}]})

    monkeypatch.setattr(serper_module.httpx, "post", fake_post)
    results = serper_module.serper("news", "query", "id", "en", tbs="qdr:w")
    assert results == [{"title": "N"}]
    assert captured["url"].endswith("/news")
    assert captured["body"] == {"q": "query", "gl": "id", "hl": "en", "tbs": "qdr:w"}


def test_serper_other_endpoint_reads_organic_key(monkeypatch):
    monkeypatch.setattr(serper_module.httpx, "post", lambda *a, **k: FakeResponse({"organic": [{"title": "O"}]}))
    assert serper_module.serper("search", "q", "", "") == [{"title": "O"}]


def test_search_maps_recency_and_endpoint(monkeypatch):
    captured = {}

    def fake_serper(endpoint, query, gl, hl, tbs):
        captured.update(endpoint=endpoint, tbs=tbs)
        return []

    monkeypatch.setattr(search_module, "serper", fake_serper)
    search_module.search("q", kind="news", recency="day")
    assert captured == {"endpoint": "news", "tbs": "qdr:d"}

    search_module.search("q", kind="web", recency="bogus")
    assert captured == {"endpoint": "search", "tbs": ""}


def test_web_fetch_rejects_non_http():
    assert "Not a fetchable URL" in web_fetch_module.web_fetch("ftp://x")


def test_web_fetch_returns_truncated_text(monkeypatch):
    monkeypatch.setattr(web_fetch_module.httpx, "post", lambda *a, **k: FakeResponse({"text": "x" * 7000}))
    out = web_fetch_module.web_fetch("https://a.com/article")
    assert len(out) == 6000


def test_web_fetch_handles_empty_content(monkeypatch):
    monkeypatch.setattr(web_fetch_module.httpx, "post", lambda *a, **k: FakeResponse({}))
    assert web_fetch_module.web_fetch("https://a.com/article") == "No content."


def test_web_fetch_falls_back_on_http_error(monkeypatch):
    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(web_fetch_module.httpx, "post", fake_post)
    out = web_fetch_module.web_fetch("https://a.com/article")
    assert "Could not fetch this URL" in out


@pytest.mark.parametrize("recency,expected", [("day", "qdr:d"), ("week", "qdr:w"), ("month", "qdr:m")])
def test_recency_table(recency, expected):
    assert search_module._RECENCY[recency] == expected
