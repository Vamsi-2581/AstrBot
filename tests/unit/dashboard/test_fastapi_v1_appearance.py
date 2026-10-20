from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from astrbot.dashboard.services.appearance_service import AppearanceService
from tests.unit.dashboard.fastapi_v1_support import _jwt_headers


def _png_bytes() -> bytes:
    payload = BytesIO()
    Image.new("RGB", (640, 360), "steelblue").save(payload, "PNG")
    return payload.getvalue()


@pytest.mark.asyncio
async def test_appearance_settings_and_wallpaper_routes(
    asgi_app,
    asgi_client,
    tmp_path,
):
    service = AppearanceService(tmp_path)
    asgi_app.state.services.appearance = service

    settings = await asgi_client.get(
        "/api/v1/appearance/settings",
        headers=_jwt_headers(),
    )
    assert settings.status_code == 200
    assert settings.json()["data"]["enabled"] is False

    updated = await asgi_client.put(
        "/api/v1/appearance/settings",
        headers=_jwt_headers(),
        json={
            **settings.json()["data"],
            "enabled": True,
            "surface_opacity": 0.4,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["surface_opacity"] == 0.4

    upload = await asgi_client.post(
        "/api/v1/appearance/wallpapers",
        headers=_jwt_headers(),
        data={"orientation": "landscape"},
        files={"file": ("wallpaper.png", _png_bytes(), "image/png")},
    )
    assert upload.status_code == 200
    item = upload.json()["data"]
    assert item["orientation"] == "landscape"
    assert item["theme_primary"].startswith("#")

    listed = await asgi_client.get(
        "/api/v1/appearance/wallpapers",
        headers=_jwt_headers(),
        params={"orientation": "portrait"},
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["items"] == []

    image = await asgi_client.get(
        f"/api/v1/appearance/wallpapers/{item['id']}",
        headers=_jwt_headers(),
    )
    assert image.status_code == 200
    assert image.headers["cache-control"] == "private, max-age=86400"

    thumbnail = await asgi_client.get(
        f"/api/v1/appearance/wallpapers/{item['id']}/thumbnail",
        headers=_jwt_headers(),
    )
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"].startswith("image/webp")

    deleted = await asgi_client.delete(
        f"/api/v1/appearance/wallpapers/{item['id']}",
        headers=_jwt_headers(),
    )
    assert deleted.status_code == 200
    assert (await service.list_wallpapers()) == []


@pytest.mark.asyncio
async def test_appearance_upload_requires_orientation(
    asgi_app,
    asgi_client,
    tmp_path,
):
    asgi_app.state.services.appearance = AppearanceService(tmp_path)
    response = await asgi_client.post(
        "/api/v1/appearance/wallpapers",
        headers=_jwt_headers(),
        files={"file": ("wallpaper.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 422
