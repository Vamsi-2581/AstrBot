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
    html_file = tmp_path / "upload.html"
    html_file.write_text("<script>alert(1)</script>", encoding="utf-8")
    image_file = tmp_path / "photo.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    resolved: dict[str, tuple[str, str]] = {
        "upload.html": (str(html_file), "text/html"),
        "photo.png": (str(image_file), "image/png"),
    }

    async def fake_resolve(filename: str | None):
        return resolved[str(filename)]

    monkeypatch.setattr(
        asgi_app.state.services.chat,
        "resolve_webchat_file",
        fake_resolve,
    )

    html_response = await asgi_client.get(
        "/api/v1/files/content?filename=upload.html",
        headers=_jwt_headers(),
    )
    assert html_response.status_code == 200
    assert html_response.headers["content-type"].startswith("application/octet-stream")
    assert html_response.headers["x-content-type-options"] == "nosniff"
    assert html_response.headers["content-disposition"].startswith("attachment;")

    image_response = await asgi_client.get(
        "/api/v1/files/content?filename=photo.png",
        headers=_jwt_headers(),
    )
    assert image_response.status_code == 200
    assert image_response.headers["content-type"].startswith("image/png")
    assert image_response.headers["x-content-type-options"] == "nosniff"
    assert image_response.headers["content-disposition"].startswith("attachment;")
