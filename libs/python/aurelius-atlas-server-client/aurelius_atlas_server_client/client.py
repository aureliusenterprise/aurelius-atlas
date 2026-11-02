"""The async client for the Atlas metadata API (CL-01..CL-05, CL-11; DD-203, DD-204, DD-205).

One client per server: constructed from an externally built ``httpx.AsyncClient``
and a token source, reading no environment variables (CL-01) — the app builds the
httpx client from its own settings (TLS, timeout) and passes it in. The request
paths are relative, appended to that client's base URL, so a URL with a trailing
slash — the ``str()`` of a pydantic ``HttpUrl`` — works as given (CL-01); the
builder closes the pool, the API client never touches its lifecycle. Because the
client arrives from outside, tests hand over one built on a ``MockTransport`` and
no socket opens (CL-02, the DD-200 seam made async). Every request carries
``authorization: Bearer <token>`` from the token source (CL-03); a non-2xx answer
raises :class:`AtlasClientError` with the status and the server's
``{errorCode, errorMessage}`` when the body parses (CL-04); an unreachable upstream
propagates as ``httpx``'s own error — mapping it to an HTTP status is the app's job
(LM-07's DV-80), not the client's (CL-05).

The paths mirror the server's routes verbatim: ``routes/admin.py`` under
``/api/atlas/admin`` (the 8.4 reads plus the 8.11 writes, CLW-01..CLW-07),
``routes/types.py`` under ``/api/atlas/v2/types``, the
entity routes of ``routes/entity.py`` under ``/api/atlas/v2/entity``
(CLE-01..CLE-12, 8.9), the glossary routes of ``routes/glossary.py`` under
``/api/atlas/v2/glossary`` (CLG-01..CLG-09, 8.10), the relationship routes of
``routes/relationship.py`` under ``/api/atlas/v2/relationship``
(CLR-01..CLR-04, 8.11), the discovery routes of
``routes/discovery.py`` under ``/api/atlas/v2/search`` (CL-13), and the lineage
feed of ``routes/lineage.py`` under ``/api/atlas/v2/lineage`` (CL-60..CL-63, 8.8).
"""

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

import httpx2 as httpx
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.bulk_import import BulkImportResponse
from aurelius_atlas_model.discovery import (
    AtlasQuickSearchResult,
    AtlasSearchResult,
    AtlasSuggestionsResult,
    QuickSearchParameters,
    SearchParameters,
    SortOrder,
)
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryExtInfo,
    AtlasGlossaryTerm,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
)
from aurelius_atlas_model.impexp import (
    AtlasExportRequest,
    AtlasImportRequest,
    AtlasImportResult,
)
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasClassifications,
    AtlasEntitiesWithExtInfo,
    AtlasEntityHeader,
    AtlasEntityHeaders,
    AtlasEntityWithExtInfo,
    AtlasRelatedObjectId,
    AtlasRelationship,
    AtlasRelationshipWithExtInfo,
    ClassificationAssociateRequest,
    EntityMutationResponse,
)
from aurelius_atlas_model.lineage import LineageOnDemandConstraints
from aurelius_atlas_model.patches import AtlasPatch
from aurelius_atlas_model.tasks import AtlasTask
from aurelius_atlas_model.typedef import (
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasRelationshipDef,
    AtlasStructDef,
    AtlasTypeDefHeader,
    AtlasTypesDef,
    TypeCategory,
)
from pydantic import ValidationError

from aurelius_atlas_server_client.lineage import Direction, LineageInfo
from aurelius_atlas_server_client.models import (
    AtlasErrorInfo,
    AtlasSessionInfo,
    AtlasStatus,
    AtlasVersion,
    DeleteType,
)

type TokenSource = str | Callable[[], str]
"""Where the bearer token comes from: a fixed token, or a callable that yields one.

The callable shape is 8.2's forwarding (LM-04): a route passes a source that yields
the caller's own token, so the client sends the browser's credential upstream.
"""

DEFAULT_TIMEOUT_SECONDS = 10.0
"""The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01)."""

ADMIN_ROOT = "api/atlas/admin"
TYPES_ROOT = "api/atlas/v2/types"
DISCOVERY_ROOT = "api/atlas/v2/search"
ENTITY_ROOT = "api/atlas/v2/entity"
GLOSSARY_ROOT = "api/atlas/v2/glossary"
RELATIONSHIP_ROOT = "api/atlas/v2/relationship"
LINEAGE_ROOT = "api/atlas/v2/lineage"
"""The route prefixes of the server's resources (``routes/admin.py``, ``routes/types.py``,
``routes/discovery.py``, ``routes/entity.py``, ``routes/glossary.py``,
``routes/relationship.py``, ``routes/lineage.py``).

Relative to the httpx client's base URL (CL-01): httpx appends them, so the base
URL the app passes — trailing slash included, as a pydantic ``HttpUrl`` renders
one — works as given. ``LINEAGE_ROOT`` carries the prefix too (CL-60): the
server mounts its feed at ``/api/atlas/v2/lineage``, as every other resource
(DD-308).
"""

CLIENT_ERROR = 400
"""The status where an answer becomes an error: the client-error boundary (CL-04)."""

type GlossarySort = Literal["ASC", "DESC"]
"""The glossary reads' ``sort`` parameter (CLG-02, GLS-05).

The wire vocabulary is the server's own: ``routes/glossary.py`` reads anything
but ``DESC`` as ascending, so ``ASC`` — the default — travels as absence.
``aurelius-atlas-model``'s ``SortOrder`` is a different vocabulary
(``ASCENDING``/``DESCENDING``, the search parameter) and is not this one.
"""

_KIND_MODELS: dict[TypeCategory, type[AtlasBaseTypeDef]] = {
    TypeCategory.ENUM: AtlasEnumDef,
    TypeCategory.STRUCT: AtlasStructDef,
    TypeCategory.CLASSIFICATION: AtlasClassificationDef,
    TypeCategory.ENTITY: AtlasEntityDef,
    TypeCategory.RELATIONSHIP: AtlasRelationshipDef,
    TypeCategory.BUSINESS_METADATA: AtlasBusinessMetadataDef,
}
"""The model of each typedef kind, for parsing a kind's lookup answer (CL-11)."""

_KIND_OF_MODEL: dict[type[AtlasBaseTypeDef], TypeCategory] = {model: kind for kind, model in _KIND_MODELS.items()}
"""The category of each kind's model — the reverse of ``_KIND_MODELS``, for typed lookups."""

KIND_PATHS: dict[TypeCategory, str] = {
    TypeCategory.ENUM: "enumdef",
    TypeCategory.STRUCT: "structdef",
    TypeCategory.CLASSIFICATION: "classificationdef",
    TypeCategory.ENTITY: "entitydef",
    TypeCategory.RELATIONSHIP: "relationshipdef",
    TypeCategory.BUSINESS_METADATA: "businessmetadatadef",
}
"""The path segment of each kind's lookups, mirroring ``routes/types.py``'s ``KIND_PATHS`` (CL-11)."""


class AtlasClientError(RuntimeError):
    """A non-2xx answer from the Atlas server, with the status and the error body (CL-04)."""

    def __init__(self, status_code: int, info: AtlasErrorInfo | None) -> None:
        self.status_code = status_code
        """The HTTP status the server answered with."""
        self.info = info
        """The server's ``{errorCode, errorMessage}``, when the body parsed as one."""
        detail = f"{info.error_code}: {info.error_message}" if info is not None else f"HTTP {status_code}"
        super().__init__(f"the Atlas server answered {status_code}: {detail}")


def _bearer(token: TokenSource) -> dict[str, str]:
    """The authorization header for the token source's current token (CL-03).

    An empty token is the unauthenticated call: no header at all — an empty
    bearer is not a legal header value, and a token source the caller leaves
    empty (a route that needs no auth, a service whose leg carries no token)
    must reach the wire unauthenticated, not malformed.
    """
    value = token() if callable(token) else token
    return {} if not value else {"authorization": f"Bearer {value}"}


def _error_info(response: httpx.Response) -> AtlasErrorInfo | None:
    """The response's Atlas error body, or None when it is not one (CL-04)."""
    try:
        return AtlasErrorInfo.model_validate_json(response.content)
    except ValidationError:
        return None


@dataclass(frozen=True)
class _Api:
    """The shared transport of a client's resource APIs: the httpx client and the token source."""

    http: httpx.AsyncClient
    token: TokenSource

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | list[tuple[str, Any]] | None = None,
        body: Any = None,  # noqa: ANN401 - a JSON request body: a model's to_json(), or any JSON value (EWR-15)
        files: Mapping[str, tuple[str | None, str | bytes]] | None = None,
    ) -> httpx.Response:
        """One request with the bearer header; a non-2xx answer raises (CL-03..CL-05).

        ``files`` sends ``multipart/form-data`` instead of JSON (CL-64) — the two
        are never given together. A part name mapped to a ``(None, text)`` pair
        travels as a plain form field, no filename (DD-313).
        """
        response = await self.http.request(
            method, path, params=params, json=body, files=files, headers=_bearer(self.token)
        )
        if response.status_code >= CLIENT_ERROR:
            raise AtlasClientError(response.status_code, _error_info(response))
        return response

    async def json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | list[tuple[str, Any]] | None = None,
        body: Any = None,  # noqa: ANN401 - the JSON body of the answer, parsed by the caller's model
    ) -> Any:  # noqa: ANN401 - the JSON body of the answer, parsed by the caller's model
        """One request answered with JSON (CL-11)."""
        return (await self.request(method, path, params=params, body=body)).json()


class AdminApi:
    """The admin resource of an :class:`AtlasClient` (CL-11): ``client.admin``."""

    def __init__(self, api: _Api) -> None:
        self._api = api

    async def version(self) -> AtlasVersion:
        """``GET /api/atlas/admin/version`` (ADM-01)."""
        return AtlasVersion.model_validate(await self._api.json("GET", f"{ADMIN_ROOT}/version"))

    async def status(self) -> AtlasStatus:
        """``GET /api/atlas/admin/status`` (ADM-02)."""
        return AtlasStatus.model_validate(await self._api.json("GET", f"{ADMIN_ROOT}/status"))

    async def session(self) -> AtlasSessionInfo:
        """``GET /api/atlas/admin/session`` (ADM-05)."""
        return AtlasSessionInfo.model_validate(await self._api.json("GET", f"{ADMIN_ROOT}/session"))

    async def liveness(self) -> str:
        """``GET /api/atlas/admin/liveness`` — the plain-text answer (ADM-03)."""
        return (await self._api.request("GET", f"{ADMIN_ROOT}/liveness")).text

    async def readiness(self) -> str:
        """``GET /api/atlas/admin/readiness`` — the plain-text answer.

        An ``AtlasClientError`` when the server is not ready (ADM-04).
        """
        return (await self._api.request("GET", f"{ADMIN_ROOT}/readiness")).text

    async def patches(self) -> list[AtlasPatch]:
        """``GET /patches``: the typedef patch records (ENS-10, CLW-01).

        Unwrapped from the server's ``{"patches": [...]}`` envelope.
        """
        answer = await self._api.json("GET", f"{ADMIN_ROOT}/patches")
        return [AtlasPatch.model_validate(patch) for patch in answer["patches"]]

    async def purge(self, guids: Sequence[str]) -> EntityMutationResponse:
        """``PUT /purge``: the ``DELETED`` entities of the guid array, removed (EDL-01..EDL-03, CLW-02).

        An empty list still sends ``[]``: the server reads a missing or
        non-array body as ``BAD_REQUEST`` (DV-10), never as "purge nothing".
        """
        return EntityMutationResponse.model_validate(
            await self._api.json("PUT", f"{ADMIN_ROOT}/purge", body=list(guids))
        )

    async def export(self, request: AtlasExportRequest | None = None) -> tuple[bytes, str]:
        """``POST /export``: the export ZIP, as bytes and content type (EXP-01..EXP-06, CLW-03, DD-310).

        No request is the empty one the server builds from a missing body
        (DV-120) — the client sends no options it was not given. The 204 the
        server answers for an empty export asked to omit its ZIP
        (EXP-05) returns ``(b"", "")``.
        """
        response = await self._api.request(
            "POST", f"{ADMIN_ROOT}/export", body=None if request is None else request.to_json()
        )
        return response.content, response.headers.get("content-type", "")

    async def import_data(self, content: bytes, request: AtlasImportRequest | None = None) -> AtlasImportResult:
        """``POST /import``: the export ZIP imported as the request asks (IMS-01..IMS-05, CLW-04, DD-310).

        The ``data`` part carries the bytes; the ``request`` part, when given,
        is a plain text field holding the request as JSON (DD-313) — never a
        file path (CL-64).
        """
        files: dict[str, tuple[str | None, str | bytes]] = {"data": ("export.zip", content)}
        if request is not None:
            files["request"] = (None, json.dumps(request.to_json()))
        answer = await self._api.request("POST", f"{ADMIN_ROOT}/import", files=files)
        return AtlasImportResult.model_validate(answer.json())

    async def import_file(self, request: AtlasImportRequest) -> AtlasImportResult:
        """``POST /importfile``: the ZIP named by the request's ``fileName`` option (IMS-06, DV-125, CLW-05).

        The server opens the name from its import folder; the client reads no
        folder of its own (DD-310) — the name travels as the request's option.
        """
        return AtlasImportResult.model_validate(
            await self._api.json("POST", f"{ADMIN_ROOT}/importfile", body=request.to_json())
        )

    async def tasks(self, guids: Sequence[str] | None = None) -> list[AtlasTask]:
        """``GET /tasks``: the tasks of the guids given, or every task (TSK-06, CLW-06).

        Each guid travels as a repeated ``guids`` parameter; none given sends
        no parameter, which the server reads as "every task".
        """
        params = [("guids", guid) for guid in guids] if guids else None
        answer = await self._api.json("GET", f"{ADMIN_ROOT}/tasks", params=params)
        return [AtlasTask.model_validate(task) for task in answer]

    async def delete_tasks(self, guids: Sequence[str]) -> None:
        """``DELETE /tasks``: the tasks of the guids given, removed (TSK-06, CLW-06). Answers 204."""
        await self._api.request("DELETE", f"{ADMIN_ROOT}/tasks", params=[("guids", guid) for guid in guids])


class TypesApi:
    """The typedef resource of an :class:`AtlasClient` (CL-11): ``client.types``.

    The paths mirror ``routes/types.py``; the bodies are ``aurelius-atlas-model``'s,
    reused whole (CL-10).
    """

    def __init__(self, api: _Api) -> None:
        self._api = api

    async def typedef_by_name(self, name: str) -> AtlasBaseTypeDef:
        """``GET /typedef/name/{name}``: the definition of any kind (TYR-01), parsed by its ``category``."""
        return _parse_def(await self._api.json("GET", f"{TYPES_ROOT}/typedef/name/{name}"))

    async def typedef_by_guid(self, guid: str) -> AtlasBaseTypeDef:
        """``GET /typedef/guid/{guid}``: the definition of any kind (TYR-02), parsed by its ``category``."""
        return _parse_def(await self._api.json("GET", f"{TYPES_ROOT}/typedef/guid/{guid}"))

    async def typedefs(self, params: Mapping[str, Any] | None = None) -> AtlasTypesDef:
        """``GET /typedefs``: the definitions the search filter keeps (TYR-05..TYR-07)."""
        return AtlasTypesDef.model_validate(await self._api.json("GET", f"{TYPES_ROOT}/typedefs", params=params))

    async def typedef_headers(self, params: Mapping[str, Any] | None = None) -> list[AtlasTypeDefHeader]:
        """``GET /typedefs/headers``: the headers the search filter keeps (TYR-08)."""
        answer = await self._api.json("GET", f"{TYPES_ROOT}/typedefs/headers", params=params)
        return [AtlasTypeDefHeader.model_validate(header) for header in answer]

    async def create_typedefs(self, types_def: AtlasTypesDef) -> AtlasTypesDef:
        """``POST /typedefs``: create the definitions, all or none (TYR-09)."""
        return AtlasTypesDef.model_validate(
            await self._api.json("POST", f"{TYPES_ROOT}/typedefs", body=types_def.to_json())
        )

    async def update_typedefs(self, types_def: AtlasTypesDef) -> AtlasTypesDef:
        """``PUT /typedefs``: update the definitions, all or none (TYR-09)."""
        return AtlasTypesDef.model_validate(
            await self._api.json("PUT", f"{TYPES_ROOT}/typedefs", body=types_def.to_json())
        )

    async def delete_typedefs(self, types_def: AtlasTypesDef) -> None:
        """``DELETE /typedefs``: delete the definitions, all or none (TYR-10); the answer is 204."""
        await self._api.request("DELETE", f"{TYPES_ROOT}/typedefs", body=types_def.to_json())

    async def delete_typedef_by_name(self, type_name: str) -> None:
        """``DELETE /typedef/name/{type_name}``: delete the named definition (TYR-10); the answer is 204."""
        await self._api.request("DELETE", f"{TYPES_ROOT}/typedef/name/{type_name}")

    async def enumdef_by_name(self, name: str) -> AtlasEnumDef:
        """``GET /enumdef/name/{name}`` (TYR-03)."""
        return await self._kind_def(AtlasEnumDef, name=name)

    async def enumdef_by_guid(self, guid: str) -> AtlasEnumDef:
        """``GET /enumdef/guid/{guid}`` (TYR-03)."""
        return await self._kind_def(AtlasEnumDef, guid=guid)

    async def structdef_by_name(self, name: str) -> AtlasStructDef:
        """``GET /structdef/name/{name}`` (TYR-03)."""
        return await self._kind_def(AtlasStructDef, name=name)

    async def structdef_by_guid(self, guid: str) -> AtlasStructDef:
        """``GET /structdef/guid/{guid}`` (TYR-03)."""
        return await self._kind_def(AtlasStructDef, guid=guid)

    async def classificationdef_by_name(self, name: str) -> AtlasClassificationDef:
        """``GET /classificationdef/name/{name}`` (TYR-03)."""
        return await self._kind_def(AtlasClassificationDef, name=name)

    async def classificationdef_by_guid(self, guid: str) -> AtlasClassificationDef:
        """``GET /classificationdef/guid/{guid}`` (TYR-03)."""
        return await self._kind_def(AtlasClassificationDef, guid=guid)

    async def entitydef_by_name(self, name: str) -> AtlasEntityDef:
        """``GET /entitydef/name/{name}`` (TYR-03)."""
        return await self._kind_def(AtlasEntityDef, name=name)

    async def entitydef_by_guid(self, guid: str) -> AtlasEntityDef:
        """``GET /entitydef/guid/{guid}`` (TYR-03)."""
        return await self._kind_def(AtlasEntityDef, guid=guid)

    async def relationshipdef_by_name(self, name: str) -> AtlasRelationshipDef:
        """``GET /relationshipdef/name/{name}`` (TYR-03)."""
        return await self._kind_def(AtlasRelationshipDef, name=name)

    async def relationshipdef_by_guid(self, guid: str) -> AtlasRelationshipDef:
        """``GET /relationshipdef/guid/{guid}`` (TYR-03)."""
        return await self._kind_def(AtlasRelationshipDef, guid=guid)

    async def businessmetadatadef_by_name(self, name: str) -> AtlasBusinessMetadataDef:
        """``GET /businessmetadatadef/name/{name}`` (TYR-03)."""
        return await self._kind_def(AtlasBusinessMetadataDef, name=name)

    async def businessmetadatadef_by_guid(self, guid: str) -> AtlasBusinessMetadataDef:
        """``GET /businessmetadatadef/guid/{guid}`` (TYR-03)."""
        return await self._kind_def(AtlasBusinessMetadataDef, guid=guid)

    async def _kind_def[KindT: AtlasBaseTypeDef](
        self, model: type[KindT], *, name: str | None = None, guid: str | None = None
    ) -> KindT:
        """One kind lookup by name or guid, parsed into the kind's model (TYR-03, CL-11)."""
        path = KIND_PATHS[_KIND_OF_MODEL[model]]
        segment = f"name/{name}" if name is not None else f"guid/{guid}"
        answer = await self._api.json("GET", f"{TYPES_ROOT}/{path}/{segment}")
        return model.model_validate(answer)


class SearchApi:
    """The discovery resource of an :class:`AtlasClient` (CL-13): ``client.search``.

    The paths mirror ``routes/discovery.py``; the bodies are ``aurelius-atlas-model``'s,
    reused whole (CL-10). The GET searches carry their parameters as query parameters,
    the POST searches as the model's JSON body — as the server's JAX-RS routes read them.
    """

    def __init__(self, api: _Api) -> None:
        self._api = api

    async def search_with_parameters(self, parameters: SearchParameters) -> AtlasSearchResult:
        """``POST /api/atlas/v2/search/basic``: the entities the body's search finds (SRC-02)."""
        return AtlasSearchResult.model_validate(
            await self._api.json("POST", f"{DISCOVERY_ROOT}/basic", body=parameters.to_json())
        )

    async def search_using_basic(  # noqa: PLR0913 - the GET route's query parameters, as routes/discovery.py reads them
        self,
        *,
        query: str | None = None,
        type_name: str | None = None,
        classification: str | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        exclude_deleted_entities: bool = False,
        limit: int = 0,
        offset: int = 0,
        marker: str | None = None,
    ) -> AtlasSearchResult:
        """``GET /api/atlas/v2/search/basic``: a search of the query parameters, not body-validated (SRC-11)."""
        params = _present(
            query=query,
            typeName=type_name,
            classification=classification,
            sortBy=sort_by,
            sortOrder=sort_order,
            excludeDeletedEntities=exclude_deleted_entities,
            limit=limit,
            offset=offset,
            marker=marker,
        )
        return AtlasSearchResult.model_validate(await self._api.json("GET", f"{DISCOVERY_ROOT}/basic", params=params))

    async def search_using_attribute(
        self,
        *,
        type_name: str | None = None,
        attr_name: str | None = None,
        attr_value_prefix: str | None = None,
        limit: int = 0,
        offset: int = 0,
    ) -> AtlasSearchResult:
        """``GET /api/atlas/v2/search/attribute``: entities whose attribute starts with the prefix (SRC-11)."""
        params = _present(
            typeName=type_name, attrName=attr_name, attrValuePrefix=attr_value_prefix, limit=limit, offset=offset
        )
        return AtlasSearchResult.model_validate(
            await self._api.json("GET", f"{DISCOVERY_ROOT}/attribute", params=params)
        )

    async def search_using_full_text(
        self,
        query: str,
        *,
        exclude_deleted_entities: bool = False,
        limit: int = 0,
        offset: int = 0,
    ) -> AtlasSearchResult:
        """``GET /api/atlas/v2/search/fulltext``: the entities matching the query, best first, with scores (FTX-05)."""
        params = _present(
            query=query,
            excludeDeletedEntities=exclude_deleted_entities,
            limit=limit,
            offset=offset,
        )
        return AtlasSearchResult.model_validate(
            await self._api.json("GET", f"{DISCOVERY_ROOT}/fulltext", params=params)
        )

    async def quick_search(self, parameters: QuickSearchParameters) -> AtlasQuickSearchResult:
        """``POST /api/atlas/v2/search/quick``: the quick search of the body, with its facets (QSR-01)."""
        return AtlasQuickSearchResult.model_validate(
            await self._api.json("POST", f"{DISCOVERY_ROOT}/quick", body=parameters.to_json())
        )

    async def quick_search_using_query(  # noqa: PLR0913 - the GET route's query parameters, as routes/discovery.py reads them
        self,
        *,
        query: str | None = None,
        type_name: str | None = None,
        exclude_deleted_entities: bool = False,
        limit: int = 0,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> AtlasQuickSearchResult:
        """``GET /api/atlas/v2/search/quick``: a quick search of the query parameters (QSR-01, QSR-02)."""
        params = _present(
            query=query,
            typeName=type_name,
            excludeDeletedEntities=exclude_deleted_entities,
            limit=limit,
            offset=offset,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        answer = await self._api.json("GET", f"{DISCOVERY_ROOT}/quick", params=params)
        return AtlasQuickSearchResult.model_validate(answer)

    async def get_suggestions(
        self, prefix_string: str | None = None, field_name: str | None = None
    ) -> AtlasSuggestionsResult:
        """``GET /api/atlas/v2/search/suggestions``: terms beginning with the prefix (SUG-01, SUG-02)."""
        params = _present(prefixString=prefix_string, fieldName=field_name)
        answer = await self._api.json("GET", f"{DISCOVERY_ROOT}/suggestions", params=params)
        return AtlasSuggestionsResult.model_validate(answer)


class EntityApi:
    """The entity resource of an :class:`AtlasClient` (CLE-01..CLE-12): ``client.entity``.

    The paths mirror ``routes/entity.py`` (37 routes); the bodies are
    ``aurelius-atlas-model``'s, reused whole (DD-309). The client validates no
    request body the server validates — it sends the model's ``to_json()`` and
    lets the server answer (CLE-12). A unique-attribute read or delete renders
    each entry as an ``attr:<name>`` query parameter, the bulk read as
    ``attr_<n>:<name>``, 1-based, in order (CLE-03).
    """

    def __init__(self, api: _Api) -> None:
        self._api = api

    async def by_guid(
        self, guid: str, *, min_ext_info: bool = False, ignore_relationships: bool = False
    ) -> AtlasEntityWithExtInfo:
        """``GET /guid/{guid}``: the entity and the entities it owns (ERD-02, CLE-02)."""
        params = _present(minExtInfo=min_ext_info, ignoreRelationships=ignore_relationships)
        return AtlasEntityWithExtInfo.model_validate(
            await self._api.json("GET", f"{ENTITY_ROOT}/guid/{guid}", params=params)
        )

    async def header_by_guid(self, guid: str) -> AtlasEntityHeader:
        """``GET /guid/{guid}/header``: the entity's header with its classifications (ERD-07)."""
        return AtlasEntityHeader.model_validate(await self._api.json("GET", f"{ENTITY_ROOT}/guid/{guid}/header"))

    async def by_unique_attributes(
        self,
        type_name: str,
        attributes: Mapping[str, Any],
        *,
        min_ext_info: bool = False,
        ignore_relationships: bool = False,
    ) -> AtlasEntityWithExtInfo:
        """``GET /uniqueAttribute/type/{t}``: the entity holding the ``attr:`` values (ERD-08, CLE-02, CLE-03)."""
        params = _attr_params(attributes) | _present(minExtInfo=min_ext_info, ignoreRelationships=ignore_relationships)
        return AtlasEntityWithExtInfo.model_validate(
            await self._api.json("GET", f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}", params=params)
        )

    async def header_by_unique_attributes(self, type_name: str, attributes: Mapping[str, Any]) -> AtlasEntityHeader:
        """``GET /uniqueAttribute/type/{t}/header``: the header of the entity holding the values (ERD-07, CLE-03)."""
        return AtlasEntityHeader.model_validate(
            await self._api.json(
                "GET", f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}/header", params=_attr_params(attributes)
            )
        )

    async def entities_by_unique_attributes(
        self,
        type_name: str,
        attribute_sets: Sequence[Mapping[str, Any]],
        *,
        min_ext_info: bool = False,
        ignore_relationships: bool = False,
    ) -> AtlasEntitiesWithExtInfo:
        """``GET /bulk/uniqueAttribute/type/{t}``: the entity each ``attr_<n>:`` set finds (ERD-08, CLE-02, CLE-03).

        The sets are 1-based in the query, in the order given (DV-19).
        """
        params = _attr_set_params(attribute_sets) | _present(
            minExtInfo=min_ext_info, ignoreRelationships=ignore_relationships
        )
        return AtlasEntitiesWithExtInfo.model_validate(
            await self._api.json("GET", f"{ENTITY_ROOT}/bulk/uniqueAttribute/type/{type_name}", params=params)
        )

    async def by_guids(
        self, guids: Sequence[str], *, min_ext_info: bool = False, ignore_relationships: bool = False
    ) -> AtlasEntitiesWithExtInfo:
        """``GET /bulk``: the entities of every ``guid``, in order (ERD-01, CLE-02)."""
        params = _present(minExtInfo=min_ext_info, ignoreRelationships=ignore_relationships)
        return AtlasEntitiesWithExtInfo.model_validate(
            await self._api.json(
                "GET", f"{ENTITY_ROOT}/bulk", params=[("guid", guid) for guid in guids] + list(params.items())
            )
        )

    async def audit_events(  # noqa: PLR0913 - the audit route's query parameters, as routes/entity.py reads them
        self,
        guid: str,
        *,
        action: EntityAuditActionV2 | None = None,
        start_key: str | None = None,
        count: int | None = None,
        offset: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> list[EntityAuditEventV2]:
        """``GET /{guid}/audit``: the entity's audit events (AUD-06..AUD-09, CLE-10).

        Each parameter travels only when set; an absent ``count`` the server
        reads as 100 and an absent ``offset`` as -1 — so, unlike ``_present``,
        this drops only the values left as ``None``: a ``count`` of 0 is a
        choice, not a default.
        """
        params = {
            name: value
            for name, value in {
                "auditAction": action,
                "startKey": start_key,
                "count": count,
                "offset": offset,
                "sortBy": sort_by,
                "sortOrder": sort_order,
            }.items()
            if value is not None
        }
        answer = await self._api.json("GET", f"{ENTITY_ROOT}/{guid}/audit", params=params)
        return [EntityAuditEventV2.model_validate(event) for event in answer]

    async def changed_classifications(self, since: int) -> AtlasEntityHeaders:
        """``GET /bulk/headers``: the entities whose classifications changed since ``since`` (CAU-07, CLE-11).

        ``since`` is the ``tagUpdateStartTime`` epoch millis; the client sends no
        end time — the server uses its own clock.
        """
        return AtlasEntityHeaders.model_validate(
            await self._api.json("GET", f"{ENTITY_ROOT}/bulk/headers", params={"tagUpdateStartTime": since})
        )

    async def create_or_update(self, entity: AtlasEntityWithExtInfo) -> EntityMutationResponse:
        """``POST ""``: create the entity, and the entities it names, or update them (EWR-02)."""
        return EntityMutationResponse.model_validate(await self._api.json("POST", ENTITY_ROOT, body=entity.to_json()))

    async def create_or_update_bulk(self, entities: AtlasEntitiesWithExtInfo) -> EntityMutationResponse:
        """``POST /bulk``: create or update every entity (EWR-02)."""
        return EntityMutationResponse.model_validate(
            await self._api.json("POST", f"{ENTITY_ROOT}/bulk", body=entities.to_json())
        )

    async def partial_update_attribute(
        self,
        guid: str,
        name: str | None,
        value: Any,  # noqa: ANN401 - the attribute value, any JSON value (EWR-15)
    ) -> EntityMutationResponse:
        """``PUT /guid/{guid}``: set the attribute ``name`` of the entity to ``value`` (EWR-15).

        The body is the bare JSON value; the server reads whatever it is.
        """
        return EntityMutationResponse.model_validate(
            await self._api.json("PUT", f"{ENTITY_ROOT}/guid/{guid}", params=_present(name=name), body=value)
        )

    async def partial_update_by_unique_attributes(
        self, type_name: str, attributes: Mapping[str, Any], entity: AtlasEntityWithExtInfo
    ) -> EntityMutationResponse:
        """``PUT /uniqueAttribute/type/{t}``: partially update the entity holding the values (EWR-14, CLE-03)."""
        return EntityMutationResponse.model_validate(
            await self._api.json(
                "PUT",
                f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}",
                params=_attr_params(attributes),
                body=entity.to_json(),
            )
        )

    async def delete_by_guid(self, guid: str, *, delete_type: DeleteType | None = None) -> EntityMutationResponse:
        """``DELETE /guid/{guid}``: the entity and what it owns (EDL-01, CLE-04).

        An absent ``delete_type`` sends no parameter: the server applies its own
        setting (EDL-04).
        """
        return EntityMutationResponse.model_validate(
            await self._api.json("DELETE", f"{ENTITY_ROOT}/guid/{guid}", params=_present(deleteType=delete_type))
        )

    async def delete_by_guids(
        self, guids: Sequence[str], *, delete_type: DeleteType | None = None
    ) -> EntityMutationResponse:
        """``DELETE /bulk``: the entities of every ``guid`` and what they own (EDL-01, CLE-04)."""
        params = [("guid", guid) for guid in guids] + list(_present(deleteType=delete_type).items())
        return EntityMutationResponse.model_validate(
            await self._api.json("DELETE", f"{ENTITY_ROOT}/bulk", params=params)
        )

    async def delete_by_unique_attributes(
        self, type_name: str, attributes: Mapping[str, Any], *, delete_type: DeleteType | None = None
    ) -> EntityMutationResponse:
        """``DELETE /uniqueAttribute/type/{t}``: the entity holding the values (EDL-02, CLE-03, CLE-04)."""
        params = _attr_params(attributes) | _present(deleteType=delete_type)
        return EntityMutationResponse.model_validate(
            await self._api.json("DELETE", f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}", params=params)
        )

    async def get_classification(self, guid: str, classification_name: str) -> AtlasClassification:
        """``GET /guid/{g}/classification/{c}``: the entity's classification of the name (CLS-03)."""
        return AtlasClassification.model_validate(
            await self._api.json("GET", f"{ENTITY_ROOT}/guid/{guid}/classification/{classification_name}")
        )

    async def get_classifications(self, guid: str) -> AtlasClassifications:
        """``GET /guid/{g}/classifications``: the entity's classifications, as a ``PList`` (CLS-03)."""
        return AtlasClassifications.model_validate(
            await self._api.json("GET", f"{ENTITY_ROOT}/guid/{guid}/classifications")
        )

    async def add_classifications(self, guid: str, classifications: Sequence[AtlasClassification]) -> None:
        """``POST /guid/{g}/classifications``: attach the classifications (CLS-04, CLE-05). Answers 204."""
        await self._api.request(
            "POST", f"{ENTITY_ROOT}/guid/{guid}/classifications", body=[c.to_json() for c in classifications]
        )

    async def add_classifications_by_unique_attributes(
        self, type_name: str, attributes: Mapping[str, Any], classifications: Sequence[AtlasClassification]
    ) -> None:
        """``POST /uniqueAttribute/type/{t}/classifications``: attach the classifications (CLS-06, CLE-03, CLE-05)."""
        await self._api.request(
            "POST",
            f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}/classifications",
            params=_attr_params(attributes),
            body=[c.to_json() for c in classifications],
        )

    async def update_classifications(self, guid: str, classifications: Sequence[AtlasClassification]) -> None:
        """``PUT /guid/{g}/classifications``: change the entity's classifications (CLS-08, CLE-05). Answers 204."""
        await self._api.request(
            "PUT", f"{ENTITY_ROOT}/guid/{guid}/classifications", body=[c.to_json() for c in classifications]
        )

    async def update_classifications_by_unique_attributes(
        self, type_name: str, attributes: Mapping[str, Any], classifications: Sequence[AtlasClassification]
    ) -> None:
        """``PUT /uniqueAttribute/type/{t}/classifications``: change them (CLS-06, CLE-03, CLE-05). Answers 204."""
        await self._api.request(
            "PUT",
            f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}/classifications",
            params=_attr_params(attributes),
            body=[c.to_json() for c in classifications],
        )

    async def delete_classification(
        self, guid: str, classification_name: str, *, associated_entity_guid: str | None = None
    ) -> None:
        """``DELETE /guid/{g}/classification/{c}``: remove it (CLS-09, CLE-05). Answers 204."""
        await self._api.request(
            "DELETE",
            f"{ENTITY_ROOT}/guid/{guid}/classification/{classification_name}",
            params=_present(associatedEntityGuid=associated_entity_guid),
        )

    async def delete_classification_by_unique_attributes(
        self, type_name: str, attributes: Mapping[str, Any], classification_name: str
    ) -> None:
        """``DELETE /uniqueAttribute/type/{t}/classification/{c}``: remove it (CLS-06, CLE-03, CLE-05)."""
        await self._api.request(
            "DELETE",
            f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}/classification/{classification_name}",
            params=_attr_params(attributes),
        )

    async def associate_classification(self, request_body: ClassificationAssociateRequest) -> None:
        """``POST /bulk/classification``: attach one classification to many entities (CLS-07, CLE-01). Answers 204."""
        await self._api.request("POST", f"{ENTITY_ROOT}/bulk/classification", body=request_body.to_json())

    async def set_classifications(self, headers: AtlasEntityHeaders) -> Any:  # noqa: ANN401 - the parsed JSON array (DV-36)
        """``POST /bulk/setClassifications``: each header's entity gets its classifications (CLA-04, CLE-08).

        The answer is a JSON array of per-guid summaries, not a model (the
        server's DV-36 text); the client returns it parsed, never reordered.
        """
        return await self._api.json("POST", f"{ENTITY_ROOT}/bulk/setClassifications", body=headers.to_json())

    async def add_or_update_business_metadata(
        self, guid: str, attributes: Mapping[str, Mapping[str, Any] | None], *, is_overwrite: bool = False
    ) -> None:
        """``POST /guid/{g}/businessmetadata``: the values set, all replaced with ``is_overwrite`` (BMD-01, CLE-07)."""
        await self._api.request(
            "POST",
            f"{ENTITY_ROOT}/guid/{guid}/businessmetadata",
            params=_present(isOverwrite=is_overwrite),
            body=dict(attributes),
        )

    async def remove_business_metadata(self, guid: str, attributes: Mapping[str, Mapping[str, Any] | None]) -> None:
        """``DELETE /guid/{g}/businessmetadata``: the body's attributes removed (BMD-05, CLE-07). Answers 204."""
        await self._api.request("DELETE", f"{ENTITY_ROOT}/guid/{guid}/businessmetadata", body=dict(attributes))

    async def add_or_update_business_metadata_of(self, guid: str, bm_name: str, attributes: Mapping[str, Any]) -> None:
        """``POST /guid/{g}/businessmetadata/{bm}``: one metadata's values set (BMD-03, CLE-07). Answers 204."""
        await self._api.request("POST", f"{ENTITY_ROOT}/guid/{guid}/businessmetadata/{bm_name}", body=dict(attributes))

    async def remove_business_metadata_of(self, guid: str, bm_name: str, attributes: Mapping[str, Any]) -> None:
        """``DELETE /guid/{g}/businessmetadata/{bm}``: one metadata's attributes, or all, removed (BMD-05, CLE-07)."""
        await self._api.request(
            "DELETE", f"{ENTITY_ROOT}/guid/{guid}/businessmetadata/{bm_name}", body=dict(attributes)
        )

    async def business_metadata_template(self) -> tuple[bytes, str]:
        """``GET /businessmetadata/import/template``: the download as bytes and content type (BMI-01, CLE-09, CL-64)."""
        response = await self._api.request("GET", f"{ENTITY_ROOT}/businessmetadata/import/template")
        return response.content, response.headers.get("content-type", "")

    async def import_business_metadata(self, file_name: str, content: bytes) -> BulkImportResponse:
        """``POST /businessmetadata/import``: the file's rows applied (BMI-02..BMI-05, CLE-09, CL-64).

        The file is the bytes the caller holds — never a path read from disk.
        """
        answer = await self._api.request(
            "POST", f"{ENTITY_ROOT}/businessmetadata/import", files={"file": (file_name, content)}
        )
        return BulkImportResponse.model_validate(answer.json())

    async def set_labels(self, guid: str, labels: Sequence[str]) -> None:
        """``POST /guid/{g}/labels``: the entity's labels become these (LBL-01, LBL-02, CLE-06). Answers 204."""
        await self._api.request("POST", f"{ENTITY_ROOT}/guid/{guid}/labels", body=list(labels))

    async def add_labels(self, guid: str, labels: Sequence[str]) -> None:
        """``PUT /guid/{g}/labels``: these labels added to the entity's (LBL-01, LBL-03, CLE-06). Answers 204."""
        await self._api.request("PUT", f"{ENTITY_ROOT}/guid/{guid}/labels", body=list(labels))

    async def remove_labels(self, guid: str, labels: Sequence[str]) -> None:
        """``DELETE /guid/{g}/labels``: these labels taken from the entity's (LBL-01, LBL-04, CLE-06). Answers 204."""
        await self._api.request("DELETE", f"{ENTITY_ROOT}/guid/{guid}/labels", body=list(labels))

    async def set_labels_by_unique_attributes(
        self, type_name: str, attributes: Mapping[str, Any], labels: Sequence[str]
    ) -> None:
        """``POST /uniqueAttribute/type/{t}/labels``: the entity holding the values gets the labels (LBL-02, CLE-06)."""
        await self._api.request(
            "POST",
            f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}/labels",
            params=_attr_params(attributes),
            body=list(labels),
        )

    async def add_labels_by_unique_attributes(
        self, type_name: str, attributes: Mapping[str, Any], labels: Sequence[str]
    ) -> None:
        """``PUT /uniqueAttribute/type/{t}/labels``: added to that entity's labels (LBL-03, CLE-03, CLE-06)."""
        await self._api.request(
            "PUT",
            f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}/labels",
            params=_attr_params(attributes),
            body=list(labels),
        )

    async def remove_labels_by_unique_attributes(
        self, type_name: str, attributes: Mapping[str, Any], labels: Sequence[str]
    ) -> None:
        """``DELETE /uniqueAttribute/type/{t}/labels``: taken from that entity's labels (LBL-04, CLE-03, CLE-06)."""
        await self._api.request(
            "DELETE",
            f"{ENTITY_ROOT}/uniqueAttribute/type/{type_name}/labels",
            params=_attr_params(attributes),
            body=list(labels),
        )


class GlossaryApi:
    """The glossary resource of an :class:`AtlasClient` (CLG-01..CLG-09): ``client.glossary``.

    The paths mirror ``routes/glossary.py`` (32 routes); the bodies are
    ``aurelius-atlas-model``'s ``glossary`` module, reused whole (DD-309). The
    paged reads send the server's ``limit``/``offset``/``sort`` defaults as
    absence (CLG-02); the create methods do not check the anchor locally
    (CLG-05) and the updates send the body as given (CLG-08) — the server
    answers. The two file routes cross as bytes (CLG-06, CL-64).
    """

    def __init__(self, api: _Api) -> None:
        self._api = api

    async def glossaries(
        self, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
    ) -> list[AtlasGlossary]:
        """``GET ""``: every glossary, paged and sorted (GLS-05, CLG-02)."""
        params = _page_params(limit, offset, sort)
        answer = await self._api.json("GET", GLOSSARY_ROOT, params=params)
        return [AtlasGlossary.model_validate(glossary) for glossary in answer]

    async def create_glossary(self, glossary: AtlasGlossary) -> AtlasGlossary:
        """``POST ""``: create the glossary (GLS-02)."""
        return AtlasGlossary.model_validate(await self._api.json("POST", GLOSSARY_ROOT, body=glossary.to_json()))

    async def import_template(self) -> tuple[bytes, str]:
        """``GET /import/template``: the download as bytes and content type (GIM-06, CLG-06, CL-64)."""
        response = await self._api.request("GET", f"{GLOSSARY_ROOT}/import/template")
        return response.content, response.headers.get("content-type", "")

    async def import_data(self, file_name: str, content: bytes) -> BulkImportResponse:
        """``POST /import``: the file's terms created (GIM-01..GIM-05, CLG-06, CL-64).

        The file is the bytes the caller holds — never a path read from disk.
        """
        answer = await self._api.request("POST", f"{GLOSSARY_ROOT}/import", files={"file": (file_name, content)})
        return BulkImportResponse.model_validate(answer.json())

    async def term(self, term_guid: str) -> AtlasGlossaryTerm:
        """``GET /term/{guid}``: the term (GTM-01)."""
        return AtlasGlossaryTerm.model_validate(await self._api.json("GET", f"{GLOSSARY_ROOT}/term/{term_guid}"))

    async def create_term(self, term: AtlasGlossaryTerm) -> AtlasGlossaryTerm:
        """``POST /term``: create the term; the anchor is the server's check (GTM-02, CLG-05)."""
        return AtlasGlossaryTerm.model_validate(
            await self._api.json("POST", f"{GLOSSARY_ROOT}/term", body=term.to_json())
        )

    async def create_terms(self, terms: Sequence[AtlasGlossaryTerm]) -> list[AtlasGlossaryTerm]:
        """``POST /terms``: create every term; the anchors are the server's check (GTM-02, CLG-05)."""
        answer = await self._api.json("POST", f"{GLOSSARY_ROOT}/terms", body=[term.to_json() for term in terms])
        return [AtlasGlossaryTerm.model_validate(term) for term in answer]

    async def update_term(self, term_guid: str, term: AtlasGlossaryTerm) -> AtlasGlossaryTerm:
        """``PUT /term/{guid}``: update the term of the path's GUID (GTM-04, CLG-08).

        The server grafts the path GUID onto the body — a body without one is
        the caller's model, sent as given.
        """
        return AtlasGlossaryTerm.model_validate(
            await self._api.json("PUT", f"{GLOSSARY_ROOT}/term/{term_guid}", body=term.to_json())
        )

    async def partial_update_term(self, term_guid: str, fields: Mapping[str, Any]) -> AtlasGlossaryTerm:
        """``PUT /term/{guid}/partial``: set the given attributes of the term (GTM-04, CLG-03).

        The body is the plain JSON object of attribute values; no fields at all
        is a caller bug the client refuses rather than a wasted round trip —
        the server's own answer for it is ``BAD_REQUEST`` (NO_PARTIAL_UPDATES).
        A field the term does not have stays the server's answer too
        (``INVALID_PARTIAL_UPDATE_ATTR``).

        Raises:
            ValueError: ``fields`` is empty.
        """
        _no_fields(fields, "GTM-04")
        return AtlasGlossaryTerm.model_validate(
            await self._api.json("PUT", f"{GLOSSARY_ROOT}/term/{term_guid}/partial", body=dict(fields))
        )

    async def delete_term(self, term_guid: str) -> None:
        """``DELETE /term/{guid}``: delete the term (GTM-05, CLG-09). Answers 204."""
        await self._api.request("DELETE", f"{GLOSSARY_ROOT}/term/{term_guid}")

    async def related_terms(self, term_guid: str) -> dict[str, list[AtlasRelatedTermHeader]]:
        """``GET /terms/{guid}/related``: the term's related terms by relation (GTM-06, CLG-07).

        The key is the relation's JSON name (``seeAlso``, ``synonyms``, …); the
        page parameters the server reads and ignores, the client does not send.
        """
        answer = await self._api.json("GET", f"{GLOSSARY_ROOT}/terms/{term_guid}/related")
        return {
            relation: [AtlasRelatedTermHeader.model_validate(header) for header in headers]
            for relation, headers in answer.items()
        }

    async def assigned_entities(
        self, term_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
    ) -> list[AtlasRelatedObjectId]:
        """``GET /terms/{guid}/assignedEntities``: the term's active assignments (GTA-01, CLG-02)."""
        answer = await self._api.json(
            "GET", f"{GLOSSARY_ROOT}/terms/{term_guid}/assignedEntities", params=_page_params(limit, offset, sort)
        )
        return [AtlasRelatedObjectId.model_validate(entity) for entity in answer]

    async def assign_term(self, term_guid: str, object_ids: Sequence[AtlasRelatedObjectId]) -> None:
        """``POST /terms/{guid}/assignedEntities``: assign the term to the entities (GTA-02, CLG-04). 204."""
        await self._api.request(
            "POST",
            f"{GLOSSARY_ROOT}/terms/{term_guid}/assignedEntities",
            body=[object_id.to_json() for object_id in object_ids],
        )

    async def remove_term_assignment(self, term_guid: str, object_ids: Sequence[AtlasRelatedObjectId]) -> None:
        """``DELETE /terms/{guid}/assignedEntities``: remove the assignments (GTA-03, CLG-04). 204."""
        await self._api.request(
            "DELETE",
            f"{GLOSSARY_ROOT}/terms/{term_guid}/assignedEntities",
            body=[object_id.to_json() for object_id in object_ids],
        )

    async def disassociate_term_assignment(self, term_guid: str, object_ids: Sequence[AtlasRelatedObjectId]) -> None:
        """``PUT /terms/{guid}/assignedEntities``: as the ``DELETE`` (GTA-03, CLG-04).

        Kept so a caller states its intent. Answers 204.
        """
        await self._api.request(
            "PUT",
            f"{GLOSSARY_ROOT}/terms/{term_guid}/assignedEntities",
            body=[object_id.to_json() for object_id in object_ids],
        )

    async def category_terms(
        self, category_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
    ) -> list[AtlasRelatedTermHeader]:
        """``GET /category/{guid}/terms``: the category's terms, paged (GTM-06, CLG-02)."""
        answer = await self._api.json(
            "GET", f"{GLOSSARY_ROOT}/category/{category_guid}/terms", params=_page_params(limit, offset, sort)
        )
        return [AtlasRelatedTermHeader.model_validate(term) for term in answer]

    async def category(self, category_guid: str) -> AtlasGlossaryCategory:
        """``GET /category/{guid}``: the category (GCT-01)."""
        return AtlasGlossaryCategory.model_validate(
            await self._api.json("GET", f"{GLOSSARY_ROOT}/category/{category_guid}")
        )

    async def related_categories(self, category_guid: str) -> dict[str, list[AtlasRelatedCategoryHeader]]:
        """``GET /category/{guid}/related``: its parent and children (GCT-07, CLG-07).

        The keys are ``parent`` and ``children``; a missing relation is absent.
        """
        answer = await self._api.json("GET", f"{GLOSSARY_ROOT}/category/{category_guid}/related")
        return {
            relation: [AtlasRelatedCategoryHeader.model_validate(header) for header in headers]
            for relation, headers in answer.items()
        }

    async def create_category(self, category: AtlasGlossaryCategory) -> AtlasGlossaryCategory:
        """``POST /category``: create the category; the anchor is the server's check (GCT-02, CLG-05)."""
        return AtlasGlossaryCategory.model_validate(
            await self._api.json("POST", f"{GLOSSARY_ROOT}/category", body=category.to_json())
        )

    async def create_categories(self, categories: Sequence[AtlasGlossaryCategory]) -> list[AtlasGlossaryCategory]:
        """``POST /categories``: create every category; anchors are the server's check (GCT-02, CLG-05)."""
        answer = await self._api.json(
            "POST", f"{GLOSSARY_ROOT}/categories", body=[category.to_json() for category in categories]
        )
        return [AtlasGlossaryCategory.model_validate(category) for category in answer]

    async def update_category(self, category_guid: str, category: AtlasGlossaryCategory) -> AtlasGlossaryCategory:
        """``PUT /category/{guid}``: update the category of the path's GUID (GCT-04, CLG-08)."""
        return AtlasGlossaryCategory.model_validate(
            await self._api.json("PUT", f"{GLOSSARY_ROOT}/category/{category_guid}", body=category.to_json())
        )

    async def partial_update_category(self, category_guid: str, fields: Mapping[str, Any]) -> AtlasGlossaryCategory:
        """``PUT /category/{guid}/partial``: set the given attributes (GCT-05, CLG-03).

        Raises:
            ValueError: ``fields`` is empty (the server's NO_PARTIAL_UPDATES).
        """
        _no_fields(fields, "GCT-05")
        return AtlasGlossaryCategory.model_validate(
            await self._api.json("PUT", f"{GLOSSARY_ROOT}/category/{category_guid}/partial", body=dict(fields))
        )

    async def delete_category(self, category_guid: str) -> None:
        """``DELETE /category/{guid}``: delete the category (GCT-06, CLG-09). Answers 204."""
        await self._api.request("DELETE", f"{GLOSSARY_ROOT}/category/{category_guid}")

    async def glossary(self, glossary_guid: str) -> AtlasGlossary:
        """``GET /{guid}``: the glossary (GLS-01, GLS-06)."""
        return AtlasGlossary.model_validate(await self._api.json("GET", f"{GLOSSARY_ROOT}/{glossary_guid}"))

    async def detailed_glossary(self, glossary_guid: str) -> AtlasGlossaryExtInfo:
        """``GET /{guid}/detailed``: the glossary with its terms and categories by GUID (GLS-06)."""
        return AtlasGlossaryExtInfo.model_validate(
            await self._api.json("GET", f"{GLOSSARY_ROOT}/{glossary_guid}/detailed")
        )

    async def glossary_categories(
        self, glossary_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
    ) -> list[AtlasGlossaryCategory]:
        """``GET /{guid}/categories``: the glossary's categories, paged (GLS-05, CLG-02)."""
        answer = await self._api.json(
            "GET",
            f"{GLOSSARY_ROOT}/{glossary_guid}/categories",
            params=_page_params(limit, offset, sort),
        )
        return [AtlasGlossaryCategory.model_validate(category) for category in answer]

    async def glossary_categories_headers(
        self, glossary_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
    ) -> list[AtlasRelatedCategoryHeader]:
        """``GET /{guid}/categories/headers``: the category headers, paged (GLS-05, CLG-02)."""
        answer = await self._api.json(
            "GET",
            f"{GLOSSARY_ROOT}/{glossary_guid}/categories/headers",
            params=_page_params(limit, offset, sort),
        )
        return [AtlasRelatedCategoryHeader.model_validate(header) for header in answer]

    async def glossary_terms(
        self, glossary_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
    ) -> list[AtlasGlossaryTerm]:
        """``GET /{guid}/terms``: the glossary's terms, paged (GTM-06, CLG-02)."""
        answer = await self._api.json(
            "GET", f"{GLOSSARY_ROOT}/{glossary_guid}/terms", params=_page_params(limit, offset, sort)
        )
        return [AtlasGlossaryTerm.model_validate(term) for term in answer]

    async def glossary_terms_headers(
        self, glossary_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
    ) -> list[AtlasRelatedTermHeader]:
        """``GET /{guid}/terms/headers``: the term headers, paged (GTM-06, CLG-02)."""
        answer = await self._api.json(
            "GET",
            f"{GLOSSARY_ROOT}/{glossary_guid}/terms/headers",
            params=_page_params(limit, offset, sort),
        )
        return [AtlasRelatedTermHeader.model_validate(header) for header in answer]

    async def update_glossary(self, glossary_guid: str, glossary: AtlasGlossary) -> AtlasGlossary:
        """``PUT /{guid}``: update the glossary of the path's GUID (GLS-03, CLG-08)."""
        return AtlasGlossary.model_validate(
            await self._api.json("PUT", f"{GLOSSARY_ROOT}/{glossary_guid}", body=glossary.to_json())
        )

    async def partial_update_glossary(self, glossary_guid: str, fields: Mapping[str, Any]) -> AtlasGlossary:
        """``PUT /{guid}/partial``: set the given attributes of the glossary (GLS-03, CLG-03).

        Raises:
            ValueError: ``fields`` is empty (the server's NO_PARTIAL_UPDATES).
        """
        _no_fields(fields, "GLS-03")
        return AtlasGlossary.model_validate(
            await self._api.json("PUT", f"{GLOSSARY_ROOT}/{glossary_guid}/partial", body=dict(fields))
        )

    async def delete_glossary(self, glossary_guid: str) -> None:
        """``DELETE /{guid}``: delete the glossary (GLS-04, CLG-09). Answers 204."""
        await self._api.request("DELETE", f"{GLOSSARY_ROOT}/{glossary_guid}")


class RelationshipApi:
    """The relationship resource of an :class:`AtlasClient` (CLR-01..CLR-04): ``client.relationship``.

    The paths mirror ``routes/relationship.py`` (4 routes); the bodies are
    ``aurelius-atlas-model``'s, reused whole (DD-309). The ends of a
    relationship are never checked here — the server answers (REL-04..REL-07).
    """

    def __init__(self, api: _Api) -> None:
        self._api = api

    async def create(self, relationship: AtlasRelationship) -> AtlasRelationship:
        """``POST ""`: a new relationship between two entities (REL-04, REL-05, CLR-03)."""
        return AtlasRelationship.model_validate(
            await self._api.json("POST", RELATIONSHIP_ROOT, body=relationship.to_json())
        )

    async def update(self, relationship: AtlasRelationship) -> AtlasRelationship:
        """``PUT ""`: the relationship's tag propagation and attributes (REL-07, CLR-03)."""
        return AtlasRelationship.model_validate(
            await self._api.json("PUT", RELATIONSHIP_ROOT, body=relationship.to_json())
        )

    async def get(self, guid: str, *, extended_info: bool = False) -> AtlasRelationshipWithExtInfo:
        """``GET /guid/{guid}``: the relationship (REL-03, REL-06, CLR-02).

        ``extended_info`` sends ``extendedInfo=true`` and the answer carries the
        ends' headers in ``referred_entities``; without it the server answers
        the same model holding only ``relationship``, and the client sends no
        parameter at all (the Java default).
        """
        answer = await self._api.json(
            "GET", f"{RELATIONSHIP_ROOT}/guid/{guid}", params=_present(extendedInfo=extended_info)
        )
        return AtlasRelationshipWithExtInfo.model_validate(answer)

    async def delete(self, guid: str, *, delete_type: DeleteType | None = None) -> None:
        """``DELETE /guid/{guid}``: soft or hard, as asked (REL-08, EDL-04, CLR-04). Answers 204.

        An absent ``delete_type`` sends no parameter: the server applies its
        own ``atlas.purge.entity.delete.strategy`` (as CLE-04).
        """
        await self._api.request("DELETE", f"{RELATIONSHIP_ROOT}/guid/{guid}", params=_present(deleteType=delete_type))


class LineageApi:
    """The lineage resource of an :class:`AtlasClient` (CL-61..CL-63): ``client.lineage``.

    The paths mirror ``routes/lineage.py``; the answer body is this library's
    ``LineageInfo`` (CL-12) — the lenient, UUID-keyed shape 8.2 consumes, not
    ``aurelius-atlas-model``'s strict ``AtlasLineageInfo``.
    """

    def __init__(self, api: _Api) -> None:
        self._api = api

    async def get(self, guid: UUID, depth: int = 3, direction: Direction = "BOTH") -> LineageInfo:
        """``GET api/atlas/v2/lineage/{guid}`` (CL-61, LM-01's upstream) — the entity's lineage graph.

        Raises:
            AtlasClientError: Any non-2xx answer, including the 404 of a guid with
                no lineage (LM-05) — the caller maps the statuses.
        """
        return LineageInfo.model_validate(
            await self._api.json("GET", f"{LINEAGE_ROOT}/{guid}", params={"depth": depth, "direction": direction})
        )

    async def get_on_demand(
        self, guid: UUID, constraints: Mapping[str, LineageOnDemandConstraints] | None = None
    ) -> LineageInfo:
        """``POST api/atlas/v2/lineage/{guid}`` (CL-62): lineage on demand, within the constraints per GUID.

        The constraints are ``aurelius-atlas-model``'s (DD-309). A server with the
        feature off answers ``LINEAGE_ON_DEMAND_NOT_ENABLED``, raised as usual (CL-04).
        """
        body = {guid: constraint.to_json() for guid, constraint in (constraints or {}).items()}
        return LineageInfo.model_validate(await self._api.json("POST", f"{LINEAGE_ROOT}/{guid}", body=body or None))

    async def get_by_unique_attributes(
        self,
        type_name: str,
        attributes: Mapping[str, Any],
        depth: int = 3,
        direction: Direction = "BOTH",
    ) -> LineageInfo:
        """``GET api/atlas/v2/lineage/uniqueAttribute/type/{type_name}`` (CL-63): the lineage of the entity.

        The entity is the one holding the ``attr:`` values, as ``routes/lineage.py`` reads them.
        """
        params: dict[str, Any] = {f"attr:{name}": value for name, value in attributes.items()}
        params.update({"depth": depth, "direction": direction})
        return LineageInfo.model_validate(
            await self._api.json("GET", f"{LINEAGE_ROOT}/uniqueAttribute/type/{type_name}", params=params)
        )


def _present(**params: Any) -> dict[str, Any]:  # noqa: ANN401 - the query parameter values
    """The endpoint's query parameters: a given value, its Java defaults left out.

    The server reads an absent boolean as false and an absent number as 0 — the
    defaults the routes pass their parameters on — so a false flag or a zero page
    travels as its absence; httpx renders a set flag as ``true``, the shape the
    route's ``flag`` parses.
    """
    return {name: value for name, value in params.items() if value is not None and value != 0}


def _attr_params(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """The unique-attribute values as ``attr:<name>`` parameters, as the route reads them (CLE-03, ERD-08)."""
    return {f"attr:{name}": value for name, value in attributes.items()}


def _attr_set_params(attribute_sets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Each set's unique-attribute values as ``attr_<n>:<name>``, 1-based, in order (CLE-03, DV-19)."""
    return {
        f"attr_{index}:{name}": value
        for index, attributes in enumerate(attribute_sets, start=1)
        for name, value in attributes.items()
    }


def _no_fields(fields: Mapping[str, Any], rule: str) -> None:
    """Refuse an empty partial-update body client-side (CLG-03).

    The server's own answer for it is ``BAD_REQUEST`` (NO_PARTIAL_UPDATES);
    ``rule`` names the server rule (GTM-04 / GCT-05 / GLS-03) the caller can
    match on.
    """
    if not fields:
        msg = f"no fields to set: the server answers BAD_REQUEST (NO_PARTIAL_UPDATES, {rule})"
        raise ValueError(msg)


def _page_params(limit: int | None, offset: int, sort: GlossarySort | None) -> dict[str, Any]:
    """The glossary reads' paging parameters, the server's defaults left out (CLG-02, GLS-05).

    The server reads an absent ``limit`` as -1 (every item), an absent
    ``offset`` as 0 and an absent ``sort`` as ``ASC`` — so a default travels as
    its absence, and a caller that passes ``limit=-1`` explicitly is sent one.
    """
    return _present(limit=limit, offset=offset, sort=sort)


def _parse_def(payload: dict[str, Any]) -> AtlasBaseTypeDef:
    """The definition of any kind, parsed into its category's model (TYR-01, TYR-02)."""
    kind = TypeCategory.__members__.get(str(payload.get("category", "")))
    model = _KIND_MODELS.get(kind, AtlasBaseTypeDef) if kind is not None else AtlasBaseTypeDef
    return model.model_validate(payload)


class AtlasClient:
    """The client for one Atlas metadata server (CL-11, DD-203, DD-205).

    Args:
        http: The ``httpx.AsyncClient`` to speak through, built by the caller —
            its builder owns its lifecycle, this client only speaks through it.
            Its base URL carries the server root; the paths here are relative to it.
        token: The bearer token source (CL-03).
    """

    def __init__(self, http: httpx.AsyncClient, token: TokenSource) -> None:
        self._http = http
        self._token = token
        api = _Api(self._http, token)
        self.admin = AdminApi(api)
        self.types = TypesApi(api)
        self.entity = EntityApi(api)
        self.glossary = GlossaryApi(api)
        self.relationship = RelationshipApi(api)
        self.search = SearchApi(api)
        self.lineage = LineageApi(api)

    def with_token(self, token: TokenSource) -> AtlasClient:
        """The same client speaking with ``token`` — sharing the connection pool (CL-03, LM-04).

        A route that forwards the caller's token binds one per request; closing the
        pool is its builder's job, not the wrapper's.
        """
        return AtlasClient(self._http, token)

    async def get_lineage(self, guid: UUID, depth: int = 3, direction: Direction = "BOTH") -> LineageInfo:
        """The alias of ``lineage.get`` (CL-61, DD-308) — use ``client.lineage.get``.

        Kept for one release-cycle for the 8.2 app, which calls it. It speaks the
        fixed path now (``api/atlas/v2/lineage``, the mounted route) — the old
        bare ``v2/lineage`` answered 404 against this workspace's server.

        Raises:
            AtlasClientError: Any non-2xx answer, including the 404 of a guid with
                no lineage (LM-05) — the caller maps the statuses.
        """
        return await self.lineage.get(guid, depth, direction)
