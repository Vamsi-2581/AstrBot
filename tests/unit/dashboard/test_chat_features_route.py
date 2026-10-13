from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from tests.unit.dashboard.fastapi_v1_support import *  # noqa: F403


@pytest.mark.asyncio
async def test_chat_features_defaults_off(
    asgi_client: httpx.AsyncClient,
) -> None:
    response = await asgi_client.get(
        "/api/v1/chat/features",
        headers=_jwt_headers(),
    )

    assert response.status_code == 200
    assert response.json()["data"]["multi_model"] == {
        "enable": False,
        "max_models": 3,
    }


@pytest.mark.asyncio
async def test_chat_features_reflect_and_clamp_config(
    asgi_app: FastAPI,
    asgi_client: httpx.AsyncClient,
) -> None:
    asgi_app.state.astrbot_config["dashboard"] = {
        "chatui_multi_model": {"enable": True, "max_models": 99}
    }

    response = await asgi_client.get(
        "/api/v1/chat/features",
        headers=_jwt_headers(),
    )

    assert response.status_code == 200
    assert response.json()["data"]["multi_model"] == {
        "enable": True,
        "max_models": 8,
    }
