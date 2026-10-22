"""The admin endpoints of ``AdminResource``: version, status, session, liveness, readiness, patches and purge.

ADM-01 to ADM-05, ENS-10, EDL-01 to EDL-08.
"""

import secrets
import string
from functools import cache
from importlib.metadata import version
from typing import Any
from zoneinfo import available_timezones

from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_store_es import ElasticsearchStore, HealthStatus
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.entity import Body, Store, writer
from aurelius_atlas_server.routes.types import validate_param_length
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

CSRF_TOKEN_LENGTH = 20
_CSRF_ALPHABET = string.ascii_letters + string.digits

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


def csrf_token() -> str:
    """A new random token of 20 letters and digits, as ``AdminResource.getUserProfile`` makes one."""
    return "".join(secrets.choice(_CSRF_ALPHABET) for _ in range(CSRF_TOKEN_LENGTH))


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
async def get_session() -> dict[str, Any]:
    """The user interface settings and the user of this session; no user until 6.1 (ADM-05, DV-04)."""
    return {
        **UI_SETTINGS,
        "atlas.entity.update.allowed": False,
        "atlas.entity.create.allowed": False,
        "userName": None,
        "groups": [],
        "timezones": time_zones(),
        "_csrfToken": csrf_token(),
    }


@ADMIN.get("/patches")
async def get_patches(request: Request) -> dict[str, Any]:
    """``getAtlasPatches``: the typedef patch records, sorted by id (ENS-10, DV-14)."""
    typedef_store: TypedefStore = request.app.state.typedef_store
    await typedef_store.refresh()
    return {"patches": [patch.to_json() for patch in typedef_store.patches()]}


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


@ADMIN.put("/purge")
async def purge_by_ids(request: Request, store: Store, body: Body) -> AtlasJSONResponse:
    """``purgeByIds``: remove the ``DELETED`` entities of a JSON array of GUIDs (EDL-01 to EDL-03).

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is not an array of strings (DV-10).
    """
    if body is not None and (not isinstance(body, list) or not all(isinstance(guid, str) for guid in body)):
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, "Invalid body: a JSON array of GUIDs is expected")
    guids = list(dict.fromkeys(body or []))
    for guid in guids:
        validate_param_length("guid", guid)
    return AtlasJSONResponse(content=(await writer(request, store).purge_by_ids(guids)).to_json())
