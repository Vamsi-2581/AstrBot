"""Normalization and availability helpers for the web search route setting.

Kept dependency-free so both configuration consumers and the search router can
import it without creating an import cycle through the tool catalog.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

FETCH_SOURCE_KEY_SETTINGS: Mapping[str, str] = {
    "tavily": "websearch_tavily_key",
    "firecrawl": "websearch_firecrawl_key",
    "exa": "websearch_exa_key",
    "deepseek": "websearch_deepseek_key",
}


def normalize_route(value: object) -> tuple[str, ...]:
    """Return the configured route as an ordered tuple of non-empty names."""

    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(name).strip() for name in value if str(name).strip())


def has_configured_keys(
    provider_settings: Mapping[str, object],
    setting_name: str,
) -> bool:
    """Return whether a key-list setting contains at least one non-blank key."""

    value = provider_settings.get(setting_name)
    if not isinstance(value, list | tuple):
        return False
    return any(str(item).strip() for item in value)


def fetch_available(
    route: Sequence[str],
    provider_settings: Mapping[str, object],
) -> bool:
    """Return whether the route has a configured page-extraction source."""

    return any(
        (setting := FETCH_SOURCE_KEY_SETTINGS.get(name)) is not None
        and has_configured_keys(provider_settings, setting)
        for name in route
    )
