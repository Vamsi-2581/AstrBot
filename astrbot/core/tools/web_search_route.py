"""Normalization for the ordered web search route setting.

Kept dependency-free so both configuration consumers and the search router can
import it without creating an import cycle through the tool catalog.
"""

from __future__ import annotations


def normalize_route(value: object) -> tuple[str, ...]:
    """Return the configured route as an ordered tuple of non-empty names."""

    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(name).strip() for name in value if str(name).strip())
