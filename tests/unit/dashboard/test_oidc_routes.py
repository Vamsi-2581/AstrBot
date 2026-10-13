from __future__ import annotations

import httpx
import pytest

from tests.unit.dashboard.fastapi_v1_support import *  # noqa: F403


@pytest.mark.asyncio
async def test_oidc_status_defaults_disabled(
    asgi_client: httpx.AsyncClient,
) -> None:
    response = await asgi_client.get("/api/v1/auth/oidc/status")

    assert response.status_code == 200
    assert response.json()["data"]["enable"] is False


@pytest.mark.asyncio
async def test_oidc_start_requires_configuration(
    asgi_client: httpx.AsyncClient,
) -> None:
    response = await asgi_client.get("/api/v1/auth/oidc/start")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_oidc_callback_rejects_unknown_state(
    asgi_client: httpx.AsyncClient,
) -> None:
    response = await asgi_client.get(
        "/api/v1/auth/oidc/callback?code=abc&state=missing",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith("/#/auth/login")
