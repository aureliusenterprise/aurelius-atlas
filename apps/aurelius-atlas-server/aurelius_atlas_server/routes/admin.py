"""The admin endpoints of ``AdminResource``: version, status, session, liveness, readiness, patches, purge, tasks,
export, import, servers and their audit trail.

ADM-01 to ADM-05, ENS-10, EDL-01 to EDL-08, TSK-06, EXP-01, IMS-01 to IMS-06, REP-01 to REP-05.
"""  # noqa: D205 - one sentence

import json
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cache
from importlib.metadata import version
from typing import Any
from zoneinfo import available_timezones

from aurelius_atlas_core.atlas_server_service import AtlasServerService
from aurelius_atlas_core.audits_writer import AuditsWriter
from aurelius_atlas_core.export_import_audit_service import ExportImportAuditService
from aurelius_atlas_core.export_service import ExportService
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_core.zip_sink import ZipSink
from aurelius_atlas_model.impexp import (
    OPTION_KEY_REPLICATED_TO,
    OPTION_SKIP_LINEAGE,
    AtlasExportRequest,
    AtlasImportRequest,
    AtlasImportResult,
    AtlasServer,
)
from aurelius_atlas_store_es import ElasticsearchStore, HealthStatus
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.datastructures import UploadFile

from aurelius_atlas_server.authentication import Session, User, acting_user, csrf_token
from aurelius_atlas_server.authorization import AtlasPrivilege, authorizer, privileges, verify_access
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.entity import INT_RANGE, Body, Store, java_number, updater, writer
from aurelius_atlas_server.routes.types import typedef_store as refreshed_typedef_store
from aurelius_atlas_server.routes.types import validate_param_length
from aurelius_atlas_server.settings import ServerSettings

ADMIN = APIRouter(prefix="/api/atlas/admin", tags=["Admin"])

NO_CONTENT = 204

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
    """The user interface settings and the user of this session (ADM-05, AUT-09).

    The CSRF token is the session's, made on first ask; a request without a session gets a new one. The entity
    permissions are the user's (AUZ-06). ``atlas.tasks.enabled`` is the server's ``tasks_enabled`` setting
    (DD-081).
    """
    user: User | None = request.state.user
    session: Session | None = request.state.session
    allowed = privileges(user)
    if session is not None and session.csrf_token is None:
        session.csrf_token = csrf_token()
    return {
        **UI_SETTINGS,
        "atlas.tasks.enabled": request.app.state.settings.tasks_enabled,
        "atlas.entity.update.allowed": AtlasPrivilege.ENTITY_UPDATE in allowed,
        "atlas.entity.create.allowed": AtlasPrivilege.ENTITY_CREATE in allowed,
        "userName": None if user is None else user.name,
        "groups": [] if user is None else sorted(user.groups),
        "timezones": time_zones(),
        "_csrfToken": csrf_token() if session is None else session.csrf_token,
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
    if guids:
        verify_access(request, AtlasPrivilege.ADMIN_PURGE, "purge entity: guids=", guids)  # AUZ-05
    return AtlasJSONResponse(content=(await writer(request, store).purge_by_ids(guids)).to_json())


@ADMIN.post("/export")
async def export(request: Request, store: Store, body: Body) -> Response:
    """``export``: the entities the request reaches, with their types and the result, as a ZIP (EXP-01 to EXP-06).

    One export or import runs at a time unless the request's options name ``skipLineage`` or ``replicatedTo``.

    Raises:
        AtlasError: ``UNAUTHORIZED_ACCESS``; ``FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK`` while another runs;
            ``BAD_REQUEST`` for a body that is no export request (DV-10).
    """
    verify_access(request, AtlasPrivilege.ADMIN_EXPORT, "export")
    export_request = _export_request(body)
    exclusive = (
        OPTION_SKIP_LINEAGE not in export_request.options and OPTION_KEY_REPLICATED_TO not in export_request.options
    )
    lock = request.app.state.import_export_lock
    if exclusive:
        if lock.locked():
            raise AtlasError(AtlasErrorCode.FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK)
        await lock.acquire()
    try:
        sink = ZipSink()
        service = ExportService(
            store, cluster_name=request.app.state.settings.cluster_name, audits=_audits(request, store)
        )
        client = "" if request.client is None else request.client.host
        result = await service.run(sink, export_request, acting_user(request), socket.gethostname(), client)
        content = sink.close()
    finally:
        if exclusive:
            lock.release()
    if not sink.guids and export_request.omit_zip_response_for_empty_export():
        return Response(status_code=204)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={type(result).__name__}"},
    )


def _export_request(body: Any) -> AtlasExportRequest:  # noqa: ANN401 - any JSON value
    """The body as an export request; no body is an empty one (DV-120).

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is no export request (DV-10).
    """
    if body is None:
        return AtlasExportRequest()
    try:
        return AtlasExportRequest.model_validate(body)
    except ValueError as error:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, f"Invalid AtlasExportRequest: {error}") from error


@ADMIN.post("/import")
async def import_data(request: Request, store: Store) -> AtlasJSONResponse:
    """``importData``: the form's ``data``, an export ZIP, imported as its ``request`` asks (IMS-01 to IMS-05).

    One export or import runs at a time unless the request names ``replicatedFrom``; an empty ZIP answers an empty
    result.

    Raises:
        AtlasError: ``UNAUTHORIZED_ACCESS``; ``FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK``; what the import fails with.
    """
    verify_access(request, AtlasPrivilege.ADMIN_IMPORT, "importData")
    form = await request.form()
    text = form.get("request")
    import_request = _import_request(text if isinstance(text, str) else "{}")
    data = form.get("data")
    content = await data.read() if isinstance(data, UploadFile) else b""
    exclusive = import_request is not None and not import_request.is_replication_option_set()
    async with _exclusively(request, exclusive=exclusive):
        try:
            result = await (await _importer(request, store)).run(content, import_request, *_who(request))
        except AtlasError as error:
            if error.code is not AtlasErrorCode.IMPORT_ATTEMPTING_EMPTY_ZIP:
                raise
            result = AtlasImportResult(time_stamp=store.now())
    return AtlasJSONResponse(content=result.to_json())


@ADMIN.post("/importfile")
async def import_file(request: Request, store: Store, body: Body) -> AtlasJSONResponse:
    """``importFile``: the export ZIP its ``fileName`` option names, from the server's import folder (IMS-06, DV-125).

    It locks other exports and imports out only when the request names ``replicatedFrom``, as Atlas does.

    Raises:
        AtlasError: ``UNAUTHORIZED_ACCESS``; ``FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK``; ``INVALID_PARAMETERS``; what
            the import fails with.
    """
    verify_access(request, AtlasPrivilege.ADMIN_IMPORT, "importFile")
    import_request = _import_request(json.dumps(body)) if body is not None else None
    exclusive = import_request is not None and import_request.is_replication_option_set()
    folder = request.app.state.settings.import_folder
    async with _exclusively(request, exclusive=exclusive):
        importer = await _importer(request, store)
        result = await importer.run_file(import_request or AtlasImportRequest(), folder, *_who(request))
    return AtlasJSONResponse(content=result.to_json())


def _import_request(text: str) -> AtlasImportRequest | None:
    """``AtlasType.fromJson`` of the request: None for text that is no request."""
    try:
        return AtlasImportRequest.model_validate_json(text)
    except ValueError:
        return None


async def _importer(request: Request, store: Store) -> ImportService:
    """The import service, its types current, its entities written as the request's user (IMS-04)."""
    return ImportService(
        store, await refreshed_typedef_store(request), updater(request, store), audits=_audits(request, store)
    )


def _audits(request: Request, store: Store) -> AuditsWriter:
    """The audit trail of the request's export or import, this server named as the settings name it (REP-02)."""
    return AuditsWriter(store, cluster_name=request.app.state.settings.cluster_name, user=acting_user(request))


@ADMIN.get("/server/{server_name}")
async def get_cluster(server_name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getCluster``: the server of the full name, with the replication it recorded (REP-01).

    Atlas checks no admin privilege here, only the entity reads of its store (DD-307).

    Raises:
        AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` for none.
    """
    service = AtlasServerService(store, user=acting_user(request), authorizer=authorizer(request))
    found = await service.get(AtlasServer(name=server_name, full_name=server_name))
    return AtlasJSONResponse(content=found.to_json())


@ADMIN.get("/expimp/audit")
async def get_export_import_audit(request: Request, store: Store) -> AtlasJSONResponse:
    """``getExportImportAudit``: the audit entries of the values given, the server either end (REP-05).

    Query parameters ``serverName``, ``userName``, ``operation``, ``startTime``, ``endTime``, ``limit`` and
    ``offset``. Atlas checks no admin privilege here, only the entity reads of its search (DD-307).
    """
    query = request.query_params
    service = ExportImportAuditService(store, user=acting_user(request), authorizer=authorizer(request))
    found = await service.get(
        query.get("userName"),
        query.get("operation"),
        query.get("serverName"),
        query.get("startTime"),
        query.get("endTime"),
        java_number(request, "limit", 0, INT_RANGE),
        java_number(request, "offset", 0, INT_RANGE),
    )
    return AtlasJSONResponse(content=[entry.to_json() for entry in found])


def _who(request: Request) -> tuple[str | None, str, str]:
    """The user, the server's host name and the client's address an import or export records."""
    return acting_user(request), socket.gethostname(), "" if request.client is None else request.client.host


@asynccontextmanager
async def _exclusively(request: Request, *, exclusive: bool) -> AsyncIterator[None]:
    """``acquireExportImportLock``: when ``exclusive``, the one export or import running (DD-304).

    Raises:
        AtlasError: ``FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK`` while another runs.
    """
    lock = request.app.state.import_export_lock
    if not exclusive:
        yield
        return
    if lock.locked():
        raise AtlasError(AtlasErrorCode.FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK)
    async with lock:
        yield


@ADMIN.get("/tasks")
async def get_task_status(request: Request) -> AtlasJSONResponse:
    """``getTaskStatus``: the tasks of the ``guids`` given that exist, in their order, else every task (TSK-06)."""
    guids = request.query_params.getlist("guids")
    management: TaskManagement = request.app.state.task_management
    found = await management.get_by_guids(guids) if guids else await management.get_all()
    return AtlasJSONResponse(content=[task.to_json() for task in found])


@ADMIN.delete("/tasks")
async def delete_task(request: Request) -> Response:
    """``deleteTask``: remove the tasks of the ``guids`` given (TSK-06)."""
    guids = request.query_params.getlist("guids")
    if guids:
        management: TaskManagement = request.app.state.task_management
        await management.delete_by_guids(guids)
    return Response(status_code=NO_CONTENT)
