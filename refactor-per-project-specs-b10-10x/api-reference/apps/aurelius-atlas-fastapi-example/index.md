# aurelius-atlas-fastapi-example

This is an example FastAPI application.

## Usage

Run the following command to start the application locally:

```
python -m aurelius_atlas_fastapi_example
```

This launches a Uvicorn server at [http://127.0.0.1:8000](<http://127.0.0.1:8000>).

## Deployment

Deploy using the provided Dockerfile. By default, the app listens on [http://0.0.0.0:8000](<http://0.0.0.0:8000>).

## Configuration

Configuration is managed via the `Settings` model:

> [!NOTE]
>
> **Settings**
>
> ## aurelius\_atlas\_fastapi\_example.models.Settings
>
> Bases: `BaseSettings`, `Hashable`
>
> Application configuration settings.
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
>         "notice",
>         "warn",
>         "warning",
>         "error",
>         "fatal"
>       ],
>       "type": "string"
>     }
>   },
>   "additionalProperties": false,
>   "description": "Application configuration settings.",
>   "properties": {
>     "environment": {
>       "default": "production",
>       "description": "The environment in which the application is running. Set to 'development' for local testing.",
>       "title": "Environment",
>       "type": "string"
>     },
>     "auth_fail_max": {
>       "default": 5,
>       "description": "The maximum number of failed authentication attempts before triggering the circuit breaker.",
>       "title": "Auth Fail Max",
>       "type": "integer"
>     },
>     "auth_realm_name": {
>       "description": "The name of the authentication realm.",
>       "title": "Auth Realm Name",
>       "type": "string"
>     },
>     "auth_reset_timeout": {
>       "default": 60,
>       "description": "The timeout in seconds to wait before resetting the authentication circuit breaker.",
>       "title": "Auth Reset Timeout",
>       "type": "integer"
>     },
>     "db_fail_max": {
>       "default": 5,
>       "description": "The maximum number of failed database operations before triggering the circuit breaker.",
>       "title": "Db Fail Max",
>       "type": "integer"
>     },
>     "auth_client_id": {
>       "anyOf": [
>         {
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "description": "The client id this application authenticates as; seeds the default auth_audience.",
>       "title": "Auth Client Id"
>     },
>     "auth_server_url": {
>       "description": "The base URL of the authentication server.",
>       "format": "uri",
>       "maxLength": 2083,
>       "minLength": 1,
>       "title": "Auth Server Url",
>       "type": "string"
>     },
>     "auth_audience": {
>       "description": "The audience this API accepts: a token is authorized when this value appears in its 'azp' claim or 'aud' claim list. Defaults to AURELIUS_ATLAS_FASTAPI_AUTH_CLIENT_ID; required outside development mode.",
>       "title": "Auth Audience",
>       "type": "string"
>     },
>     "auth_write_role": {
>       "default": "",
>       "description": "The role mutating endpoints (PUT/DELETE) require: accepted when it appears in the token's 'realm_access.roles' or in the 'resource_access.<auth_audience>.roles' list (client roles are namespaced per client; roles of other clients never satisfy the gate). Empty disables the authorization check; required outside development mode so a deployment cannot ship authentication without authorization by forgetting the variable.",
>       "title": "Auth Write Role",
>       "type": "string"
>     },
>     "auto_create_schema": {
>       "description": "Automatically create the database schema. Enabled by default in development mode.",
>       "title": "Auto Create Schema",
>       "type": "boolean"
>     },
>     "cdc_disconnect_poll_timeout": {
>       "default": 5.0,
>       "description": "The timeout in seconds to wait for SSE notifications before re-checking whether the client has disconnected.",
>       "title": "Cdc Disconnect Poll Timeout",
>       "type": "number"
>     },
>     "cdc_shutdown_join_timeout": {
>       "default": 2.0,
>       "description": "The timeout in seconds to wait for the CDC polling thread to stop during shutdown.",
>       "title": "Cdc Shutdown Join Timeout",
>       "type": "number"
>     },
>     "cdc_subscriber_queue_maxsize": {
>       "default": 1000,
>       "description": "The maximum number of buffered CDC notifications per SSE subscriber queue.",
>       "title": "Cdc Subscriber Queue Maxsize",
>       "type": "integer"
>     },
>     "db_reset_timeout": {
>       "default": 60,
>       "description": "The timeout in seconds to wait before resetting the database circuit breaker.",
>       "title": "Db Reset Timeout",
>       "type": "integer"
>     },
>     "database_driver": {
>       "default": "postgresql+psycopg",
>       "description": "The driver for the database.",
>       "title": "Database Driver",
>       "type": "string"
>     },
>     "database_host": {
>       "default": "localhost",
>       "description": "The host for the database.",
>       "title": "Database Host",
>       "type": "string"
>     },
>     "database_name": {
>       "default": "postgres",
>       "description": "The name of the database.",
>       "title": "Database Name",
>       "type": "string"
>     },
>     "database_password": {
>       "description": "The password for the database.",
>       "format": "password",
>       "title": "Database Password",
>       "type": "string",
>       "writeOnly": true
>     },
>     "database_port": {
>       "default": 5432,
>       "description": "The port for the database.",
>       "title": "Database Port",
>       "type": "integer"
>     },
>     "database_username": {
>       "default": "postgres",
>       "description": "The username for the database.",
>       "title": "Database Username",
>       "type": "string"
>     },
>     "host": {
>       "default": "127.0.0.1",
>       "description": "The host to bind the server to.",
>       "title": "Host",
>       "type": "string"
>     },
>     "log_level": {
>       "$ref": "#/$defs/LogLevel",
>       "default": "info",
>       "description": "The logging level for the application."
>     },
>     "port": {
>       "default": 8000,
>       "description": "The port to bind the server to.",
>       "title": "Port",
>       "type": "integer"
>     },
>     "auth_ca_file": {
>       "default": "",
>       "description": "PEM CA bundle used to verify the authentication server's TLS certificate. Empty uses the operating system default trust store.",
>       "title": "Auth Ca File",
>       "type": "string"
>     },
>     "database_sslmode": {
>       "default": "prefer",
>       "description": "PostgreSQL TLS mode (disable, prefer, require, verify-ca, verify-full). The development defaults set verify-full to match the TLS-only database.",
>       "title": "Database Sslmode",
>       "type": "string"
>     },
>     "database_sslrootcert": {
>       "default": "",
>       "description": "PEM CA bundle used to verify the database server's TLS certificate. Required for verify-ca and verify-full; ignored by libpq otherwise.",
>       "title": "Database Sslrootcert",
>       "type": "string"
>     },
>     "tls_cert_file": {
>       "default": "",
>       "description": "PEM certificate served by the application. Empty disables TLS on the server.",
>       "title": "Tls Cert File",
>       "type": "string"
>     },
>     "tls_key_file": {
>       "default": "",
>       "description": "PEM private key matching tls_cert_file. Required when TLS is enabled.",
>       "title": "Tls Key File",
>       "type": "string"
>     }
>   },
>   "required": [
>     "auth_realm_name",
>     "auth_server_url",
>     "database_password"
>   ],
>   "title": "Settings",
>   "type": "object"
> }
> ```
>
> Config:
>
> - `env_prefix`: `ENV_PREFIX`
> - `frozen`: `True`
>
> Fields:
>
> - `environment` (`str`)
> - `auth_fail_max` (`int`)
> - `auth_realm_name` (`str`)
> - `auth_reset_timeout` (`int`)
> - `db_fail_max` (`int`)
> - `auth_client_id` (`str | None`)
> - `auth_server_url` (`HttpUrl`)
> - `auth_audience` (`str`)
> - `auth_write_role` (`str`)
> - `auto_create_schema` (`bool`)
> - `cdc_disconnect_poll_timeout` (`float`)
> - `cdc_shutdown_join_timeout` (`float`)
> - `cdc_subscriber_queue_maxsize` (`int`)
> - `db_reset_timeout` (`int`)
> - `database_driver` (`str`)
> - `database_host` (`str`)
> - `database_name` (`str`)
> - `database_password` (`SecretStr`)
> - `database_port` (`int`)
> - `database_username` (`str`)
> - `host` (`str`)
> - `log_level` (`LogLevel`)
> - `port` (`int`)
> - `auth_ca_file` (`str`)
> - `database_sslmode` (`str`)
> - `database_sslrootcert` (`str`)
> - `tls_cert_file` (`str`)
> - `tls_key_file` (`str`)
>
> Validators:
>
> - `enforce_transport_security`
> - `enforce_auth_security`
>
> ### auth\_audience
>
> ```
> auth_audience: str
> ```
>
> The audience this API accepts: a token is authorized when this value appears in its 'azp' claim or 'aud' claim list. Defaults to AURELIUS\_ATLAS\_FASTAPI\_AUTH\_CLIENT\_ID; required outside development mode.
>
> ### auth\_ca\_file
>
> ```
> auth_ca_file: str = ''
> ```
>
> PEM CA bundle used to verify the authentication server's TLS certificate. Empty uses the operating system default trust store.
>
> ### auth\_client\_id
>
> ```
> auth_client_id: str | None = None
> ```
>
> The client id this application authenticates as; seeds the default auth\_audience.
>
> ### auth\_fail\_max
>
> ```
> auth_fail_max: int = 5
> ```
>
> The maximum number of failed authentication attempts before triggering the circuit breaker.
>
> ### auth\_realm\_name
>
> ```
> auth_realm_name: str
> ```
>
> The name of the authentication realm.
>
> ### auth\_reset\_timeout
>
> ```
> auth_reset_timeout: int = 60
> ```
>
> The timeout in seconds to wait before resetting the authentication circuit breaker.
>
> ### auth\_server\_url
>
> ```
> auth_server_url: HttpUrl
> ```
>
> The base URL of the authentication server.
>
> ### auth\_write\_role
>
> ```
> auth_write_role: str = ''
> ```
>
> The role mutating endpoints (PUT/DELETE) require: accepted when it appears in the token's 'realm\_access.roles' or in the 'resource\_access..roles' list (client roles are namespaced per client; roles of other clients never satisfy the gate). Empty disables the authorization check; required outside development mode so a deployment cannot ship authentication without authorization by forgetting the variable.
>
> ### auto\_create\_schema
>
> ```
> auto_create_schema: bool
> ```
>
> Automatically create the database schema. Enabled by default in development mode.
>
> ### cdc\_disconnect\_poll\_timeout
>
> ```
> cdc_disconnect_poll_timeout: float = 5.0
> ```
>
> The timeout in seconds to wait for SSE notifications before re-checking whether the client has disconnected.
>
> ### cdc\_shutdown\_join\_timeout
>
> ```
> cdc_shutdown_join_timeout: float = 2.0
> ```
>
> The timeout in seconds to wait for the CDC polling thread to stop during shutdown.
>
> ### cdc\_subscriber\_queue\_maxsize
>
> ```
> cdc_subscriber_queue_maxsize: int = 1000
> ```
>
> The maximum number of buffered CDC notifications per SSE subscriber queue.
>
> ### database\_driver
>
> ```
> database_driver: str = 'postgresql+psycopg'
> ```
>
> The driver for the database.
>
> ### database\_host
>
> ```
> database_host: str = 'localhost'
> ```
>
> The host for the database.
>
> ### database\_name
>
> ```
> database_name: str = 'postgres'
> ```
>
> The name of the database.
>
> ### database\_password
>
> ```
> database_password: SecretStr
> ```
>
> The password for the database.
>
> ### database\_port
>
> ```
> database_port: int = 5432
> ```
>
> The port for the database.
>
> ### database\_sslmode
>
> ```
> database_sslmode: str = 'prefer'
> ```
>
> PostgreSQL TLS mode (disable, prefer, require, verify-ca, verify-full). The development defaults set verify-full to match the TLS-only database.
>
> ### database\_sslrootcert
>
> ```
> database_sslrootcert: str = ''
> ```
>
> PEM CA bundle used to verify the database server's TLS certificate. Required for verify-ca and verify-full; ignored by libpq otherwise.
>
> ### database\_url
>
> ```
> database_url: URL
> ```
>
> Construct the database URL.
>
> ### database\_username
>
> ```
> database_username: str = 'postgres'
> ```
>
> The username for the database.
>
> ### db\_fail\_max
>
> ```
> db_fail_max: int = 5
> ```
>
> The maximum number of failed database operations before triggering the circuit breaker.
>
> ### db\_reset\_timeout
>
> ```
> db_reset_timeout: int = 60
> ```
>
> The timeout in seconds to wait before resetting the database circuit breaker.
>
> ### environment
>
> ```
> environment: str = 'production'
> ```
>
> The environment in which the application is running. Set to 'development' for local testing.
>
> ### host
>
> ```
> host: str = '127.0.0.1'
> ```
>
> The host to bind the server to.
>
> ### is\_development
>
> ```
> is_development: bool
> ```
>
> Check if the application is running in development mode.
>
> ### log\_level
>
> ```
> log_level: LogLevel = 'info'
> ```
>
> The logging level for the application.
>
> ### model\_config
>
> ```
> model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True)
> ```
>
> ### port
>
> ```
> port: int = 8000
> ```
>
> The port to bind the server to.
>
> ### tls\_cert\_file
>
> ```
> tls_cert_file: str = ''
> ```
>
> PEM certificate served by the application. Empty disables TLS on the server.
>
> ### tls\_key\_file
>
> ```
> tls_key_file: str = ''
> ```
>
> PEM private key matching tls\_cert\_file. Required when TLS is enabled.
>
> ### enforce\_auth\_security
>
> ```
> enforce_auth_security() -> Settings
> ```
>
> Fail fast when a non-development deployment misconfigures authentication or authorization.
>
> Two silent-downgrade paths are closed here:
>
> - A plaintext `auth_server_url` lets a network-path attacker serve a forged OpenID configuration / JWKS, which mints tokens this API would accept — the whole bearer-token scheme collapses. OAuth token endpoints elsewhere in the workspace are https-only for the same reason.
> - An empty `auth_audience` (no `AUTH_CLIENT_ID`, no explicit audience) would accept any token from the issuer, and an empty `auth_write_role` would authenticate every caller for mutating operations. Both must be explicit.
>
> ### enforce\_transport\_security
>
> ```
> enforce_transport_security() -> Settings
> ```
>
> Fail fast when a non-development deployment runs with unverified transport.
>
> The defaults (`database_sslmode="prefer"`, empty `tls_cert_file`) are convenient for local development, where the TLS material lives in the project `.env`. Outside development they must be set explicitly: otherwise a deployment that forgets the variables silently downgrades to opportunistic/unverified TLS — credentials and tokens over a channel a network-path attacker can read or impersonate.

You can set configuration options using environment variables or CLI arguments.

> [!TIP]
>
> **View CLI Arguments**
>
> To see available CLI options, run:
>
> ```
> python -m aurelius_atlas_fastapi_example --help
> ```
