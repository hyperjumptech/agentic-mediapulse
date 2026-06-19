import importlib

import httpx
import pytest

from agents.tools.providers.dispatch import AllProvidersFailed, Provider, dispatch, reset_cursor

# Import the provider/tool modules via importlib: `agents.tools` re-exports `web_search`/`web_fetch`
# as function names that would shadow the submodules under `import ... as`.
serper_module = importlib.import_module("agents.tools.providers.serper")
exa_module = importlib.import_module("agents.tools.providers.exa")
tavily_module = importlib.import_module("agents.tools.providers.tavily")
firecrawl_module = importlib.import_module("agents.tools.providers.firecrawl")
diffbot_module = importlib.import_module("agents.tools.providers.diffbot")
web_search_module = importlib.import_module("agents.tools.web_search")
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


# --- format_results (now lives in web_search) ---


def test_format_results_empty():
    assert web_search_module.format_results([]) == "No results found."


def test_format_results_builds_blocks():
    results = [
        {"title": "T1", "link": "https://a.com/1", "snippet": "s1", "date": "2024"},
        {"title": "T2", "link": "https://a.com/2", "snippet": "s2", "date": ""},
    ]
    out = web_search_module.format_results(results)
    assert "T1\nhttps://a.com/1\n2024 s1" in out
    assert "\n\n" in out


def test_format_results_caps_at_ten():
    results = [{"title": f"T{index}", "link": f"https://a.com/{index}"} for index in range(15)]
    out = web_search_module.format_results(results)
    assert out.count("https://a.com/") == 10


# --- Serper low-level client + adapter ---


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


def test_serper_search_maps_recency_and_endpoint(monkeypatch):
    captured = {}

    def fake_serper(endpoint, query, gl, hl, tbs):
        captured.update(endpoint=endpoint, tbs=tbs)
        return []

    monkeypatch.setattr(serper_module, "serper", fake_serper)
    serper_module.search("q", "news", "", "", "day")
    assert captured == {"endpoint": "news", "tbs": "qdr:d"}

    serper_module.search("q", "web", "", "", "bogus")
    assert captured == {"endpoint": "search", "tbs": ""}


@pytest.mark.parametrize("recency,expected", [("day", "qdr:d"), ("week", "qdr:w"), ("month", "qdr:m")])
def test_recency_table(recency, expected):
    assert serper_module._RECENCY[recency] == expected


# --- Exa adapter ---


def test_exa_search_maps_to_serper_shape(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "exa-key")
    captured = {}
    item = {"title": "T", "url": "https://a.com/x", "publishedDate": "2026-01-01", "text": "hello  world"}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json
        return FakeResponse({"results": [item]})

    monkeypatch.setattr(exa_module.httpx, "post", fake_post)
    results = exa_module.search("apple", "news", "id", "id", "week")
    assert captured["url"] == "https://api.exa.ai/search"
    assert captured["headers"]["x-api-key"] == "exa-key"
    assert captured["body"]["category"] == "news"
    assert "startPublishedDate" in captured["body"]
    assert results == [{"title": "T", "link": "https://a.com/x", "snippet": "hello world", "date": "2026-01-01"}]


def test_exa_fetch_returns_text(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "exa-key")
    monkeypatch.setattr(exa_module.httpx, "post", lambda *a, **k: FakeResponse({"results": [{"text": "body"}]}))
    assert exa_module.fetch("https://a.com/x") == "body"


def test_exa_fetch_empty_without_results(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "exa-key")
    monkeypatch.setattr(exa_module.httpx, "post", lambda *a, **k: FakeResponse({"results": []}))
    assert exa_module.fetch("https://a.com/x") == ""


# --- Tavily adapter ---


def test_tavily_search_maps_to_serper_shape(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tav-key")
    captured = {}
    item = {"title": "T", "url": "https://a.com/y", "content": "snip", "published_date": "2026-02-02"}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json
        return FakeResponse({"results": [item]})

    monkeypatch.setattr(tavily_module.httpx, "post", fake_post)
    results = tavily_module.search("apple", "news", "", "", "week")
    assert captured["url"] == "https://api.tavily.com/search"
    assert captured["headers"]["Authorization"] == "Bearer tav-key"
    assert captured["body"]["topic"] == "news"
    assert captured["body"]["time_range"] == "week"
    assert results == [{"title": "T", "link": "https://a.com/y", "snippet": "snip", "date": "2026-02-02"}]


def test_tavily_fetch_returns_raw_content(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tav-key")

    def fake_post(*a, **k):
        return FakeResponse({"results": [{"raw_content": "raw"}]})

    monkeypatch.setattr(tavily_module.httpx, "post", fake_post)
    assert tavily_module.fetch("https://a.com/y") == "raw"


# --- Firecrawl adapter ---


def test_firecrawl_fetch_returns_markdown(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-key")
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse({"success": True, "data": {"markdown": "# md"}})

    monkeypatch.setattr(firecrawl_module.httpx, "post", fake_post)
    out = firecrawl_module.fetch("https://a.com/z")
    assert captured["url"] == "https://api.firecrawl.dev/v1/scrape"
    assert captured["headers"]["Authorization"] == "Bearer fc-key"
    assert out == "# md"


# --- Diffbot adapter ---


def test_diffbot_fetch_returns_text(monkeypatch):
    monkeypatch.setenv("DIFFBOT_API_KEY", "db-key")
    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse({"objects": [{"text": "article"}]})

    monkeypatch.setattr(diffbot_module.httpx, "get", fake_get)
    out = diffbot_module.fetch("https://a.com/article")
    assert captured["url"] == "https://api.diffbot.com/v3/article"
    assert captured["params"] == {"token": "db-key", "url": "https://a.com/article"}
    assert out == "article"


# --- dispatch engine (fake providers) ---


def test_dispatch_round_robin_rotates(monkeypatch):
    monkeypatch.setenv("A_KEY", "1")
    monkeypatch.setenv("B_KEY", "1")
    reset_cursor()
    providers = [Provider("a", "A_KEY", lambda: "A"), Provider("b", "B_KEY", lambda: "B")]
    assert dispatch("search", providers, lambda fn: fn(), accept=bool) == "A"
    assert dispatch("search", providers, lambda fn: fn(), accept=bool) == "B"
    assert dispatch("search", providers, lambda fn: fn(), accept=bool) == "A"


def test_dispatch_fails_over_on_error(monkeypatch):
    monkeypatch.setenv("A_KEY", "1")
    monkeypatch.setenv("B_KEY", "1")
    reset_cursor()

    def boom():
        raise RuntimeError("down")

    providers = [Provider("a", "A_KEY", boom), Provider("b", "B_KEY", lambda: "B")]
    assert dispatch("search", providers, lambda fn: fn(), accept=bool) == "B"


def test_dispatch_all_errored_raises_named(monkeypatch):
    monkeypatch.setenv("A_KEY", "1")
    monkeypatch.setenv("B_KEY", "1")
    reset_cursor()

    def boom_a():
        raise RuntimeError("a-down")

    def boom_b():
        raise ValueError("b-down")

    providers = [Provider("a", "A_KEY", boom_a), Provider("b", "B_KEY", boom_b)]

    with pytest.raises(AllProvidersFailed) as excinfo:
        dispatch("search", providers, lambda fn: fn(), accept=bool)

    message = str(excinfo.value)
    assert "all search providers failed" in message
    assert "a=" in message
    assert "b=" in message


def test_dispatch_returns_empty_result_without_raising(monkeypatch):
    monkeypatch.setenv("A_KEY", "1")
    reset_cursor()
    providers = [Provider("a", "A_KEY", lambda: [])]
    assert dispatch("search", providers, lambda fn: fn(), accept=bool) == []


def test_dispatch_skips_unconfigured_providers(monkeypatch):
    monkeypatch.delenv("A_KEY", raising=False)
    monkeypatch.setenv("B_KEY", "1")
    reset_cursor()
    providers = [Provider("a", "A_KEY", lambda: "A"), Provider("b", "B_KEY", lambda: "B")]
    assert dispatch("search", providers, lambda fn: fn(), accept=bool) == "B"


def test_dispatch_no_providers_raises(monkeypatch):
    monkeypatch.delenv("A_KEY", raising=False)
    reset_cursor()
    providers = [Provider("a", "A_KEY", lambda: "A")]

    with pytest.raises(AllProvidersFailed):
        dispatch("search", providers, lambda fn: fn(), accept=bool)


# --- web_search / web_fetch routing (Serper active via conftest) ---


def test_web_search_routes_and_formats(monkeypatch):
    reset_cursor()

    def fake_serper(endpoint, query, gl, hl, tbs):
        return [{"title": "T", "link": "https://a.com/1", "snippet": "s", "date": "2026"}]

    monkeypatch.setattr(serper_module, "serper", fake_serper)
    out = web_search_module.web_search("apple")
    assert "https://a.com/1" in out


def test_web_fetch_rejects_non_http():
    assert "Not a fetchable URL" in web_fetch_module.web_fetch("ftp://x")


def test_web_fetch_returns_truncated_text(monkeypatch):
    reset_cursor()
    monkeypatch.setattr(serper_module.httpx, "post", lambda *a, **k: FakeResponse({"text": "x" * 7000}))
    out = web_fetch_module.web_fetch("https://a.com/article")
    assert len(out) == 6000


def test_web_fetch_handles_empty_content(monkeypatch):
    reset_cursor()
    monkeypatch.setattr(serper_module.httpx, "post", lambda *a, **k: FakeResponse({}))
    assert web_fetch_module.web_fetch("https://a.com/article") == "No content."


def test_web_fetch_falls_back_when_all_providers_fail(monkeypatch):
    reset_cursor()

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(serper_module.httpx, "post", boom)
    out = web_fetch_module.web_fetch("https://a.com/article")
    assert "Could not fetch this URL" in out


def test_web_fetch_fails_over_to_next_provider(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "exa-key")
    reset_cursor()

    def fake_post(url, *a, **k):
        if "serper" in url:
            raise httpx.ConnectError("serper down")

        return FakeResponse({"results": [{"text": "exa body"}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert web_fetch_module.web_fetch("https://a.com/article") == "exa body"
