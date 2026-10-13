from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from tests.unit.dashboard.fastapi_v1_support import *  # noqa: F403


@pytest.mark.asyncio
async def test_metrics_disabled_returns_404(asgi_client: httpx.AsyncClient) -> None:
    response = await asgi_client.get("/metrics")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_metrics_enabled_returns_prometheus_text(
    asgi_app: FastAPI,
    asgi_client: httpx.AsyncClient,
) -> None:
    asgi_app.state.observability.metrics_enabled = True
    asgi_app.state.observability.registry.counter("demo_total", "Demo.").inc()

    response = await asgi_client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "demo_total 1" in response.text


@pytest.mark.asyncio
async def test_metrics_render_backlog_gauge(
    asgi_app: FastAPI,
    asgi_client: httpx.AsyncClient,
) -> None:
    asgi_app.state.observability.metrics_enabled = True
    asgi_app.state.observability.register_backlog_source(lambda: 3)

    response = await asgi_client.get("/metrics")

    assert response.status_code == 200
    assert "astrbot_event_bus_backlog 3" in response.text


def test_metrics_route_stays_out_of_the_versioned_schema(asgi_app: FastAPI) -> None:
    assert "/metrics" not in asgi_app.openapi().get("paths", {})
