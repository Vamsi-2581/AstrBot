"""Diagnostic export route contract coverage."""

import io
import json
import os
import stat
import zipfile
from pathlib import Path
from types import SimpleNamespace

import httpx
import jwt
import pytest

from tests.unit.dashboard.fastapi_v1_support import *  # noqa: F403
from tests.unit.dashboard.fastapi_v1_support import (
    DASHBOARD_JWT_COOKIE_NAME,
    JWT_SECRET,
    _jwt_headers,
)


@pytest.mark.asyncio
async def test_v1_log_export_packs_log_files_and_memory_logs(
    monkeypatch, tmp_path: Path, asgi_app, asgi_client: httpx.AsyncClient
):
    """The archive covers data/logs, configured log files elsewhere and memory logs."""
    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    logs_dir = tmp_path / "data" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "event_loop_watchdog.log").write_text("watchdog", encoding="utf-8")
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    (external_dir / "custom.log").write_text("current", encoding="utf-8")
    (external_dir / "custom.1.log").write_text("rotated", encoding="utf-8")
    service = asgi_app.state.services.logs
    service.config["log"] = {
        "file_enable": True,
        "file_path": str(external_dir / "custom.log"),
    }
    service.log_broker.publish(
        {"level": "INFO", "time": 1.0, "data": "[INFO] hello", "category": "system"}
    )
    service.log_broker.publish(
        {
            "type": "trace",
            "level": "TRACE",
            "time": 2.0,
            "span_id": "span-1",
            "action": "start",
            "fields": {},
        }
    )

    response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "astrbot-diagnostics-" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert sorted(archive.namelist()) == [
            "config.json",
            "environment.json",
            "external/custom.1.log",
            "external/custom.log",
            "logs/event_loop_watchdog.log",
            "manifest.json",
            "memory/logs.txt",
            "memory/traces.jsonl",
            "plugins.json",
            "traces/history.jsonl",
        ]
        assert archive.read("external/custom.log") == b"current"
        assert archive.read("external/custom.1.log") == b"rotated"
        assert archive.read("logs/event_loop_watchdog.log") == b"watchdog"
        assert archive.read("memory/logs.txt").decode() == "[INFO] hello\n"
        traces = archive.read("memory/traces.jsonl").decode().splitlines()
        # Current LogBroker only retains ordinary logs; traces are persisted.
        assert traces == []
        manifest = json.loads(archive.read("manifest.json"))
    assert sorted(manifest["files"]) == [
        "external/custom.1.log",
        "external/custom.log",
        "logs/event_loop_watchdog.log",
    ]
    assert manifest["skipped"] == []
    assert (manifest["memory_logs"], manifest["memory_traces"]) == (1, 0)
    assert str(tmp_path) not in json.dumps(manifest)
    assert not any((tmp_path / "data" / "temp" / "log_exports").iterdir())


@pytest.mark.asyncio
async def test_v1_log_export_skips_files_that_are_not_regular(
    monkeypatch, tmp_path: Path, asgi_client: httpx.AsyncClient
):
    """A symlink in the log directory must not pull in a file from elsewhere."""
    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    logs_dir = tmp_path / "data" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "astrbot.log").write_text("ok", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("not a log", encoding="utf-8")
    link = logs_dir / "link.log"
    try:
        link.symlink_to(outside)
    except OSError:
        # No symlink privilege (e.g. Windows without developer mode): report a
        # regular file as a symlink instead, which takes the same code path.
        link.write_text("not a log", encoding="utf-8")
        real_lstat = Path.lstat

        def fake_lstat(self, *args, **kwargs):
            if self.name == "link.log":
                return os.stat_result((stat.S_IFLNK | 0o777, 0, 0, 0, 0, 0, 0, 0, 0, 0))
            return real_lstat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "lstat", fake_lstat)

    response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert "logs/link.log" not in archive.namelist()
        assert archive.read("logs/astrbot.log") == b"ok"
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["skipped"] == [
        {"name": "logs/link.log", "reason": "not a regular file"}
    ]


@pytest.mark.asyncio
async def test_v1_log_export_keeps_archive_names_unique(
    monkeypatch, tmp_path: Path, asgi_app, asgi_client: httpx.AsyncClient
):
    """Log files never take the names of the generated entries."""
    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "manifest.json").write_text("trace log", encoding="utf-8")
    service = asgi_app.state.services.logs
    service.config["log"] = {"file_path": "manifest.json"}

    response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert archive.read("2/manifest.json") == b"trace log"
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["files"] == ["2/manifest.json"]


@pytest.mark.asyncio
async def test_v1_log_export_refuses_when_disk_space_is_short(
    monkeypatch, tmp_path: Path, asgi_client: httpx.AsyncClient
):
    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    logs_dir = tmp_path / "data" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "astrbot.log").write_text("x" * 1024, encoding="utf-8")
    monkeypatch.setattr(
        "astrbot.dashboard.services.log_service.shutil.disk_usage",
        lambda _path: SimpleNamespace(total=2048, used=2048, free=0),
    )

    response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())

    assert response.status_code == 400
    assert "disk space" in response.json()["message"]
    assert not any((tmp_path / "data" / "temp" / "log_exports").iterdir())


@pytest.mark.asyncio
async def test_v1_log_export_runs_one_export_at_a_time(
    monkeypatch, tmp_path: Path, asgi_app, asgi_client: httpx.AsyncClient
):
    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    lock = asgi_app.state.services.logs._export_lock
    lock.acquire()
    try:
        response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())
    finally:
        lock.release()

    assert response.status_code == 400
    assert "already running" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("redact", [True, False])
async def test_v1_log_export_requires_authentication(asgi_client, redact):
    response = await asgi_client.get("/api/v1/logs/export", params={"redact": redact})

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("redact", [True, False])
@pytest.mark.parametrize(
    "method", ["developer_header", "developer_bearer", "query", "expired"]
)
async def test_diagnostic_export_rejects_non_admin_auth(
    method, redact, fake_db, asgi_app, asgi_client
):
    from unittest.mock import Mock

    fake_db.add_api_key("diagnostic-developer-key", ["system", "config", "*"])
    export = Mock(
        side_effect=AssertionError("Export must not run before authentication")
    )
    asgi_app.state.services.logs.export_logs = export
    options = {
        "developer_header": {"headers": {"X-API-Key": "diagnostic-developer-key"}},
        "developer_bearer": {
            "headers": {"Authorization": "Bearer diagnostic-developer-key"}
        },
        "query": {"params": {"api_key": "diagnostic-developer-key"}},
        "expired": {
            "headers": {
                "Authorization": "Bearer "
                + jwt.encode(
                    {"username": "admin", "exp": 1}, JWT_SECRET, algorithm="HS256"
                )
            }
        },
    }
    options[method].setdefault("params", {})["redact"] = redact
    response = await asgi_client.get("/api/v1/logs/export", **options[method])
    # API keys and invalid Dashboard credentials are rejected before the
    # export runs; only a request with no credentials at all is a plain 401.
    expected = 401 if method == "query" else 403
    assert response.status_code == expected
    export.assert_not_called()


@pytest.mark.asyncio
async def test_diagnostic_export_requires_system_manage_authorization(
    asgi_app, asgi_client
):
    from unittest.mock import Mock

    export = Mock(
        side_effect=AssertionError("Export must not run without authorization")
    )
    asgi_app.state.services.logs.export_logs = export

    async def deny(_subject, _action, _resource, _context):
        return SimpleNamespace(allowed=False, requires_step_up=False)

    asgi_app.state.runtime.services.authorization.authorize = deny
    response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())
    assert response.status_code == 403
    export.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("redact", [True, False])
async def test_diagnostic_export_respects_redaction_for_every_section(
    monkeypatch, tmp_path, asgi_app, asgi_client, redact
):
    from urllib.parse import quote

    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    service = asgi_app.state.services.logs
    config = service.config
    config["trace"] = {"enable": False}
    secret = "private/configured+credential"
    plugin_secret = "private-plugin-credential"
    trace_secret = "previous-provider-credential"
    config["diagnostic_network"] = {
        "public_endpoint": "http://8.8.8.8:8080/v1",
        "public_ipv6": "https://[2606:4700:4700::1111]:443/v1",
        "local_endpoint": "http://192.168.1.2:6185/health",
    }
    config["provider_sources"] = [
        {"key": [secret], "api_base": "https://example.com/v1"}
    ]
    config.setdefault("dashboard", {}).update(
        password="private-password",
        jwt_secret="private-jwt-secret",
        password_storage_upgraded=True,
        password_change_required=False,
    )
    config["max_tokens"] = 4096
    plugin = service.core.catalogs.plugins.get_by_name("astrbot_plugin_demo")
    plugin.config = {"api_key": plugin_secret}
    logs = tmp_path / "data/logs"
    logs.mkdir(parents=True)
    (logs / "astrbot.log").write_text(
        f"{secret}\n{quote(secret, safe='')}\n{plugin_secret}\n{trace_secret}\nhttp://8.8.8.8:8080/v1 https://[2606:4700:4700::1111]:443/v1 http://192.168.1.2:6185/health\nAuthorization: Bearer unknown-header-token\nCookie: session=unknown; second=secret\n-----BEGIN PRIVATE KEY-----\nprivate-key-body\n-----END PRIVATE KEY-----\n",
        encoding="utf-8",
    )
    (logs / "astrbot.1.log").write_text(plugin_secret, encoding="utf-8")
    (logs / "binary.log").write_bytes(b"\x00binary-private-data")
    service.log_broker.publish(
        {"time": 1, "level": "INFO", "data": f"{secret} peer=8.8.8.8"}
    )
    service.log_broker.publish(
        {"type": "trace", "time": 2, "fields": {"api_key": secret, "enabled": True}}
    )
    (logs / "traces.db").touch()

    class Store:
        def list_traces(self, **_kwargs):
            return {"traces": [{"trace_id": "a" * 32}], "total": 1}

        def get_trace(self, _trace_id):
            return {
                "trace": {"trace_id": "a" * 32},
                "spans": [
                    {
                        "attributes": {
                            "api_key": trace_secret,
                            "message": plugin_secret,
                            "peer": "::ffff:8.8.8.8",
                            "ipv6": "2606:4700:4700:0:0:0:0:1111",
                        }
                    }
                ],
            }

    monkeypatch.setattr(
        "astrbot.dashboard.services.log_service.get_trace_store", lambda *_: Store()
    )
    response = await asgi_client.get(
        "/api/v1/logs/export",
        headers=_jwt_headers(),
        params={} if redact else {"redact": "false"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert ("raw-" in response.headers["content-disposition"]) is (not redact)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        all_text = "\n".join(archive.read(name).decode() for name in archive.namelist())
        for private in (
            secret,
            quote(secret, safe=""),
            plugin_secret,
            trace_secret,
            "private-password",
            "private-jwt-secret",
            "unknown-header-token",
            "session=unknown",
            "second=secret",
            "private-key-body",
        ):
            assert (private not in all_text) is redact
        assert "binary-private-data" not in all_text
        if not redact:
            assert (
                archive.read("logs/astrbot.log") == (logs / "astrbot.log").read_bytes()
            )
        exported = json.loads(archive.read("config.json"))["profiles"]["default"]
        if redact:
            assert (
                exported["diagnostic_network"]["public_endpoint"]
                == "http://[PUBLIC_IP_1]:8080/v1"
            )
            assert (
                exported["diagnostic_network"]["public_ipv6"]
                == "https://[PUBLIC_IP_2]:443/v1"
            )
            assert b"peer=[PUBLIC_IP_1]" in archive.read("memory/logs.txt")
            trace = json.loads(archive.read("traces/history.jsonl"))["spans"][0][
                "attributes"
            ]
            assert trace["peer"] == "[PUBLIC_IP_1]"
            assert trace["ipv6"] == "[PUBLIC_IP_2]"
            assert "8.8.8.8" not in all_text
            assert "2606:4700:4700" not in all_text
        else:
            assert exported["diagnostic_network"] == config["diagnostic_network"]
            assert "::ffff:8.8.8.8" in all_text
        assert (
            exported["diagnostic_network"]["local_endpoint"]
            == "http://192.168.1.2:6185/health"
        )
        assert exported["dashboard"]["password_storage_upgraded"] is True
        assert exported["dashboard"]["password_change_required"] is False
        assert exported["max_tokens"] == 4096
        assert exported["provider_sources"][0]["key"] == [
            "[REDACTED]" if redact else secret
        ]
        assert json.loads(archive.read("plugins.json"))["plugins"][0]["enabled"] is True
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["trace_history"]["count"] == 1
        assert manifest["trace_enabled"] is False
        assert manifest["redacted"] is redact
        assert "logs/traces.db" not in archive.namelist()
        assert "logs/binary.log" not in archive.namelist()
        assert archive.read("memory/traces.jsonl") == b""


@pytest.mark.asyncio
async def test_diagnostic_export_without_trace_does_not_create_or_enable_it(
    monkeypatch, tmp_path, asgi_app, asgi_client
):
    from unittest.mock import Mock

    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    asgi_app.state.services.logs.config["trace"] = {"enable": False}
    getter = Mock(side_effect=AssertionError("No database should be opened"))
    monkeypatch.setattr(
        "astrbot.dashboard.services.log_service.get_trace_store", getter
    )
    response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["trace_enabled"] is False
        assert manifest["trace_history"]["status"] == "disabled_no_history"
        assert archive.read("traces/history.jsonl") == b""
    getter.assert_not_called()
    assert not (tmp_path / "data/logs/traces.db").exists()
    assert asgi_app.state.services.logs.config["trace"]["enable"] is False


@pytest.mark.asyncio
async def test_diagnostic_export_authenticates_dashboard_cookie(
    monkeypatch, tmp_path, asgi_client
):
    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    token = _jwt_headers()["Authorization"].removeprefix("Bearer ")
    asgi_client.cookies.set(DASHBOARD_JWT_COOKIE_NAME, token)
    response = await asgi_client.get("/api/v1/logs/export")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_diagnostic_export_redaction_failure_is_closed_and_unlocks(
    monkeypatch, tmp_path, asgi_app, asgi_client
):
    from unittest.mock import Mock

    from astrbot.dashboard.services import log_service

    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    original = log_service.collect_diagnostics
    monkeypatch.setattr(
        log_service,
        "collect_diagnostics",
        Mock(side_effect=RuntimeError("private-value-in-error")),
    )
    response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())
    assert response.status_code == 400
    assert "private-value-in-error" not in response.text
    assert not asgi_app.state.services.logs._export_lock.locked()
    assert not list((tmp_path / "data/temp/log_exports").glob("*.zip"))
    monkeypatch.setattr(log_service, "collect_diagnostics", original)
    response = await asgi_client.get("/api/v1/logs/export", headers=_jwt_headers())
    assert response.status_code == 200
