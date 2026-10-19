# aurelius-atlas-store-es

Elasticsearch access for Aurelius Atlas: settings, client lifecycle, version check and health check.

## Installation

```
dependencies = ["aurelius-atlas-store-es"]

[tool.uv.sources.aurelius-atlas-store-es]
workspace = true
```

Tests that need a server add `aurelius-atlas-store-es[testing]` to their dev dependencies.

## Design

The technology-specific detail of the store. The property it keeps — one search store as the system of record — is [ADR 047](<https://aureliusenterprise.github.io/docs-editorial-pass/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>); the layout decisions are recorded as [DD-005](<https://aureliusenterprise.github.io/docs-editorial-pass/architecture/conversion/design-log/#dd-005-the-store-uses-the-official-async-elasticsearch-client>), [DD-008](<https://aureliusenterprise.github.io/docs-editorial-pass/architecture/conversion/design-log/#dd-008-a-yellow-cluster-is-healthy>) and [DD-028](<https://aureliusenterprise.github.io/docs-editorial-pass/architecture/conversion/design-log/#dd-028-the-type-definitions-are-one-elasticsearch-document>).

**Client.** One official async Elasticsearch client per store, created from `StoreSettings` and owned by the store's lifespan. Connections are always HTTPS with certificate verification (`ca_certs`, `verify_certs=True`) plus basic auth; plain-`http` hosts are rejected by settings validation, before a connection is opened — pointing the server at a stock local Elasticsearch (which serves plaintext by default) fails with a validation message, not a connection error. `dev/elasticsearch` is the TLS-served store made for this, with the CA the server trusts. The store fails fast unless the server reports Elasticsearch 9.

**Health.** `health()` never raises: green **and yellow** both count as up — a single-node dev cluster is permanently yellow, and yellow means every primary shard serves ([DD-008](<https://aureliusenterprise.github.io/docs-editorial-pass/architecture/conversion/design-log/#dd-008-a-yellow-cluster-is-healthy>)).

**Type-definition layout (increment 1.4).** All type definitions live in **one** document, behind the alias `aurelius-atlas-typedefs`, which always names the current write index (`aurelius-atlas-typedefs-000001`). The alias is created when the store first opens, refreshed on every write, and loaded into the type registry at server start (rule TDS-12). The document is replaced whole under an `if_seq_no` guard: Atlas changes several definitions in one graph transaction, and Elasticsearch has no transaction across documents, so atomicity costs one version number for all types and serialised type changes. The built-in model is about 1 MB; a deployment with tens of thousands of custom types revisits the choice (DD-028). The document is not searched — searching over catalogue entries arrives with the entity index layout in increment 2.2.

**Test fixtures.** `testing.fake` is a stand-in client for unit tests (no extra needed); `testing.container` starts a TLS-enabled Elasticsearch through testcontainers, with an ephemeral per-run certificate authority.

## Documentation

## aurelius\_atlas\_store\_es

Modules:

- **`errors`** –
- **`health`** –
- **`settings`** –
- **`store`** –
- **`testing`** –

  Test helpers for code that uses the store.

Classes:

- **`ElasticsearchStore`** –

  The single entry point to Elasticsearch: owns one client from `open` to `close` (STO-03).
- **`HealthReport`** –

  The outcome of one health check.
- **`HealthStatus`** –

  Whether the store can serve requests.
- **`StoreError`** –

  Base class for errors raised by the Elasticsearch store.
- **`StoreSettings`** –

  Connection settings for the Elasticsearch store.
- **`StoreUnavailableError`** –

  The store could not be opened: the server is unreachable, timed out or rejected the request.
- **`UnsupportedVersionError`** –

  The server runs an Elasticsearch major version this store does not support.

Functions:

- **`check_health`** –

  Ask the cluster for its health, without ever raising (STO-06).

Attributes:

- **`SUPPORTED_MAJOR_VERSION`** –

  The Elasticsearch major version this store supports (STO-04).

### SUPPORTED\_MAJOR\_VERSION

```
SUPPORTED_MAJOR_VERSION = 9
```

The Elasticsearch major version this store supports (STO-04).

### \_\_all\_\_

```
__all__ = [
    "SUPPORTED_MAJOR_VERSION",
    "ElasticsearchStore",
    "HealthReport",
    "HealthStatus",
    "StoreError",
    "StoreSettings",
    "StoreUnavailableError",
    "UnsupportedVersionError",
    "check_health",
]
```

### ElasticsearchStore

```
ElasticsearchStore(settings: StoreSettings)
```

The single entry point to Elasticsearch: owns one client from `open` to `close` (STO-03).

Use it as an async context manager:

```
async with ElasticsearchStore(settings) as store:
    report = await store.health()
```

Methods:

- **`__aenter__`** –
- **`__aexit__`** –
- **`close`** –

  Close the client; closing a closed store does nothing (STO-03).
- **`health`** –

  Report whether the store can serve requests; never raises (STO-05, STO-06).
- **`open`** –

  Connect and check that the server runs a supported version (STO-04).

Attributes:

- **`client`** (`AsyncElasticsearch`) –

  The open client.
- **`is_open`** (`bool`) –

  Whether the store holds an open client.

#### client

```
client: AsyncElasticsearch
```

The open client.

Raises:

- `RuntimeError` –

  When the store is not open.

#### is\_open

```
is_open: bool
```

Whether the store holds an open client.

#### \_\_aenter\_\_

```
__aenter__() -> Self
```

#### \_\_aexit\_\_

```
__aexit__(
    exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
) -> None
```

#### close

```
close() -> None
```

Close the client; closing a closed store does nothing (STO-03).

#### health

```
health() -> HealthReport
```

Report whether the store can serve requests; never raises (STO-05, STO-06).

#### open

```
open() -> None
```

Connect and check that the server runs a supported version (STO-04).

Opening an open store does nothing.

Raises:

- `StoreUnavailableError` –

  When the server cannot be reached or rejects the request.
- `UnsupportedVersionError` –

  When the server's major version is not supported.

### HealthReport

Bases: `BaseModel`

The outcome of one health check.

The server fields are filled whenever the server answered (STO-07); `reason` explains a `DOWN` status. The report never contains credentials (STO-08).

**Show JSON schema:**

```
{
  "$defs": {
    "HealthStatus": {
      "description": "Whether the store can serve requests.",
      "enum": [
        "up",
        "down"
      ],
      "title": "HealthStatus",
      "type": "string"
    }
  },
  "description": "The outcome of one health check.\n\nThe server fields are filled whenever the server answered (STO-07); ``reason`` explains a\n``DOWN`` status. The report never contains credentials (STO-08).",
  "properties": {
    "status": {
      "$ref": "#/$defs/HealthStatus"
    },
    "cluster_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Cluster Name"
    },
    "version": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version"
    },
    "cluster_status": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Cluster Status"
    },
    "reason": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Reason"
    }
  },
  "required": [
    "status"
  ],
  "title": "HealthReport",
  "type": "object"
}
```

Config:

- `frozen`: `True`

Fields:

- `status` (`HealthStatus`)
- `cluster_name` (`str | None`)
- `version` (`str | None`)
- `cluster_status` (`str | None`)
- `reason` (`str | None`)

#### cluster\_name

```
cluster_name: str | None = None
```

#### cluster\_status

```
cluster_status: str | None = None
```

#### model\_config

```
model_config = ConfigDict(frozen=True)
```

#### reason

```
reason: str | None = None
```

#### status

```
status: HealthStatus
```

#### version

```
version: str | None = None
```

### HealthStatus

Bases: `StrEnum`

Whether the store can serve requests.

Attributes:

- **`DOWN`** –
- **`UP`** –

#### DOWN

```
DOWN = 'down'
```

#### UP

```
UP = 'up'
```

### StoreError

Bases: `Exception`

Base class for errors raised by the Elasticsearch store.

### StoreSettings

Bases: `BaseModel`

Connection settings for the Elasticsearch store.

The application builds this object from its own configuration; the library never reads environment variables (STO-01). There is deliberately no setting that disables certificate verification (STO-02).

**Show JSON schema:**

```
{
  "description": "Connection settings for the Elasticsearch store.\n\nThe application builds this object from its own configuration; the library never reads\nenvironment variables (STO-01). There is deliberately no setting that disables certificate\nverification (STO-02).",
  "properties": {
    "hosts": {
      "items": {
        "format": "uri",
        "maxLength": 2083,
        "minLength": 1,
        "type": "string"
      },
      "minItems": 1,
      "title": "Hosts",
      "type": "array"
    },
    "username": {
      "default": "elastic",
      "title": "Username",
      "type": "string"
    },
    "password": {
      "format": "password",
      "title": "Password",
      "type": "string",
      "writeOnly": true
    },
    "ca_certs": {
      "format": "file-path",
      "title": "Ca Certs",
      "type": "string"
    },
    "request_timeout": {
      "default": 10.0,
      "exclusiveMinimum": 0,
      "title": "Request Timeout",
      "type": "number"
    }
  },
  "required": [
    "hosts",
    "password",
    "ca_certs"
  ],
  "title": "StoreSettings",
  "type": "object"
}
```

Config:

- `frozen`: `True`

Fields:

- `hosts` (`list[HttpUrl]`)
- `username` (`str`)
- `password` (`SecretStr`)
- `ca_certs` (`FilePath`)
- `request_timeout` (`float`)

Validators:

- `_require_https` → `hosts`

#### ca\_certs

```
ca_certs: FilePath
```

PEM file with the certificate authority that signed the server certificate.

#### ca\_certs\_path

```
ca_certs_path: Path
```

The CA file as a path.

#### host\_urls

```
host_urls: list[str]
```

The hosts as plain strings, in the form the Elasticsearch client expects.

#### hosts

```
hosts: list[HttpUrl]
```

Base URLs of the cluster nodes, e.g. `https://localhost:9200`.

#### model\_config

```
model_config = ConfigDict(frozen=True)
```

#### password

```
password: SecretStr
```

Password for HTTP basic authentication; never shown in `repr` or logs (STO-08).

#### request\_timeout

```
request_timeout: float = 10.0
```

Seconds to wait for a single request before it counts as failed.

#### username

```
username: str = 'elastic'
```

User for HTTP basic authentication.

### StoreUnavailableError

Bases: `StoreError`

The store could not be opened: the server is unreachable, timed out or rejected the request.

### UnsupportedVersionError

```
UnsupportedVersionError(version: str, supported_major: int)
```

Bases: `StoreError`

The server runs an Elasticsearch major version this store does not support.

Attributes:

- **`supported_major`** –
- **`version`** –

#### supported\_major

```
supported_major = supported_major
```

#### version

```
version = version
```

### check\_health

```
check_health(client: AsyncElasticsearch) -> HealthReport
```

Ask the cluster for its health, without ever raising (STO-06).

Parameters:

- #### **`client`**

  (`AsyncElasticsearch`) –

  An open Elasticsearch client.

Returns:

- `HealthReport` –

  `UP` when the cluster status is green or yellow, `DOWN` when it is red or the server
- `HealthReport` –

  could not be asked (STO-05, STO-06).

## aurelius\_atlas\_store\_es.testing.fake

A stand-in for `AsyncElasticsearch` for unit tests that need no server.

Classes:

- **`FakeClient`** –

  Records how it was built and closed; `info` and `cluster.health` return or raise as configured.
- **`FakeCluster`** –

  The `cluster` namespace of the fake client.
- **`FakeIndices`** –

  The `indices` namespace of the fake client: aliases and index creation.

Functions:

- **`response_meta`** –

  Response metadata as the transport attaches it to an `ApiError`.

Attributes:

- **`NODE`** –

### NODE

```
NODE = NodeConfig('https', 'localhost', 9200)
```

### FakeClient

```
FakeClient(**kwargs: object)
```

Records how it was built and closed; `info` and `cluster.health` return or raise as configured.

Cast it to `AsyncElasticsearch` where a client is expected; it implements only what the store uses.

Methods:

- **`close`** –

  Count the call.
- **`get`** –

  Answer like `GET index/_doc/id`, raising `NotFoundError` for a missing document.
- **`index`** –

  Store `document`, raising `ConflictError` like Elasticsearch for `op_type=create` or `if_seq_no`.
- **`info`** –

  Answer like `GET /`, or raise the configured error.

Attributes:

- **`aliases`** (`dict[str, str]`) –
- **`close_calls`** –
- **`cluster`** –
- **`cluster_name`** –
- **`cluster_status`** –
- **`documents`** (`dict[str, dict[str, tuple[dict[str, Any], int]]]`) –
- **`health_error`** (`BaseException | None`) –
- **`indices`** –
- **`info_error`** (`BaseException | None`) –
- **`kwargs`** –
- **`primary_term`** –
- **`seq_no`** –
- **`version`** –

#### aliases

```
aliases: dict[str, str] = {}
```

#### close\_calls

```
close_calls = 0
```

#### cluster

```
cluster = FakeCluster(self)
```

#### cluster\_name

```
cluster_name = 'aurelius-atlas'
```

#### cluster\_status

```
cluster_status = 'green'
```

#### documents

```
documents: dict[str, dict[str, tuple[dict[str, Any], int]]] = {}
```

#### health\_error

```
health_error: BaseException | None = None
```

#### indices

```
indices = FakeIndices(self)
```

#### info\_error

```
info_error: BaseException | None = None
```

#### kwargs

```
kwargs = kwargs
```

#### primary\_term

```
primary_term = 1
```

#### seq\_no

```
seq_no = -1
```

#### version

```
version = '9.5.5'
```

#### close

```
close() -> None
```

Count the call.

#### get

```
get(*, index: str, id: str, source: bool = True) -> dict[str, Any]
```

Answer like `GET index/_doc/id`, raising `NotFoundError` for a missing document.

#### index

```
index(
    *,
    index: str,
    id: str,
    document: dict[str, Any],
    op_type: str | None = None,
    if_seq_no: int | None = None,
    if_primary_term: int | None = None,
    **_options: object,
) -> dict[str, Any]
```

Store `document`, raising `ConflictError` like Elasticsearch for `op_type=create` or `if_seq_no`.

#### info

```
info() -> dict[str, Any]
```

Answer like `GET /`, or raise the configured error.

### FakeCluster

```
FakeCluster(client: FakeClient)
```

The `cluster` namespace of the fake client.

Methods:

- **`health`** –

  Answer like `GET _cluster/health`, or raise the configured error.

#### health

```
health() -> dict[str, Any]
```

Answer like `GET _cluster/health`, or raise the configured error.

### FakeIndices

```
FakeIndices(client: FakeClient)
```

The `indices` namespace of the fake client: aliases and index creation.

Methods:

- **`create`** –

  Create `index` with `aliases`; settings and mappings are accepted and ignored.
- **`exists_alias`** –

  Whether `name` is an alias of a created index.

#### create

```
create(*, index: str, aliases: dict[str, Any] | None = None, **_settings: object) -> dict[str, Any]
```

Create `index` with `aliases`; settings and mappings are accepted and ignored.

#### exists\_alias

```
exists_alias(*, name: str) -> bool
```

Whether `name` is an alias of a created index.

### response\_meta

```
response_meta(status: int) -> ApiResponseMeta
```

Response metadata as the transport attaches it to an `ApiError`.

## aurelius\_atlas\_store\_es.testing.container

A TLS-enabled Elasticsearch in a container, for tests that need a real server (DD-007).

> [!NOTE]
>
> Please install the `testing` extra to use this module.

Functions:

- **`elasticsearch_container`** –

  Start a single-node Elasticsearch with TLS and authentication on, and yield settings for it.

Attributes:

- **`ELASTICSEARCH_HOST`** –

  Host test clients connect to: the ephemeral certificate covers only loopback names.
- **`ELASTICSEARCH_IMAGE`** –

  Hardened Elasticsearch image; the same tag as `dev/elasticsearch`.
- **`STARTUP_TIMEOUT_ERROR`** –
- **`STARTUP_TIMEOUT_SECONDS`** –

  How long to wait for the cluster to report green or yellow.

### ELASTICSEARCH\_HOST

```
ELASTICSEARCH_HOST = 'localhost'
```

Host test clients connect to: the ephemeral certificate covers only loopback names.

### ELASTICSEARCH\_IMAGE

```
ELASTICSEARCH_IMAGE = 'dhi.io/elasticsearch:9.5-debian13'
```

Hardened Elasticsearch image; the same tag as `dev/elasticsearch`.

### STARTUP\_TIMEOUT\_ERROR

```
STARTUP_TIMEOUT_ERROR = 'Elasticsearch did not become healthy within {timeout} seconds'
```

### STARTUP\_TIMEOUT\_SECONDS

```
STARTUP_TIMEOUT_SECONDS = 180.0
```

How long to wait for the cluster to report green or yellow.

### elasticsearch\_container

```
elasticsearch_container(
    image: str = ELASTICSEARCH_IMAGE, heap: str = "512m", timeout: float = STARTUP_TIMEOUT_SECONDS
) -> Generator[StoreSettings]
```

Start a single-node Elasticsearch with TLS and authentication on, and yield settings for it.

The node is configured like `dev/elasticsearch` (DD-006): HTTPS only with a certificate from an ephemeral CA, basic authentication for `elastic` with a random password. The container and the TLS material are removed on exit.

Parameters:

- #### **`image`**

  (`str`, default: `ELASTICSEARCH_IMAGE` ) –

  The Elasticsearch image.
- #### **`heap`**

  (`str`, default: `'512m'` ) –

  JVM heap size, used for both `-Xms` and `-Xmx`.
- #### **`timeout`**

  (`float`, default: `STARTUP_TIMEOUT_SECONDS` ) –

  Seconds to wait for the cluster to become green or yellow.

Yields:

- `Generator[StoreSettings]` –

  Settings that connect to the container through its published port on localhost.
