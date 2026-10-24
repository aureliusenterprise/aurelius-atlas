# aurelius-atlas-lineage-model-client

The contract and the async client of the lineage-model API (8.4, DD-114, DD-115): the query-parameter model of `GET /v2/lineage` and the model-document response. The `aurelius-atlas-lineage-model` app imports its own contract from here; a no-lineage answer (204) is `None`.

## Installation

```
[project.dependencies]
aurelius-atlas-lineage-model-client = "*"

[tool.uv.sources.aurelius-atlas-lineage-model-client]
workspace = true
```

## Documentation

## aurelius\_atlas\_lineage\_model\_client.models

The request and response shapes of the lineage-model API (CL-30, LM-01/LM-04; DD-114).

The ids of this module's rules stay here: `LineageModelParams` is LM-01's query (DV-20/DV-21 are its rejections), `LineageModelResponse` is the LM-04/LM-01 forward of the data2model answer (DV-15's contract). Field descriptions are the public OpenAPI documentation, so they name no rule ids; the Java classes ported are in the increment spec.

The query of `GET /` and the answer it forwards from data2model, stated once so the app validates its own query with the same model a caller builds (CL-07). The lineage directions are imported from `aurelius-atlas-server-client` — the lineage vocabulary belongs to the lineage API (CL-12), not to each consumer; reusing it is CL-10's rule applied to types.

Classes:

- **`LineageModelParams`** –

  The `GET /` query of the lineage-model API: which entity, how deep, which way.
- **`LineageModelResponse`** –

  The answer of `GET /`: the flattened lineage as an ar3 model and its metadata.

Attributes:

- **`DEFAULT_DEPTH`** –

  The lineage depth the endpoint defaults to when the query omits it (LM-01).
- **`MIN_DEPTH`** –

  The smallest depth the endpoint accepts (LM-01's `ge=1`).

### DEFAULT\_DEPTH

```
DEFAULT_DEPTH = 3
```

The lineage depth the endpoint defaults to when the query omits it (LM-01).

### MIN\_DEPTH

```
MIN_DEPTH = 1
```

The smallest depth the endpoint accepts (LM-01's `ge=1`).

### \_\_all\_\_

```
__all__ = ['DEFAULT_DEPTH', 'MIN_DEPTH', 'Direction', 'LineageModelParams', 'LineageModelResponse']
```

### LineageModelParams

Bases: `BaseModel`

The `GET /` query of the lineage-model API: which entity, how deep, which way.

**Show JSON schema:**

```
{
  "$defs": {
    "Direction": {
      "enum": [
        "BOTH",
        "INPUT",
        "OUTPUT"
      ],
      "type": "string"
    }
  },
  "additionalProperties": false,
  "description": "The ``GET /`` query of the lineage-model API: which entity, how deep, which way.",
  "properties": {
    "guid": {
      "description": "The guid of the entity whose lineage is flattened.",
      "format": "uuid",
      "title": "Guid",
      "type": "string"
    },
    "depth": {
      "default": 3,
      "description": "How many hops of lineage to walk; at least one.",
      "minimum": 1,
      "title": "Depth",
      "type": "integer"
    },
    "direction": {
      "$ref": "#/$defs/Direction",
      "default": "BOTH",
      "description": "Which way to walk the lineage: upstream, downstream, or both."
    }
  },
  "required": [
    "guid"
  ],
  "title": "LineageModelParams",
  "type": "object"
}
```

Config:

- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `guid` (`UUID`)
- `depth` (`int`)
- `direction` (`Direction`)

#### depth

```
depth: int = DEFAULT_DEPTH
```

How many hops of lineage to walk; at least one.

#### direction

```
direction: Direction = 'BOTH'
```

Which way to walk the lineage: upstream, downstream, or both.

#### guid

```
guid: UUID
```

The guid of the entity whose lineage is flattened.

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

### LineageModelResponse

Bases: `BaseModel`

The answer of `GET /`: the flattened lineage as an ar3 model and its metadata.

**Show JSON schema:**

```
{
  "description": "The answer of ``GET /``: the flattened lineage as an ar3 model and its metadata.",
  "properties": {
    "model": {
      "description": "The ar3 model, JSON-encoded as a string; the browser draws it.",
      "title": "Model",
      "type": "string"
    },
    "metadata": {
      "description": "One entry per element, edge, and view: the provenance of each row and its mapped attributes, as open key/value maps.",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "title": "Metadata",
      "type": "array"
    }
  },
  "required": [
    "model"
  ],
  "title": "LineageModelResponse",
  "type": "object"
}
```

Config:

- `extra`: `ignore`
- `frozen`: `True`

Fields:

- `model` (`str`)
- `metadata` (`list[dict[str, Any]]`)

#### metadata

```
metadata: list[dict[str, Any]]
```

One entry per element, edge, and view: the provenance of each row and its mapped attributes, as open key/value maps.

#### model

```
model: str
```

The ar3 model, JSON-encoded as a string; the browser draws it.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

## aurelius\_atlas\_lineage\_model\_client.client

The async client for the lineage-model API (CL-01..CL-05, CL-30; DD-114, DD-115, DD-116).

The shared client conventions of increment 8.4: constructed from an externally built `httpx.AsyncClient` and a token source, reading no environment variables (CL-01). The request path is relative, appended to that client's base URL, so a URL with a trailing slash — the `str()` of a pydantic `HttpUrl` — works as given (CL-01); the builder closes the pool, the API client never touches its lifecycle. Tests hand over one built on a `MockTransport` and no socket opens (CL-02); the bearer goes on every call (CL-03); `LineageModelClientError` rises on a non-2xx answer with the Atlas-shaped body when it parses (CL-04); an unreachable upstream propagates as `httpx`'s own error (CL-05).

The 204 of LM-05/LM-06 — the empty answer, no model — is *not* an error: it maps to `None`, the caller's success path (CL-04).

Type Aliases:

- **`TokenSource`** –

  Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03).

Classes:

- **`LineageModelClient`** –

  The client for one lineage-model service (CL-30, DD-114, DD-116).
- **`LineageModelClientError`** –

  A non-2xx answer from the lineage-model API, with the status and the error body (CL-04).

Attributes:

- **`CLIENT_ERROR`** –

  The status where an answer becomes an error: the client-error boundary (CL-04).
- **`DEFAULT_TIMEOUT_SECONDS`** –

  The suggested request timeout, seconds — for the httpx client an app builds (the browser's bound).
- **`NO_CONTENT`** –

  The empty answer of a guid with no lineage: the caller's success, not an error (CL-04, LM-05/LM-06).

### CLIENT\_ERROR

```
CLIENT_ERROR = 400
```

The status where an answer becomes an error: the client-error boundary (CL-04).

### DEFAULT\_TIMEOUT\_SECONDS

```
DEFAULT_TIMEOUT_SECONDS = 10.0
```

The suggested request timeout, seconds — for the httpx client an app builds (the browser's bound).

### NO\_CONTENT

```
NO_CONTENT = 204
```

The empty answer of a guid with no lineage: the caller's success, not an error (CL-04, LM-05/LM-06).

### TokenSource

```
TokenSource = str | Callable[[], str]
```

Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03).

### LineageModelClient

```
LineageModelClient(http: AsyncClient, token: TokenSource)
```

The client for one lineage-model service (CL-30, DD-114, DD-116).

Parameters:

- #### **`http`**

  (`AsyncClient`) –

  The `httpx.AsyncClient` to speak through, built by the caller — its builder owns its lifecycle, this client only speaks through it. Its base URL carries the service root; the route path is relative to it.
- #### **`token`**

  (`TokenSource`) –

  The bearer token source (CL-03).

Methods:

- **`get`** –

  `GET /?guid=&depth=&direction=`: the flattened lineage's model (LM-01, CL-30).
- **`with_token`** –

  The same client speaking with `token` — sharing the connection pool (CL-03).

#### get

```
get(guid: UUID, depth: int = DEFAULT_DEPTH, direction: Direction = 'BOTH') -> LineageModelResponse | None
```

`GET /?guid=&depth=&direction=`: the flattened lineage's model (LM-01, CL-30).

:returns: the model document, or `None` for the empty answer of LM-05/LM-06 (204).

Raises:

- `LineageModelClientError` –

  The API answered 4xx/5xx (400 is DV-20/DV-21, 502 is DV-22 — both with the Atlas-shaped body).

#### with\_token

```
with_token(token: TokenSource) -> LineageModelClient
```

The same client speaking with `token` — sharing the connection pool (CL-03).

### LineageModelClientError

```
LineageModelClientError(status_code: int, error_code: str | None, error_message: str | None)
```

Bases: `RuntimeError`

A non-2xx answer from the lineage-model API, with the status and the error body (CL-04).

Attributes:

- **`error_code`** –

  The `errorCode` of the Atlas-shaped body, when it parsed (DV-20/DV-21/DV-22).
- **`error_message`** –

  The `errorMessage` of the Atlas-shaped body, when it parsed.
- **`status_code`** –

  The HTTP status the API answered with.

#### error\_code

```
error_code = error_code
```

The `errorCode` of the Atlas-shaped body, when it parsed (DV-20/DV-21/DV-22).

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
