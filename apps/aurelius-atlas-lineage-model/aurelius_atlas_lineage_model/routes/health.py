"""The container healthcheck: 204 while the process serves, no auth (LM-09)."""

from fastapi import APIRouter

HEALTH = APIRouter()
"""The health router: mounted without the auth gate, outside the API's contract."""


@HEALTH.get("/liveness", status_code=204)
def liveness() -> None:
    """The container healthcheck: 204 while the process serves (no auth)."""
