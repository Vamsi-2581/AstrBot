"""Multi-source web search and page fetch routing.

The router turns an ordered ``websearch_route`` into either one fused search
result list or one fetched page.  Search queries every configured route member
in parallel and ranks the surviving pages with reciprocal rank fusion (RRF).
Page fetch reuses the route order but tries configured extraction providers
sequentially, moving on when one fails or times out.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunparse

from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass

from astrbot import logger
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext
from astrbot.core.tools.registry import builtin_tool
from astrbot.core.tools.web_search_route import (
    fetch_available,
    has_configured_keys,
    normalize_route,
)
from astrbot.core.tools.web_search_tools import (
    _WEB_SEARCH_ENABLED_CONFIG,
    SearchResult,
    _anysearch_search,
    _baidu_search,
    _bocha_search,
    _brave_search,
    _deepseek_fetch,
    _deepseek_search,
    _duckduckgo_search,
    _exa_get_contents,
    _exa_search,
    _firecrawl_scrape,
    _firecrawl_search,
    _get_runtime,
    _searxng_search,
    _serpapi_search,
    _tavily_extract,
    _tavily_search,
)
from astrbot.core.utils.error_redaction import safe_error

DEFAULT_RRF_K = 60
DEFAULT_OVERSAMPLE = 8
SOURCE_TIMEOUT_SECONDS = 20.0
MAX_FETCH_URL_LENGTH = 8192
_WEB_SEARCH_DEFAULT_MAX_RESULTS = 7
_WEB_FETCH_DEFAULT_MAX_CHARACTERS = 3000
_FETCH_URL_ERROR = (
    "Error: url must be an HTTP or HTTPS URL with a host, no embedded "
    f"credentials, and at most {MAX_FETCH_URL_LENGTH} characters."
)

_TRACKING_QUERY_KEYS = frozenset({"gclid", "fbclid"})
_TRACKING_QUERY_PREFIXES = ("utm_",)


class NoSearchSourceError(RuntimeError):
    """Raised when no configured source remains in the web search route."""


@dataclass(frozen=True, slots=True)
class SearchSource:
    """One route member: how to fetch, when it is usable, and its result cap."""

    name: str
    fetch: Callable[[dict, str, int], Awaitable[list[SearchResult]]]
    is_configured: Callable[[dict], bool]
    max_candidates: int


def _has_text(provider_settings: dict, setting_name: str) -> bool:
    return bool(str(provider_settings.get(setting_name, "")).strip())


async def _tavily_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _tavily_search(
        provider_settings,
        {
            "query": query,
            "max_results": count,
            "include_favicon": True,
            "search_depth": "basic",
            "topic": "general",
        },
    )


async def _bocha_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _bocha_search(
        provider_settings,
        {"query": query, "count": count, "summary": False},
    )


async def _brave_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _brave_search(
        provider_settings,
        {
            "q": query,
            "count": count,
            "country": "US",
            "search_lang": "zh-hans",
        },
    )


async def _exa_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _exa_search(
        provider_settings,
        {
            "query": query,
            "numResults": count,
            "type": "auto",
            "contents": {"text": {"maxCharacters": 500}},
        },
    )


async def _firecrawl_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _firecrawl_search(
        provider_settings,
        {"query": query, "limit": count, "sources": ["web"]},
    )


async def _baidu_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _baidu_search(
        provider_settings,
        {
            "messages": [{"role": "user", "content": str(query)[:72]}],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [{"type": "web", "top_k": count}],
        },
    )


async def _anysearch_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _anysearch_search(
        provider_settings,
        {"query": query, "max_results": count, "format": "json"},
    )


async def _deepseek_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _deepseek_search(
        provider_settings,
        {"query": query, "count": count, "need_content": False},
    )


async def _serpapi_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _serpapi_search(
        provider_settings,
        {"q": query, "num": count},
    )


async def _searxng_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _searxng_search(
        provider_settings,
        {"query": query, "count": count},
    )


async def _duckduckgo_source(
    provider_settings: dict, query: str, count: int
) -> list[SearchResult]:
    return await _duckduckgo_search(
        provider_settings,
        {"query": query, "count": count},
    )


def _anysearch_configured(provider_settings: dict) -> bool:
    # AnySearch also serves anonymous traffic with a daily free quota.
    return True


def _searxng_configured(provider_settings: dict) -> bool:
    return _has_text(provider_settings, "websearch_searxng_url")


def _duckduckgo_configured(provider_settings: dict) -> bool:
    return True


SEARCH_SOURCES: Mapping[str, SearchSource] = {
    "searxng": SearchSource("searxng", _searxng_source, _searxng_configured, 30),
    "duckduckgo": SearchSource(
        "duckduckgo", _duckduckgo_source, _duckduckgo_configured, 30
    ),
    "tavily": SearchSource(
        "tavily",
        _tavily_source,
        lambda settings: has_configured_keys(settings, "websearch_tavily_key"),
        20,
    ),
    "bocha": SearchSource(
        "bocha",
        _bocha_source,
        lambda settings: has_configured_keys(settings, "websearch_bocha_key"),
        50,
    ),
    "brave": SearchSource(
        "brave",
        _brave_source,
        lambda settings: has_configured_keys(settings, "websearch_brave_key"),
        20,
    ),
    "exa": SearchSource(
        "exa",
        _exa_source,
        lambda settings: has_configured_keys(settings, "websearch_exa_key"),
        20,
    ),
    "firecrawl": SearchSource(
        "firecrawl",
        _firecrawl_source,
        lambda settings: has_configured_keys(settings, "websearch_firecrawl_key"),
        100,
    ),
    "baidu_ai_search": SearchSource(
        "baidu_ai_search",
        _baidu_source,
        lambda settings: _has_text(settings, "websearch_baidu_app_builder_key"),
        50,
    ),
    "anysearch": SearchSource(
        "anysearch",
        _anysearch_source,
        _anysearch_configured,
        10,
    ),
    "deepseek": SearchSource(
        "deepseek",
        _deepseek_source,
        lambda settings: has_configured_keys(settings, "websearch_deepseek_key"),
        50,
    ),
    "serpapi": SearchSource(
        "serpapi",
        _serpapi_source,
        lambda settings: has_configured_keys(settings, "websearch_serpapi_key"),
        10,
    ),
}


def source_is_configured(name: str, provider_settings: dict) -> bool:
    """Return whether one route member has the configuration it needs."""

    source = SEARCH_SOURCES.get(name)
    if source is None:
        return False
    return source.is_configured(provider_settings)


def canonical_url(url: str) -> str:
    """Normalize a result URL for cross-source deduplication.

    Lowercases the scheme and host, drops a leading ``www.``, removes the
    fragment and trailing slash, and strips tracking query parameters.

    Args:
        url: A result URL.

    Returns:
        The canonical key, or an empty string when the URL has no host.
    """

    if not isinstance(url, str) or not url.strip():
        return ""
    raw = url.strip()
    try:
        parsed = urlparse(raw)
        port = parsed.port
    except ValueError:
        return raw
    host = (parsed.hostname or "").lower()
    if not host:
        return raw
    if host.startswith("www."):
        host = host[4:]
    netloc = f"{host}:{port}" if port is not None else host
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_QUERY_KEYS
        and not key.lower().startswith(_TRACKING_QUERY_PREFIXES)
    ]
    return urlunparse(
        (
            (parsed.scheme or "https").lower(),
            netloc,
            path,
            "",
            urlencode(query_pairs),
            "",
        )
    )


def reciprocal_rank_fusion(
    result_lists: Sequence[Sequence[SearchResult]],
    *,
    k: int = DEFAULT_RRF_K,
    limit: int | None = None,
) -> list[SearchResult]:
    """Fuse ranked result lists with reciprocal rank fusion.

    Each occurrence contributes ``1 / (k + rank)`` to its canonical URL; the
    first occurrence supplies the returned title and snippet.  Ties keep the
    order in which canonical URLs first appeared.

    Args:
        result_lists: Ranked result lists, highest priority first.
        k: RRF smoothing constant.
        limit: Optional maximum number of fused results.

    Returns:
        The fused results, highest score first.
    """

    scores: dict[str, float] = {}
    chosen: dict[str, SearchResult] = {}
    position: dict[str, int] = {}
    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            key = canonical_url(result.url)
            if not key:
                continue
            if key not in chosen:
                chosen[key] = result
                position[key] = len(position)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    ranked = sorted(chosen, key=lambda key: (-scores[key], position[key]))
    fused = [chosen[key] for key in ranked]
    return fused[:limit] if limit is not None else fused


async def _run_source(
    source: SearchSource,
    provider_settings: dict,
    query: str,
    per_source: int,
) -> list[SearchResult]:
    count = min(per_source, source.max_candidates)
    try:
        results = await asyncio.wait_for(
            source.fetch(provider_settings, query, count),
            timeout=SOURCE_TIMEOUT_SECONDS,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning(
            "Web search source %s failed: %s",
            source.name,
            safe_error("", exc),
        )
        return []
    return [
        result for result in results if isinstance(result, SearchResult) and result.url
    ]


async def search(
    route: Sequence[str],
    provider_settings: dict,
    *,
    query: str,
    max_results: int,
    oversample: int = DEFAULT_OVERSAMPLE,
) -> list[SearchResult]:
    """Fan out over the route and return one fused, deduplicated result list.

    Args:
        route: Ordered web search source names.
        provider_settings: Provider settings with per-source configuration.
        query: Search query.
        max_results: Target number of fused results.
        oversample: Candidate multiplier applied per source before fusion.

    Returns:
        Fused results, highest score first.

    Raises:
        NoSearchSourceError: If no route member is configured.
    """

    sources: list[SearchSource] = []
    for name in route:
        source = SEARCH_SOURCES.get(name)
        if source is None:
            logger.warning("Ignoring unknown web search source: %s", name)
            continue
        if source.is_configured(provider_settings):
            sources.append(source)
    if not sources:
        raise NoSearchSourceError(
            "No configured web search source in route: " + ", ".join(route),
        )

    target = max(int(max_results), 1)
    per_source = target * max(int(oversample), 1)
    result_lists = await asyncio.gather(
        *(
            _run_source(source, provider_settings, query, per_source)
            for source in sources
        )
    )
    non_empty = [results for results in result_lists if results]
    if not non_empty:
        return []
    return reciprocal_rank_fusion(non_empty, limit=target)


def validate_fetch_url(url: object) -> str:
    """Validate one model-supplied page URL before any provider dispatch.

    Args:
        url: Candidate URL from a tool call.

    Returns:
        The stripped URL.

    Raises:
        ValueError: If the URL is not HTTP(S), has no host, embeds credentials,
            contains whitespace, has invalid port syntax, or exceeds the length
            limit.
    """

    if not isinstance(url, str):
        raise ValueError(_FETCH_URL_ERROR)
    candidate = url.strip()
    if (
        not candidate
        or len(candidate) > MAX_FETCH_URL_LENGTH
        or any(char.isspace() for char in candidate)
    ):
        raise ValueError(_FETCH_URL_ERROR)
    try:
        parsed = urlsplit(candidate)
        # Port syntax and range are validated only when this property is read.
        _ = parsed.port
    except ValueError:
        raise ValueError(_FETCH_URL_ERROR) from None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(_FETCH_URL_ERROR)
    return candidate


def _format_fetched_page(url: str, content: object, title: object = None) -> str:
    lines = [f"URL: {url}"]
    if isinstance(title, str) and title.strip():
        lines.append(f"Title: {title}")
    lines.append(f"Content: {content}")
    return "\n".join(lines)


async def _tavily_fetch(provider_settings: dict, url: str) -> str | None:
    results = await _tavily_extract(
        provider_settings,
        {"urls": [url], "extract_depth": "basic"},
    )
    for result in results:
        if not isinstance(result, dict):
            continue
        content = result.get("raw_content")
        if content:
            return _format_fetched_page(
                str(result.get("url") or url),
                content,
                result.get("title"),
            )
    return None


async def _firecrawl_fetch(provider_settings: dict, url: str) -> str | None:
    result = await _firecrawl_scrape(
        provider_settings,
        {"url": url, "formats": ["markdown"], "onlyMainContent": True},
    )
    if not isinstance(result, dict):
        return None
    content = result.get("markdown")
    if not content:
        return None
    metadata = result.get("metadata")
    title = metadata.get("title") if isinstance(metadata, dict) else None
    return _format_fetched_page(str(result.get("url") or url), content, title)


async def _exa_fetch(provider_settings: dict, url: str) -> str | None:
    results = await _exa_get_contents(
        provider_settings,
        {
            "ids": [url],
            "text": {"maxCharacters": _WEB_FETCH_DEFAULT_MAX_CHARACTERS},
        },
    )
    for result in results:
        if not isinstance(result, dict):
            continue
        content = result.get("text")
        if content:
            return _format_fetched_page(
                str(result.get("url") or url),
                content,
                result.get("title"),
            )
    return None


async def _deepseek_fetch_page(provider_settings: dict, url: str) -> str | None:
    data = await _deepseek_fetch(provider_settings, {"url": url})
    if not isinstance(data, dict):
        return None
    content = data.get("content")
    if not content:
        return None
    return _format_fetched_page(url, content, data.get("title"))


_FETCHERS: Mapping[str, Callable[[dict, str], Awaitable[str | None]]] = {
    "tavily": _tavily_fetch,
    "firecrawl": _firecrawl_fetch,
    "exa": _exa_fetch,
    "deepseek": _deepseek_fetch_page,
}
_WEB_FETCH_SOURCE_NAMES = frozenset(_FETCHERS)


async def fetch_page(
    route: Sequence[str],
    provider_settings: dict,
    url: object,
) -> str | None:
    """Fetch one page from the first working extraction provider in route order.

    Args:
        route: Ordered web search source names.
        provider_settings: Provider settings with per-source configuration.
        url: Candidate page URL.

    Returns:
        Normalized page text, or ``None`` when no provider returned content.

    Raises:
        ValueError: If ``url`` fails :func:`validate_fetch_url`.
    """

    target = validate_fetch_url(url)
    for name in route:
        if name not in _WEB_FETCH_SOURCE_NAMES:
            continue
        fetcher = _FETCHERS.get(name)
        if fetcher is None or not source_is_configured(name, provider_settings):
            continue
        try:
            content = await asyncio.wait_for(
                fetcher(provider_settings, target),
                timeout=SOURCE_TIMEOUT_SECONDS,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "Web fetch source %s failed: %s",
                name,
                safe_error("", exc),
            )
            continue
        if content:
            return content
    return None


def _search_result_payload(results: list[SearchResult]) -> str:
    ref_uuid = str(uuid.uuid4())[:4]
    ret_ls = []
    for idx, result in enumerate(results, 1):
        index = f"{ref_uuid}.{idx}"
        ret_ls.append(
            {
                "title": f"{result.title}",
                "url": f"{result.url}",
                "snippet": f"{result.snippet}",
                "index": index,
            }
        )
    return json.dumps({"results": ret_ls}, ensure_ascii=False)


@builtin_tool(config=_WEB_SEARCH_ENABLED_CONFIG, required_actions=("tool.web_search",))
@pydantic_dataclass
class WebSearchTool(FunctionTool[AstrAgentContext]):
    """Aggregate web search across every source in the configured route."""

    name: str = "web_search"
    description: str = (
        "A web search tool that queries every source configured in the web search "
        "route in parallel, deduplicates results by canonical URL, and fuses them "
        "with reciprocal rank fusion. Use it to gather current information, news, "
        "and detailed web content."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required. Search query."},
                "max_results": {
                    "type": "integer",
                    "description": (
                        "Optional. The maximum number of fused results to return. "
                        "Default is 7."
                    ),
                },
            },
            "required": ["query"],
        }
    )

    async def call(self, context, **kwargs) -> ToolExecResult:
        _, provider_settings, _ = _get_runtime(context)
        route = normalize_route(provider_settings.get("websearch_route"))
        if not route:
            return "Error: web search route is not configured in AstrBot."

        try:
            max_results = int(
                kwargs.get("max_results", _WEB_SEARCH_DEFAULT_MAX_RESULTS)
            )
        except TypeError, ValueError:
            max_results = _WEB_SEARCH_DEFAULT_MAX_RESULTS
        if max_results < 1:
            max_results = _WEB_SEARCH_DEFAULT_MAX_RESULTS

        try:
            oversample = int(
                provider_settings.get("websearch_oversample", DEFAULT_OVERSAMPLE)
            )
        except TypeError, ValueError:
            oversample = DEFAULT_OVERSAMPLE

        try:
            results = await search(
                route,
                provider_settings,
                query=kwargs["query"],
                max_results=max_results,
                oversample=oversample,
            )
        except NoSearchSourceError:
            return "Error: no configured web search source in route: " + ", ".join(
                route
            )
        if not results:
            return "Error: web search does not return any results."
        return _search_result_payload(results)


@builtin_tool(config=_WEB_SEARCH_ENABLED_CONFIG, required_actions=("tool.web_search",))
@pydantic_dataclass
class WebFetchTool(FunctionTool[AstrAgentContext]):
    """Fetch one page through the configured extraction-capable sources."""

    name: str = "web_fetch"
    description: str = (
        "Fetch the text content of one web page through the configured web search "
        "route. Use it to read a known URL, including a page found through web "
        "search."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "Required. HTTP or HTTPS URL with a host, no embedded "
                        f"credentials, and at most {MAX_FETCH_URL_LENGTH} characters."
                    ),
                },
            },
            "required": ["url"],
        }
    )

    async def call(self, context, **kwargs) -> ToolExecResult:
        _, provider_settings, _ = _get_runtime(context)
        route = normalize_route(provider_settings.get("websearch_route"))
        if not route:
            return "Error: web search route is not configured in AstrBot."

        try:
            content = await fetch_page(route, provider_settings, kwargs.get("url"))
        except ValueError as exc:
            return str(exc)
        if not content:
            return (
                "Error: web fetch did not return content from any configured provider."
            )
        return content


__all__ = [
    "DEFAULT_OVERSAMPLE",
    "DEFAULT_RRF_K",
    "MAX_FETCH_URL_LENGTH",
    "NoSearchSourceError",
    "SEARCH_SOURCES",
    "SearchSource",
    "SOURCE_TIMEOUT_SECONDS",
    "WebFetchTool",
    "WebSearchTool",
    "canonical_url",
    "fetch_available",
    "fetch_page",
    "normalize_route",
    "reciprocal_rank_fusion",
    "search",
    "source_is_configured",
    "validate_fetch_url",
]
