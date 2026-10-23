# aurelius-atlas-validate-entity-client

The contract and the async client of the validate-entity API (8.4, DD-114, DD-115): the governance validation card the screen renders and the `ValidateEntityClient` that asks for it. The `aurelius-atlas-validate-entity` app imports its own response model from here.

## Installation

```
[project.dependencies]
aurelius-atlas-validate-entity-client = "*"

[tool.uv.sources.aurelius-atlas-validate-entity-client]
workspace = true
```

## Documentation

## aurelius\_atlas\_validate\_entity\_client.models

The governance-quality answer of the validate-entity API (CL-40, VE-02; DD-114).

The body the 8.3 mock answers — the four cards the webapp's editor renders, the `AppSearchResult<GovQualitySearchObject>` shape of the legacy `libs/atlas/api::GovQualityApi` (ADR 055 R4) — stated as models so a caller parses it and the app's constant is checked against one shape (VE-02, DV-14).

Every leaf is a `{"raw": …}` wrapper, and the `doc-…` ids, string `compliant` flags and `_meta.engine` of the mock are part of the browser contract, so they are modelled as they arrive, not normalised. The card keys and `isNonCompliant` are camelCase, the legacy's names.

Classes:

- **`GovQualityItem`** –

  One governance check: a verdict item of a card (VE-02).
- **`GovQualityMeta`** –

  The `_meta` of an item: the engine, score and document id (VE-02).
- **`GovQualityValue`** –

  A `{"raw": …}` wrapper — every leaf of the governance document is one (VE-02).
- **`ValidationCard`** –

  One governance card: the items of one aspect, with the card's verdict (VE-02).
- **`ValidationResponse`** –

  The `POST /` answer: the four governance cards (VE-02, DV-14; CL-40).

### GovQualityItem

Bases: `BaseModel`

One governance check: a verdict item of a card (VE-02).

**Show JSON schema:**

```
{
  "$defs": {
    "GovQualityMeta": {
      "additionalProperties": false,
      "description": "The ``_meta`` of an item: the engine, score and document id (VE-02).",
      "properties": {
        "engine": {
          "title": "Engine",
          "type": "string"
        },
        "score": {
          "title": "Score",
          "type": "integer"
        },
        "id": {
          "title": "Id",
          "type": "string"
        }
      },
      "required": [
        "engine",
        "score",
        "id"
      ],
      "title": "GovQualityMeta",
      "type": "object"
    },
    "GovQualityValue": {
      "additionalProperties": false,
      "description": "A ``{\"raw\": \u2026}`` wrapper \u2014 every leaf of the governance document is one (VE-02).",
      "properties": {
        "raw": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            }
          ],
          "title": "Raw"
        }
      },
      "required": [
        "raw"
      ],
      "title": "GovQualityValue",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "description": "One governance check: a verdict item of a card (VE-02).",
  "properties": {
    "result": {
      "$ref": "#/$defs/GovQualityValue"
    },
    "dataqualitytype": {
      "$ref": "#/$defs/GovQualityValue"
    },
    "usedattributes": {
      "$ref": "#/$defs/GovQualityValue"
    },
    "name": {
      "$ref": "#/$defs/GovQualityValue"
    },
    "compliant": {
      "$ref": "#/$defs/GovQualityValue"
    },
    "_meta": {
      "$ref": "#/$defs/GovQualityMeta"
    },
    "id": {
      "$ref": "#/$defs/GovQualityValue"
    }
  },
  "required": [
    "result",
    "dataqualitytype",
    "usedattributes",
    "name",
    "compliant",
    "_meta",
    "id"
  ],
  "title": "GovQualityItem",
  "type": "object"
}
```

Config:

- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `result` (`GovQualityValue`)
- `dataqualitytype` (`GovQualityValue`)
- `usedattributes` (`GovQualityValue`)
- `name` (`GovQualityValue`)
- `compliant` (`GovQualityValue`)
- `meta` (`GovQualityMeta`)
- `id` (`GovQualityValue`)

#### compliant

```
compliant: GovQualityValue
```

The verdict flag, a string `'0'`/`'1'` — as the legacy emits it (VE-02).

#### dataqualitytype

```
dataqualitytype: GovQualityValue
```

The kind of check; the mock's items are `attribute` checks (the legacy's lower-case name).

#### id

```
id: GovQualityValue
```

The item's document id, wrapped like every leaf.

#### meta

```
meta: GovQualityMeta
```

The producing engine's record.

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### name

```
name: GovQualityValue
```

The check's name; the mock's items name `Attribute - <key>`.

#### result

```
result: GovQualityValue
```

The human-readable verdict.

#### usedattributes

```
usedattributes: GovQualityValue
```

The entity attributes the check reads.

### GovQualityMeta

Bases: `BaseModel`

The `_meta` of an item: the engine, score and document id (VE-02).

**Show JSON schema:**

```
{
  "additionalProperties": false,
  "description": "The ``_meta`` of an item: the engine, score and document id (VE-02).",
  "properties": {
    "engine": {
      "title": "Engine",
      "type": "string"
    },
    "score": {
      "title": "Score",
      "type": "integer"
    },
    "id": {
      "title": "Id",
      "type": "string"
    }
  },
  "required": [
    "engine",
    "score",
    "id"
  ],
  "title": "GovQualityMeta",
  "type": "object"
}
```

Config:

- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `engine` (`str`)
- `score` (`int`)
- `id` (`str`)

#### engine

```
engine: str
```

The engine that produced the item; the mock names `atlas-dev-gov-quality` (DV-14).

#### id

```
id: str
```

The document id; the mock's `doc-…` ids are the browser contract.

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### score

```
score: int
```

The item's score.

### GovQualityValue

Bases: `BaseModel`

A `{"raw": …}` wrapper — every leaf of the governance document is one (VE-02).

**Show JSON schema:**

```
{
  "additionalProperties": false,
  "description": "A ``{\"raw\": \u2026}`` wrapper \u2014 every leaf of the governance document is one (VE-02).",
  "properties": {
    "raw": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        }
      ],
      "title": "Raw"
    }
  },
  "required": [
    "raw"
  ],
  "title": "GovQualityValue",
  "type": "object"
}
```

Config:

- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `raw` (`str | list[str]`)

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### raw

```
raw: str | list[str]
```

The value: a string, or a list of strings (`usedattributes`).

### ValidationCard

Bases: `BaseModel`

One governance card: the items of one aspect, with the card's verdict (VE-02).

**Show JSON schema:**

```
{
  "$defs": {
    "GovQualityItem": {
      "additionalProperties": false,
      "description": "One governance check: a verdict item of a card (VE-02).",
      "properties": {
        "result": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "dataqualitytype": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "usedattributes": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "name": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "compliant": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "_meta": {
          "$ref": "#/$defs/GovQualityMeta"
        },
        "id": {
          "$ref": "#/$defs/GovQualityValue"
        }
      },
      "required": [
        "result",
        "dataqualitytype",
        "usedattributes",
        "name",
        "compliant",
        "_meta",
        "id"
      ],
      "title": "GovQualityItem",
      "type": "object"
    },
    "GovQualityMeta": {
      "additionalProperties": false,
      "description": "The ``_meta`` of an item: the engine, score and document id (VE-02).",
      "properties": {
        "engine": {
          "title": "Engine",
          "type": "string"
        },
        "score": {
          "title": "Score",
          "type": "integer"
        },
        "id": {
          "title": "Id",
          "type": "string"
        }
      },
      "required": [
        "engine",
        "score",
        "id"
      ],
      "title": "GovQualityMeta",
      "type": "object"
    },
    "GovQualityValue": {
      "additionalProperties": false,
      "description": "A ``{\"raw\": \u2026}`` wrapper \u2014 every leaf of the governance document is one (VE-02).",
      "properties": {
        "raw": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            }
          ],
          "title": "Raw"
        }
      },
      "required": [
        "raw"
      ],
      "title": "GovQualityValue",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "description": "One governance card: the items of one aspect, with the card's verdict (VE-02).",
  "properties": {
    "items": {
      "items": {
        "$ref": "#/$defs/GovQualityItem"
      },
      "title": "Items",
      "type": "array"
    },
    "isNonCompliant": {
      "title": "Isnoncompliant",
      "type": "boolean"
    }
  },
  "required": [
    "isNonCompliant"
  ],
  "title": "ValidationCard",
  "type": "object"
}
```

Config:

- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `items` (`list[GovQualityItem]`)
- `is_non_compliant` (`bool`)

#### is\_non\_compliant

```
is_non_compliant: bool
```

Whether any item fails; the editor's badge.

#### items

```
items: list[GovQualityItem]
```

The checks of this card.

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

### ValidationResponse

Bases: `BaseModel`

The `POST /` answer: the four governance cards (VE-02, DV-14; CL-40).

The keys are the legacy's — `dataEntity`, `definition`, `domainLead`, `name` — the aspects the editor's governance panel renders.

**Show JSON schema:**

```
{
  "$defs": {
    "GovQualityItem": {
      "additionalProperties": false,
      "description": "One governance check: a verdict item of a card (VE-02).",
      "properties": {
        "result": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "dataqualitytype": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "usedattributes": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "name": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "compliant": {
          "$ref": "#/$defs/GovQualityValue"
        },
        "_meta": {
          "$ref": "#/$defs/GovQualityMeta"
        },
        "id": {
          "$ref": "#/$defs/GovQualityValue"
        }
      },
      "required": [
        "result",
        "dataqualitytype",
        "usedattributes",
        "name",
        "compliant",
        "_meta",
        "id"
      ],
      "title": "GovQualityItem",
      "type": "object"
    },
    "GovQualityMeta": {
      "additionalProperties": false,
      "description": "The ``_meta`` of an item: the engine, score and document id (VE-02).",
      "properties": {
        "engine": {
          "title": "Engine",
          "type": "string"
        },
        "score": {
          "title": "Score",
          "type": "integer"
        },
        "id": {
          "title": "Id",
          "type": "string"
        }
      },
      "required": [
        "engine",
        "score",
        "id"
      ],
      "title": "GovQualityMeta",
      "type": "object"
    },
    "GovQualityValue": {
      "additionalProperties": false,
      "description": "A ``{\"raw\": \u2026}`` wrapper \u2014 every leaf of the governance document is one (VE-02).",
      "properties": {
        "raw": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            }
          ],
          "title": "Raw"
        }
      },
      "required": [
        "raw"
      ],
      "title": "GovQualityValue",
      "type": "object"
    },
    "ValidationCard": {
      "additionalProperties": false,
      "description": "One governance card: the items of one aspect, with the card's verdict (VE-02).",
      "properties": {
        "items": {
          "items": {
            "$ref": "#/$defs/GovQualityItem"
          },
          "title": "Items",
          "type": "array"
        },
        "isNonCompliant": {
          "title": "Isnoncompliant",
          "type": "boolean"
        }
      },
      "required": [
        "isNonCompliant"
      ],
      "title": "ValidationCard",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "description": "The ``POST /`` answer: the four governance cards (VE-02, DV-14; CL-40).\n\nThe keys are the legacy's \u2014 ``dataEntity``, ``definition``, ``domainLead``,\n``name`` \u2014 the aspects the editor's governance panel renders.",
  "properties": {
    "dataEntity": {
      "$ref": "#/$defs/ValidationCard"
    },
    "definition": {
      "$ref": "#/$defs/ValidationCard"
    },
    "domainLead": {
      "$ref": "#/$defs/ValidationCard"
    },
    "name": {
      "$ref": "#/$defs/ValidationCard"
    }
  },
  "required": [
    "dataEntity",
    "definition",
    "domainLead",
    "name"
  ],
  "title": "ValidationResponse",
  "type": "object"
}
```

Config:

- `populate_by_name`: `True`
- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `data_entity` (`ValidationCard`)
- `definition` (`ValidationCard`)
- `domain_lead` (`ValidationCard`)
- `name` (`ValidationCard`)

#### data\_entity

```
data_entity: ValidationCard
```

#### definition

```
definition: ValidationCard
```

#### domain\_lead

```
domain_lead: ValidationCard
```

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='forbid', frozen=True)
```

#### name

```
name: ValidationCard
```

## aurelius\_atlas\_validate\_entity\_client.client

The async client for the validate-entity API (CL-01..CL-05, CL-40; DD-114, DD-115, DD-116).

The shared client conventions of increment 8.4: constructed from an externally built `httpx.AsyncClient` and a token source, reading no environment variables (CL-01). The request path is relative, appended to that client's base URL, so a URL with a trailing slash — the `str()` of a pydantic `HttpUrl` — works as given (CL-01); the builder closes the pool, the API client never touches its lifecycle. Tests pass one built on a `MockTransport` and no socket opens (CL-02); the bearer goes on every call (CL-03); `ValidateEntityClientError` rises on a non-2xx answer (CL-04); `httpx`'s own error propagates on an unreachable upstream (CL-05).

`validate` posts any mapping — the endpoint never reads the body (VE-01, DD-112), so the request is not a model — and parses the fixed governance document into a :class:`~aurelius_atlas_validate_entity_client.models.ValidationResponse` (CL-40).

Type Aliases:

- **`TokenSource`** –

  Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03).

Classes:

- **`ValidateEntityClient`** –

  The client for one validate-entity service (CL-40, DD-114, DD-116).
- **`ValidateEntityClientError`** –

  A non-2xx answer from the validate-entity API, with the status (CL-04).

Attributes:

- **`CLIENT_ERROR`** –

  The status where an answer becomes an error: the client-error boundary (CL-04).
- **`DEFAULT_TIMEOUT_SECONDS`** –

  The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01).
- **`VALIDATE_PATH`** –

  The validation endpoint of the 8.3 app (VE-01): the service root, relative to the base URL (CL-01).

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

### VALIDATE\_PATH

```
VALIDATE_PATH = ''
```

The validation endpoint of the 8.3 app (VE-01): the service root, relative to the base URL (CL-01).

### TokenSource

```
TokenSource = str | Callable[[], str]
```

Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03).

### ValidateEntityClient

```
ValidateEntityClient(http: AsyncClient, token: TokenSource)
```

The client for one validate-entity service (CL-40, DD-114, DD-116).

Parameters:

- #### **`http`**

  (`AsyncClient`) –

  The `httpx.AsyncClient` to speak through, built by the caller — its builder owns its lifecycle, this client only speaks through it. Its base URL carries the service root; the path above is relative to it.
- #### **`token`**

  (`TokenSource`) –

  The bearer token source (CL-03).

Methods:

- **`validate`** –

  `POST /`: the entity in, the governance-quality document out (VE-01, CL-40).
- **`with_token`** –

  The same client speaking with `token` — sharing the connection pool (CL-03).

#### validate

```
validate(entity: Mapping[str, Any]) -> ValidationResponse
```

`POST /`: the entity in, the governance-quality document out (VE-01, CL-40).

:param entity: the entity being edited; the mock never reads it (VE-01).

Raises:

- `ValidateEntityClientError` –

  The API answered 4xx/5xx (a 401 is VE-03).

#### with\_token

```
with_token(token: TokenSource) -> ValidateEntityClient
```

The same client speaking with `token` — sharing the connection pool (CL-03).

### ValidateEntityClientError

```
ValidateEntityClientError(status_code: int, error_code: str | None, error_message: str | None)
```

Bases: `RuntimeError`

A non-2xx answer from the validate-entity API, with the status (CL-04).

Attributes:

- **`error_code`** –

  The `errorCode` of the Atlas-shaped body, when it parsed (VE-03's 401).
- **`error_message`** –

  The `errorMessage` of the Atlas-shaped body, when it parsed.
- **`status_code`** –

  The HTTP status the API answered with.

#### error\_code

```
error_code = error_code
```

The `errorCode` of the Atlas-shaped body, when it parsed (VE-03's 401).

#### error\_message

```
error_message = error_message
```

The `errorMessage` of the Atlas-shaped body, when it parsed.

#### status\_code

```
status_code = status_code
```

The HTTP status the API answered with.
