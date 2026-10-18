"""The admin endpoints of ``AdminResource``: version, status, session, liveness and readiness (ADM-01 to ADM-05)."""

from functools import cache
from importlib.metadata import version
from typing import Any
from zoneinfo import available_timezones

from aurelius_atlas_store_es import ElasticsearchStore, HealthStatus
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from aurelius_atlas_server.auth.sessions import csrf_token
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_server.settings import ServerSettings

ADMIN = APIRouter(prefix="/api/atlas/admin", tags=["Admin"])

NAME = "aurelius-atlas"
DESCRIPTION = "Apache Atlas 2.4.0 REST API on Elasticsearch"
"""What ``admin/version`` reports instead of Apache Atlas's name and description (DV-03)."""

ACTIVE = "ACTIVE"
"""The only service state: Aurelius Atlas has no high-availability states."""

LIVE = "Service is live"
READY = "Service is ready to accept requests"
NOT_READY = "Service not ready to accept client requests"

UI_SETTINGS: dict[str, Any] = {
    "atlas.rest-csrf.enabled": True,
    "atlas.rest-csrf.browser-useragents-regex": "^Mozilla.*,^Opera.*,^Chrome",
    "atlas.rest-csrf.methods-to-ignore": "GET,OPTIONS,HEAD,TRACE",
    "atlas.rest-csrf.custom-header": "X-XSRF-HEADER",
    "atlas.ui.editable.entity.types": "hdfs_path",
    "atlas.ui.default.version": "v2",
    "atlas.ui.date.timezone.format.enabled": True,
    "atlas.ui.date.format": "MM/DD/YYYY hh:mm:ss A",
    "atlas.debug.metrics.enabled": False,
    "atlas.tasks.enabled": True,
    "atlas.tasks.ui.tab.enabled": False,
    "atlas.lineage.on.demand.enabled": False,
    "atlas.lineage.on.demand.default.node.count": 3,
    "atlas.relationship.search.enabled": False,
}
"""The session's settings at the defaults of Atlas 2.4.0 (``AdminResource``, ``AtlasCSRFPreventionFilter``,
``AtlasConfiguration``)."""


@cache
def time_zones() -> list[str]:
    """The IANA time zone ids, sorted (DV-05)."""
    return sorted(available_timezones())


@ADMIN.get("/version")
async def get_version(request: Request) -> dict[str, str]:
    """The server's name, release and revision (ADM-01, DV-03)."""
    settings: ServerSettings = request.app.state.settings
    return {
        "Version": version("aurelius-atlas-server"),
        "Revision": settings.revision,
        "Name": NAME,
        "Description": DESCRIPTION,
    }


@ADMIN.get("/status")
async def get_status() -> dict[str, str]:
    """The service state, which is always ``ACTIVE`` while the server runs (ADM-02)."""
    return {"Status": ACTIVE}


@ADMIN.get("/session")
async def get_session(request: Request) -> dict[str, Any]:
    """The user interface settings and the user of this session (ADM-05, ADM-06).

    Without authentication the user is nobody (DV-04). With it, ``userName`` and ``groups`` name the
    principal the guard resolved (ADM-06) and ``_csrfToken`` is the session's token, minted here at the
    first call and kept for the session's life (CRS-02); a bearer-authenticated call has no session and
    reports a fresh token, as Atlas does for a request whose container session is new.
    """
    session = getattr(request.state, "session", None)
    username: str | None = getattr(request.state, "username", None)
    groups: list[str] = getattr(request.state, "groups", [])
    response: dict[str, Any] = {
        **UI_SETTINGS,
        "atlas.entity.update.allowed": False,  # the authorizer's answer arrives in 6.2
        "atlas.entity.create.allowed": False,
        "userName": username,
        "groups": list(groups),
        "timezones": time_zones(),
    }
    idle = getattr(request.app.state.settings, "auth_session_idle_seconds", None)
    if idle is not None:
        response["atlas.session.timeout.secs"] = idle  # ADM-07, AtlasConfiguration.SESSION_TIMEOUT_SECS
    if session is not None:
        response["_csrfToken"] = session.csrf_token
    else:
        response["_csrfToken"] = csrf_token()
    return response


@ADMIN.get("/liveness", response_class=PlainTextResponse)
async def get_liveness() -> str:
    """Whether the server runs (ADM-03)."""
    return LIVE


@ADMIN.get("/readiness", response_class=PlainTextResponse)
async def get_readiness(request: Request) -> str:
    """Whether the server can serve requests: its store must be healthy (ADM-04).

    Raises:
        AtlasError: ``INTERNAL_ERROR`` when the store is not healthy.
    """
    store: ElasticsearchStore = request.app.state.store
    report = await store.health()
    if report.status is not HealthStatus.UP:
        raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, NOT_READY)
    return READY
