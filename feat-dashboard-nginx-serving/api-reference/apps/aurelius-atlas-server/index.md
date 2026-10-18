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
>       "title": "Tls Cert File"
>     },
>     "tls_key_file": {
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
>       "title": "Tls Key File"
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
>     "auth_issuer": {
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
>       "title": "Auth Issuer"
>     },
>     "auth_client_id": {
>       "default": "aurelius-atlas",
>       "title": "Auth Client Id",
>       "type": "string"
>     },
>     "auth_client_secret": {
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
>       "title": "Auth Client Secret"
>     },
>     "auth_redirect_uri": {
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
>       "title": "Auth Redirect Uri"
>     },
>     "auth_ca_file": {
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
>       "title": "Auth Ca File"
>     },
>     "auth_session_idle_seconds": {
>       "anyOf": [
>         {
>           "minimum": 60,
>           "type": "integer"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Auth Session Idle Seconds"
>     }
>   },
>   "required": [
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
> - `tls_cert_file` (`FilePath | None`)
> - `tls_key_file` (`FilePath | None`)
> - `models_dir` (`Path`)
> - `typedef_refresh_seconds` (`float`)
> - `revision` (`str`)
> - `elasticsearch_hosts` (`list[HttpUrl]`)
> - `elasticsearch_username` (`str`)
> - `elasticsearch_password` (`SecretStr`)
> - `elasticsearch_ca_certs` (`FilePath`)
> - `auth_issuer` (`HttpUrl | None`)
> - `auth_client_id` (`str`)
> - `auth_client_secret` (`SecretStr | None`)
> - `auth_redirect_uri` (`HttpUrl | None`)
> - `auth_ca_file` (`FilePath | None`)
> - `auth_session_idle_seconds` (`int | None`)
>
> Validators:
>
> - `_tls_pair`
> - `_auth_trio`
>
> ### auth\_ca\_file
>
> ```
> auth_ca_file: FilePath | None = None
> ```
>
> PEM file with the certificate authority to verify the issuer's TLS with; by default the system store.
>
> ### auth\_client\_id
>
> ```
> auth_client_id: str = 'aurelius-atlas'
> ```
>
> The client this server registers as at the issuer (AUTH-06), its audience (AUTH-03).
>
> ### auth\_client\_secret
>
> ```
> auth_client_secret: SecretStr | None = None
> ```
>
> The secret of `auth_client_id`; the confidential client proves itself at the token endpoints.
>
> ### auth\_enabled
>
> ```
> auth_enabled: bool
> ```
>
> Whether the server demands a principal (AUTH-01): an issuer is configured.
>
> ### auth\_issuer
>
> ```
> auth_issuer: HttpUrl | None = None
> ```
>
> The OIDC issuer that vouches for users, e.g. `https://keycloak.localhost:8443/realms/master`; with it unset the server answers without authentication (AUTH-01, DV-04).
>
> ### auth\_redirect\_uri
>
> ```
> auth_redirect_uri: HttpUrl | None = None
> ```
>
> The registered redirect URI of the browser flow — this deployment's `/api/atlas/auth/callback`.
>
> ### auth\_session\_idle\_seconds
>
> ```
> auth_session_idle_seconds: int | None = None
> ```
>
> How long a session lives without use; reported to the dashboard as `atlas.session.timeout.secs` when set (ADM-07).
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
> ### host
>
> ```
> host: str = 'localhost'
> ```
>
> The interface to listen on; the container image sets `0.0.0.0`.
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
> ### tls
>
> ```
> tls: tuple[Path, Path] | None
> ```
>
> The certificate and key to serve HTTPS with, or None for plain HTTP.
>
> ### tls\_cert\_file
>
> ```
> tls_cert_file: FilePath | None = None
> ```
>
> PEM certificate to serve HTTPS with; requires `tls_key_file` (SRV-03).
>
> ### tls\_key\_file
>
> ```
> tls_key_file: FilePath | None = None
> ```
>
> PEM private key of `tls_cert_file`.
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

## Documentation

## aurelius\_atlas\_server.app

The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016).

Functions:

- **`create_app`** –

  Build the application.

Attributes:

- **`LOGGER`** –
- **`NAME`** –

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

The type registry is loaded from the stored type definitions when the application starts (TDS-12), then the models are loaded and patched (MDL-16).

## aurelius\_atlas\_server.errors

The body Atlas errors are answered with (SRV-04, SRV-05), as `AtlasBaseExceptionMapper` does.

The errors themselves live in `aurelius_atlas_model.errors` (DD-023) and are re-exported here.

Classes:

- **`AtlasJSONResponse`** –

  A JSON response with the Atlas media type (SRV-05).

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

A JSON response with the Atlas media type (SRV-05).

Attributes:

- **`media_type`** –

#### media\_type

```
media_type = ATLAS_JSON_MEDIA_TYPE
```

### atlas\_error\_handler

```
atlas_error_handler(_request: Request, error: Exception) -> AtlasJSONResponse
```

Answer an `AtlasError` with its status and `{"errorCode", "errorMessage"[, "errorCause"]}` (SRV-04).

## aurelius\_atlas\_server.routes.admin

The admin endpoints of `AdminResource`: version, status, session, liveness and readiness (ADM-01 to ADM-05).

Functions:

- **`get_liveness`** –

  Whether the server runs (ADM-03).
- **`get_readiness`** –

  Whether the server can serve requests: its store must be healthy (ADM-04).
- **`get_session`** –

  The user interface settings and the user of this session (ADM-05, ADM-06).
- **`get_status`** –

  The service state, which is always `ACTIVE` while the server runs (ADM-02).
- **`get_version`** –

  The server's name, release and revision (ADM-01, DV-03).
- **`time_zones`** –

  The IANA time zone ids, sorted (DV-05).

Attributes:

- **`ACTIVE`** –

  The only service state: Aurelius Atlas has no high-availability states.
- **`ADMIN`** –
- **`DESCRIPTION`** –

  What `admin/version` reports instead of Apache Atlas's name and description (DV-03).
- **`LIVE`** –
- **`NAME`** –
- **`NOT_READY`** –
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

### get\_liveness

```
get_liveness() -> str
```

Whether the server runs (ADM-03).

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

The user interface settings and the user of this session (ADM-05, ADM-06).

Without authentication the user is nobody (DV-04). With it, `userName` and `groups` name the principal the guard resolved (ADM-06) and `_csrfToken` is the session's token, minted here at the first call and kept for the session's life (CRS-02); a bearer-authenticated call has no session and reports a fresh token, as Atlas does for a request whose container session is new.

### get\_status

```
get_status() -> dict[str, str]
```

The service state, which is always `ACTIVE` while the server runs (ADM-02).

### get\_version

```
get_version(request: Request) -> dict[str, str]
```

The server's name, release and revision (ADM-01, DV-03).

### time\_zones

```
time_zones() -> list[str]
```

The IANA time zone ids, sorted (DV-05).
