from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from astrbot.dashboard.services.chat_service import ChatServiceError
from tests.unit.dashboard.fastapi_v1_support import *  # noqa: F403


def _share_service() -> SimpleNamespace:
    return SimpleNamespace(
        create_share=AsyncMock(
            return_value={"share_id": "share-1", "token": "raw-token"}
        ),
        list_shares=AsyncMock(return_value={"shares": []}),
        revoke_share=AsyncMock(return_value={"revoked": True}),
        get_shared_transcript=AsyncMock(
            return_value={"title": "Shared", "messages": []}
        ),
    )


@pytest.mark.asyncio
async def test_owner_share_routes_delegate_to_service(
    asgi_app: FastAPI,
    asgi_client: httpx.AsyncClient,
) -> None:
    stub = _share_service()
    asgi_app.state.services.chat = stub

    created = await asgi_client.post(
        "/api/v1/chat/sessions/sess-1/share",
        json={"expires_in_days": 30},
        headers=_jwt_headers(),
    )
    assert created.status_code == 200
    assert created.json()["data"]["share_id"] == "share-1"
    assert stub.create_share.await_args.args[1] == "sess-1"
    assert stub.create_share.await_args.args[2] == 30

    listed = await asgi_client.get(
        "/api/v1/chat/sessions/sess-1/shares",
        headers=_jwt_headers(),
    )
    assert listed.status_code == 200
    stub.list_shares.assert_awaited_once()

    revoked = await asgi_client.delete(
        "/api/v1/chat/shares/share-1",
        headers=_jwt_headers(),
    )
    assert revoked.status_code == 200
    stub.revoke_share.assert_awaited_once()


@pytest.mark.asyncio
async def test_share_expiry_is_validated(
    asgi_app: FastAPI,
    asgi_client: httpx.AsyncClient,
) -> None:
    stub = _share_service()
    asgi_app.state.services.chat = stub

    response = await asgi_client.post(
        "/api/v1/chat/sessions/sess-1/share",
        json={"expires_in_days": 400},
        headers=_jwt_headers(),
    )

    assert response.status_code == 422
    stub.create_share.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_share_route_requires_no_auth(
    asgi_app: FastAPI,
    asgi_client: httpx.AsyncClient,
) -> None:
    stub = _share_service()
    asgi_app.state.services.chat = stub

    response = await asgi_client.get("/api/v1/shares/raw-token")

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Shared"
    stub.get_shared_transcript.assert_awaited_once_with("raw-token")


@pytest.mark.asyncio
async def test_public_share_route_hides_missing_tokens(
    asgi_app: FastAPI,
    asgi_client: httpx.AsyncClient,
) -> None:
    stub = _share_service()
    stub.get_shared_transcript = AsyncMock(
        side_effect=ChatServiceError("Share not found")
    )
    asgi_app.state.services.chat = stub

    response = await asgi_client.get("/api/v1/shares/missing")

    assert response.status_code == 404
