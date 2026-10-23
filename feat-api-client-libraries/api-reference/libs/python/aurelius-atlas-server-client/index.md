# aurelius-atlas-server-client

The contract and the async client of the Atlas REST API (8.4, DD-114, DD-115): the admin, types and lineage models every consumer of `aurelius-atlas-server` speaks, and the `httpx`-based `AtlasClient` that calls it. The lineage-model app imports the lineage wire models from here — one source of truth for both sides of the wire.

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

  The body every Atlas error is answered with (SRV-04; CL-10).
- **`AtlasSessionInfo`** –

  The body of `GET /api/atlas/admin/session` (ADM-05, DV-04; CL-10).
- **`AtlasStatus`** –

  The body of `GET /api/atlas/admin/status` (ADM-02; CL-10).
- **`AtlasVersion`** –

  The body of `GET /api/atlas/admin/version` (ADM-01, DV-03; CL-10).

### AtlasErrorInfo

Bases: `AtlasModel`

The body every Atlas error is answered with (SRV-04; CL-10).

`{errorCode, errorMessage}`, plus `errorCause` on the server-side codes. The 8.x auxiliary apps reuse the shape with the `ATLAS-400-00-029` code.

**Show JSON schema:**

```
{
  "description": "The body every Atlas error is answered with (SRV-04; CL-10).\n\n``{errorCode, errorMessage}``, plus ``errorCause`` on the server-side codes.\nThe 8.x auxiliary apps reuse the shape with the ``ATLAS-400-00-029`` code.",
  "properties": {
    "errorCode": {
      "title": "Errorcode",
      "type": "string"
    },
    "errorMessage": {
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

#### error\_code

```
error_code: str
```

#### error\_message

```
error_message: str
```

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

### AtlasSessionInfo

Bases: `AtlasModel`

The body of `GET /api/atlas/admin/session` (ADM-05, DV-04; CL-10).

The `atlas.*` UI settings ride along as extras; the typed fields are the session's own — no user until 6.1, so `user_name` answers `None`.

**Show JSON schema:**

```
{
  "description": "The body of ``GET /api/atlas/admin/session`` (ADM-05, DV-04; CL-10).\n\nThe ``atlas.*`` UI settings ride along as extras; the typed fields are the\nsession's own \u2014 no user until 6.1, so ``user_name`` answers ``None``.",
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
      "title": "Username"
    },
    "groups": {
      "items": {
        "type": "string"
      },
      "title": "Groups",
      "type": "array"
    },
    "timezones": {
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

#### groups

```
groups: list[str]
```

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

#### user\_name

```
user_name: str | None = None
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

### AtlasStatus

Bases: `AtlasModel`

The body of `GET /api/atlas/admin/status` (ADM-02; CL-10).

**Show JSON schema:**

```
{
  "description": "The body of ``GET /api/atlas/admin/status`` (ADM-02; CL-10).",
  "properties": {
    "Status": {
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

The service state; the only one Aurelius Atlas has is `ACTIVE`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

### AtlasVersion

Bases: `AtlasModel`

The body of `GET /api/atlas/admin/version` (ADM-01, DV-03; CL-10).

The keys are Atlas's, capitalised; the Aurelius server reports its own name and description there (DV-03).

**Show JSON schema:**

```
{
  "description": "The body of ``GET /api/atlas/admin/version`` (ADM-01, DV-03; CL-10).\n\nThe keys are Atlas's, capitalised; the Aurelius server reports its own name\nand description there (DV-03).",
  "properties": {
    "Version": {
      "title": "Version",
      "type": "string"
    },
    "Revision": {
      "title": "Revision",
      "type": "string"
    },
    "Name": {
      "title": "Name",
      "type": "string"
    },
    "Description": {
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

#### revision

```
revision: str
```

#### version

```
version: str
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

## aurelius\_atlas\_server\_client.lineage

The Atlas `v2/lineage/{guid}` body, as the server client's contract (CL-12, LM-04).

Moved here from `aurelius_atlas_lineage_model.lineage` by increment 8.4 (DD-114): the body is the *server's* answer — the Aurelius `LineageInfo` wire shape of `libs/m4i-atlas-core` (ADR 055 R4), stated as pydantic (DD-109) so the serving side (5.1's lineage feed) and every calling side (8.2 today) validate one class.

The *flattening* is not here: `PROCESS_TYPES`, `LINEAGE_RULES` and `flatten_relations` are 8.2's app logic and stay in the app (8.4 spec, CL-12).

Type Aliases:

- **`Direction`** –

  The lineage directions Atlas accepts (the legacy's `LineageDirection` enum, LM-01).

Classes:

- **`EntityHeaderLite`** –

  The fields of an Atlas entity header the lineage body carries (LM-02).
- **`LineageInfo`** –

  The body of Atlas's `v2/lineage/{guid}` answer (LM-04).
- **`LineageRelation`** –

  One Atlas lineage relation: an edge between two entity guids (LM-02).

### Direction

```
Direction = Literal['BOTH', 'INPUT', 'OUTPUT']
```

The lineage directions Atlas accepts (the legacy's `LineageDirection` enum, LM-01).

### EntityHeaderLite

Bases: `BaseModel`

The fields of an Atlas entity header the lineage body carries (LM-02).

Extra fields are ignored — Atlas's header carries classifications, labels, statuses and more that the lineage rows never use.

**Show JSON schema:**

```
{
  "description": "The fields of an Atlas entity header the lineage body carries (LM-02).\n\nExtra fields are ignored \u2014 Atlas's header carries classifications,\nlabels, statuses and more that the lineage rows never use.",
  "properties": {
    "guid": {
      "title": "Guid",
      "type": "string"
    },
    "typeName": {
      "default": "",
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

- `guid` (`str`)
- `type_name` (`str`)
- `display_text` (`str | None`)

#### display\_text

```
display_text: str | None = None
```

#### guid

```
guid: str
```

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='ignore')
```

#### type\_name

```
type_name: str = ''
```

### LineageInfo

Bases: `BaseModel`

The body of Atlas's `v2/lineage/{guid}` answer (LM-04).

The legacy's `LineageInfo` dataclass, as a pydantic model: the camelCase wire names are the aliases; `baseEntityGuid`, `lineageDepth` and `lineageDirection` exist upstream but the flattening reads none of them.

**Show JSON schema:**

```
{
  "$defs": {
    "EntityHeaderLite": {
      "description": "The fields of an Atlas entity header the lineage body carries (LM-02).\n\nExtra fields are ignored \u2014 Atlas's header carries classifications,\nlabels, statuses and more that the lineage rows never use.",
      "properties": {
        "guid": {
          "title": "Guid",
          "type": "string"
        },
        "typeName": {
          "default": "",
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
      "description": "One Atlas lineage relation: an edge between two entity guids (LM-02).",
      "properties": {
        "fromEntityId": {
          "title": "Fromentityid",
          "type": "string"
        },
        "relationshipId": {
          "title": "Relationshipid",
          "type": "string"
        },
        "toEntityId": {
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
  "description": "The body of Atlas's ``v2/lineage/{guid}`` answer (LM-04).\n\nThe legacy's ``LineageInfo`` dataclass, as a pydantic model: the camelCase\nwire names are the aliases; ``baseEntityGuid``, ``lineageDepth`` and\n``lineageDirection`` exist upstream but the flattening reads none of them.",
  "properties": {
    "guidEntityMap": {
      "additionalProperties": {
        "$ref": "#/$defs/EntityHeaderLite"
      },
      "title": "Guidentitymap",
      "type": "object"
    },
    "relations": {
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

- `guid_entity_map` (`dict[str, EntityHeaderLite]`)
- `relations` (`list[LineageRelation]`)

#### guid\_entity\_map

```
guid_entity_map: dict[str, EntityHeaderLite]
```

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='ignore')
```

#### relations

```
relations: list[LineageRelation]
```

### LineageRelation

Bases: `BaseModel`

One Atlas lineage relation: an edge between two entity guids (LM-02).

**Show JSON schema:**

```
{
  "description": "One Atlas lineage relation: an edge between two entity guids (LM-02).",
  "properties": {
    "fromEntityId": {
      "title": "Fromentityid",
      "type": "string"
    },
    "relationshipId": {
      "title": "Relationshipid",
      "type": "string"
    },
    "toEntityId": {
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

- `from_entity_id` (`str`)
- `relationship_id` (`str`)
- `to_entity_id` (`str`)

#### from\_entity\_id

```
from_entity_id: str
```

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='ignore')
```

#### relationship\_id

```
relationship_id: str
```

#### to\_entity\_id

```
to_entity_id: str
```

## aurelius\_atlas\_server\_client.client

The async client for the Atlas metadata API (CL-01..CL-05, CL-11; DD-114, DD-115, DD-116).

One client per server: constructed from an externally built `httpx.AsyncClient` and a token source, reading no environment variables (CL-01) — the app builds the httpx client from its own settings (TLS, timeout) and passes it in. The request paths are relative, appended to that client's base URL, so a URL with a trailing slash — the `str()` of a pydantic `HttpUrl` — works as given (CL-01); the builder closes the pool, the API client never touches its lifecycle. Because the client arrives from outside, tests hand over one built on a `MockTransport` and no socket opens (CL-02, the DD-111 seam made async). Every request carries `authorization: Bearer <token>` from the token source (CL-03); a non-2xx answer raises :class:`AtlasClientError` with the status and the server's `{errorCode, errorMessage}` when the body parses (CL-04); an unreachable upstream propagates as `httpx`'s own error — mapping it to an HTTP status is the app's job (LM-07's DV-22), not the client's (CL-05).

The paths mirror the server's routes verbatim: `routes/admin.py` under `/api/atlas/admin`, `routes/types.py` under `/api/atlas/v2/types`, and the `v2/lineage/{guid}` feed of the server root (whose route lands with 5.1, CL-11).

Type Aliases:

- **`TokenSource`** –

  Where the bearer token comes from: a fixed token, or a callable that yields one.

Classes:

- **`AdminApi`** –

  The admin resource of an :class:`AtlasClient` (CL-11): `client.admin`.
- **`AtlasClient`** –

  The client for one Atlas metadata server (CL-11, DD-114, DD-116).
- **`AtlasClientError`** –

  A non-2xx answer from the Atlas server, with the status and the error body (CL-04).
- **`TypesApi`** –

  The typedef resource of an :class:`AtlasClient` (CL-11): `client.types`.

Attributes:

- **`ADMIN_ROOT`** –
- **`CLIENT_ERROR`** –

  The status where an answer becomes an error: the client-error boundary (CL-04).
- **`DEFAULT_TIMEOUT_SECONDS`** –

  The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01).
- **`KIND_PATHS`** (`dict[TypeCategory, str]`) –

  The path segment of each kind's lookups, mirroring `routes/types.py`'s `KIND_PATHS` (CL-11).
- **`LINEAGE_ROOT`** –

  The route prefixes of the server's resources (`routes/admin.py`, `routes/types.py`, 5.1's feed).
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

The route prefixes of the server's resources (`routes/admin.py`, `routes/types.py`, 5.1's feed).

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

The client for one Atlas metadata server (CL-11, DD-114, DD-116).

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
- **`types`** –

#### admin

```
admin = AdminApi(api)
```

#### types

```
types = TypesApi(api)
```

#### get\_lineage

```
get_lineage(guid: str, depth: int = 3, direction: Direction = 'BOTH') -> LineageInfo
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
