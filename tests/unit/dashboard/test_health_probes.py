from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from tests.unit.dashboard.fastapi_v1_support import *  # noqa: F403


@pytest.mark.asyncio
async def test_healthz_reports_liveness(asgi_client: httpx.AsyncClient) -> None:
    response = await asgi_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_reports_not_ready_while_starting(
    asgi_client: httpx.AsyncClient,
) -> None:
    response = await asgi_client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


@pytest.mark.asyncio
async def test_readyz_reports_ready_after_startup(
    asgi_app: FastAPI,
    asgi_client: httpx.AsyncClient,
) -> None:
    asgi_app.state.core_control.is_ready = True

    response = await asgi_client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_health_probes_stay_out_of_the_versioned_schema(asgi_app: FastAPI) -> None:
    paths = asgi_app.openapi().get("paths", {})

    assert "/healthz" not in paths
    assert "/readyz" not in paths
