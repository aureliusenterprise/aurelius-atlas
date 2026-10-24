"""The container healthcheck: the anonymous liveness probe (DTM-10)."""

from fastapi import APIRouter

from aurelius_atlas_data2model.globals import NO_CONTENT

HEALTH = APIRouter()
"""The health router, mounted ungated."""


@HEALTH.get("/liveness", status_code=NO_CONTENT)
def liveness() -> None:
    """The container healthcheck: 204 while the process serves (no auth)."""
