"""The container healthcheck: the anonymous liveness probe (VE-04, DV-59)."""

from fastapi import APIRouter

from aurelius_atlas_validate_entity.globals import NO_CONTENT

HEALTH = APIRouter()
"""The health router, mounted ungated."""


@HEALTH.get("/liveness", status_code=NO_CONTENT)
def liveness() -> None:
    """The container healthcheck: 204 while the process serves (no auth)."""
