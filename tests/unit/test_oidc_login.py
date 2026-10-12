from __future__ import annotations

import pytest
from sqlmodel import select

from astrbot.core.db.po import DashboardAccount, DashboardExternalIdentity
from astrbot.core.db.sqlite import SQLiteDatabase
from astrbot.core.utils.totp import TotpRuntimeState
from astrbot.dashboard.services import auth_service as auth_service_module
from astrbot.dashboard.services.auth_service import (
    AuthService,
    DashboardTokenValidator,
)
from astrbot.dashboard.services.oidc_service import OidcClient, OidcError

_JWT_SECRET = "x" * 32


class _FakeOidcClient:
    def __init__(self, config) -> None:
        self.config = config

    async def build_authorization_url(self, redirect_uri: str):
        return ("https://idp.example.com/authorize?x=1", "state-1", "nonce-1", "v1")

    async def exchange_code(self, code, redirect_uri, code_verifier):
        return {"id_token": "id-token", "access_token": "access-token"}

    async def verify_id_token(self, id_token, nonce):
        return {
            "sub": "subject-123",
            "email": "alice@example.com",
            "preferred_username": "alice",
        }


def _service(db: SQLiteDatabase, **oidc) -> AuthService:
    config = {
        "dashboard": {"jwt_secret": _JWT_SECRET, "oidc": oidc},
        "callback_api_base": "https://astrbot.example.com",
    }
    return AuthService(
        db,
        config,
        demo_mode=False,
        totp_runtime_state=TotpRuntimeState(),
        token_validator=DashboardTokenValidator(_JWT_SECRET),
    )


def test_oidc_client_requires_issuer_and_client_id() -> None:
    with pytest.raises(OidcError):
        OidcClient({"issuer": "", "client_id": ""})
    with pytest.raises(OidcError):
        OidcClient({"issuer": "https://idp", "client_id": ""})


@pytest.mark.asyncio
async def test_oidc_client_builds_pkce_url(monkeypatch) -> None:
    client = OidcClient({"issuer": "https://idp", "client_id": "cid"})

    async def fake_discovery():
        return {
            "issuer": "https://idp",
            "authorization_endpoint": "https://idp/authorize",
            "token_endpoint": "https://idp/token",
        }

    monkeypatch.setattr(client, "discovery", fake_discovery)

    url, state, nonce, verifier = await client.build_authorization_url(
        "https://app/callback"
    )

    assert url.startswith("https://idp/authorize?")
    assert "code_challenge_method=S256" in url
    assert state and nonce and verifier


@pytest.mark.asyncio
async def test_oidc_status_and_start_disabled(temp_db: SQLiteDatabase) -> None:
    service = _service(temp_db)

    status = await service.oidc_status()
    assert status.data == {"enable": False, "button_label": "SSO"}

    started = await service.oidc_start()
    assert started.status_code == 404


@pytest.mark.asyncio
async def test_oidc_callback_rejects_unknown_state(temp_db: SQLiteDatabase) -> None:
    service = _service(temp_db, enable=True, issuer="https://idp", client_id="cid")

    result = await service.oidc_callback("code", "missing-state")

    assert result.status_code == 400


@pytest.mark.asyncio
async def test_oidc_flow_creates_and_reuses_account(
    temp_db: SQLiteDatabase,
    monkeypatch,
) -> None:
    monkeypatch.setattr(auth_service_module, "OidcClient", _FakeOidcClient)
    service = _service(
        temp_db,
        enable=True,
        issuer="https://idp",
        client_id="cid",
        redirect_uri="https://astrbot.example.com/api/v1/auth/oidc/callback",
    )

    started = await service.oidc_start()
    assert started.data["authorize_url"].startswith("https://idp.example.com/")

    first = await service.oidc_callback("code", "state-1")
    assert first.jwt_token
    assert first.data["username"] == "alice"

    async with temp_db.get_db() as session:
        identities = (
            await session.execute(select(DashboardExternalIdentity))
        ).scalars().all()
        accounts = (await session.execute(select(DashboardAccount))).scalars().all()
    assert len(identities) == 1
    assert identities[0].subject == "subject-123"
    assert len(accounts) == 1
    assert accounts[0].created_by == "oidc"

    # A replayed state is single-use and rejected.
    replayed = await service.oidc_callback("code", "state-1")
    assert replayed.status_code == 400

    await service.oidc_start()
    second = await service.oidc_callback("code", "state-1")
    assert second.data["username"] == first.data["username"]


@pytest.mark.asyncio
async def test_oidc_callback_rejects_unlinked_when_auto_create_disabled(
    temp_db: SQLiteDatabase,
    monkeypatch,
) -> None:
    monkeypatch.setattr(auth_service_module, "OidcClient", _FakeOidcClient)
    service = _service(
        temp_db,
        enable=True,
        issuer="https://idp",
        client_id="cid",
        redirect_uri="https://astrbot.example.com/api/v1/auth/oidc/callback",
        auto_create=False,
    )

    await service.oidc_start()
    result = await service.oidc_callback("code", "state-1")

    assert result.status_code == 403
