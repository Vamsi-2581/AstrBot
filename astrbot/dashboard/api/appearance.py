"""Dashboard appearance settings and wallpaper asset API."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse

from astrbot.dashboard.responses import ok
from astrbot.dashboard.schemas import AppearanceSettingsRequest, model_dict
from astrbot.dashboard.services.appearance_service import (
    AppearanceService,
    AppearanceServiceError,
)

from .auth import AuthContext, require_scope

router = APIRouter(tags=["Appearance"])
_IMAGE_HEADERS = {
    "Cache-Control": "private, max-age=86400",
    "X-Content-Type-Options": "nosniff",
}
_WALLPAPER_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Wallpaper image bytes",
        "content": {
            "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
            "image/png": {"schema": {"type": "string", "format": "binary"}},
            "image/webp": {"schema": {"type": "string", "format": "binary"}},
            "image/gif": {"schema": {"type": "string", "format": "binary"}},
        },
    }
}
_THUMBNAIL_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "WebP wallpaper thumbnail bytes",
        "content": {"image/webp": {"schema": {"type": "string", "format": "binary"}}},
    }
}


def get_service(request: Request) -> AppearanceService:
    return request.app.state.services.appearance


async def require_appearance_scope(request: Request) -> AuthContext:
    return await require_scope(request, "config")


@router.get("/appearance/settings")
async def get_appearance_settings(
    _auth: AuthContext = Depends(require_appearance_scope),
    service: AppearanceService = Depends(get_service),
):
    return ok(await service.get_settings())


@router.put("/appearance/settings")
async def update_appearance_settings(
    payload: AppearanceSettingsRequest,
    _auth: AuthContext = Depends(require_appearance_scope),
    service: AppearanceService = Depends(get_service),
):
    try:
        settings = await service.update_settings(model_dict(payload))
    except AppearanceServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ok(settings)


@router.get("/appearance/wallpapers")
async def list_wallpapers(
    orientation: Literal["landscape", "portrait"] | None = Query(default=None),
    _auth: AuthContext = Depends(require_appearance_scope),
    service: AppearanceService = Depends(get_service),
):
    try:
        items = await service.list_wallpapers(orientation)
    except AppearanceServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ok({"items": items})


@router.post("/appearance/wallpapers")
async def upload_wallpaper(
    orientation: Literal["landscape", "portrait"] = Form(...),
    file: UploadFile = File(...),
    _auth: AuthContext = Depends(require_appearance_scope),
    service: AppearanceService = Depends(get_service),
):
    try:
        return ok(await service.save_wallpaper(file, orientation))
    except AppearanceServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/appearance/wallpapers/{wallpaper_id}/thumbnail",
    responses=_THUMBNAIL_RESPONSE,
)
async def get_wallpaper_thumbnail(
    wallpaper_id: str,
    _auth: AuthContext = Depends(require_appearance_scope),
    service: AppearanceService = Depends(get_service),
):
    try:
        path, content_type = await service.resolve_thumbnail(wallpaper_id)
    except AppearanceServiceError as exc:
        raise HTTPException(
            status_code=404, detail="Wallpaper thumbnail not found"
        ) from exc
    return FileResponse(path, media_type=content_type, headers=_IMAGE_HEADERS)


@router.get("/appearance/wallpapers/{wallpaper_id}", responses=_WALLPAPER_RESPONSE)
async def get_wallpaper(
    wallpaper_id: str,
    _auth: AuthContext = Depends(require_appearance_scope),
    service: AppearanceService = Depends(get_service),
):
    try:
        path, content_type = await service.resolve_wallpaper(wallpaper_id)
    except AppearanceServiceError as exc:
        raise HTTPException(status_code=404, detail="Wallpaper not found") from exc
    return FileResponse(path, media_type=content_type, headers=_IMAGE_HEADERS)


@router.delete("/appearance/wallpapers/{wallpaper_id}")
async def delete_wallpaper(
    wallpaper_id: str,
    _auth: AuthContext = Depends(require_appearance_scope),
    service: AppearanceService = Depends(get_service),
):
    try:
        await service.delete_wallpaper(wallpaper_id)
    except AppearanceServiceError as exc:
        raise HTTPException(status_code=404, detail="Wallpaper not found") from exc
    return ok({"id": wallpaper_id})
