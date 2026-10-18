import asyncio
from types import SimpleNamespace

import pytest

from astrbot.core.tools import web_search_route as route
from astrbot.core.tools import web_search_router as router
from astrbot.core.tools import web_search_tools as tools


def _result(url: str, title: str = "title", snippet: str = "snippet"):
    return tools.SearchResult(title=title, url=url, snippet=snippet)


def test_canonical_url_normalizes_equivalent_urls():
    assert router.canonical_url(
        "https://WWW.Example.com/path/?utm_source=x#frag"
    ) == router.canonical_url("https://example.com/path")
    assert router.canonical_url(
        "https://example.com/path/?gclid=1&fbclid=2&q=keep"
    ) == router.canonical_url("https://example.com/path?q=keep")


def test_canonical_url_keeps_distinct_hosts_apart():
    assert router.canonical_url("https://example.com/a") != router.canonical_url(
        "https://other.com/a"
    )


def test_canonical_url_tolerates_a_malformed_port():
    assert router.canonical_url("https://example.com:not-a-port/a") == (
        "https://example.com:not-a-port/a"
    )


def test_reciprocal_rank_fusion_prefers_shared_results():
    first = [
        _result("https://shared.example/1"),
        _result("https://only-a.example/1"),
    ]
    second = [
        _result("https://only-b.example/1"),
        _result("https://shared.example/1"),
    ]

    fused = router.reciprocal_rank_fusion([first, second])

    assert fused[0].url == "https://shared.example/1"
    assert [item.url for item in fused] == [
        "https://shared.example/1",
        "https://only-b.example/1",
        "https://only-a.example/1",
    ]


def test_reciprocal_rank_fusion_deduplicates_and_limits():
    fused = router.reciprocal_rank_fusion(
        [[_result("https://a.example/1"), _result("https://b.example/1")]],
        limit=1,
    )

    assert [item.url for item in fused] == ["https://a.example/1"]


def test_reciprocal_rank_fusion_skips_urlless_results():
    fused = router.reciprocal_rank_fusion(
        [[_result(""), _result("https://a.example/1")]]
    )

    assert [item.url for item in fused] == ["https://a.example/1"]


def _fake_source(name, fetch, configured=True, max_candidates=100):
    return router.SearchSource(
        name=name,
        fetch=fetch,
        is_configured=lambda settings: configured,
        max_candidates=max_candidates,
    )


@pytest.mark.asyncio
async def test_search_fans_out_and_fuses(monkeypatch):
    async def source_a(settings, query, count):
        assert count == 16
        return [_result("https://a.example/1"), _result("https://shared.example/1")]

    async def source_b(settings, query, count):
        return [_result("https://b.example/1"), _result("https://shared.example/1")]

    monkeypatch.setattr(
        router,
        "SEARCH_SOURCES",
        {
            "a": _fake_source("a", source_a),
            "b": _fake_source("b", source_b),
        },
    )

    fused = await router.search(["a", "b"], {}, query="q", max_results=2, oversample=8)

    assert fused[0].url == "https://shared.example/1"
    assert len(fused) == 2


@pytest.mark.asyncio
async def test_search_isolates_a_failing_source(monkeypatch):
    async def failing(settings, query, count):
        raise RuntimeError("boom")

    async def working(settings, query, count):
        return [_result("https://ok.example/1")]

    monkeypatch.setattr(
        router,
        "SEARCH_SOURCES",
        {
            "bad": _fake_source("bad", failing),
            "good": _fake_source("good", working),
        },
    )

    fused = await router.search(["bad", "good"], {}, query="q", max_results=5)

    assert [item.url for item in fused] == ["https://ok.example/1"]


@pytest.mark.asyncio
async def test_search_skips_unconfigured_sources(monkeypatch):
    async def working(settings, query, count):
        return [_result("https://ok.example/1")]

    monkeypatch.setattr(
        router,
        "SEARCH_SOURCES",
        {
            "off": _fake_source("off", working, configured=False),
            "on": _fake_source("on", working),
        },
    )

    fused = await router.search(["off", "on"], {}, query="q", max_results=5)

    assert [item.url for item in fused] == ["https://ok.example/1"]


@pytest.mark.asyncio
async def test_search_raises_when_no_source_configured(monkeypatch):
    async def working(settings, query, count):
        return [_result("https://ok.example/1")]

    monkeypatch.setattr(
        router,
        "SEARCH_SOURCES",
        {"off": _fake_source("off", working, configured=False)},
    )

    with pytest.raises(router.NoSearchSourceError):
        await router.search(["off"], {}, query="q", max_results=5)


def test_source_is_configured_reads_expected_keys():
    assert router.source_is_configured("duckduckgo", {}) is True
    assert router.source_is_configured("searxng", {}) is False
    assert (
        router.source_is_configured(
            "searxng", {"websearch_searxng_url": "http://localhost:8080"}
        )
        is True
    )
    assert router.source_is_configured("tavily", {}) is False
    assert (
        router.source_is_configured("tavily", {"websearch_tavily_key": ["k"]}) is True
    )
    assert router.source_is_configured("unknown", {}) is False


class _FakeResponse:
    def __init__(self, status=200, json_data=None, text_data=""):
        self.status = status
        self._json_data = json_data or {}
        self._text_data = text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def json(self, content_type=None):
        return self._json_data

    async def text(self):
        return self._text_data


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return self.response

    def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return self.response


@pytest.mark.asyncio
async def test_searxng_search_maps_json_results(monkeypatch):
    session = _FakeSession(
        _FakeResponse(
            status=200,
            json_data={
                "results": [
                    {
                        "title": "AstrBot",
                        "url": "https://example.com",
                        "content": "result",
                        "favicon": "https://example.com/favicon.ico",
                    }
                ]
            },
        )
    )
    monkeypatch.setattr(tools, "_client_session", lambda **kwargs: session)
    monkeypatch.setattr(
        tools,
        "validate_outbound_url",
        lambda url, policy: SimpleNamespace(url=url),
    )

    results = await tools._searxng_search(
        {"websearch_searxng_url": "http://searx.internal:8080"},
        {"query": "AstrBot"},
    )

    assert results == [
        tools.SearchResult(
            title="AstrBot",
            url="https://example.com",
            snippet="result",
            favicon="https://example.com/favicon.ico",
        )
    ]
    method, url, kwargs = session.requests[0]
    assert method == "GET"
    assert url == "http://searx.internal:8080/search"
    assert kwargs["params"]["format"] == "json"
    assert kwargs["allow_redirects"] is False


@pytest.mark.asyncio
async def test_searxng_search_requires_url():
    with pytest.raises(ValueError, match="SearXNG"):
        await tools._searxng_search({}, {"query": "AstrBot"})


@pytest.mark.asyncio
async def test_duckduckgo_search_parses_html(monkeypatch):
    html = """
    <div class="result">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&amp;rut=x">AstrBot</a>
      <a class="result__snippet">A snippet</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://direct.example/b">Direct</a>
    </div>
    """
    session = _FakeSession(_FakeResponse(status=200, text_data=html))
    monkeypatch.setattr(tools, "_client_session", lambda **kwargs: session)

    results = await tools._duckduckgo_search({}, {"query": "AstrBot"})

    assert results[0].url == "https://example.com/a"
    assert results[0].title == "AstrBot"
    assert results[0].snippet == "A snippet"
    assert results[1].url == "https://direct.example/b"


def test_decode_duckduckgo_url_handles_wrappers_and_plain_links():
    assert (
        tools._decode_duckduckgo_url(
            "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa"
        )
        == "https://example.com/a"
    )
    assert tools._decode_duckduckgo_url("https://example.com/b") == (
        "https://example.com/b"
    )
    assert tools._decode_duckduckgo_url("") == ""


def test_deepseek_source_requires_api_key():
    assert router.source_is_configured("deepseek", {}) is False
    assert (
        router.source_is_configured("deepseek", {"websearch_deepseek_key": ["key"]})
        is True
    )


@pytest.mark.asyncio
async def test_deepseek_source_requests_summaries(monkeypatch):
    calls = []

    async def fake_search(provider_settings, payload):
        calls.append((provider_settings, payload))
        return [_result("https://example.com")]

    monkeypatch.setattr(router, "_deepseek_search", fake_search)
    settings = {"websearch_deepseek_key": ["key"]}

    results = await router._deepseek_source(settings, "AstrBot", 12)

    assert [item.url for item in results] == ["https://example.com"]
    assert calls == [
        (
            settings,
            {"query": "AstrBot", "count": 12, "need_content": False},
        )
    ]


def test_serpapi_source_requires_api_key():
    assert router.source_is_configured("serpapi", {}) is False
    assert (
        router.source_is_configured("serpapi", {"websearch_serpapi_key": ["key"]})
        is True
    )


@pytest.mark.asyncio
async def test_serpapi_source_uses_google_web_search(monkeypatch):
    calls = []

    async def fake_search(provider_settings, payload):
        calls.append((provider_settings, payload))
        return [_result("https://example.com")]

    monkeypatch.setattr(router, "_serpapi_search", fake_search)
    settings = {"websearch_serpapi_key": ["key"]}

    results = await router._serpapi_source(settings, "AstrBot", 8)

    assert [item.url for item in results] == ["https://example.com"]
    assert calls == [(settings, {"q": "AstrBot", "num": 8})]


def _context_with_provider_settings(provider_settings):
    config = {"provider_settings": provider_settings}
    agent_context = SimpleNamespace(
        context=SimpleNamespace(get_config=lambda umo: config),
        event=SimpleNamespace(unified_msg_origin="test:private:session"),
    )
    return SimpleNamespace(context=agent_context)


def test_fetch_available_requires_configured_extraction_source():
    assert route.fetch_available(["searxng", "duckduckgo"], {}) is False
    assert router.fetch_available(["tavily"], {}) is False
    assert router.fetch_available(["tavily"], {"websearch_tavily_key": ["k"]}) is True
    assert (
        router.fetch_available(["firecrawl"], {"websearch_firecrawl_key": ["k"]})
        is True
    )
    assert router.fetch_available(["exa"], {"websearch_exa_key": ["k"]}) is True
    assert (
        router.fetch_available(["deepseek"], {"websearch_deepseek_key": ["k"]}) is True
    )


def test_fetch_sources_match_availability_settings():
    assert set(router._FETCHERS) == set(route.FETCH_SOURCE_KEY_SETTINGS)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://",
        "https://user:pass@example.com",
        "https://example.com:not-a-port",
        "https://exa mple.com",
        "https://example.com/" + ("a" * router.MAX_FETCH_URL_LENGTH),
        123,
        "",
    ],
)
def test_validate_fetch_url_rejects_unsafe_inputs(url):
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        router.validate_fetch_url(url)


def test_validate_fetch_url_accepts_http_and_https():
    assert router.validate_fetch_url("https://example.com/path?q=1") == (
        "https://example.com/path?q=1"
    )
    assert router.validate_fetch_url("  http://example.com  ") == ("http://example.com")


@pytest.mark.asyncio
async def test_fetch_page_uses_fixed_provider_defaults(monkeypatch):
    url = "https://example.com/page"
    calls = {}

    async def fake_tavily(settings, payload):
        calls["tavily"] = payload
        return [{"url": url, "raw_content": "tavily content"}]

    async def fake_firecrawl(settings, payload):
        calls["firecrawl"] = payload
        return {"url": url, "markdown": "firecrawl content"}

    async def fake_exa(settings, payload):
        calls["exa"] = payload
        return [{"url": url, "text": "exa content"}]

    async def fake_deepseek(settings, payload):
        calls["deepseek"] = payload
        return {"title": "Example", "content": "deepseek content"}

    monkeypatch.setattr(router, "_tavily_extract", fake_tavily)
    monkeypatch.setattr(router, "_firecrawl_scrape", fake_firecrawl)
    monkeypatch.setattr(router, "_exa_get_contents", fake_exa)
    monkeypatch.setattr(router, "_deepseek_fetch", fake_deepseek)

    settings = {
        "websearch_tavily_key": ["k"],
        "websearch_firecrawl_key": ["k"],
        "websearch_exa_key": ["k"],
        "websearch_deepseek_key": ["k"],
    }

    assert await router.fetch_page(["tavily"], settings, url) == (
        f"URL: {url}\nContent: tavily content"
    )
    assert await router.fetch_page(["firecrawl"], settings, url) == (
        f"URL: {url}\nContent: firecrawl content"
    )
    assert await router.fetch_page(["exa"], settings, url) == (
        f"URL: {url}\nContent: exa content"
    )
    assert await router.fetch_page(["deepseek"], settings, url) == (
        f"URL: {url}\nTitle: Example\nContent: deepseek content"
    )

    assert calls["tavily"] == {"urls": [url], "extract_depth": "basic"}
    assert calls["firecrawl"] == {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }
    assert "timeout" not in calls["firecrawl"]
    assert "maxAge" not in calls["firecrawl"]
    assert calls["exa"] == {"ids": [url], "text": {"maxCharacters": 3000}}
    assert calls["deepseek"] == {"url": url}


@pytest.mark.asyncio
async def test_fetch_page_follows_route_order_and_fails_over(monkeypatch):
    calls = []

    async def failing_tavily(settings, payload):
        calls.append("tavily")
        raise RuntimeError("tavily failed")

    async def working_firecrawl(settings, payload):
        calls.append("firecrawl")
        return {"markdown": "fallback content"}

    async def unused_exa(settings, payload):
        calls.append("exa")
        return [{"text": "exa content"}]

    monkeypatch.setattr(router, "_tavily_extract", failing_tavily)
    monkeypatch.setattr(router, "_firecrawl_scrape", working_firecrawl)
    monkeypatch.setattr(router, "_exa_get_contents", unused_exa)

    settings = {
        "websearch_tavily_key": ["k"],
        "websearch_firecrawl_key": ["k"],
        "websearch_exa_key": ["k"],
    }

    result = await router.fetch_page(
        ["searxng", "tavily", "firecrawl", "exa"],
        settings,
        "https://example.com/page",
    )

    assert result == "URL: https://example.com/page\nContent: fallback content"
    assert calls == ["tavily", "firecrawl"]


@pytest.mark.asyncio
async def test_fetch_page_fails_over_after_empty_source_result(monkeypatch):
    calls = []

    async def empty_tavily(settings, payload):
        calls.append("tavily")
        return [{"url": "https://example.com/page", "raw_content": ""}]

    async def working_firecrawl(settings, payload):
        calls.append("firecrawl")
        return {"markdown": "fallback content"}

    monkeypatch.setattr(router, "_tavily_extract", empty_tavily)
    monkeypatch.setattr(router, "_firecrawl_scrape", working_firecrawl)

    settings = {
        "websearch_tavily_key": ["k"],
        "websearch_firecrawl_key": ["k"],
    }

    result = await router.fetch_page(
        ["tavily", "firecrawl"],
        settings,
        "https://example.com/page",
    )

    assert result == "URL: https://example.com/page\nContent: fallback content"
    assert calls == ["tavily", "firecrawl"]


@pytest.mark.asyncio
async def test_fetch_page_skips_unconfigured_extraction_sources(monkeypatch):
    calls = []

    async def fake_tavily(settings, payload):
        calls.append("tavily")
        return [{"raw_content": "content"}]

    monkeypatch.setattr(router, "_tavily_extract", fake_tavily)

    assert (
        await router.fetch_page(
            ["searxng", "tavily"],
            {},
            "https://example.com/page",
        )
        is None
    )
    assert calls == []


@pytest.mark.asyncio
async def test_fetch_page_moves_on_after_timeout(monkeypatch):
    async def slow_tavily(settings, payload):
        await asyncio.sleep(1)
        return [{"raw_content": "too late"}]

    async def fast_firecrawl(settings, payload):
        return {"markdown": "in time"}

    monkeypatch.setattr(router, "_tavily_extract", slow_tavily)
    monkeypatch.setattr(router, "_firecrawl_scrape", fast_firecrawl)
    monkeypatch.setattr(router, "SOURCE_TIMEOUT_SECONDS", 0.01)

    settings = {
        "websearch_tavily_key": ["k"],
        "websearch_firecrawl_key": ["k"],
    }

    result = await router.fetch_page(
        ["tavily", "firecrawl"],
        settings,
        "https://example.com/page",
    )

    assert result == "URL: https://example.com/page\nContent: in time"


@pytest.mark.asyncio
async def test_fetch_page_returns_none_and_logs_redacted_failures(monkeypatch, caplog):
    async def failing_tavily(settings, payload):
        raise RuntimeError("failed at https://secret.example/path?api_key=abc")

    monkeypatch.setattr(router, "_tavily_extract", failing_tavily)

    result = await router.fetch_page(
        ["tavily"],
        {"websearch_tavily_key": ["k"]},
        "https://example.com/page",
    )

    assert result is None
    assert "https://secret.example" not in caplog.text
    assert "Web fetch source tavily failed" in caplog.text


@pytest.mark.asyncio
async def test_web_fetch_tool_returns_content(monkeypatch):
    async def fake_fetch_page(route, provider_settings, url):
        assert route == ("tavily",)
        return "URL: https://example.com\nContent: page"

    monkeypatch.setattr(router, "fetch_page", fake_fetch_page)
    tool = router.WebFetchTool()
    context = _context_with_provider_settings(
        {"websearch_route": ["tavily"], "websearch_tavily_key": ["k"]}
    )

    result = await tool.call(context, url="https://example.com")

    assert result == "URL: https://example.com\nContent: page"


@pytest.mark.asyncio
async def test_web_fetch_tool_returns_generic_error_when_all_providers_fail(
    monkeypatch,
):
    async def fake_fetch_page(route, provider_settings, url):
        return None

    monkeypatch.setattr(router, "fetch_page", fake_fetch_page)
    tool = router.WebFetchTool()
    context = _context_with_provider_settings(
        {"websearch_route": ["tavily"], "websearch_tavily_key": ["k"]}
    )

    result = await tool.call(context, url="https://example.com")

    assert result == (
        "Error: web fetch did not return content from any configured provider."
    )


@pytest.mark.asyncio
async def test_web_fetch_tool_rejects_invalid_url_before_dispatch(monkeypatch):
    calls = []

    async def fake_tavily(settings, payload):
        calls.append(payload)
        return [{"raw_content": "content"}]

    monkeypatch.setattr(router, "_tavily_extract", fake_tavily)
    tool = router.WebFetchTool()
    context = _context_with_provider_settings(
        {"websearch_route": ["tavily"], "websearch_tavily_key": ["k"]}
    )

    result = await tool.call(context, url="file:///etc/passwd")

    assert result == router._FETCH_URL_ERROR
    assert calls == []


@pytest.mark.asyncio
async def test_web_fetch_tool_reports_missing_route():
    tool = router.WebFetchTool()
    context = _context_with_provider_settings({})

    result = await tool.call(context, url="https://example.com")

    assert result.startswith("Error: web search route")
