from types import SimpleNamespace

import pytest

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
