"""Dashboard trace history and detail contract coverage."""

import time

import pytest

from astrbot.core.utils.trace_store import TraceStore
from astrbot.dashboard.services import log_service

from tests.unit.dashboard.fastapi_v1_support import (  # noqa: F401
    _jwt_headers,
    asgi_client,
)


@pytest.mark.asyncio
async def test_v1_persistent_trace_routes(asgi_client, monkeypatch, tmp_path):
    """Verify durable history/detail validation and dashboard authentication."""
    store = TraceStore(tmp_path / "traces.db", {"trace": {"db_max_mb": 8}})
    monkeypatch.setattr(log_service, "get_trace_store", lambda *_: store)
    stamp = str(time.time_ns())
    trace_id = "a" * 32
    span_id = "b" * 16
    summary = {
        "trace_id": trace_id,
        "root_span_id": span_id,
        "start_time_unix_nano": stamp,
        "end_time_unix_nano": stamp,
        "updated_time_unix_nano": stamp,
        "state": "completed",
        "has_errors": False,
        "has_models": False,
        "has_plugins": False,
        "span_count": 1,
        "attributes": {"astrbot.message_outline": "Hello"},
    }
    try:
        assert store.append(
            {
                "trace": summary,
                "time_unix_nano": stamp,
                "span": {
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "parent_span_id": None,
                    "name": "message",
                    "start_time_unix_nano": stamp,
                    "end_time_unix_nano": stamp,
                    "attributes": {},
                    "status": {"code": 1},
                },
            }
        )
        assert store.flush()
        assert (await asgi_client.get("/api/v1/trace/history")).status_code == 401
        headers = _jwt_headers()
        response = await asgi_client.get(
            "/api/v1/trace/history",
            params={"limit": 1, "query": "Hello"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["total"] == 1
        response = await asgi_client.get(
            "/api/v1/trace/history",
            params={"limit": 1, "page": 999},
            headers=headers,
        )
        assert response.json()["data"]["page"] == 1
        assert len(response.json()["data"]["traces"]) == 1
        assert (
            await asgi_client.get("/api/v1/trace/history?page=0", headers=headers)
        ).status_code == 422
        response = await asgi_client.get(f"/api/v1/trace/{trace_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["spans"][0]["span_id"] == span_id
        assert (
            await asgi_client.get("/api/v1/trace/history?limit=101", headers=headers)
        ).status_code == 422
        assert (
            await asgi_client.get("/api/v1/trace/invalid", headers=headers)
        ).status_code == 422
        assert (
            await asgi_client.get("/api/v1/trace/" + "c" * 32, headers=headers)
        ).status_code == 404
        assert (
            await asgi_client.get("/api/v1/trace/settings", headers=headers)
        ).status_code == 200
    finally:
        store.close()
