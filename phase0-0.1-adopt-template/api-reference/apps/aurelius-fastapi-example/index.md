# aurelius-fastapi-example

This is an example FastAPI application.

## Usage

Run the following command to start the application locally:

```
python -m aurelius_fastapi_example
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
> ## aurelius\_fastapi\_example.models.Settings
>
> Bases: `BaseSettings`, `Hashable`
>
> Application configuration settings.
>
> **Show JSON schema:**
>
> ```
> {
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
>     "auth_server_url": {
>       "description": "The base URL of the authentication server.",
>       "format": "uri",
>       "maxLength": 2083,
>       "minLength": 1,
>       "title": "Auth Server Url",
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
>       "default": "info",
>       "description": "The logging level for the application.",
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
>       "title": "Log Level",
>       "type": "string"
>     },
>     "port": {
>       "default": 8000,
>       "description": "The port to bind the server to.",
>       "title": "Port",
>       "type": "integer"
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
> - `frozen`: `True`
>
> Fields:
>
> - `environment` (`str`)
> - `auth_fail_max` (`int`)
> - `auth_realm_name` (`str`)
> - `auth_reset_timeout` (`int`)
> - `db_fail_max` (`int`)
> - `auth_server_url` (`HttpUrl`)
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
> - `log_level` (`LevelName`)
> - `port` (`int`)
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
> log_level: LevelName = 'info'
> ```
>
> The logging level for the application.
>
> ### model\_config
>
> ```
> model_config = SettingsConfigDict(frozen=True)
> ```
>
> ### port
>
> ```
> port: int = 8000
> ```
>
> The port to bind the server to.

You can set configuration options using environment variables or CLI arguments.

> [!TIP]
>
> **View CLI Arguments**
>
> To see available CLI options, run:
>
> ```
> python -m aurelius_fastapi_example --help
> ```
