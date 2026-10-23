"""The async client for the Atlas metadata API (CL-01..CL-05, CL-11; DD-114, DD-115, DD-116).

One client per server: constructed from an externally built ``httpx.AsyncClient``
and a token source, reading no environment variables (CL-01) — the app builds the
httpx client from its own settings (TLS, timeout) and passes it in. The request
paths are relative, appended to that client's base URL, so a URL with a trailing
slash — the ``str()`` of a pydantic ``HttpUrl`` — works as given (CL-01); the
builder closes the pool, the API client never touches its lifecycle. Because the
client arrives from outside, tests hand over one built on a ``MockTransport`` and
no socket opens (CL-02, the DD-111 seam made async). Every request carries
``authorization: Bearer <token>`` from the token source (CL-03); a non-2xx answer
raises :class:`AtlasClientError` with the status and the server's
``{errorCode, errorMessage}`` when the body parses (CL-04); an unreachable upstream
propagates as ``httpx``'s own error — mapping it to an HTTP status is the app's job
(LM-07's DV-22), not the client's (CL-05).

The paths mirror the server's routes verbatim: ``routes/admin.py`` under
``/api/atlas/admin``, ``routes/types.py`` under ``/api/atlas/v2/types``, and the
``v2/lineage/{guid}`` feed of the server root (whose route lands with 5.1, CL-11).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx
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
from aurelius_atlas_server_client.models import AtlasErrorInfo, AtlasSessionInfo, AtlasStatus, AtlasVersion

type TokenSource = str | Callable[[], str]
"""Where the bearer token comes from: a fixed token, or a callable that yields one.

The callable shape is 8.2's forwarding (LM-04): a route passes a source that yields
the caller's own token, so the client sends the browser's credential upstream.
"""

DEFAULT_TIMEOUT_SECONDS = 10.0
"""The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01)."""

ADMIN_ROOT = "api/atlas/admin"
TYPES_ROOT = "api/atlas/v2/types"
LINEAGE_ROOT = "v2/lineage"
"""The route prefixes of the server's resources (``routes/admin.py``, ``routes/types.py``, 5.1's feed).

Relative to the httpx client's base URL (CL-01): httpx appends them, so the base
URL the app passes — trailing slash included, as a pydantic ``HttpUrl`` renders
one — works as given.
"""

CLIENT_ERROR = 400
"""The status where an answer becomes an error: the client-error boundary (CL-04)."""
"""The route prefixes of the server's resources (``routes/admin.py``, ``routes/types.py``, 5.1's feed)."""

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
        params: Mapping[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """One request with the bearer header; a non-2xx answer raises (CL-03..CL-05)."""
        response = await self.http.request(method, path, params=params, json=body, headers=_bearer(self.token))
        if response.status_code >= CLIENT_ERROR:
            raise AtlasClientError(response.status_code, _error_info(response))
        return response

    async def json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        body: dict[str, Any] | None = None,
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


def _parse_def(payload: dict[str, Any]) -> AtlasBaseTypeDef:
    """The definition of any kind, parsed into its category's model (TYR-01, TYR-02)."""
    kind = TypeCategory.__members__.get(str(payload.get("category", "")))
    model = _KIND_MODELS.get(kind, AtlasBaseTypeDef) if kind is not None else AtlasBaseTypeDef
    return model.model_validate(payload)


class AtlasClient:
    """The client for one Atlas metadata server (CL-11, DD-114, DD-116).

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

    def with_token(self, token: TokenSource) -> AtlasClient:
        """The same client speaking with ``token`` — sharing the connection pool (CL-03, LM-04).

        A route that forwards the caller's token binds one per request; closing the
        pool is its builder's job, not the wrapper's.
        """
        return AtlasClient(self._http, token)

    async def get_lineage(self, guid: str, depth: int = 3, direction: Direction = "BOTH") -> LineageInfo:
        """``GET /v2/lineage/{guid}`` (LM-01's upstream, CL-11/CL-12) — the server route lands with 5.1.

        Raises:
            AtlasClientError: Any non-2xx answer, including the 404 of a guid with
                no lineage (LM-05) — the caller maps the statuses.
        """
        return LineageInfo.model_validate(
            await _Api(self._http, self._token).json(
                "GET", f"{LINEAGE_ROOT}/{guid}", params={"depth": depth, "direction": direction}
            )
        )
