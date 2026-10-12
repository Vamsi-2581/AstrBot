"""Unauthenticated liveness and readiness probes for the Dashboard ASGI app.

These routes stay outside the versioned ``/api/v1`` contract and the auth
middleware, which only guards ``/api`` paths. They return a minimal body and
never expose internal state.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(include_in_schema=False)


@router.get("/healthz")
async def liveness() -> JSONResponse:
    """Report that the process is up and the event loop responds."""

    return JSONResponse({"status": "ok"})


@router.get("/readyz")
async def readiness(request: Request) -> JSONResponse:
    """Report whether core startup completed and the runtime is usable."""

    core_control = getattr(request.app.state, "core_control", None)
    if bool(getattr(core_control, "is_ready", False)):
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "not_ready"}, status_code=503)
