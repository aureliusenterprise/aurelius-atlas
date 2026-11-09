"""The health probes: liveness while the process serves, readiness once the model has loaded (EMB-07)."""

from fastapi import APIRouter, Request, Response

from aurelius_atlas_embedder.globals import NO_CONTENT, NOT_READY

HEALTH = APIRouter()
"""The health router, mounted ungated."""


@HEALTH.get("/liveness", status_code=NO_CONTENT)
def liveness() -> None:
    """204 while the process serves."""


@HEALTH.get("/readiness", status_code=NO_CONTENT)
def readiness(request: Request, response: Response) -> None:
    """204 once the model has loaded and embedded its warm-up text, 503 before."""
    if request.app.state.model is None:
        response.status_code = NOT_READY
