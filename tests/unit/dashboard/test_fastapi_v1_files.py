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
