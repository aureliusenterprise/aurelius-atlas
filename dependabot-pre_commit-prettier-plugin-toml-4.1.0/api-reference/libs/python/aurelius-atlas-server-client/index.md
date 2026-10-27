# aurelius-atlas-server-client

The contract and the async client of the Atlas REST API (8.4, DD-203, DD-204): the admin, types and lineage models every consumer of `aurelius-atlas-server` speaks, and the `httpx2`-based `AtlasClient` that calls it. The lineage-model app imports the lineage wire models from here — one source of truth for both sides of the wire.

## Installation

```
[project.dependencies]
aurelius-atlas-server-client = "*"

[tool.uv.sources.aurelius-atlas-server-client]
workspace = true
```

## Documentation

## aurelius\_atlas\_server\_client.models

The admin and error shapes of the Atlas metadata API (CL-10, 8.4).

The response bodies the server's `routes/admin.py` and its error handler answer, stated as models so a client can parse them and a test can name them. The typedef bodies are not restated here — they are `aurelius-atlas-model`'s (DD-002), reused whole (CL-10); this module covers only what that library never had: the admin answers, and the `{errorCode, errorMessage}` body of every Atlas error (SRV-04).

Classes:

- **`AtlasErrorInfo`** –

  The body every Atlas error is answered with.
- **`AtlasSessionInfo`** –

  The body of `GET /api/atlas/admin/session`.
- **`AtlasStatus`** –

  The body of `GET /api/atlas/admin/status`.
- **`AtlasVersion`** –

  The body of `GET /api/atlas/admin/version`.

### AtlasErrorInfo

Bases: `AtlasModel`

The body every Atlas error is answered with.

**Show JSON schema:**

```
{
  "description": "The body every Atlas error is answered with.",
  "properties": {
    "errorCode": {
      "description": "The Atlas error code, e.g. ``ATLAS-400-00-007``.",
      "title": "Errorcode",
      "type": "string"
    },
    "errorMessage": {
      "description": "The human-readable error message.",
      "title": "Errormessage",
      "type": "string"
    },
    "errorCause": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The cause of a server-side error, when there is one.",
      "title": "Errorcause"
    }
  },
  "required": [
    "errorCode",
    "errorMessage"
  ],
  "title": "AtlasErrorInfo",
  "type": "object"
}
```

Fields:

- `error_code` (`str`)
- `error_message` (`str`)
- `error_cause` (`str | None`)

#### error\_cause

```
error_cause: str | None = None
```

The cause of a server-side error, when there is one.

#### error\_code

```
error_code: str
```

The Atlas error code, e.g. `ATLAS-400-00-007`.

#### error\_message

```
error_message: str
```

The human-readable error message.

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasSessionInfo

Bases: `AtlasModel`

The body of `GET /api/atlas/admin/session`.

**Show JSON schema:**

```
{
  "description": "The body of ``GET /api/atlas/admin/session``.",
  "properties": {
    "userName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The signed-in user's name, when known.",
      "title": "Username"
    },
    "groups": {
      "description": "The groups of the signed-in user.",
      "items": {
        "type": "string"
      },
      "title": "Groups",
      "type": "array"
    },
    "timezones": {
      "description": "The timezones the UI offers.",
      "items": {
        "type": "string"
      },
      "title": "Timezones",
      "type": "array"
    },
    "_csrfToken": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The CSRF token mutating requests must carry.",
      "title": "Csrftoken"
    }
  },
  "title": "AtlasSessionInfo",
  "type": "object"
}
```

Fields:

- `user_name` (`str | None`)
- `groups` (`list[str]`)
- `timezones` (`list[str]`)
- `csrf_token` (`str | None`)

#### csrf\_token

```
csrf_token: str | None = None
```

The CSRF token mutating requests must carry.

#### groups

```
groups: list[str]
```

The groups of the signed-in user.

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### timezones

```
timezones: list[str]
```

The timezones the UI offers.

#### user\_name

```
user_name: str | None = None
```

The signed-in user's name, when known.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasStatus

Bases: `AtlasModel`

The body of `GET /api/atlas/admin/status`.

**Show JSON schema:**

```
{
  "description": "The body of ``GET /api/atlas/admin/status``.",
  "properties": {
    "Status": {
      "description": "The service state; the only state is ``ACTIVE``.",
      "title": "Status",
      "type": "string"
    }
  },
  "required": [
    "Status"
  ],
  "title": "AtlasStatus",
  "type": "object"
}
```

Fields:

- `status` (`str`)

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### status

```
status: str
```

The service state; the only state is `ACTIVE`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasVersion

Bases: `AtlasModel`

The body of `GET /api/atlas/admin/version`.

**Show JSON schema:**

```
{
  "description": "The body of ``GET /api/atlas/admin/version``.",
  "properties": {
    "Version": {
      "description": "The software version.",
      "title": "Version",
      "type": "string"
    },
    "Revision": {
      "description": "The source revision the software was built from.",
      "title": "Revision",
      "type": "string"
    },
    "Name": {
      "description": "The software name.",
      "title": "Name",
      "type": "string"
    },
    "Description": {
      "description": "A description of the software.",
      "title": "Description",
      "type": "string"
    }
  },
  "required": [
    "Version",
    "Revision",
    "Name",
    "Description"
  ],
  "title": "AtlasVersion",
  "type": "object"
}
```

Config:

- `alias_generator`: `to_camel`
- `validate_by_alias`: `True`
- `validate_by_name`: `True`
- `validate_assignment`: `True`
- `extra`: `ignore`
- `coerce_numbers_to_str`: `True`

Fields:

- `version` (`str`)
- `revision` (`str`)
- `name` (`str`)
- `description` (`str`)

#### description

```
description: str
```

A description of the software.

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str
```

The software name.

#### revision

```
revision: str
```

The source revision the software was built from.

#### version

```
version: str
```

The software version.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_server\_client.lineage

The Atlas `v2/lineage/{guid}` body, as the server client's contract (CL-12, LM-04).

Moved here from `aurelius_atlas_lineage_model.lineage` by increment 8.4 (DD-203): the body is the *server's* answer — the Aurelius `LineageInfo` wire shape of `libs/m4i-atlas-core` (ADR 055 R4), stated as pydantic (DD-198) so the serving side (5.1's lineage feed) and every calling side (8.2 today) validate one class.

The *flattening* is not here: `PROCESS_TYPES`, `LINEAGE_RULES` and `flatten_relations` are 8.2's app logic and stay in the app (8.4 spec, CL-12).

Type Aliases:

- **`Direction`** –

  The lineage directions Atlas accepts (the legacy's `LineageDirection` enum, LM-01).

Classes:

- **`EntityHeaderLite`** –

  The fields of an Atlas entity header the lineage body carries.
- **`LineageInfo`** –

  The body of Atlas's `v2/lineage/{guid}` answer.
- **`LineageRelation`** –

  One Atlas lineage relation: an edge between two entity guids.

### Direction

```
Direction = Literal['BOTH', 'INPUT', 'OUTPUT']
```

The lineage directions Atlas accepts (the legacy's `LineageDirection` enum, LM-01).

### EntityHeaderLite

Bases: `BaseModel`

The fields of an Atlas entity header the lineage body carries.

**Show JSON schema:**

```
{
  "description": "The fields of an Atlas entity header the lineage body carries.",
  "properties": {
    "guid": {
      "description": "The entity's guid.",
      "format": "uuid",
      "title": "Guid",
      "type": "string"
    },
    "typeName": {
      "default": "",
      "description": "The entity's type name.",
      "title": "Typename",
      "type": "string"
    },
    "displayText": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The entity's display text, when it has one.",
      "title": "Displaytext"
    }
  },
  "required": [
    "guid"
  ],
  "title": "EntityHeaderLite",
  "type": "object"
}
```

Config:

- `populate_by_name`: `True`
- `extra`: `ignore`

Fields:

- `guid` (`UUID`)
- `type_name` (`str`)
- `display_text` (`str | None`)

#### display\_text

```
display_text: str | None = None
```

The entity's display text, when it has one.

#### guid

```
guid: UUID
```

The entity's guid.

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='ignore')
```

#### type\_name

```
type_name: str = ''
```

The entity's type name.

### LineageInfo

Bases: `BaseModel`

The body of Atlas's `v2/lineage/{guid}` answer.

**Show JSON schema:**

```
{
  "$defs": {
    "EntityHeaderLite": {
      "description": "The fields of an Atlas entity header the lineage body carries.",
      "properties": {
        "guid": {
          "description": "The entity's guid.",
          "format": "uuid",
          "title": "Guid",
          "type": "string"
        },
        "typeName": {
          "default": "",
          "description": "The entity's type name.",
          "title": "Typename",
          "type": "string"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The entity's display text, when it has one.",
          "title": "Displaytext"
        }
      },
      "required": [
        "guid"
      ],
      "title": "EntityHeaderLite",
      "type": "object"
    },
    "LineageRelation": {
      "description": "One Atlas lineage relation: an edge between two entity guids.",
      "properties": {
        "fromEntityId": {
          "description": "The guid of the source entity.",
          "format": "uuid",
          "title": "Fromentityid",
          "type": "string"
        },
        "relationshipId": {
          "description": "The id of the lineage relation.",
          "title": "Relationshipid",
          "type": "string"
        },
        "toEntityId": {
          "description": "The guid of the target entity.",
          "format": "uuid",
          "title": "Toentityid",
          "type": "string"
        }
      },
      "required": [
        "fromEntityId",
        "relationshipId",
        "toEntityId"
      ],
      "title": "LineageRelation",
      "type": "object"
    }
  },
  "description": "The body of Atlas's ``v2/lineage/{guid}`` answer.",
  "properties": {
    "guidEntityMap": {
      "additionalProperties": {
        "$ref": "#/$defs/EntityHeaderLite"
      },
      "description": "The entity headers of the lineage graph, keyed by guid.",
      "propertyNames": {
        "format": "uuid"
      },
      "title": "Guidentitymap",
      "type": "object"
    },
    "relations": {
      "description": "The lineage edges of the graph.",
      "items": {
        "$ref": "#/$defs/LineageRelation"
      },
      "title": "Relations",
      "type": "array"
    }
  },
  "title": "LineageInfo",
  "type": "object"
}
```

Config:

- `populate_by_name`: `True`
- `extra`: `ignore`

Fields:

- `guid_entity_map` (`dict[UUID, EntityHeaderLite]`)
- `relations` (`list[LineageRelation]`)

#### guid\_entity\_map

```
guid_entity_map: dict[UUID, EntityHeaderLite]
```

The entity headers of the lineage graph, keyed by guid.

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='ignore')
```

#### relations

```
relations: list[LineageRelation]
```

The lineage edges of the graph.

### LineageRelation

Bases: `BaseModel`

One Atlas lineage relation: an edge between two entity guids.

**Show JSON schema:**

```
{
  "description": "One Atlas lineage relation: an edge between two entity guids.",
  "properties": {
    "fromEntityId": {
      "description": "The guid of the source entity.",
      "format": "uuid",
      "title": "Fromentityid",
      "type": "string"
    },
    "relationshipId": {
      "description": "The id of the lineage relation.",
      "title": "Relationshipid",
      "type": "string"
    },
    "toEntityId": {
      "description": "The guid of the target entity.",
      "format": "uuid",
      "title": "Toentityid",
      "type": "string"
    }
  },
  "required": [
    "fromEntityId",
    "relationshipId",
    "toEntityId"
  ],
  "title": "LineageRelation",
  "type": "object"
}
```

Config:

- `populate_by_name`: `True`
- `extra`: `ignore`

Fields:

- `from_entity_id` (`UUID`)
- `relationship_id` (`str`)
- `to_entity_id` (`UUID`)

#### from\_entity\_id

```
from_entity_id: UUID
```

The guid of the source entity.

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='ignore')
```

#### relationship\_id

```
relationship_id: str
```

The id of the lineage relation.

#### to\_entity\_id

```
to_entity_id: UUID
```

The guid of the target entity.

## aurelius\_atlas\_server\_client.client

The async client for the Atlas metadata API (CL-01..CL-05, CL-11; DD-203, DD-204, DD-205).

One client per server: constructed from an externally built `httpx.AsyncClient` and a token source, reading no environment variables (CL-01) — the app builds the httpx client from its own settings (TLS, timeout) and passes it in. The request paths are relative, appended to that client's base URL, so a URL with a trailing slash — the `str()` of a pydantic `HttpUrl` — works as given (CL-01); the builder closes the pool, the API client never touches its lifecycle. Because the client arrives from outside, tests hand over one built on a `MockTransport` and no socket opens (CL-02, the DD-200 seam made async). Every request carries `authorization: Bearer <token>` from the token source (CL-03); a non-2xx answer raises :class:`AtlasClientError` with the status and the server's `{errorCode, errorMessage}` when the body parses (CL-04); an unreachable upstream propagates as `httpx`'s own error — mapping it to an HTTP status is the app's job (LM-07's DV-80), not the client's (CL-05).

The paths mirror the server's routes verbatim: `routes/admin.py` under `/api/atlas/admin`, `routes/types.py` under `/api/atlas/v2/types`, the discovery routes of `routes/discovery.py` under `/api/atlas/v2/search` (CL-13), and the `v2/lineage/{guid}` feed of the server root (whose route lands with 5.1, CL-11).

Type Aliases:

- **`TokenSource`** –

  Where the bearer token comes from: a fixed token, or a callable that yields one.

Classes:

- **`AdminApi`** –

  The admin resource of an :class:`AtlasClient` (CL-11): `client.admin`.
- **`AtlasClient`** –

  The client for one Atlas metadata server (CL-11, DD-203, DD-205).
- **`AtlasClientError`** –

  A non-2xx answer from the Atlas server, with the status and the error body (CL-04).
- **`SearchApi`** –

  The discovery resource of an :class:`AtlasClient` (CL-13): `client.search`.
- **`TypesApi`** –

  The typedef resource of an :class:`AtlasClient` (CL-11): `client.types`.

Attributes:

- **`ADMIN_ROOT`** –
- **`CLIENT_ERROR`** –

  The status where an answer becomes an error: the client-error boundary (CL-04).
- **`DEFAULT_TIMEOUT_SECONDS`** –

  The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01).
- **`DISCOVERY_ROOT`** –
- **`KIND_PATHS`** (`dict[TypeCategory, str]`) –

  The path segment of each kind's lookups, mirroring `routes/types.py`'s `KIND_PATHS` (CL-11).
- **`LINEAGE_ROOT`** –

  The route prefixes of the server's resources (`routes/admin.py`, `routes/types.py`,
- **`TYPES_ROOT`** –

### ADMIN\_ROOT

```
ADMIN_ROOT = 'api/atlas/admin'
```

### CLIENT\_ERROR

```
CLIENT_ERROR = 400
```

The status where an answer becomes an error: the client-error boundary (CL-04).

### DEFAULT\_TIMEOUT\_SECONDS

```
DEFAULT_TIMEOUT_SECONDS = 10.0
```

The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01).

### DISCOVERY\_ROOT

```
DISCOVERY_ROOT = 'api/atlas/v2/search'
```

### KIND\_PATHS

```
KIND_PATHS: dict[TypeCategory, str] = {
    TypeCategory.ENUM: "enumdef",
    TypeCategory.STRUCT: "structdef",
    TypeCategory.CLASSIFICATION: "classificationdef",
    TypeCategory.ENTITY: "entitydef",
    TypeCategory.RELATIONSHIP: "relationshipdef",
    TypeCategory.BUSINESS_METADATA: "businessmetadatadef",
}
```

The path segment of each kind's lookups, mirroring `routes/types.py`'s `KIND_PATHS` (CL-11).

### LINEAGE\_ROOT

```
LINEAGE_ROOT = 'v2/lineage'
```

The route prefixes of the server's resources (`routes/admin.py`, `routes/types.py`, `routes/discovery.py`, 5.1's feed).

Relative to the httpx client's base URL (CL-01): httpx appends them, so the base URL the app passes — trailing slash included, as a pydantic `HttpUrl` renders one — works as given.

### TYPES\_ROOT

```
TYPES_ROOT = 'api/atlas/v2/types'
```

### TokenSource

```
TokenSource = str | Callable[[], str]
```

Where the bearer token comes from: a fixed token, or a callable that yields one.

The callable shape is 8.2's forwarding (LM-04): a route passes a source that yields the caller's own token, so the client sends the browser's credential upstream.

### AdminApi

```
AdminApi(api: _Api)
```

The admin resource of an :class:`AtlasClient` (CL-11): `client.admin`.

Methods:

- **`liveness`** –

  `GET /api/atlas/admin/liveness` — the plain-text answer (ADM-03).
- **`readiness`** –

  `GET /api/atlas/admin/readiness` — the plain-text answer.
- **`session`** –

  `GET /api/atlas/admin/session` (ADM-05).
- **`status`** –

  `GET /api/atlas/admin/status` (ADM-02).
- **`version`** –

  `GET /api/atlas/admin/version` (ADM-01).

#### liveness

```
liveness() -> str
```

`GET /api/atlas/admin/liveness` — the plain-text answer (ADM-03).

#### readiness

```
readiness() -> str
```

`GET /api/atlas/admin/readiness` — the plain-text answer.

An `AtlasClientError` when the server is not ready (ADM-04).

#### session

```
session() -> AtlasSessionInfo
```

`GET /api/atlas/admin/session` (ADM-05).

#### status

```
status() -> AtlasStatus
```

`GET /api/atlas/admin/status` (ADM-02).

#### version

```
version() -> AtlasVersion
```

`GET /api/atlas/admin/version` (ADM-01).

### AtlasClient

```
AtlasClient(http: AsyncClient, token: TokenSource)
```

The client for one Atlas metadata server (CL-11, DD-203, DD-205).

Parameters:

- #### **`http`**

  (`AsyncClient`) –

  The `httpx.AsyncClient` to speak through, built by the caller — its builder owns its lifecycle, this client only speaks through it. Its base URL carries the server root; the paths here are relative to it.
- #### **`token`**

  (`TokenSource`) –

  The bearer token source (CL-03).

Methods:

- **`get_lineage`** –

  `GET /v2/lineage/{guid}` (LM-01's upstream, CL-11/CL-12) — the server route lands with 5.1.
- **`with_token`** –

  The same client speaking with `token` — sharing the connection pool (CL-03, LM-04).

Attributes:

- **`admin`** –
- **`search`** –
- **`types`** –

#### admin

```
admin = AdminApi(api)
```

#### search

```
search = SearchApi(api)
```

#### types

```
types = TypesApi(api)
```

#### get\_lineage

```
get_lineage(guid: UUID, depth: int = 3, direction: Direction = 'BOTH') -> LineageInfo
```

`GET /v2/lineage/{guid}` (LM-01's upstream, CL-11/CL-12) — the server route lands with 5.1.

Raises:

- `AtlasClientError` –

  Any non-2xx answer, including the 404 of a guid with no lineage (LM-05) — the caller maps the statuses.

#### with\_token

```
with_token(token: TokenSource) -> AtlasClient
```

The same client speaking with `token` — sharing the connection pool (CL-03, LM-04).

A route that forwards the caller's token binds one per request; closing the pool is its builder's job, not the wrapper's.

### AtlasClientError

```
AtlasClientError(status_code: int, info: AtlasErrorInfo | None)
```

Bases: `RuntimeError`

A non-2xx answer from the Atlas server, with the status and the error body (CL-04).

Attributes:

- **`info`** –

  The server's `{errorCode, errorMessage}`, when the body parsed as one.
- **`status_code`** –

  The HTTP status the server answered with.

#### info

```
info = info
```

The server's `{errorCode, errorMessage}`, when the body parsed as one.

#### status\_code

```
status_code = status_code
```

The HTTP status the server answered with.

### SearchApi

```
SearchApi(api: _Api)
```

The discovery resource of an :class:`AtlasClient` (CL-13): `client.search`.

The paths mirror `routes/discovery.py`; the bodies are `aurelius-atlas-model`'s, reused whole (CL-10). The GET searches carry their parameters as query parameters, the POST searches as the model's JSON body — as the server's JAX-RS routes read them.

Methods:

- **`get_suggestions`** –

  `GET /api/atlas/v2/search/suggestions`: terms beginning with the prefix (SUG-01, SUG-02).
- **`quick_search`** –

  `POST /api/atlas/v2/search/quick`: the quick search of the body, with its facets (QSR-01).
- **`quick_search_using_query`** –

  `GET /api/atlas/v2/search/quick`: a quick search of the query parameters (QSR-01, QSR-02).
- **`search_using_attribute`** –

  `GET /api/atlas/v2/search/attribute`: entities whose attribute starts with the prefix (SRC-11).
- **`search_using_basic`** –

  `GET /api/atlas/v2/search/basic`: a search of the query parameters, not body-validated (SRC-11).
- **`search_using_full_text`** –

  `GET /api/atlas/v2/search/fulltext`: the entities matching the query, best first, with scores (FTX-05).
- **`search_with_parameters`** –

  `POST /api/atlas/v2/search/basic`: the entities the body's search finds (SRC-02).

#### get\_suggestions

```
get_suggestions(prefix_string: str | None = None, field_name: str | None = None) -> AtlasSuggestionsResult
```

`GET /api/atlas/v2/search/suggestions`: terms beginning with the prefix (SUG-01, SUG-02).

#### quick\_search

```
quick_search(parameters: QuickSearchParameters) -> AtlasQuickSearchResult
```

`POST /api/atlas/v2/search/quick`: the quick search of the body, with its facets (QSR-01).

#### quick\_search\_using\_query

```
quick_search_using_query(
    *,
    query: str | None = None,
    type_name: str | None = None,
    exclude_deleted_entities: bool = False,
    limit: int = 0,
    offset: int = 0,
    sort_by: str | None = None,
    sort_order: SortOrder | None = None,
) -> AtlasQuickSearchResult
```

`GET /api/atlas/v2/search/quick`: a quick search of the query parameters (QSR-01, QSR-02).

#### search\_using\_attribute

```
search_using_attribute(
    *,
    type_name: str | None = None,
    attr_name: str | None = None,
    attr_value_prefix: str | None = None,
    limit: int = 0,
    offset: int = 0,
) -> AtlasSearchResult
```

`GET /api/atlas/v2/search/attribute`: entities whose attribute starts with the prefix (SRC-11).

#### search\_using\_basic

```
search_using_basic(
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
) -> AtlasSearchResult
```

`GET /api/atlas/v2/search/basic`: a search of the query parameters, not body-validated (SRC-11).

#### search\_using\_full\_text

```
search_using_full_text(
    query: str, *, exclude_deleted_entities: bool = False, limit: int = 0, offset: int = 0
) -> AtlasSearchResult
```

`GET /api/atlas/v2/search/fulltext`: the entities matching the query, best first, with scores (FTX-05).

#### search\_with\_parameters

```
search_with_parameters(parameters: SearchParameters) -> AtlasSearchResult
```

`POST /api/atlas/v2/search/basic`: the entities the body's search finds (SRC-02).

### TypesApi

```
TypesApi(api: _Api)
```

The typedef resource of an :class:`AtlasClient` (CL-11): `client.types`.

The paths mirror `routes/types.py`; the bodies are `aurelius-atlas-model`'s, reused whole (CL-10).

Methods:

- **`businessmetadatadef_by_guid`** –

  `GET /businessmetadatadef/guid/{guid}` (TYR-03).
- **`businessmetadatadef_by_name`** –

  `GET /businessmetadatadef/name/{name}` (TYR-03).
- **`classificationdef_by_guid`** –

  `GET /classificationdef/guid/{guid}` (TYR-03).
- **`classificationdef_by_name`** –

  `GET /classificationdef/name/{name}` (TYR-03).
- **`create_typedefs`** –

  `POST /typedefs`: create the definitions, all or none (TYR-09).
- **`delete_typedef_by_name`** –

  `DELETE /typedef/name/{type_name}`: delete the named definition (TYR-10); the answer is 204.
- **`delete_typedefs`** –

  `DELETE /typedefs`: delete the definitions, all or none (TYR-10); the answer is 204.
- **`entitydef_by_guid`** –

  `GET /entitydef/guid/{guid}` (TYR-03).
- **`entitydef_by_name`** –

  `GET /entitydef/name/{name}` (TYR-03).
- **`enumdef_by_guid`** –

  `GET /enumdef/guid/{guid}` (TYR-03).
- **`enumdef_by_name`** –

  `GET /enumdef/name/{name}` (TYR-03).
- **`relationshipdef_by_guid`** –

  `GET /relationshipdef/guid/{guid}` (TYR-03).
- **`relationshipdef_by_name`** –

  `GET /relationshipdef/name/{name}` (TYR-03).
- **`structdef_by_guid`** –

  `GET /structdef/guid/{guid}` (TYR-03).
- **`structdef_by_name`** –

  `GET /structdef/name/{name}` (TYR-03).
- **`typedef_by_guid`** –

  `GET /typedef/guid/{guid}`: the definition of any kind (TYR-02), parsed by its `category`.
- **`typedef_by_name`** –

  `GET /typedef/name/{name}`: the definition of any kind (TYR-01), parsed by its `category`.
- **`typedef_headers`** –

  `GET /typedefs/headers`: the headers the search filter keeps (TYR-08).
- **`typedefs`** –

  `GET /typedefs`: the definitions the search filter keeps (TYR-05..TYR-07).
- **`update_typedefs`** –

  `PUT /typedefs`: update the definitions, all or none (TYR-09).

#### businessmetadatadef\_by\_guid

```
businessmetadatadef_by_guid(guid: str) -> AtlasBusinessMetadataDef
```

`GET /businessmetadatadef/guid/{guid}` (TYR-03).

#### businessmetadatadef\_by\_name

```
businessmetadatadef_by_name(name: str) -> AtlasBusinessMetadataDef
```

`GET /businessmetadatadef/name/{name}` (TYR-03).

#### classificationdef\_by\_guid

```
classificationdef_by_guid(guid: str) -> AtlasClassificationDef
```

`GET /classificationdef/guid/{guid}` (TYR-03).

#### classificationdef\_by\_name

```
classificationdef_by_name(name: str) -> AtlasClassificationDef
```

`GET /classificationdef/name/{name}` (TYR-03).

#### create\_typedefs

```
create_typedefs(types_def: AtlasTypesDef) -> AtlasTypesDef
```

`POST /typedefs`: create the definitions, all or none (TYR-09).

#### delete\_typedef\_by\_name

```
delete_typedef_by_name(type_name: str) -> None
```

`DELETE /typedef/name/{type_name}`: delete the named definition (TYR-10); the answer is 204.

#### delete\_typedefs

```
delete_typedefs(types_def: AtlasTypesDef) -> None
```

`DELETE /typedefs`: delete the definitions, all or none (TYR-10); the answer is 204.

#### entitydef\_by\_guid

```
entitydef_by_guid(guid: str) -> AtlasEntityDef
```

`GET /entitydef/guid/{guid}` (TYR-03).

#### entitydef\_by\_name

```
entitydef_by_name(name: str) -> AtlasEntityDef
```

`GET /entitydef/name/{name}` (TYR-03).

#### enumdef\_by\_guid

```
enumdef_by_guid(guid: str) -> AtlasEnumDef
```

`GET /enumdef/guid/{guid}` (TYR-03).

#### enumdef\_by\_name

```
enumdef_by_name(name: str) -> AtlasEnumDef
```

`GET /enumdef/name/{name}` (TYR-03).

#### relationshipdef\_by\_guid

```
relationshipdef_by_guid(guid: str) -> AtlasRelationshipDef
```

`GET /relationshipdef/guid/{guid}` (TYR-03).

#### relationshipdef\_by\_name

```
relationshipdef_by_name(name: str) -> AtlasRelationshipDef
```

`GET /relationshipdef/name/{name}` (TYR-03).

#### structdef\_by\_guid

```
structdef_by_guid(guid: str) -> AtlasStructDef
```

`GET /structdef/guid/{guid}` (TYR-03).

#### structdef\_by\_name

```
structdef_by_name(name: str) -> AtlasStructDef
```

`GET /structdef/name/{name}` (TYR-03).

#### typedef\_by\_guid

```
typedef_by_guid(guid: str) -> AtlasBaseTypeDef
```

`GET /typedef/guid/{guid}`: the definition of any kind (TYR-02), parsed by its `category`.

#### typedef\_by\_name

```
typedef_by_name(name: str) -> AtlasBaseTypeDef
```

`GET /typedef/name/{name}`: the definition of any kind (TYR-01), parsed by its `category`.

#### typedef\_headers

```
typedef_headers(params: Mapping[str, Any] | None = None) -> list[AtlasTypeDefHeader]
```

`GET /typedefs/headers`: the headers the search filter keeps (TYR-08).

#### typedefs

```
typedefs(params: Mapping[str, Any] | None = None) -> AtlasTypesDef
```

`GET /typedefs`: the definitions the search filter keeps (TYR-05..TYR-07).

#### update\_typedefs

```
update_typedefs(types_def: AtlasTypesDef) -> AtlasTypesDef
```

`PUT /typedefs`: update the definitions, all or none (TYR-09).
