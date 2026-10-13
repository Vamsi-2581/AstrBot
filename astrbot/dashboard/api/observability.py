"""Opt-in Prometheus metrics endpoint for the Dashboard ASGI app.

The route stays outside the versioned ``/api/v1`` contract and is only served
when metrics are explicitly enabled. When disabled it returns ``404`` so the
default surface is unchanged.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from astrbot.core.observability import get_observability

router = APIRouter(include_in_schema=False)


@router.get("/metrics")
async def metrics(request: Request):
    """Expose Prometheus text metrics when observability metrics are enabled."""

    observability = getattr(request.app.state, "observability", None)
    if observability is None:
        observability = get_observability()
    if not observability.metrics_enabled:
        return JSONResponse({"status": "disabled"}, status_code=404)
    return PlainTextResponse(
        observability.render_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
