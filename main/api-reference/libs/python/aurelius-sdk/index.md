# aurelius-sdk

This library provides common utilities for Aurelius projects.

## Installation

You can include `aurelius-sdk` in your project by adding it to your `pyproject.toml`:

```
dependencies = ["aurelius-sdk"]

[tool.uv.sources.aurelius-sdk]
workspace = true
```

Ensure the path points to the correct location of the `aurelius-sdk` library.

## Documentation

## aurelius\_sdk

Modules:

- **`aws`** –

  This module provides utilities for working with AWS services.
- **`encoding`** –
- **`events`** –
- **`logger`** –

  This module provides logging utilities for Aurelius applications.
- **`msal`** –

  This module provides authentication utilities for the Microsoft Identity Platform.
- **`postgresql`** –
- **`testing`** –

  This module provides testing utilities for Aurelius applications.

## aurelius\_sdk.aws

This module provides utilities for working with AWS services.

> [!NOTE]
>
> Please install the `aws` extra to use this module.

Functions:

- **`get_secret`** –

  Get the secret value from AWS Secrets Manager.

### get\_secret

```
get_secret(client: SecretsManagerClient, secret_name: str) -> str
```

Get the secret value from AWS Secrets Manager.

Parameters:

- #### **`client`**

  (`SecretsManagerClient`) –

  The Secrets Manager client.
- #### **`secret_name`**

  (`str`) –

  The name of the secret.

Returns:

- **`str`** ( `str` ) –

  The secret value.

## aurelius\_sdk.logger

This module provides logging utilities for Aurelius applications.

> [!NOTE]
>
> Please install the `logging` extra to use this module.

Functions:

- **`setup_logger`** –

  Set up logging for the application with a standardized log output format.

Attributes:

- **`DEFAULT_DATEFMT`** –
- **`DEFAULT_FMT`** –

### DEFAULT\_DATEFMT

```
DEFAULT_DATEFMT = '%Y-%m-%d %H:%M:%S'
```

### DEFAULT\_FMT

```
DEFAULT_FMT = '{asctime} {levelname:<8} [{name}] {message}'
```

### setup\_logger

```
setup_logger(level: int | str = INFO) -> None
```

Set up logging for the application with a standardized log output format.

This function configures the logging system to use the specified logging level, with a custom log format that includes the timestamp, log level, logger name, and log message. Log levels can be provided as either an integer or a string corresponding to standard logging levels.

- `CRITICAL`
- `ERROR`
- `WARNING`
- `INFO`
- `DEBUG`

Parameters:

- #### **`level`**

  (`int or str`, default: `INFO` ) –

  The logging level to set. Defaults to `logging.INFO`.

Examples:

Set up logging with the default level. This will log messages with a level of INFO and above.

```
>>> setup_logging()
```

Set up logging to show DEBUG-level messages (and above) by providing the logging level's integer value.

```
>>> setup_logging(logging.DEBUG)
```

Set up logging by specifying the logging level as a string. This is equivalent to the previous example.

```
>>> setup_logging("DEBUG")
```

## aurelius\_sdk.msal

This module provides authentication utilities for the Microsoft Identity Platform.

> [!NOTE]
>
> Please install the `azure` extra to use this module.

Classes:

- **`MSALOAuthTokenProvider`** –

  A class to handle OAuth authentication for the Microsoft Identity Platform.

### MSALOAuthTokenProvider

```
MSALOAuthTokenProvider(auth: ConfidentialClientApplication, scopes: list[str])
```

A class to handle OAuth authentication for the Microsoft Identity Platform.

This class implements the `httpx` authentication provider interface to add an OAuth token to HTTP requests.

Parameters:

- #### **`auth`**

  (`ConfidentialClientApplication`) –

  The MSAL client to acquire tokens.
- #### **`scopes`**

  (`list[str]`) –

  The scopes to request.

Methods:

- **`__call__`** –

  Add the authorization header to the request.

#### \_\_call\_\_

```
__call__(request: Request) -> Request
```

Add the authorization header to the request.

Parameters:

- ##### **`request`**

  (`Request`) –

  The request to modify.

Returns:

- `Request` –

  httpx.Request: The modified request.

## aurelius\_sdk.postgresql

Modules:

- **`listener`** –
- **`sanitize_tsquery`** –

Type Aliases:

- **`ConsumerCallback`** –

Classes:

- **`PostgresListener`** –

  Provides a simple interface for subscribing to PostgreSQL notifications on a single connection.

### \_\_all\_\_

```
__all__ = ['ConsumerCallback', 'PostgresListener', 'sanitize_tsquery']
```

### ConsumerCallback

```
ConsumerCallback = Callable[[Notify], None]
```

### PostgresListener

```
PostgresListener(connection: Connection, channel: str)
```

Provides a simple interface for subscribing to PostgreSQL notifications on a single connection.

Methods:

- **`__enter__`** –

  Start the listener when entering a context manager block.
- **`__exit__`** –

  Stop the listener when exiting a context manager block.
- **`__iter__`** –

  Yield notifications directly from psycopg when the listener is running.
- **`start`** –

  Start LISTEN and initialize the notification generator.
- **`stop`** –

  Stop listening and release listener resources.

Attributes:

- **`is_running`** (`bool`) –

  Check if the listener is currently running.

#### is\_running

```
is_running: bool
```

Check if the listener is currently running.

#### \_\_enter\_\_

```
__enter__() -> Self
```

Start the listener when entering a context manager block.

#### \_\_exit\_\_

```
__exit__(
    exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
) -> None
```

Stop the listener when exiting a context manager block.

#### \_\_iter\_\_

```
__iter__() -> Generator[Notify]
```

Yield notifications directly from psycopg when the listener is running.

#### start

```
start() -> None
```

Start LISTEN and initialize the notification generator.

#### stop

```
stop() -> None
```

Stop listening and release listener resources.

## aurelius\_sdk.testing

This module provides testing utilities for Aurelius applications.

> [!NOTE]
>
> Please install the `testing` extra to use this module.

Functions:

- **`capture_docker_compose_logs`** –

  Capture logs from the given Docker Compose services. Omit services to capture all available logs.

### capture\_docker\_compose\_logs

```
capture_docker_compose_logs(compose: DockerCompose, *services: str, logger: Logger | None = None) -> None
```

Capture logs from the given Docker Compose services. Omit services to capture all available logs.
