"""The admin endpoints of ``AdminResource``: version, status, session, liveness, readiness, patches, metrics, purge,
tasks, export, import, servers and their audit trail.

ADM-01 to ADM-05, ENS-10, EDL-01 to EDL-08, TSK-06, EXP-01, IMS-01 to IMS-06, REP-01 to REP-05, MET-01 to MET-04,
MHS-01 to MHS-04.
"""  # noqa: D205 - one sentence

import json
import re
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cache
from importlib.metadata import version
from typing import Annotated, Any
from zoneinfo import available_timezones

from aurelius_atlas_core.atlas_audit_service import AtlasAuditService
from aurelius_atlas_core.atlas_server_service import AtlasServerService
from aurelius_atlas_core.audit_reduction_service import AtlasAuditReductionService
from aurelius_atlas_core.audits_writer import AuditsWriter
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.export_import_audit_service import ExportImportAuditService
from aurelius_atlas_core.export_service import ExportService
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.metrics_service import MetricsService
from aurelius_atlas_core.zip_sink import ZipSink
from aurelius_atlas_model import codec
from aurelius_atlas_model.admin import AtlasServiceStatus, AtlasSessionProfile, AtlasVersionInfo
from aurelius_atlas_model.atlas_audit import AtlasAuditEntry, AuditOperation, AuditSearchParameters
from aurelius_atlas_model.audit_reduction import AuditReductionCriteria
from aurelius_atlas_model.impexp import (
    OPTION_KEY_REPLICATED_TO,
    OPTION_SKIP_LINEAGE,
    AtlasExportRequest,
    AtlasImportRequest,
    AtlasImportResult,
    AtlasServer,
    ExportImportAuditEntry,
)
from aurelius_atlas_model.instance import AtlasEntityHeader, AtlasObjectId, EntityMutationResponse
from aurelius_atlas_model.lists import Guids
from aurelius_atlas_model.metrics import AtlasMetrics, AtlasMetricsCharts, AtlasMetricsStat
from aurelius_atlas_model.params import (
    AuditDetailsParams,
    EntityGuidParams,
    ExportImportAuditParams,
    MetricsListParams,
    MetricsTimeParams,
    read_params,
)
from aurelius_atlas_model.patches import AtlasPatches
from aurelius_atlas_model.tasks import AtlasTask
from aurelius_atlas_store_es import ElasticsearchStore, HealthStatus
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.datastructures import UploadFile

from aurelius_atlas_server.authentication import Session, User, acting_user, csrf_token
from aurelius_atlas_server.authorization import AtlasPrivilege, authorizer, privileges, verify_access
from aurelius_atlas_server.bodies import json_root
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.openapi import (
    array_of,
    download_response,
    form_request,
    json_response,
    request_body,
    text_response,
)
from aurelius_atlas_server.openapi import no_content as no_content_response
from aurelius_atlas_server.routes.entity import INVALID_PARAMETER, Body, Store, updater, writer
from aurelius_atlas_server.routes.types import typedef_store as refreshed_typedef_store
from aurelius_atlas_server.routes.types import validate_param_length
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.tenant_stores import stores

OPERATION_STATUS = "operationStatus"
"""The option an export's or import's admin audit adds its status as (ADA-02)."""

ADMIN = APIRouter(prefix="/api/atlas/admin", tags=["Admin"])

NO_CONTENT = 204

NAME = "aurelius-atlas"
DESCRIPTION = "Apache Atlas 2.4.0 REST API on Elasticsearch"
"""What ``admin/version`` reports instead of Apache Atlas's name and description (DV-03)."""

LIVE = "Service is live"
READY = "Service is ready to accept requests"
NOT_READY = "Service not ready to accept client requests"

PURGE_BODY = json_root(Guids)
"""``purgeByIds``: the GUIDs to purge, a JSON array of them (EDL-01, DV-10)."""

type PurgeBody = Annotated[list[str] | None, Depends(PURGE_BODY)]


@cache
def time_zones() -> list[str]:
    """The IANA time zone ids, sorted (DV-05)."""
    return sorted(available_timezones())


@ADMIN.get(
    "/version",
    responses=json_response(AtlasVersionInfo, description="The server's name, release and revision (ADM-01, DV-03)."),
)
async def get_version(request: Request) -> dict[str, Any]:
    """The server's name, release and revision (ADM-01, DV-03)."""
    settings: ServerSettings = request.app.state.settings
    return AtlasVersionInfo.model_validate(
        {
            "version": version("aurelius-atlas-server"),
            "revision": settings.revision,
            "name": NAME,
            "description": DESCRIPTION,
        }
    ).to_json()


@ADMIN.get(
    "/status",
    responses=json_response(
        AtlasServiceStatus, description="The service state, always ACTIVE while the server runs (ADM-02)."
    ),
)
async def get_status() -> dict[str, Any]:
    """The service state, which is always ``ACTIVE`` while the server runs (ADM-02)."""
    return AtlasServiceStatus().to_json()


@ADMIN.get(
    "/session",
    responses=json_response(
        AtlasSessionProfile,
        description="The UI settings, permissions, userName, groups, timezones and _csrfToken (ADM-05, AUT-09).",
    ),
)
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
    profile = AtlasSessionProfile()
    profile.tasks_enabled = request.app.state.settings.tasks_enabled
    profile.entity_update_allowed = AtlasPrivilege.ENTITY_UPDATE in allowed
    profile.entity_create_allowed = AtlasPrivilege.ENTITY_CREATE in allowed
    profile.user_name = None if user is None else user.name
    profile.groups = [] if user is None else sorted(user.groups)
    profile.timezones = time_zones()
    token: str = csrf_token() if session is None else session.csrf_token or csrf_token()
    profile.csrf_token = token
    return profile.to_json()


@ADMIN.get(
    "/patches",
    responses=json_response(AtlasPatches, description="The typedef patch records, sorted by id (ENS-10, DV-14)."),
)
async def get_patches(request: Request) -> dict[str, Any]:
    """``getAtlasPatches``: the typedef patch records, sorted by id (ENS-10, DV-14)."""
    typedef_store = stores(request).typedef_store
    await typedef_store.refresh()
    return AtlasPatches(patches=typedef_store.patches()).to_json()


@ADMIN.get("/liveness", response_class=PlainTextResponse, responses=text_response("The server runs (ADM-03)."))
async def get_liveness() -> str:
    """Whether the server runs (ADM-03)."""
    return LIVE


@ADMIN.get(
    "/readiness",
    response_class=PlainTextResponse,
    responses=text_response("The server can serve requests; its store answers healthy (ADM-04)."),
)
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


@ADMIN.get(
    "/metrics",
    responses=json_response(
        AtlasMetrics,
        description="The counts of types, entities and classifications, and the server's stats (MET-01 to MET-04).",
    ),
)
async def get_metrics(request: Request, store: Store) -> dict[str, Any]:
    """``getMetrics``: the counts of the types, entities and classifications the user may read, the server's stats
    and its system details; a store that is not healthy is ``not-connected`` (MET-01 to MET-04).
    """  # noqa: D205 - one sentence
    search_store: ElasticsearchStore = request.app.state.store
    report = await search_store.health()
    metrics = await _metrics_service(request, store).get_metrics(store_connected=report.status is HealthStatus.UP)
    return metrics.to_json()


LONG_RANGE = (-(2**63), 2**63 - 1)
JAVA_LONG = re.compile(r"[+-]?\d+")


def _metrics_service(request: Request, store: EntityStore) -> MetricsService:
    """The metrics of ``store`` as the request's user reads them, kept as the settings say (MHS-01)."""
    settings: ServerSettings = request.app.state.settings
    return MetricsService(
        store,
        request.app.state.metrics_util,
        authorizer=authorizer(request),
        namespace=settings.cluster_name,
        ttl_hours=settings.metrics_ttl_hours,
    )


def _java_long(name: str, value: str) -> int:
    """``Long.parseLong`` of a parameter.

    Raises:
        AtlasError: ``BAD_REQUEST`` for text that is no ``long`` (DV-136).
    """
    if not JAVA_LONG.fullmatch(value) or not LONG_RANGE[0] <= int(value) <= LONG_RANGE[1]:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_PARAMETER.format(value=value, name=name))
    return int(value)


def _time_range(request: Request) -> tuple[int, int, list[str]]:
    """The ``startTime``, ``endTime`` and ``typeName`` parameters of a range, per ``MetricsTimeParams`` (MHS-03).

    Raises:
        AtlasError: ``BAD_REQUEST`` for a missing or blank time, or one that is no ``long`` (DV-136);
            ``INVALID_QUERY_PARAM_LENGTH`` for a long one.
    """
    return read_params(MetricsTimeParams, request.query_params).checked()


@ADMIN.get(
    "/metricsstats",
    responses=json_response(array_of(AtlasMetricsStat), description="Every stored metric, the latest first (MHS-02)."),
)
async def get_all_metrics(request: Request, store: Store) -> list[dict[str, Any]]:
    """``getAllMetrics``: every stored metric, the latest first; with ``mininfo``, the default, without the metrics
    (MHS-02).
    """  # noqa: D205 - one sentence
    min_info = read_params(MetricsListParams, request.query_params).min_info
    found = await _metrics_service(request, store).get_all_metrics_stats(min_info=min_info)
    return [stat.to_json() for stat in found]


@ADMIN.get(
    "/metricsstat/{collection_time}",
    responses=json_response(AtlasMetricsStat, description="The metric stored at that time (MHS-02)."),
)
async def get_metrics_by_collection_time(request: Request, store: Store, collection_time: str) -> dict[str, Any]:
    """``getMetricsByCollectionTime``: the metric stored at that time (MHS-02)."""
    validate_param_length("collectionTime", collection_time)
    service = _metrics_service(request, store)
    found = await service.get_metrics_stat_by_collection_time(_java_long("collectionTime", collection_time))
    return found.to_json()


@ADMIN.get(
    "/metricsstats/range",
    responses=json_response(array_of(AtlasMetricsStat), description="The metrics stored in the range (MHS-03)."),
)
async def get_metrics_in_time_range(request: Request, store: Store) -> list[dict[str, Any]]:
    """``getMetricsInTimeRange``: the metrics stored in the range, with the type data of the type names (MHS-03)."""
    start, end, type_names = _time_range(request)
    found = await _metrics_service(request, store).get_metrics_in_range_by_type_names(start, end, type_names)
    return [stat.to_json() for stat in found]


@ADMIN.get(
    "/metricsstats/charts",
    responses=json_response(
        AtlasMetricsCharts, description="Per type name, its counts in the range by state (MHS-04)."
    ),
)
async def get_metrics_for_chart_by_type_names(request: Request, store: Store) -> dict[str, list[dict[str, Any]]]:
    """``getMetricsForChartByTypeNames``: per type name, its counts in the range by state (MHS-04)."""
    start, end, type_names = _time_range(request)
    charts = await _metrics_service(request, store).get_metrics_for_chart_by_type_names(start, end, type_names)
    return {name: [chart.to_json() for chart in found] for name, found in charts.items()}


@ADMIN.put(
    "/purge",
    responses=json_response(EntityMutationResponse, description="The purged entities (EDL-01 to EDL-03)."),
    **request_body(array_of(str), required=False, description="The GUIDs of the DELETED entities to purge."),
)
async def purge_by_ids(request: Request, store: Store, guids_body: PurgeBody) -> AtlasJSONResponse:
    """``purgeByIds``: remove the ``DELETED`` entities of a JSON array of GUIDs (EDL-01 to EDL-03).

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is not an array of strings (DV-10).
    """
    guids = list(dict.fromkeys(guids_body or []))
    if guids:
        verify_access(request, AtlasPrivilege.ADMIN_PURGE, "purge entity: guids=", guids)  # AUZ-05
    EntityGuidParams(guids=guids).checked()  # the access check comes first, as Atlas checks it first (DV-161)
    response = await writer(request, store).purge_by_ids(guids)
    purged = response.get_purged_entities()
    if purged:  # ADA-02
        params = "[" + ", ".join(guids) + "]"  # List.toString
        await AtlasAuditService(store).add(
            AuditOperation.PURGE, params, response.get_purged_entities_ids(), len(purged)
        )
    return AtlasJSONResponse(content=response.to_json())


@ADMIN.post(
    "/export",
    responses={
        **download_response(
            "application/zip", description="The exported entities, types and result as a ZIP (EXP-01 to EXP-06)."
        ),
        204: {"description": "An empty export, for the request asks the ZIP to be omitted."},
    },
    **request_body(
        AtlasExportRequest, required=False, description="What to export: the items to export and the options."
    ),
)
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
    if "options" in export_request.model_fields_set and export_request.items_to_export:
        options = {**export_request.options, OPERATION_STATUS: result.operation_status.value}
        await _audit_items(store, AuditOperation.EXPORT, export_request.items_to_export, options)
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


@ADMIN.post(
    "/import",
    responses=json_response(AtlasImportResult, description="What the import processed (IMS-01 to IMS-05)."),
    **form_request(
        fields={"data": "An export ZIP.", "request": "An AtlasImportRequest as JSON text."},
        text=("request",),
    ),
)
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
            return AtlasJSONResponse(content=AtlasImportResult(time_stamp=store.now()).to_json())
    await _audit_import(store, result)
    return AtlasJSONResponse(content=result.to_json())


@ADMIN.post(
    "/importfile",
    responses=json_response(AtlasImportResult, description="What the import processed (IMS-06, DV-125)."),
    **request_body(
        AtlasImportRequest,
        required=False,
        description="The import request; its fileName option names the ZIP in the server's import folder.",
    ),
)
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


async def _audit_import(store: Store, result: AtlasImportResult) -> None:
    """``addToImportOperationAudits``: the export's items by type, or without an export request the import's
    metrics and its count of entities (ADA-02).
    """  # noqa: D205 - one sentence
    options = {OPERATION_STATUS: result.operation_status.value}
    exported = None if result.export_result is None else result.export_result.request
    if exported is not None:
        await _audit_items(store, AuditOperation.IMPORT, exported.items_to_export, options)
        return
    metrics = codec.dumps(result.metrics).decode()
    await AtlasAuditService(store).add(
        AuditOperation.IMPORT, codec.dumps(options).decode(), metrics, len(result.processed_entities)
    )


async def _audit_items(
    store: Store, operation: AuditOperation, items: list[AtlasObjectId], options: dict[str, Any]
) -> None:
    """``auditImportExportOperations``: the options as the parameters, the items counted by type as the result,
    and their count; an item without a type is not counted by type (DV-131).
    """  # noqa: D205 - one sentence
    by_type: dict[str, int] = {}
    for item in items:
        if item.type_name is not None:
            by_type[item.type_name] = by_type.get(item.type_name, 0) + 1
    params, counted = codec.dumps(options).decode(), codec.dumps(by_type).decode()
    await AtlasAuditService(store).add(operation, params, counted, len(items))


@ADMIN.post(
    "/audits",
    responses=json_response(
        array_of(AtlasAuditEntry), description="The admin audits the search parameters find (ADA-04)."
    ),
    **request_body(
        AuditSearchParameters, required=False, description="The audit search parameters; none asks for every entry."
    ),
)
async def get_atlas_audits(request: Request, store: Store, body: Body) -> AtlasJSONResponse:
    """``getAtlasAudits``: the admin audits the search parameters find (ADA-04); it needs ``ADMIN_AUDITS``.

    Raises:
        AtlasError: ``UNAUTHORIZED_ACCESS``; ``INVALID_PARAMETERS`` for no body; ``UNKNOWN_ATTRIBUTE``;
            ``BAD_REQUEST`` for a body that is no search (DV-10).
    """
    verify_access(request, AtlasPrivilege.ADMIN_AUDITS, "Admin Audits")
    try:
        parameters = None if body is None else AuditSearchParameters.model_validate(body)
    except ValueError as error:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, f"Invalid AuditSearchParameters: {error}") from error
    found = await AtlasAuditService(store, authorizer=authorizer(request)).get(parameters)
    return AtlasJSONResponse(content=[entry.to_json() for entry in found])


@ADMIN.post(
    "/audits/ageout",
    responses={
        **json_response(array_of(AtlasTask), description="The queued aging tasks (AGE-01 to AGE-03)."),
        204: {"description": "No aging was queued."},
    },
    **request_body(
        AuditReductionCriteria, required=False, description="The aging criteria; ignored when useAuditConfig is true."
    ),
)
async def ageout_audit_data(request: Request, store: Store, body: Body) -> Response:
    """``ageoutAuditData``: the agings the criteria ask for, or with ``useAuditConfig`` the configuration's, queued
    as tasks and answered; none queued is 204 (AGE-01 to AGE-03). It needs ``ADMIN_AUDITS``.

    Raises:
        AtlasError: ``UNAUTHORIZED_ACCESS``; ``BAD_REQUEST`` for a body that is no criteria (DV-10);
            ``INTERNAL_ERROR`` for action types of which none names an action.
    """  # noqa: D205 - one sentence
    verify_access(request, AtlasPrivilege.ADMIN_AUDITS, "Admin Audits Ageout")
    settings: ServerSettings = request.app.state.settings
    service = AtlasAuditReductionService(store, settings.audit_aging_config())
    if (request.query_params.get("useAuditConfig") or "").lower() == "true":
        tasks = await service.start_by_config()
    else:
        try:
            criteria = AuditReductionCriteria.model_validate(body or {})
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, f"Invalid AuditReductionCriteria: {error}") from error
        if criteria.default_ageout_ttl_in_days <= 0:
            criteria.default_ageout_ttl_in_days = settings.audit_default_ageout_ttl_in_days
        tasks = await service.start_by_criteria(service.build_ageout_criteria(criteria))
    if not tasks:
        return Response(status_code=NO_CONTENT)
    return AtlasJSONResponse(content=[task.to_json() for task in tasks])


@ADMIN.get(
    "/audit/{audit_guid}/details",
    responses=json_response(
        array_of(AtlasEntityHeader), description="The entity headers a purge's audit names (ADA-05)."
    ),
)
async def get_audit_details(audit_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getAuditDetails``: the entity headers a purge's audit names, ``limit`` (10) from ``offset`` (ADA-05).

    Atlas checks no admin privilege here, only the entity read of the entry.

    Raises:
        AtlasError: ``INSTANCE_GUID_NOT_FOUND``; ``UNAUTHORIZED_ACCESS``; ``INTERNAL_ERROR`` for an audit other
            than a purge.
    """
    page = read_params(AuditDetailsParams, request.query_params)
    service = AtlasAuditService(store, authorizer=authorizer(request))
    found = await service.details(audit_guid, stores(request).entity_audits, page.limit, page.offset)
    return AtlasJSONResponse(content=[header.to_json() for header in found])


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


@ADMIN.get(
    "/server/{server_name}",
    responses=json_response(
        AtlasServer, description="The server of the full name, with the replication it recorded (REP-01)."
    ),
)
async def get_cluster(server_name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getCluster``: the server of the full name, with the replication it recorded (REP-01).

    Atlas checks no admin privilege here, only the entity reads of its store (DD-307).

    Raises:
        AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` for none.
    """
    service = AtlasServerService(store, user=acting_user(request), authorizer=authorizer(request))
    found = await service.get(AtlasServer(name=server_name, full_name=server_name))
    return AtlasJSONResponse(content=found.to_json())


@ADMIN.get(
    "/expimp/audit",
    responses=json_response(
        array_of(ExportImportAuditEntry),
        description="The audit entries of the values given, the server either end (REP-05).",
    ),
)
async def get_export_import_audit(request: Request, store: Store) -> AtlasJSONResponse:
    """``getExportImportAudit``: the audit entries of the values given, the server either end (REP-05).

    Query parameters ``serverName``, ``userName``, ``operation``, ``startTime``, ``endTime``, ``limit`` and
    ``offset``. Atlas checks no admin privilege here, only the entity reads of its search (DD-307).
    """
    asked = read_params(ExportImportAuditParams, request.query_params)
    service = ExportImportAuditService(store, user=acting_user(request), authorizer=authorizer(request))
    found = await service.get(
        asked.user_name,
        asked.operation,
        asked.server_name,
        asked.start_time,
        asked.end_time,
        asked.limit,
        asked.offset,
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


@ADMIN.get(
    "/tasks",
    responses=json_response(
        array_of(AtlasTask), description="The tasks of the guids given, in their order, else every task (TSK-06)."
    ),
)
async def get_task_status(request: Request) -> AtlasJSONResponse:
    """``getTaskStatus``: the tasks of the ``guids`` given that exist, in their order, else every task (TSK-06)."""
    guids = request.query_params.getlist("guids")
    management = stores(request).task_management
    found = await management.get_by_guids(guids) if guids else await management.get_all()
    return AtlasJSONResponse(content=[task.to_json() for task in found])


@ADMIN.delete("/tasks", responses=no_content_response("The tasks of the guids given are removed (TSK-06)."))
async def delete_task(request: Request) -> Response:
    """``deleteTask``: remove the tasks of the ``guids`` given (TSK-06)."""
    guids = request.query_params.getlist("guids")
    if guids:
        management = stores(request).task_management
        await management.delete_by_guids(guids)
    return Response(status_code=NO_CONTENT)
