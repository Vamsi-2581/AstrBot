from __future__ import annotations

import pytest

from tests.unit.dashboard.fastapi_v1_support import *  # noqa: F403


@pytest.mark.asyncio
async def test_v1_file_content_is_forced_to_attachment(
    asgi_client: httpx.AsyncClient,
    asgi_app: FastAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    (tmp_path / "upload.html").write_text("<script>alert(1)</script>", encoding="utf-8")
    (tmp_path / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "voice.wav").write_bytes(b"RIFF....WAVE")
    (tmp_path / "clip.mov").write_bytes(b"\x00\x00\x00\x14ftypqt  ")
    (tmp_path / "payload.svg").write_text("<svg/>", encoding="utf-8")

    declared: dict[str, str | None] = {
        "upload.html": "text/html",
        "photo.png": "image/png",
        "voice.wav": "audio/x-wav",
        "clip.mov": "video/quicktime",
        "payload.svg": "image/svg+xml",
    }
    resolved: dict[str, tuple[str, str | None]] = {
        name: (str(tmp_path / name), mimetype) for name, mimetype in declared.items()
    }

    async def fake_resolve(filename: str | None):
        return resolved[str(filename)]

    monkeypatch.setattr(
        asgi_app.state.services.chat,
        "resolve_webchat_file",
        fake_resolve,
    )

    expected_type = {
        "upload.html": "application/octet-stream",
        "photo.png": "image/png",
        # Media types the ChatUI renders inline must survive the hardening.
        "voice.wav": "audio/x-wav",
        "clip.mov": "video/quicktime",
        "payload.svg": "application/octet-stream",
    }

    for filename, media_type in expected_type.items():
        response = await asgi_client.get(
            f"/api/v1/files/content?filename={filename}",
            headers=_jwt_headers(),
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(media_type)
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-disposition"].startswith("attachment;")


@pytest.mark.asyncio
async def test_v1_token_file_is_forced_to_attachment(
    asgi_client: httpx.AsyncClient,
    asgi_app: FastAPI,
    tmp_path: Path,
):
    html_file = tmp_path / "token.html"
    html_file.write_text("<script>alert(1)</script>", encoding="utf-8")
    png_file = tmp_path / "token.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    token_service = asgi_app.state.services.files.file_token_service
    html_token = await token_service.register_file(str(html_file), ttl_seconds=60)
    png_token = await token_service.register_file(str(png_file), ttl_seconds=60)

    html_response = await asgi_client.get(f"/api/v1/files/tokens/{html_token}")
    assert html_response.status_code == 200
    assert html_response.headers["content-type"].startswith("application/octet-stream")
    assert html_response.headers["x-content-type-options"] == "nosniff"
    assert html_response.headers["content-disposition"].startswith("attachment;")

    png_response = await asgi_client.get(f"/api/v1/files/tokens/{png_token}")
    assert png_response.status_code == 200
    assert png_response.headers["content-type"].startswith("image/png")
    assert png_response.headers["content-disposition"].startswith("attachment;")


@pytest.mark.asyncio
async def test_open_api_file_download_is_forced_to_attachment(
    asgi_client: httpx.AsyncClient,
    asgi_app: FastAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    html_file = tmp_path / "attachment.html"
    html_file.write_text("<script>alert(1)</script>", encoding="utf-8")
    png_file = tmp_path / "attachment.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    resolved = {
        "html-attachment": (str(html_file), "text/html"),
        "png-attachment": (str(png_file), "image/png"),
    }

    async def fake_resolve(attachment_id: str):
        return resolved[attachment_id]

    monkeypatch.setattr(
        asgi_app.state.services.chat,
        "resolve_attachment_file",
        fake_resolve,
    )

    html_response = await asgi_client.get(
        "/api/v1/file?attachment_id=html-attachment",
        headers=_jwt_headers(),
    )
    assert html_response.status_code == 200
    assert html_response.headers["content-type"].startswith("application/octet-stream")
    assert html_response.headers["x-content-type-options"] == "nosniff"
    assert html_response.headers["content-disposition"].startswith("attachment;")

    png_response = await asgi_client.get(
        "/api/v1/file?attachment_id=png-attachment",
        headers=_jwt_headers(),
    )
    assert png_response.status_code == 200
    assert png_response.headers["content-type"].startswith("image/png")
    assert png_response.headers["x-content-type-options"] == "nosniff"
    assert png_response.headers["content-disposition"].startswith("attachment;")
