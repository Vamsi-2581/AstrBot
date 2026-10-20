from typing import Any

from fastapi import APIRouter, Depends, Header, Path, Query, Request
from fastapi.responses import StreamingResponse

from astrbot.dashboard.responses import ApiError, ok
from astrbot.dashboard.schemas import TraceSettingsRequest
from astrbot.dashboard.services.log_service import LogService, LogServiceError

from .auth import AuthContext, require_scope

router = APIRouter(tags=["Logs"])
_SSE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Server-sent log stream",
        "content": {"text/event-stream": {"schema": {"type": "string"}}},
    }
}


async def require_system_scope(request: Request) -> AuthContext:
    return await require_scope(request, "system")


def get_service(request: Request) -> LogService:
    return request.app.state.services.logs


def _raise_log_error(exc: LogServiceError) -> None:
    raise ApiError(str(exc)) from exc


def _get_log_history(
    service: LogService,
    *,
    categories: set[str] | None = None,
    privacy: set[str] | None = None,
):
    try:
        return ok(service.get_log_history(categories=categories, privacy=privacy))
    except LogServiceError as exc:
        _raise_log_error(exc)


def _get_trace_settings(service: LogService):
    try:
        return ok(service.get_trace_settings())
    except LogServiceError as exc:
        _raise_log_error(exc)


async def _update_trace_settings(payload: TraceSettingsRequest, service: LogService):
    try:
        message = await service.update_trace_settings(payload.enabled)
        return ok(message=message)
    except LogServiceError as exc:
        _raise_log_error(exc)


@router.get("/logs/history")
async def get_log_history(
    _auth: AuthContext = Depends(require_system_scope),
    service: LogService = Depends(get_service),
    category: list[str] | None = Query(default=None),
    privacy: list[str] | None = Query(default=None),
):
    return _get_log_history(
        service,
        categories=set(category or ()),
        privacy=set(privacy or ()),
    )


@router.get("/logs/live", responses=_SSE_RESPONSE)
async def live_logs(
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    _auth: AuthContext = Depends(require_system_scope),
    service: LogService = Depends(get_service),
    category: list[str] | None = Query(default=None),
    privacy: list[str] | None = Query(default=None),
):
    return StreamingResponse(
        service.stream_log_events(
            last_event_id,
            categories=set(category or ()),
            privacy=set(privacy or ()),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )


@router.get("/trace/settings")
async def get_trace_settings(
    _auth: AuthContext = Depends(require_system_scope),
    service: LogService = Depends(get_service),
):
    return _get_trace_settings(service)


@router.get("/trace/history")
async def list_traces(
    limit: int = Query(default=50, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    cursor: str | None = Query(default=None, max_length=64),
    query: str = Query(default="", max_length=256),
    errors: bool = False,
    models: bool = False,
    plugins: bool = False,
    _auth: AuthContext = Depends(require_system_scope),
    service: LogService = Depends(get_service),
):
    """Return a page of persisted trace summaries."""
    try:
        return ok(
            await service.get_trace_history(
                limit=limit,
                page=page,
                cursor=cursor,
                query=query,
                errors=errors,
                models=models,
                plugins=plugins,
            )
        )
    except LogServiceError as exc:
        _raise_log_error(exc)


@router.get("/trace/{trace_id}")
async def get_trace_detail(
    trace_id: str = Path(pattern="^[0-9a-f]{32}$"),
    _auth: AuthContext = Depends(require_system_scope),
    service: LogService = Depends(get_service),
):
    """Return one trace's canonical spans and events."""
    try:
        detail = await service.get_trace_detail(trace_id)
    except LogServiceError as exc:
        _raise_log_error(exc)
    if detail is None:
        raise ApiError("Trace not found or already evicted.", status_code=404)
    return ok(detail)


@router.put("/trace/settings")
async def update_trace_settings(
    payload: TraceSettingsRequest,
    _auth: AuthContext = Depends(require_system_scope),
    service: LogService = Depends(get_service),
):
    return await _update_trace_settings(payload, service)
