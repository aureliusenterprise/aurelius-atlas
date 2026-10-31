# aurelius-atlas-server

The Aurelius Atlas server: the Apache Atlas 2.4.0 REST API on Elasticsearch.

## Usage

```
npx nx serve aurelius-atlas-server
```

This starts the dev Elasticsearch store and the observability stack, then the server at [https://localhost:21000](<https://localhost:21000>), the port Apache Atlas uses.

## Deployment

Deploy the image built from the provided Dockerfile. It listens on port 21000 and needs the Elasticsearch settings; it does not start without its store.

## Configuration

> [!NOTE]
>
> **Settings**
>
> ## aurelius\_atlas\_server.settings.ServerSettings
>
> Bases: `BaseSettings`
>
> How the server runs and where its store is.
>
> **Show JSON schema:**
>
> ```
> {
>   "$defs": {
>     "LogLevel": {
>       "enum": [
>         "trace",
>         "debug",
>         "info",
>         "warning",
>         "error"
>       ],
>       "type": "string"
>     }
>   },
>   "description": "How the server runs and where its store is.",
>   "properties": {
>     "host": {
>       "default": "localhost",
>       "title": "Host",
>       "type": "string"
>     },
>     "port": {
>       "default": 21000,
>       "maximum": 65535,
>       "minimum": 1,
>       "title": "Port",
>       "type": "integer"
>     },
>     "log_level": {
>       "$ref": "#/$defs/LogLevel",
>       "default": "info"
>     },
>     "tls_cert_file": {
>       "format": "file-path",
>       "title": "Tls Cert File",
>       "type": "string"
>     },
>     "tls_key_file": {
>       "format": "file-path",
>       "title": "Tls Key File",
>       "type": "string"
>     },
>     "hsts_enabled": {
>       "default": true,
>       "title": "Hsts Enabled",
>       "type": "boolean"
>     },
>     "forwarded_allow_ips": {
>       "default": "127.0.0.1",
>       "title": "Forwarded Allow Ips",
>       "type": "string"
>     },
>     "dashboard_dir": {
>       "anyOf": [
>         {
>           "format": "directory-path",
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Dashboard Dir"
>     },
>     "models_dir": {
>       "default": "/home/runner/work/aurelius-atlas/aurelius-atlas/libs/python/aurelius-atlas-core/aurelius_atlas_core/models",
>       "format": "path",
>       "title": "Models Dir",
>       "type": "string"
>     },
>     "typedef_refresh_seconds": {
>       "default": 5.0,
>       "minimum": 0,
>       "title": "Typedef Refresh Seconds",
>       "type": "number"
>     },
>     "delete_type": {
>       "default": "soft",
>       "enum": [
>         "soft",
>         "hard"
>       ],
>       "title": "Delete Type",
>       "type": "string"
>     },
>     "delete_type_override": {
>       "default": false,
>       "title": "Delete Type Override",
>       "type": "boolean"
>     },
>     "tasks_enabled": {
>       "default": true,
>       "title": "Tasks Enabled",
>       "type": "boolean"
>     },
>     "task_poll_seconds": {
>       "default": 10.0,
>       "exclusiveMinimum": 0,
>       "title": "Task Poll Seconds",
>       "type": "number"
>     },
>     "revision": {
>       "default": "UNKNOWN",
>       "title": "Revision",
>       "type": "string"
>     },
>     "elasticsearch_hosts": {
>       "items": {
>         "format": "uri",
>         "maxLength": 2083,
>         "minLength": 1,
>         "type": "string"
>       },
>       "minItems": 1,
>       "title": "Elasticsearch Hosts",
>       "type": "array"
>     },
>     "elasticsearch_username": {
>       "default": "elastic",
>       "title": "Elasticsearch Username",
>       "type": "string"
>     },
>     "elasticsearch_password": {
>       "format": "password",
>       "title": "Elasticsearch Password",
>       "type": "string",
>       "writeOnly": true
>     },
>     "elasticsearch_ca_certs": {
>       "format": "file-path",
>       "title": "Elasticsearch Ca Certs",
>       "type": "string"
>     },
>     "otel_token_url": {
>       "anyOf": [
>         {
>           "format": "uri",
>           "maxLength": 2083,
>           "minLength": 1,
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Otel Token Url"
>     },
>     "otel_client_id": {
>       "default": "otel-atlas-server",
>       "title": "Otel Client Id",
>       "type": "string"
>     },
>     "otel_client_secret": {
>       "anyOf": [
>         {
>           "format": "password",
>           "type": "string",
>           "writeOnly": true
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Otel Client Secret"
>     },
>     "otel_endpoint": {
>       "default": "https://localhost:4319",
>       "title": "Otel Endpoint",
>       "type": "string"
>     },
>     "otel_ca_file": {
>       "anyOf": [
>         {
>           "format": "file-path",
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Otel Ca File"
>     }
>   },
>   "required": [
>     "tls_cert_file",
>     "tls_key_file",
>     "elasticsearch_hosts",
>     "elasticsearch_password",
>     "elasticsearch_ca_certs"
>   ],
>   "title": "ServerSettings",
>   "type": "object"
> }
> ```
>
> Config:
>
> - `env_prefix`: `ENV_PREFIX`
> - `frozen`: `True`
> - `extra`: `ignore`
>
> Fields:
>
> - `host` (`str`)
> - `port` (`int`)
> - `log_level` (`LogLevel`)
> - `tls_cert_file` (`FilePath`)
> - `tls_key_file` (`FilePath`)
> - `hsts_enabled` (`bool`)
> - `forwarded_allow_ips` (`str`)
> - `dashboard_dir` (`DirectoryPath | None`)
> - `models_dir` (`Path`)
> - `typedef_refresh_seconds` (`float`)
> - `delete_type` (`Literal['soft', 'hard']`)
> - `delete_type_override` (`bool`)
> - `tasks_enabled` (`bool`)
> - `task_poll_seconds` (`float`)
> - `revision` (`str`)
> - `elasticsearch_hosts` (`list[HttpUrl]`)
> - `elasticsearch_username` (`str`)
> - `elasticsearch_password` (`SecretStr`)
> - `elasticsearch_ca_certs` (`FilePath`)
> - `otel_token_url` (`HttpUrl | None`)
> - `otel_client_id` (`str`)
> - `otel_client_secret` (`SecretStr | None`)
> - `otel_endpoint` (`str`)
> - `otel_ca_file` (`FilePath | None`)
>
> ### dashboard\_dir
>
> ```
> dashboard_dir: DirectoryPath | None = None
> ```
>
> The built dashboards: `dashboardv2` at its root and `dashboardv3` in `n/`; None serves the API only (DSH-04).
>
> ### delete\_type
>
> ```
> delete_type: Literal['soft', 'hard'] = 'soft'
> ```
>
> How entities are deleted unless a request chooses: `atlas.DeleteHandlerV1.impl` (EDL-04, DD-059).
>
> ### delete\_type\_override
>
> ```
> delete_type_override: bool = False
> ```
>
> Whether a request's `deleteType` chooses: `atlas.rest.enable.delete.type.override` (EDL-04, DD-059).
>
> ### elasticsearch\_ca\_certs
>
> ```
> elasticsearch_ca_certs: FilePath
> ```
>
> PEM file with the certificate authority of the Elasticsearch server certificate.
>
> ### elasticsearch\_hosts
>
> ```
> elasticsearch_hosts: list[HttpUrl]
> ```
>
> Base URLs of the Elasticsearch nodes, as a JSON list: `["https://localhost:9200"]`.
>
> ### elasticsearch\_password
>
> ```
> elasticsearch_password: SecretStr
> ```
>
> Password for the store; never shown in logs.
>
> ### elasticsearch\_username
>
> ```
> elasticsearch_username: str = 'elastic'
> ```
>
> User for the store.
>
> ### forwarded\_allow\_ips
>
> ```
> forwarded_allow_ips: str = '127.0.0.1'
> ```
>
> Which peers may rewrite the client address through `X-Forwarded-For` (SRV-10, DD-238), passed to uvicorn. The default trusts only the loopback; behind a proxy the arrangement names the proxy network, so the access log and OTel peer attributes key on the browser's address, not the proxy's. The rate limit itself lives at the webapp's nginx edge, not here (SRV-09, DD-238).
>
> ### host
>
> ```
> host: str = 'localhost'
> ```
>
> The interface to listen on; the container image sets `0.0.0.0`.
>
> ### hsts\_enabled
>
> ```
> hsts_enabled: bool = True
> ```
>
> Whether responses carry `Strict-Transport-Security` (SRV-08, DD-236). The image ships True; the dev arrangement turns it off so a browser that visited the mkcert server is not pinned to HTTPS on the plaintext dev surfaces (ADR 039's named relaxations).
>
> ### log\_level
>
> ```
> log_level: LogLevel = 'info'
> ```
>
> The lowest level of log record the server and uvicorn emit.
>
> ### model\_config
>
> ```
> model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra='ignore')
> ```
>
> ### models\_dir
>
> ```
> models_dir: Path = BUILTIN_MODELS_DIR
> ```
>
> The models loaded at start-up: by default `addons/models` of Apache Atlas 2.4.0; a missing directory loads none (MDL-01, MDL-16, DD-032).
>
> ### otel\_ca\_file
>
> ```
> otel_ca_file: FilePath | None = None
> ```
>
> PEM CA verifying the collector's TLS for the OTLP export; unset uses the system trust store (the dev stack's mkcert CA is not system-wide).
>
> ### otel\_client\_id
>
> ```
> otel_client_id: str = 'otel-atlas-server'
> ```
>
> The ingest realm client the server mints for (7.18, DD-196).
>
> ### otel\_client\_secret
>
> ```
> otel_client_secret: SecretStr | None = None
> ```
>
> The secret of `otel_client_id`; never shown in logs.
>
> ### otel\_endpoint
>
> ```
> otel_endpoint: str = 'https://localhost:4319'
> ```
>
> The collector's per-service-leg HTTP base for the OTLP export (7.18, DD-196); the dev compose overrides with the service DNS name.
>
> ### otel\_token\_url
>
> ```
> otel_token_url: HttpUrl | None = None
> ```
>
> The issuer's token endpoint for the OTLP ingest credential (7.18, DD-196): with `otel_client_secret` set, the server exports OTLP through the app-owned pipeline (the collector's per-service leg accepts only client-credentials JWTs); unset, the server exports no OTLP (console only). The OTel env vars (`OTEL_EXPORTER_OTLP_*`) are deliberately not read: the 60s dev token cannot ride a static header (DD-196).
>
> ### port
>
> ```
> port: int = DEFAULT_PORT
> ```
>
> The port to listen on (SRV-03).
>
> ### revision
>
> ```
> revision: str = 'UNKNOWN'
> ```
>
> The source revision the server was built from, reported by `admin/version` (ADM-01).
>
> ### task\_poll\_seconds
>
> ```
> task_poll_seconds: float = 10.0
> ```
>
> How often the worker looks for tasks other processes recorded or left behind (DD-080).
>
> ### tasks\_enabled
>
> ```
> tasks_enabled: bool = True
> ```
>
> Whether propagation is deferred to tasks a worker runs after the request: `atlas.tasks.enabled` (TSK-02, DD-081).
>
> ### tls
>
> ```
> tls: tuple[Path, Path]
> ```
>
> The certificate and key to serve HTTPS with (SRV-03, SRV-06, DD-234).
>
> ### tls\_cert\_file
>
> ```
> tls_cert_file: FilePath
> ```
>
> PEM certificate to serve HTTPS with (SRV-06, DD-234): required — the server never serves plaintext, the way the store's password is required (SRV-01, SRV-02).
>
> ### tls\_key\_file
>
> ```
> tls_key_file: FilePath
> ```
>
> PEM private key of `tls_cert_file` (SRV-06).
>
> ### typedef\_refresh\_seconds
>
> ```
> typedef_refresh_seconds: float = 5.0
> ```
>
> How long the server answers from its type registry before it checks for another process's type change (TDS-13, DD-029).
>
> ### store\_settings
>
> ```
> store_settings() -> StoreSettings
> ```
>
> The settings of the Elasticsearch store.

## Design

The technology-specific detail of how the server runs. The properties it must keep are in the architecture: [Configuration Management](<https://aureliusenterprise.github.io/feat-chart-digest-pinning-chart-signing/architecture/platform/delivery/configuration-management/index.md>) (ADR 018), [Components &amp; Interfaces](<https://aureliusenterprise.github.io/feat-chart-digest-pinning-chart-signing/architecture/platform/components-and-interfaces/index.md>).

**Settings.** Read once at start-up into a frozen `ServerSettings`; a validation failure (missing key, bad scheme, missing TLS material) stops start-up with a message naming the variable (SRV-01, SRV-02, SRV-06). All names carry the `AURELIUS_ATLAS_SERVER_` prefix. What a deployment must supply, with no defaults:

| Variable | Purpose |
| --- | --- |
| `..._ELASTICSEARCH_HOSTS` | JSON list of store node URLs, e.g. `["https://es-0:9200"]` — `https` only |
| `..._ELASTICSEARCH_PASSWORD` | Store password — a `SecretStr`, never shown in logs |
| `..._ELASTICSEARCH_CA_CERTS` | PEM CA of the store certificate; the store link is https-only (ADR 039) |
| `..._TLS_CERT_FILE` + `..._TLS_KEY_FILE` | PEM pair for serving HTTPS: both required — the server never serves plaintext (SRV-06, DD-234) |

With defaults: `HOST` (`0.0.0.0` in the image), `PORT` (21000, Atlas's port — kept so existing clients find the catalogue where Atlas was, ADR 046), `LOG_LEVEL`, `REVISION` (reported by `admin/version`, ADM-01), `HSTS_ENABLED` (true — the dev arrangement sets it false, SRV-08/DD-236), `DASHBOARD_DIR` (None serves the API only, DSH-04), `MODELS_DIR` (default: the vendored Atlas 2.4.0 `addons/models`, MDL-16/DD-032), `TYPEDEF_REFRESH_SECONDS` (5.0 — how long the server answers from its type registry before checking for another process's type change, TDS-13/DD-029).

> [!WARNING]
>
> **The server does not start without TLS material**
>
> `TLS_CERT_FILE` and `TLS_KEY_FILE` are required settings — there is no plaintext mode (SRV-06, DD-234, superseding the both-or-neither rule of SRV-03). A container that mounts no material exits with a message naming the missing variable; this is the design working, not a broken image. The image's `ENV` names where the pair lives (`/certs/server.pem`, `/certs/server-key.pem` — DD-216's stack-owned mount).

**The image** (`apps/aurelius-atlas-server/Dockerfile`: hardened base, runs as `nonroot`) bakes in the production defaults — listen on `0.0.0.0:21000`, dashboards served from `/application/dashboard` — and a liveness healthcheck against `/api/atlas/admin/liveness` over HTTPS, verifying the served certificate (SRV-06). Liveness is the probe a restart decision uses; readiness also fails while the store is away (DD-016).

**Security headers.** Every answer carries them (SRV-08, DD-236): `security_headers.py` stamps the JSON API with no-store/nosniff/framing-closed headers and a documents-free CSP, the dashboards with a same-origin CSP (DV-86) and immutable caching on bust-versioned assets, and HSTS when `HSTS_ENABLED`.

**Parity scenarios.** `scenarios/<resource>/*.scenario.yaml` state each expectation as Atlas's own answer — e.g. `scenarios/admin/version.scenario.yaml` expects `Version: "2.4.0"`, `Name: apache-atlas`, the exact content type — each cited to the Java source that produces it. Build-varying fields are marked volatile; the two places Aurelius Atlas must answer differently (name, description) carry a `deviations: DV-03` entry. Anything else that differs fails the scenario (ADR 052).

## Documentation

## aurelius\_atlas\_server.app

The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016).

Functions:

- **`create_app`** –

  Build the application.
- **`mount_dashboards`** –

  Serve `dashboardv3` at `/n/` and `dashboardv2` at `/` (DSH-01, DSH-02; DD-018).

Attributes:

- **`DASHBOARD_V3_DIR`** –

  Where `dashboardv3` sits in the dashboard directory, and below which path it is served.
- **`LOGGER`** –
- **`NAME`** –

### DASHBOARD\_V3\_DIR

```
DASHBOARD_V3_DIR = 'n'
```

Where `dashboardv3` sits in the dashboard directory, and below which path it is served.

### LOGGER

```
LOGGER = logging.getLogger(NAME)
```

### NAME

```
NAME = 'aurelius-atlas-server'
```

### create\_app

```
create_app(settings: ServerSettings, store: ElasticsearchStore | None = None) -> FastAPI
```

Build the application.

Parameters:

- #### **`settings`**

  (`ServerSettings`) –

  The server's settings.
- #### **`store`**

  (`ElasticsearchStore | None`, default: `None` ) –

  The store to use; by default one built from the settings. It is opened when the application starts, which fails when the store cannot be opened (SRV-02), and closed when it stops.

The type registry is loaded from the stored type definitions when the application starts (TDS-12), then the models are loaded and patched (MDL-16); the entity store's indices are created and interrupted writes recovered (ENS-01, ENS-07), and the audit index (DD-082). With tasks enabled, a worker runs the tasks requests record (TSK-04, DD-080).

### mount\_dashboards

```
mount_dashboards(app: FastAPI, directory: Path) -> None
```

Serve `dashboardv3` at `/n/` and `dashboardv2` at `/` (DSH-01, DSH-02; DD-018).

Mounted after the API routes, so the API takes precedence (DSH-03).

## aurelius\_atlas\_server.errors

The body Atlas errors are answered with (SRV-04, SRV-05, SRV-07), as `AtlasBaseExceptionMapper` does.

The errors themselves live in `aurelius_atlas_model.errors` (DD-023) and are re-exported here. 5xx bodies are opaque: the cause is logged, and the trace id rides along for correlation (DD-235, DV-85).

Classes:

- **`AtlasJSONResponse`** –

  A JSON response with the Atlas media type (SRV-05), written by Atlas's JSON codec (VAL-01, DD-039).

Functions:

- **`atlas_error_handler`** –

  Answer an `AtlasError` with its status and `{"errorCode", "errorMessage"[, "errorCause"]}` (SRV-04).

Attributes:

- **`ATLAS_JSON_MEDIA_TYPE`** –

  The media type of Atlas JSON responses (`Servlets.JSON_MEDIA_TYPE`).

### ATLAS\_JSON\_MEDIA\_TYPE

```
ATLAS_JSON_MEDIA_TYPE = 'application/json; charset=UTF-8'
```

The media type of Atlas JSON responses (`Servlets.JSON_MEDIA_TYPE`).

### LOGGER

```
LOGGER = logging.getLogger(__name__)
```

### \_\_all\_\_

```
__all__ = ['ATLAS_JSON_MEDIA_TYPE', 'AtlasError', 'AtlasErrorCode', 'AtlasJSONResponse', 'atlas_error_handler']
```

### AtlasJSONResponse

Bases: `JSONResponse`

A JSON response with the Atlas media type (SRV-05), written by Atlas's JSON codec (VAL-01, DD-039).

Methods:

- **`render`** –

  Decimals keep their digits and dates are epoch milliseconds, as Jackson writes them.

Attributes:

- **`media_type`** –

#### media\_type

```
media_type = ATLAS_JSON_MEDIA_TYPE
```

#### render

```
render(content: Any) -> bytes
```

Decimals keep their digits and dates are epoch milliseconds, as Jackson writes them.

### atlas\_error\_handler

```
atlas_error_handler(_request: Request, error: Exception) -> AtlasJSONResponse
```

Answer an `AtlasError` with its status and `{"errorCode", "errorMessage"[, "errorCause"]}` (SRV-04).

A server error (5xx) keeps Atlas's two-field shape and adds the trace id of the request as `requestId` (SRV-07, DD-235): the cause's text goes to the log, never to the wire, so a wrapped store or transport failure cannot leak internals; the id ties the response to the logged stack and the trace. A client error (4xx) echoes the cause as Atlas does (SRV-04) — there the cause is the request's own defect, not server internals.

## aurelius\_atlas\_server.routes.admin

The admin endpoints of `AdminResource`: version, status, session, liveness, readiness, patches, purge, tasks.

ADM-01 to ADM-05, ENS-10, EDL-01 to EDL-08, TSK-06.

Functions:

- **`csrf_token`** –

  A new random token of 20 letters and digits, as `AdminResource.getUserProfile` makes one.
- **`delete_task`** –

  `deleteTask`: remove the tasks of the `guids` given (TSK-06).
- **`get_liveness`** –

  Whether the server runs (ADM-03).
- **`get_patches`** –

  `getAtlasPatches`: the typedef patch records, sorted by id (ENS-10, DV-14).
- **`get_readiness`** –

  Whether the server can serve requests: its store must be healthy (ADM-04).
- **`get_session`** –

  The user interface settings and the user of this session; no user until 6.1 (ADM-05, DV-04).
- **`get_status`** –

  The service state, which is always `ACTIVE` while the server runs (ADM-02).
- **`get_task_status`** –

  `getTaskStatus`: the tasks of the `guids` given that exist, in their order, else every task (TSK-06).
- **`get_version`** –

  The server's name, release and revision (ADM-01, DV-03).
- **`purge_by_ids`** –

  `purgeByIds`: remove the `DELETED` entities of a JSON array of GUIDs (EDL-01 to EDL-03).
- **`time_zones`** –

  The IANA time zone ids, sorted (DV-05).

Attributes:

- **`ACTIVE`** –

  The only service state: Aurelius Atlas has no high-availability states.
- **`ADMIN`** –
- **`CSRF_TOKEN_LENGTH`** –
- **`DESCRIPTION`** –

  What `admin/version` reports instead of Apache Atlas's name and description (DV-03).
- **`LIVE`** –
- **`NAME`** –
- **`NOT_READY`** –
- **`NO_CONTENT`** –
- **`READY`** –
- **`UI_SETTINGS`** (`dict[str, Any]`) –

  The session's settings at the defaults of Atlas 2.4.0 (`AdminResource`, `AtlasCSRFPreventionFilter`,

### ACTIVE

```
ACTIVE = 'ACTIVE'
```

The only service state: Aurelius Atlas has no high-availability states.

### ADMIN

```
ADMIN = APIRouter(prefix='/api/atlas/admin', tags=['Admin'])
```

### CSRF\_TOKEN\_LENGTH

```
CSRF_TOKEN_LENGTH = 20
```

### DESCRIPTION

```
DESCRIPTION = 'Apache Atlas 2.4.0 REST API on Elasticsearch'
```

What `admin/version` reports instead of Apache Atlas's name and description (DV-03).

### LIVE

```
LIVE = 'Service is live'
```

### NAME

```
NAME = 'aurelius-atlas'
```

### NOT\_READY

```
NOT_READY = 'Service not ready to accept client requests'
```

### NO\_CONTENT

```
NO_CONTENT = 204
```

### READY

```
READY = 'Service is ready to accept requests'
```

### UI\_SETTINGS

```
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
```

The session's settings at the defaults of Atlas 2.4.0 (`AdminResource`, `AtlasCSRFPreventionFilter`, `AtlasConfiguration`).

### csrf\_token

```
csrf_token() -> str
```

A new random token of 20 letters and digits, as `AdminResource.getUserProfile` makes one.

### delete\_task

```
delete_task(request: Request) -> Response
```

`deleteTask`: remove the tasks of the `guids` given (TSK-06).

### get\_liveness

```
get_liveness() -> str
```

Whether the server runs (ADM-03).

### get\_patches

```
get_patches(request: Request) -> dict[str, Any]
```

`getAtlasPatches`: the typedef patch records, sorted by id (ENS-10, DV-14).

### get\_readiness

```
get_readiness(request: Request) -> str
```

Whether the server can serve requests: its store must be healthy (ADM-04).

Raises:

- `AtlasError` –

  `INTERNAL_ERROR` when the store is not healthy.

### get\_session

```
get_session(request: Request) -> dict[str, Any]
```

The user interface settings and the user of this session; no user until 6.1 (ADM-05, DV-04).

`atlas.tasks.enabled` is the server's `tasks_enabled` setting (DD-081).

### get\_status

```
get_status() -> dict[str, str]
```

The service state, which is always `ACTIVE` while the server runs (ADM-02).

### get\_task\_status

```
get_task_status(request: Request) -> AtlasJSONResponse
```

`getTaskStatus`: the tasks of the `guids` given that exist, in their order, else every task (TSK-06).

### get\_version

```
get_version(request: Request) -> dict[str, str]
```

The server's name, release and revision (ADM-01, DV-03).

### purge\_by\_ids

```
purge_by_ids(request: Request, store: Store, body: Body) -> AtlasJSONResponse
```

`purgeByIds`: remove the `DELETED` entities of a JSON array of GUIDs (EDL-01 to EDL-03).

Raises:

- `AtlasError` –

  `BAD_REQUEST` for a body that is not an array of strings (DV-10).

### time\_zones

```
time_zones() -> list[str]
```

The IANA time zone ids, sorted (DV-05).
