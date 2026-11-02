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
- **`DeleteType`** –

  How a delete removes entities: `DEFAULT` defers to the server's setting.

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

### DeleteType

Bases: `StrEnum`

How a delete removes entities: `DEFAULT` defers to the server's setting.

Attributes:

- **`DEFAULT`** –
- **`HARD`** –
- **`SOFT`** –

#### DEFAULT

```
DEFAULT = 'DEFAULT'
```

#### HARD

```
HARD = 'HARD'
```

#### SOFT

```
SOFT = 'SOFT'
```

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

The paths mirror the server's routes verbatim: `routes/admin.py` under `/api/atlas/admin`, `routes/types.py` under `/api/atlas/v2/types`, the entity routes of `routes/entity.py` under `/api/atlas/v2/entity` (CLE-01..CLE-12, 8.9), the glossary routes of `routes/glossary.py` under `/api/atlas/v2/glossary` (CLG-01..CLG-09, 8.10), the discovery routes of `routes/discovery.py` under `/api/atlas/v2/search` (CL-13), and the lineage feed of `routes/lineage.py` under `/api/atlas/v2/lineage` (CL-60..CL-63, 8.8).

Type Aliases:

- **`GlossarySort`** –

  The glossary reads' `sort` parameter (CLG-02, GLS-05).
- **`TokenSource`** –

  Where the bearer token comes from: a fixed token, or a callable that yields one.

Classes:

- **`AdminApi`** –

  The admin resource of an :class:`AtlasClient` (CL-11): `client.admin`.
- **`AtlasClient`** –

  The client for one Atlas metadata server (CL-11, DD-203, DD-205).
- **`AtlasClientError`** –

  A non-2xx answer from the Atlas server, with the status and the error body (CL-04).
- **`EntityApi`** –

  The entity resource of an :class:`AtlasClient` (CLE-01..CLE-12): `client.entity`.
- **`GlossaryApi`** –

  The glossary resource of an :class:`AtlasClient` (CLG-01..CLG-09): `client.glossary`.
- **`LineageApi`** –

  The lineage resource of an :class:`AtlasClient` (CL-61..CL-63): `client.lineage`.
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
- **`ENTITY_ROOT`** –
- **`GLOSSARY_ROOT`** –
- **`KIND_PATHS`** (`dict[TypeCategory, str]`) –

  The path segment of each kind's lookups, mirroring `routes/types.py`'s `KIND_PATHS` (CL-11).
- **`LINEAGE_ROOT`** –

  The route prefixes of the server's resources (`routes/admin.py`, `routes/types.py`,
- **`RELATIONSHIP_ROOT`** –
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

### ENTITY\_ROOT

```
ENTITY_ROOT = 'api/atlas/v2/entity'
```

### GLOSSARY\_ROOT

```
GLOSSARY_ROOT = 'api/atlas/v2/glossary'
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
LINEAGE_ROOT = 'api/atlas/v2/lineage'
```

The route prefixes of the server's resources (`routes/admin.py`, `routes/types.py`, `routes/discovery.py`, `routes/entity.py`, `routes/glossary.py`, `routes/relationship.py`, `routes/lineage.py`).

Relative to the httpx client's base URL (CL-01): httpx appends them, so the base URL the app passes — trailing slash included, as a pydantic `HttpUrl` renders one — works as given. `LINEAGE_ROOT` carries the prefix too (CL-60): the server mounts its feed at `/api/atlas/v2/lineage`, as every other resource (DD-308).

### RELATIONSHIP\_ROOT

```
RELATIONSHIP_ROOT = 'api/atlas/v2/relationship'
```

### TYPES\_ROOT

```
TYPES_ROOT = 'api/atlas/v2/types'
```

### GlossarySort

```
GlossarySort = Literal['ASC', 'DESC']
```

The glossary reads' `sort` parameter (CLG-02, GLS-05).

The wire vocabulary is the server's own: `routes/glossary.py` reads anything but `DESC` as ascending, so `ASC` — the default — travels as absence. `aurelius-atlas-model`'s `SortOrder` is a different vocabulary (`ASCENDING`/`DESCENDING`, the search parameter) and is not this one.

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

  The alias of `lineage.get` (CL-61, DD-308) — use `client.lineage.get`.
- **`with_token`** –

  The same client speaking with `token` — sharing the connection pool (CL-03, LM-04).

Attributes:

- **`admin`** –
- **`entity`** –
- **`glossary`** –
- **`lineage`** –
- **`search`** –
- **`types`** –

#### admin

```
admin = AdminApi(api)
```

#### entity

```
entity = EntityApi(api)
```

#### glossary

```
glossary = GlossaryApi(api)
```

#### lineage

```
lineage = LineageApi(api)
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

The alias of `lineage.get` (CL-61, DD-308) — use `client.lineage.get`.

Kept for one release-cycle for the 8.2 app, which calls it. It speaks the fixed path now (`api/atlas/v2/lineage`, the mounted route) — the old bare `v2/lineage` answered 404 against this workspace's server.

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

### EntityApi

```
EntityApi(api: _Api)
```

The entity resource of an :class:`AtlasClient` (CLE-01..CLE-12): `client.entity`.

The paths mirror `routes/entity.py` (37 routes); the bodies are `aurelius-atlas-model`'s, reused whole (DD-309). The client validates no request body the server validates — it sends the model's `to_json()` and lets the server answer (CLE-12). A unique-attribute read or delete renders each entry as an `attr:<name>` query parameter, the bulk read as `attr_<n>:<name>`, 1-based, in order (CLE-03).

Methods:

- **`add_classifications`** –

  `POST /guid/{g}/classifications`: attach the classifications (CLS-04, CLE-05). Answers 204.
- **`add_classifications_by_unique_attributes`** –

  `POST /uniqueAttribute/type/{t}/classifications`: attach the classifications (CLS-06, CLE-03, CLE-05).
- **`add_labels`** –

  `PUT /guid/{g}/labels`: these labels added to the entity's (LBL-01, LBL-03, CLE-06). Answers 204.
- **`add_labels_by_unique_attributes`** –

  `PUT /uniqueAttribute/type/{t}/labels`: added to that entity's labels (LBL-03, CLE-03, CLE-06).
- **`add_or_update_business_metadata`** –

  `POST /guid/{g}/businessmetadata`: the values set, all replaced with `is_overwrite` (BMD-01, CLE-07).
- **`add_or_update_business_metadata_of`** –

  `POST /guid/{g}/businessmetadata/{bm}`: one metadata's values set (BMD-03, CLE-07). Answers 204.
- **`associate_classification`** –

  `POST /bulk/classification`: attach one classification to many entities (CLS-07, CLE-01). Answers 204.
- **`audit_events`** –

  `GET /{guid}/audit`: the entity's audit events (AUD-06..AUD-09, CLE-10).
- **`business_metadata_template`** –

  `GET /businessmetadata/import/template`: the download as bytes and content type (BMI-01, CLE-09, CL-64).
- **`by_guid`** –

  `GET /guid/{guid}`: the entity and the entities it owns (ERD-02, CLE-02).
- **`by_guids`** –

  `GET /bulk`: the entities of every `guid`, in order (ERD-01, CLE-02).
- **`by_unique_attributes`** –

  `GET /uniqueAttribute/type/{t}`: the entity holding the `attr:` values (ERD-08, CLE-02, CLE-03).
- **`changed_classifications`** –

  `GET /bulk/headers`: the entities whose classifications changed since `since` (CAU-07, CLE-11).
- **`create_or_update`** –

  `POST ""`: create the entity, and the entities it names, or update them (EWR-02).
- **`create_or_update_bulk`** –

  `POST /bulk`: create or update every entity (EWR-02).
- **`delete_by_guid`** –

  `DELETE /guid/{guid}`: the entity and what it owns (EDL-01, CLE-04).
- **`delete_by_guids`** –

  `DELETE /bulk`: the entities of every `guid` and what they own (EDL-01, CLE-04).
- **`delete_by_unique_attributes`** –

  `DELETE /uniqueAttribute/type/{t}`: the entity holding the values (EDL-02, CLE-03, CLE-04).
- **`delete_classification`** –

  `DELETE /guid/{g}/classification/{c}`: remove it (CLS-09, CLE-05). Answers 204.
- **`delete_classification_by_unique_attributes`** –

  `DELETE /uniqueAttribute/type/{t}/classification/{c}`: remove it (CLS-06, CLE-03, CLE-05).
- **`entities_by_unique_attributes`** –

  `GET /bulk/uniqueAttribute/type/{t}`: the entity each `attr_<n>:` set finds (ERD-08, CLE-02, CLE-03).
- **`get_classification`** –

  `GET /guid/{g}/classification/{c}`: the entity's classification of the name (CLS-03).
- **`get_classifications`** –

  `GET /guid/{g}/classifications`: the entity's classifications, as a `PList` (CLS-03).
- **`header_by_guid`** –

  `GET /guid/{guid}/header`: the entity's header with its classifications (ERD-07).
- **`header_by_unique_attributes`** –

  `GET /uniqueAttribute/type/{t}/header`: the header of the entity holding the values (ERD-07, CLE-03).
- **`import_business_metadata`** –

  `POST /businessmetadata/import`: the file's rows applied (BMI-02..BMI-05, CLE-09, CL-64).
- **`partial_update_attribute`** –

  `PUT /guid/{guid}`: set the attribute `name` of the entity to `value` (EWR-15).
- **`partial_update_by_unique_attributes`** –

  `PUT /uniqueAttribute/type/{t}`: partially update the entity holding the values (EWR-14, CLE-03).
- **`remove_business_metadata`** –

  `DELETE /guid/{g}/businessmetadata`: the body's attributes removed (BMD-05, CLE-07). Answers 204.
- **`remove_business_metadata_of`** –

  `DELETE /guid/{g}/businessmetadata/{bm}`: one metadata's attributes, or all, removed (BMD-05, CLE-07).
- **`remove_labels`** –

  `DELETE /guid/{g}/labels`: these labels taken from the entity's (LBL-01, LBL-04, CLE-06). Answers 204.
- **`remove_labels_by_unique_attributes`** –

  `DELETE /uniqueAttribute/type/{t}/labels`: taken from that entity's labels (LBL-04, CLE-03, CLE-06).
- **`set_classifications`** –

  `POST /bulk/setClassifications`: each header's entity gets its classifications (CLA-04, CLE-08).
- **`set_labels`** –

  `POST /guid/{g}/labels`: the entity's labels become these (LBL-01, LBL-02, CLE-06). Answers 204.
- **`set_labels_by_unique_attributes`** –

  `POST /uniqueAttribute/type/{t}/labels`: the entity holding the values gets the labels (LBL-02, CLE-06).
- **`update_classifications`** –

  `PUT /guid/{g}/classifications`: change the entity's classifications (CLS-08, CLE-05). Answers 204.
- **`update_classifications_by_unique_attributes`** –

  `PUT /uniqueAttribute/type/{t}/classifications`: change them (CLS-06, CLE-03, CLE-05). Answers 204.

#### add\_classifications

```
add_classifications(guid: str, classifications: Sequence[AtlasClassification]) -> None
```

`POST /guid/{g}/classifications`: attach the classifications (CLS-04, CLE-05). Answers 204.

#### add\_classifications\_by\_unique\_attributes

```
add_classifications_by_unique_attributes(
    type_name: str, attributes: Mapping[str, Any], classifications: Sequence[AtlasClassification]
) -> None
```

`POST /uniqueAttribute/type/{t}/classifications`: attach the classifications (CLS-06, CLE-03, CLE-05).

#### add\_labels

```
add_labels(guid: str, labels: Sequence[str]) -> None
```

`PUT /guid/{g}/labels`: these labels added to the entity's (LBL-01, LBL-03, CLE-06). Answers 204.

#### add\_labels\_by\_unique\_attributes

```
add_labels_by_unique_attributes(type_name: str, attributes: Mapping[str, Any], labels: Sequence[str]) -> None
```

`PUT /uniqueAttribute/type/{t}/labels`: added to that entity's labels (LBL-03, CLE-03, CLE-06).

#### add\_or\_update\_business\_metadata

```
add_or_update_business_metadata(
    guid: str, attributes: Mapping[str, Mapping[str, Any] | None], *, is_overwrite: bool = False
) -> None
```

`POST /guid/{g}/businessmetadata`: the values set, all replaced with `is_overwrite` (BMD-01, CLE-07).

#### add\_or\_update\_business\_metadata\_of

```
add_or_update_business_metadata_of(guid: str, bm_name: str, attributes: Mapping[str, Any]) -> None
```

`POST /guid/{g}/businessmetadata/{bm}`: one metadata's values set (BMD-03, CLE-07). Answers 204.

#### associate\_classification

```
associate_classification(request_body: ClassificationAssociateRequest) -> None
```

`POST /bulk/classification`: attach one classification to many entities (CLS-07, CLE-01). Answers 204.

#### audit\_events

```
audit_events(
    guid: str,
    *,
    action: EntityAuditActionV2 | None = None,
    start_key: str | None = None,
    count: int | None = None,
    offset: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> list[EntityAuditEventV2]
```

`GET /{guid}/audit`: the entity's audit events (AUD-06..AUD-09, CLE-10).

Each parameter travels only when set; an absent `count` the server reads as 100 and an absent `offset` as -1 — so, unlike `_present`, this drops only the values left as `None`: a `count` of 0 is a choice, not a default.

#### business\_metadata\_template

```
business_metadata_template() -> tuple[bytes, str]
```

`GET /businessmetadata/import/template`: the download as bytes and content type (BMI-01, CLE-09, CL-64).

#### by\_guid

```
by_guid(guid: str, *, min_ext_info: bool = False, ignore_relationships: bool = False) -> AtlasEntityWithExtInfo
```

`GET /guid/{guid}`: the entity and the entities it owns (ERD-02, CLE-02).

#### by\_guids

```
by_guids(
    guids: Sequence[str], *, min_ext_info: bool = False, ignore_relationships: bool = False
) -> AtlasEntitiesWithExtInfo
```

`GET /bulk`: the entities of every `guid`, in order (ERD-01, CLE-02).

#### by\_unique\_attributes

```
by_unique_attributes(
    type_name: str, attributes: Mapping[str, Any], *, min_ext_info: bool = False, ignore_relationships: bool = False
) -> AtlasEntityWithExtInfo
```

`GET /uniqueAttribute/type/{t}`: the entity holding the `attr:` values (ERD-08, CLE-02, CLE-03).

#### changed\_classifications

```
changed_classifications(since: int) -> AtlasEntityHeaders
```

`GET /bulk/headers`: the entities whose classifications changed since `since` (CAU-07, CLE-11).

`since` is the `tagUpdateStartTime` epoch millis; the client sends no end time — the server uses its own clock.

#### create\_or\_update

```
create_or_update(entity: AtlasEntityWithExtInfo) -> EntityMutationResponse
```

`POST ""`: create the entity, and the entities it names, or update them (EWR-02).

#### create\_or\_update\_bulk

```
create_or_update_bulk(entities: AtlasEntitiesWithExtInfo) -> EntityMutationResponse
```

`POST /bulk`: create or update every entity (EWR-02).

#### delete\_by\_guid

```
delete_by_guid(guid: str, *, delete_type: DeleteType | None = None) -> EntityMutationResponse
```

`DELETE /guid/{guid}`: the entity and what it owns (EDL-01, CLE-04).

An absent `delete_type` sends no parameter: the server applies its own setting (EDL-04).

#### delete\_by\_guids

```
delete_by_guids(guids: Sequence[str], *, delete_type: DeleteType | None = None) -> EntityMutationResponse
```

`DELETE /bulk`: the entities of every `guid` and what they own (EDL-01, CLE-04).

#### delete\_by\_unique\_attributes

```
delete_by_unique_attributes(
    type_name: str, attributes: Mapping[str, Any], *, delete_type: DeleteType | None = None
) -> EntityMutationResponse
```

`DELETE /uniqueAttribute/type/{t}`: the entity holding the values (EDL-02, CLE-03, CLE-04).

#### delete\_classification

```
delete_classification(guid: str, classification_name: str, *, associated_entity_guid: str | None = None) -> None
```

`DELETE /guid/{g}/classification/{c}`: remove it (CLS-09, CLE-05). Answers 204.

#### delete\_classification\_by\_unique\_attributes

```
delete_classification_by_unique_attributes(
    type_name: str, attributes: Mapping[str, Any], classification_name: str
) -> None
```

`DELETE /uniqueAttribute/type/{t}/classification/{c}`: remove it (CLS-06, CLE-03, CLE-05).

#### entities\_by\_unique\_attributes

```
entities_by_unique_attributes(
    type_name: str,
    attribute_sets: Sequence[Mapping[str, Any]],
    *,
    min_ext_info: bool = False,
    ignore_relationships: bool = False,
) -> AtlasEntitiesWithExtInfo
```

`GET /bulk/uniqueAttribute/type/{t}`: the entity each `attr_<n>:` set finds (ERD-08, CLE-02, CLE-03).

The sets are 1-based in the query, in the order given (DV-19).

#### get\_classification

```
get_classification(guid: str, classification_name: str) -> AtlasClassification
```

`GET /guid/{g}/classification/{c}`: the entity's classification of the name (CLS-03).

#### get\_classifications

```
get_classifications(guid: str) -> AtlasClassifications
```

`GET /guid/{g}/classifications`: the entity's classifications, as a `PList` (CLS-03).

#### header\_by\_guid

```
header_by_guid(guid: str) -> AtlasEntityHeader
```

`GET /guid/{guid}/header`: the entity's header with its classifications (ERD-07).

#### header\_by\_unique\_attributes

```
header_by_unique_attributes(type_name: str, attributes: Mapping[str, Any]) -> AtlasEntityHeader
```

`GET /uniqueAttribute/type/{t}/header`: the header of the entity holding the values (ERD-07, CLE-03).

#### import\_business\_metadata

```
import_business_metadata(file_name: str, content: bytes) -> BulkImportResponse
```

`POST /businessmetadata/import`: the file's rows applied (BMI-02..BMI-05, CLE-09, CL-64).

The file is the bytes the caller holds — never a path read from disk.

#### partial\_update\_attribute

```
partial_update_attribute(guid: str, name: str | None, value: Any) -> EntityMutationResponse
```

`PUT /guid/{guid}`: set the attribute `name` of the entity to `value` (EWR-15).

The body is the bare JSON value; the server reads whatever it is.

#### partial\_update\_by\_unique\_attributes

```
partial_update_by_unique_attributes(
    type_name: str, attributes: Mapping[str, Any], entity: AtlasEntityWithExtInfo
) -> EntityMutationResponse
```

`PUT /uniqueAttribute/type/{t}`: partially update the entity holding the values (EWR-14, CLE-03).

#### remove\_business\_metadata

```
remove_business_metadata(guid: str, attributes: Mapping[str, Mapping[str, Any] | None]) -> None
```

`DELETE /guid/{g}/businessmetadata`: the body's attributes removed (BMD-05, CLE-07). Answers 204.

#### remove\_business\_metadata\_of

```
remove_business_metadata_of(guid: str, bm_name: str, attributes: Mapping[str, Any]) -> None
```

`DELETE /guid/{g}/businessmetadata/{bm}`: one metadata's attributes, or all, removed (BMD-05, CLE-07).

#### remove\_labels

```
remove_labels(guid: str, labels: Sequence[str]) -> None
```

`DELETE /guid/{g}/labels`: these labels taken from the entity's (LBL-01, LBL-04, CLE-06). Answers 204.

#### remove\_labels\_by\_unique\_attributes

```
remove_labels_by_unique_attributes(type_name: str, attributes: Mapping[str, Any], labels: Sequence[str]) -> None
```

`DELETE /uniqueAttribute/type/{t}/labels`: taken from that entity's labels (LBL-04, CLE-03, CLE-06).

#### set\_classifications

```
set_classifications(headers: AtlasEntityHeaders) -> Any
```

`POST /bulk/setClassifications`: each header's entity gets its classifications (CLA-04, CLE-08).

The answer is a JSON array of per-guid summaries, not a model (the server's DV-36 text); the client returns it parsed, never reordered.

#### set\_labels

```
set_labels(guid: str, labels: Sequence[str]) -> None
```

`POST /guid/{g}/labels`: the entity's labels become these (LBL-01, LBL-02, CLE-06). Answers 204.

#### set\_labels\_by\_unique\_attributes

```
set_labels_by_unique_attributes(type_name: str, attributes: Mapping[str, Any], labels: Sequence[str]) -> None
```

`POST /uniqueAttribute/type/{t}/labels`: the entity holding the values gets the labels (LBL-02, CLE-06).

#### update\_classifications

```
update_classifications(guid: str, classifications: Sequence[AtlasClassification]) -> None
```

`PUT /guid/{g}/classifications`: change the entity's classifications (CLS-08, CLE-05). Answers 204.

#### update\_classifications\_by\_unique\_attributes

```
update_classifications_by_unique_attributes(
    type_name: str, attributes: Mapping[str, Any], classifications: Sequence[AtlasClassification]
) -> None
```

`PUT /uniqueAttribute/type/{t}/classifications`: change them (CLS-06, CLE-03, CLE-05). Answers 204.

### GlossaryApi

```
GlossaryApi(api: _Api)
```

The glossary resource of an :class:`AtlasClient` (CLG-01..CLG-09): `client.glossary`.

The paths mirror `routes/glossary.py` (32 routes); the bodies are `aurelius-atlas-model`'s `glossary` module, reused whole (DD-309). The paged reads send the server's `limit`/`offset`/`sort` defaults as absence (CLG-02); the create methods do not check the anchor locally (CLG-05) and the updates send the body as given (CLG-08) — the server answers. The two file routes cross as bytes (CLG-06, CL-64).

Methods:

- **`assign_term`** –

  `POST /terms/{guid}/assignedEntities`: assign the term to the entities (GTA-02, CLG-04). 204.
- **`assigned_entities`** –

  `GET /terms/{guid}/assignedEntities`: the term's active assignments (GTA-01, CLG-02).
- **`category`** –

  `GET /category/{guid}`: the category (GCT-01).
- **`category_terms`** –

  `GET /category/{guid}/terms`: the category's terms, paged (GTM-06, CLG-02).
- **`create_categories`** –

  `POST /categories`: create every category; anchors are the server's check (GCT-02, CLG-05).
- **`create_category`** –

  `POST /category`: create the category; the anchor is the server's check (GCT-02, CLG-05).
- **`create_glossary`** –

  `POST ""`: create the glossary (GLS-02).
- **`create_term`** –

  `POST /term`: create the term; the anchor is the server's check (GTM-02, CLG-05).
- **`create_terms`** –

  `POST /terms`: create every term; the anchors are the server's check (GTM-02, CLG-05).
- **`delete_category`** –

  `DELETE /category/{guid}`: delete the category (GCT-06, CLG-09). Answers 204.
- **`delete_glossary`** –

  `DELETE /{guid}`: delete the glossary (GLS-04, CLG-09). Answers 204.
- **`delete_term`** –

  `DELETE /term/{guid}`: delete the term (GTM-05, CLG-09). Answers 204.
- **`detailed_glossary`** –

  `GET /{guid}/detailed`: the glossary with its terms and categories by GUID (GLS-06).
- **`disassociate_term_assignment`** –

  `PUT /terms/{guid}/assignedEntities`: as the `DELETE` (GTA-03, CLG-04).
- **`glossaries`** –

  `GET ""`: every glossary, paged and sorted (GLS-05, CLG-02).
- **`glossary`** –

  `GET /{guid}`: the glossary (GLS-01, GLS-06).
- **`glossary_categories`** –

  `GET /{guid}/categories`: the glossary's categories, paged (GLS-05, CLG-02).
- **`glossary_categories_headers`** –

  `GET /{guid}/categories/headers`: the category headers, paged (GLS-05, CLG-02).
- **`glossary_terms`** –

  `GET /{guid}/terms`: the glossary's terms, paged (GTM-06, CLG-02).
- **`glossary_terms_headers`** –

  `GET /{guid}/terms/headers`: the term headers, paged (GTM-06, CLG-02).
- **`import_data`** –

  `POST /import`: the file's terms created (GIM-01..GIM-05, CLG-06, CL-64).
- **`import_template`** –

  `GET /import/template`: the download as bytes and content type (GIM-06, CLG-06, CL-64).
- **`partial_update_category`** –

  `PUT /category/{guid}/partial`: set the given attributes (GCT-05, CLG-03).
- **`partial_update_glossary`** –

  `PUT /{guid}/partial`: set the given attributes of the glossary (GLS-03, CLG-03).
- **`partial_update_term`** –

  `PUT /term/{guid}/partial`: set the given attributes of the term (GTM-04, CLG-03).
- **`related_categories`** –

  `GET /category/{guid}/related`: its parent and children (GCT-07, CLG-07).
- **`related_terms`** –

  `GET /terms/{guid}/related`: the term's related terms by relation (GTM-06, CLG-07).
- **`remove_term_assignment`** –

  `DELETE /terms/{guid}/assignedEntities`: remove the assignments (GTA-03, CLG-04). 204.
- **`term`** –

  `GET /term/{guid}`: the term (GTM-01).
- **`update_category`** –

  `PUT /category/{guid}`: update the category of the path's GUID (GCT-04, CLG-08).
- **`update_glossary`** –

  `PUT /{guid}`: update the glossary of the path's GUID (GLS-03, CLG-08).
- **`update_term`** –

  `PUT /term/{guid}`: update the term of the path's GUID (GTM-04, CLG-08).

#### assign\_term

```
assign_term(term_guid: str, object_ids: Sequence[AtlasRelatedObjectId]) -> None
```

`POST /terms/{guid}/assignedEntities`: assign the term to the entities (GTA-02, CLG-04). 204.

#### assigned\_entities

```
assigned_entities(
    term_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
) -> list[AtlasRelatedObjectId]
```

`GET /terms/{guid}/assignedEntities`: the term's active assignments (GTA-01, CLG-02).

#### category

```
category(category_guid: str) -> AtlasGlossaryCategory
```

`GET /category/{guid}`: the category (GCT-01).

#### category\_terms

```
category_terms(
    category_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
) -> list[AtlasRelatedTermHeader]
```

`GET /category/{guid}/terms`: the category's terms, paged (GTM-06, CLG-02).

#### create\_categories

```
create_categories(categories: Sequence[AtlasGlossaryCategory]) -> list[AtlasGlossaryCategory]
```

`POST /categories`: create every category; anchors are the server's check (GCT-02, CLG-05).

#### create\_category

```
create_category(category: AtlasGlossaryCategory) -> AtlasGlossaryCategory
```

`POST /category`: create the category; the anchor is the server's check (GCT-02, CLG-05).

#### create\_glossary

```
create_glossary(glossary: AtlasGlossary) -> AtlasGlossary
```

`POST ""`: create the glossary (GLS-02).

#### create\_term

```
create_term(term: AtlasGlossaryTerm) -> AtlasGlossaryTerm
```

`POST /term`: create the term; the anchor is the server's check (GTM-02, CLG-05).

#### create\_terms

```
create_terms(terms: Sequence[AtlasGlossaryTerm]) -> list[AtlasGlossaryTerm]
```

`POST /terms`: create every term; the anchors are the server's check (GTM-02, CLG-05).

#### delete\_category

```
delete_category(category_guid: str) -> None
```

`DELETE /category/{guid}`: delete the category (GCT-06, CLG-09). Answers 204.

#### delete\_glossary

```
delete_glossary(glossary_guid: str) -> None
```

`DELETE /{guid}`: delete the glossary (GLS-04, CLG-09). Answers 204.

#### delete\_term

```
delete_term(term_guid: str) -> None
```

`DELETE /term/{guid}`: delete the term (GTM-05, CLG-09). Answers 204.

#### detailed\_glossary

```
detailed_glossary(glossary_guid: str) -> AtlasGlossaryExtInfo
```

`GET /{guid}/detailed`: the glossary with its terms and categories by GUID (GLS-06).

#### disassociate\_term\_assignment

```
disassociate_term_assignment(term_guid: str, object_ids: Sequence[AtlasRelatedObjectId]) -> None
```

`PUT /terms/{guid}/assignedEntities`: as the `DELETE` (GTA-03, CLG-04).

Kept so a caller states its intent. Answers 204.

#### glossaries

```
glossaries(*, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None) -> list[AtlasGlossary]
```

`GET ""`: every glossary, paged and sorted (GLS-05, CLG-02).

#### glossary

```
glossary(glossary_guid: str) -> AtlasGlossary
```

`GET /{guid}`: the glossary (GLS-01, GLS-06).

#### glossary\_categories

```
glossary_categories(
    glossary_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
) -> list[AtlasGlossaryCategory]
```

`GET /{guid}/categories`: the glossary's categories, paged (GLS-05, CLG-02).

#### glossary\_categories\_headers

```
glossary_categories_headers(
    glossary_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
) -> list[AtlasRelatedCategoryHeader]
```

`GET /{guid}/categories/headers`: the category headers, paged (GLS-05, CLG-02).

#### glossary\_terms

```
glossary_terms(
    glossary_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
) -> list[AtlasGlossaryTerm]
```

`GET /{guid}/terms`: the glossary's terms, paged (GTM-06, CLG-02).

#### glossary\_terms\_headers

```
glossary_terms_headers(
    glossary_guid: str, *, limit: int | None = None, offset: int = 0, sort: GlossarySort | None = None
) -> list[AtlasRelatedTermHeader]
```

`GET /{guid}/terms/headers`: the term headers, paged (GTM-06, CLG-02).

#### import\_data

```
import_data(file_name: str, content: bytes) -> BulkImportResponse
```

`POST /import`: the file's terms created (GIM-01..GIM-05, CLG-06, CL-64).

The file is the bytes the caller holds — never a path read from disk.

#### import\_template

```
import_template() -> tuple[bytes, str]
```

`GET /import/template`: the download as bytes and content type (GIM-06, CLG-06, CL-64).

#### partial\_update\_category

```
partial_update_category(category_guid: str, fields: Mapping[str, Any]) -> AtlasGlossaryCategory
```

`PUT /category/{guid}/partial`: set the given attributes (GCT-05, CLG-03).

Raises:

- `ValueError` –

  `fields` is empty (the server's NO\_PARTIAL\_UPDATES).

#### partial\_update\_glossary

```
partial_update_glossary(glossary_guid: str, fields: Mapping[str, Any]) -> AtlasGlossary
```

`PUT /{guid}/partial`: set the given attributes of the glossary (GLS-03, CLG-03).

Raises:

- `ValueError` –

  `fields` is empty (the server's NO\_PARTIAL\_UPDATES).

#### partial\_update\_term

```
partial_update_term(term_guid: str, fields: Mapping[str, Any]) -> AtlasGlossaryTerm
```

`PUT /term/{guid}/partial`: set the given attributes of the term (GTM-04, CLG-03).

The body is the plain JSON object of attribute values; no fields at all is a caller bug the client refuses rather than a wasted round trip — the server's own answer for it is `BAD_REQUEST` (NO\_PARTIAL\_UPDATES). A field the term does not have stays the server's answer too (`INVALID_PARTIAL_UPDATE_ATTR`).

Raises:

- `ValueError` –

  `fields` is empty.

#### related\_categories

```
related_categories(category_guid: str) -> dict[str, list[AtlasRelatedCategoryHeader]]
```

`GET /category/{guid}/related`: its parent and children (GCT-07, CLG-07).

The keys are `parent` and `children`; a missing relation is absent.

#### related\_terms

```
related_terms(term_guid: str) -> dict[str, list[AtlasRelatedTermHeader]]
```

`GET /terms/{guid}/related`: the term's related terms by relation (GTM-06, CLG-07).

The key is the relation's JSON name (`seeAlso`, `synonyms`, …); the page parameters the server reads and ignores, the client does not send.

#### remove\_term\_assignment

```
remove_term_assignment(term_guid: str, object_ids: Sequence[AtlasRelatedObjectId]) -> None
```

`DELETE /terms/{guid}/assignedEntities`: remove the assignments (GTA-03, CLG-04). 204.

#### term

```
term(term_guid: str) -> AtlasGlossaryTerm
```

`GET /term/{guid}`: the term (GTM-01).

#### update\_category

```
update_category(category_guid: str, category: AtlasGlossaryCategory) -> AtlasGlossaryCategory
```

`PUT /category/{guid}`: update the category of the path's GUID (GCT-04, CLG-08).

#### update\_glossary

```
update_glossary(glossary_guid: str, glossary: AtlasGlossary) -> AtlasGlossary
```

`PUT /{guid}`: update the glossary of the path's GUID (GLS-03, CLG-08).

#### update\_term

```
update_term(term_guid: str, term: AtlasGlossaryTerm) -> AtlasGlossaryTerm
```

`PUT /term/{guid}`: update the term of the path's GUID (GTM-04, CLG-08).

The server grafts the path GUID onto the body — a body without one is the caller's model, sent as given.

### LineageApi

```
LineageApi(api: _Api)
```

The lineage resource of an :class:`AtlasClient` (CL-61..CL-63): `client.lineage`.

The paths mirror `routes/lineage.py`; the answer body is this library's `LineageInfo` (CL-12) — the lenient, UUID-keyed shape 8.2 consumes, not `aurelius-atlas-model`'s strict `AtlasLineageInfo`.

Methods:

- **`get`** –

  `GET api/atlas/v2/lineage/{guid}` (CL-61, LM-01's upstream) — the entity's lineage graph.
- **`get_by_unique_attributes`** –

  `GET api/atlas/v2/lineage/uniqueAttribute/type/{type_name}` (CL-63): the lineage of the entity.
- **`get_on_demand`** –

  `POST api/atlas/v2/lineage/{guid}` (CL-62): lineage on demand, within the constraints per GUID.

#### get

```
get(guid: UUID, depth: int = 3, direction: Direction = 'BOTH') -> LineageInfo
```

`GET api/atlas/v2/lineage/{guid}` (CL-61, LM-01's upstream) — the entity's lineage graph.

Raises:

- `AtlasClientError` –

  Any non-2xx answer, including the 404 of a guid with no lineage (LM-05) — the caller maps the statuses.

#### get\_by\_unique\_attributes

```
get_by_unique_attributes(
    type_name: str, attributes: Mapping[str, Any], depth: int = 3, direction: Direction = "BOTH"
) -> LineageInfo
```

`GET api/atlas/v2/lineage/uniqueAttribute/type/{type_name}` (CL-63): the lineage of the entity.

The entity is the one holding the `attr:` values, as `routes/lineage.py` reads them.

#### get\_on\_demand

```
get_on_demand(guid: UUID, constraints: Mapping[str, LineageOnDemandConstraints] | None = None) -> LineageInfo
```

`POST api/atlas/v2/lineage/{guid}` (CL-62): lineage on demand, within the constraints per GUID.

The constraints are `aurelius-atlas-model`'s (DD-309). A server with the feature off answers `LINEAGE_ON_DEMAND_NOT_ENABLED`, raised as usual (CL-04).

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
