# aurelius-atlas-auth

Keycloak bearer-token authentication shared by the Aurelius Atlas services (8.0, DD-197): OIDC discovery, JWKS verification and the write-role gate.

## Installation

```
[project.dependencies]
aurelius-atlas-auth = "*"

[tool.uv.sources.aurelius-atlas-auth]
workspace = true
```

## Documentation

## aurelius\_atlas\_auth.auth

Keycloak bearer-token authentication for Aurelius Atlas services (8.0, DD-197).

Ported from the template's FastAPI example (the workspace's reference for the pattern: `apps/aurelius-atlas-fastapi-example/.../providers/auth.py`), reshaped as a per-service object so each application owns one :class:`KeycloakAuth` built from its own settings — no module-level caches shared across applications.

The verification story (AUX-02..AUX-05):

- OIDC discovery and JWKS are fetched through a circuit breaker (a Keycloak outage is a 503, not a hang) and cached for an hour.
- Tokens are verified with PyJWT by `kid`: RS256 signature, issuer and expiry. The audience is checked after decoding against the union of the `azp` and `aud` claims, which pyjwt's built-in check cannot express.
- The write gate accepts the configured role from `realm_access.roles` or `resource_access.<audience>.roles` — Keycloak namespaces client roles per client, so only this service's own client entry counts.

Classes:

- **`AuthConfig`** –

  What a service needs to verify its tokens. Apps map their settings in.
- **`KeycloakAuth`** –

  One service's Keycloak verifier: dependencies for FastAPI routers.

Attributes:

- **`bearer_scheme`** –

  The scheme every :class:`KeycloakAuth` shares: one instance keeps FastAPI's

### CACHE\_TTL\_SECONDS

```
CACHE_TTL_SECONDS = 3600
```

How long the discovery and JWKS documents are cached.

### HTTP\_TIMEOUT\_SECONDS

```
HTTP_TIMEOUT_SECONDS = 5.0
```

Timeout for the issuer calls (discovery, JWKS).

### LOGGER

```
LOGGER = logging.getLogger('aurelius-atlas-auth')
```

### \_\_all\_\_

```
__all__ = ['AuthConfig', 'KeycloakAuth', 'bearer_scheme']
```

### bearer\_scheme

```
bearer_scheme = HTTPBearer(auto_error=True)
```

The scheme every :class:`KeycloakAuth` shares: one instance keeps FastAPI's OpenAPI security scheme singular across the dependencies below.

### AuthConfig

```
AuthConfig(
    server_url: str,
    realm: str,
    audience: str,
    write_role: str = "",
    fail_max: int = 5,
    reset_timeout: float = 60.0,
    ca_file: str | None = None,
    extra_audiences: tuple[str, ...] = (),
)
```

What a service needs to verify its tokens. Apps map their settings in.

:param server\_url: the issuer root, e.g. `https://keycloak.localhost:8443` :param realm: the realm name (`master` in dev) :param audience: accepted `azp`/`aud` value — the service's Keycloak client id :param write\_role: role required for mutating routes; empty disables the gate :param fail\_max: issuer failures before the circuit opens :param reset\_timeout: seconds the circuit stays open :param ca\_file: PEM CA verifying the issuer's TLS (None: system trust)

Attributes:

- **`audience`** (`str`) –
- **`audiences`** (`frozenset[str]`) –

  Every accepted `azp`/`aud` value: the audience and the extra ones (AUT-10).
- **`ca_file`** (`str | None`) –
- **`extra_audiences`** (`tuple[str, ...]`) –

  Further accepted `azp`/`aud` values: the clients whose tokens the service also takes (AUT-10).
- **`fail_max`** (`int`) –
- **`realm`** (`str`) –
- **`reset_timeout`** (`float`) –
- **`server_url`** (`str`) –
- **`write_role`** (`str`) –

#### audience

```
audience: str
```

#### audiences

```
audiences: frozenset[str]
```

Every accepted `azp`/`aud` value: the audience and the extra ones (AUT-10).

#### ca\_file

```
ca_file: str | None = None
```

#### extra\_audiences

```
extra_audiences: tuple[str, ...] = ()
```

Further accepted `azp`/`aud` values: the clients whose tokens the service also takes (AUT-10).

#### fail\_max

```
fail_max: int = 5
```

#### realm

```
realm: str
```

#### reset\_timeout

```
reset_timeout: float = 60.0
```

#### server\_url

```
server_url: str
```

#### write\_role

```
write_role: str = ''
```

### KeycloakAuth

```
KeycloakAuth(config: AuthConfig, http: Client | None = None)
```

One service's Keycloak verifier: dependencies for FastAPI routers.

Use through the :attr:`require_bearer`, :attr:`require_auth` and :attr:`require_write` dependencies::

```
@router.get("/", dependencies=[Depends(auth.require_auth)])
def read(...): ...
```

:param config: the verification configuration :param http: the HTTP client for the issuer calls; injectable for tests

Methods:

- **`bearer`** –

  The raw bearer token, for routes that forward it upstream (AUX-05).
- **`close`** –

  Close the issuer HTTP client (the app calls it on shutdown).
- **`discovery`** –

  The issuer's OpenID configuration: its endpoints, fetched once, cached an hour (AUT-10).
- **`require_write_access`** –

  Require the write role for mutating routes (AUX-04).
- **`user_info`** –

  Verify the bearer token and return its claims (AUX-02, AUX-03).
- **`verify`** –

  Verify a token and return its claims, for callers outside a route dependency (AUX-02, AUT-10).

Attributes:

- **`base_url`** –
- **`config`** –
- **`require_auth`** (`Depends`) –

  Route dependency: a verified token; yields its claims (AUX-02, AUX-03).
- **`require_bearer`** (`Depends`) –

  Route dependency: a bearer credential must be present; yields the raw token.
- **`require_write`** (`Depends`) –

  Route dependency: a verified token carrying the write role (AUX-04).

#### base\_url

```
base_url = f"{config.server_url.rstrip('/')}/realms/{config.realm}"
```

#### config

```
config = config
```

#### require\_auth

```
require_auth: Depends
```

Route dependency: a verified token; yields its claims (AUX-02, AUX-03).

#### require\_bearer

```
require_bearer: Depends
```

Route dependency: a bearer credential must be present; yields the raw token.

#### require\_write

```
require_write: Depends
```

Route dependency: a verified token carrying the write role (AUX-04).

#### bearer

```
bearer(auth: HTTPAuthorizationCredentials) -> str
```

The raw bearer token, for routes that forward it upstream (AUX-05).

The scheme proves a bearer credential is present; the token itself is not verified here — it is the caller's, forwarded to the upstream service, which verifies it.

#### close

```
close() -> None
```

Close the issuer HTTP client (the app calls it on shutdown).

#### discovery

```
discovery() -> dict
```

The issuer's OpenID configuration: its endpoints, fetched once, cached an hour (AUT-10).

#### require\_write\_access

```
require_write_access(auth: HTTPAuthorizationCredentials) -> dict
```

Require the write role for mutating routes (AUX-04).

:attr:`user_info` only proves *who* the caller is; without this gate any valid token of the realm could write. An empty `write_role` disables the check — a development-only posture the app's settings enforce.

#### user\_info

```
user_info(auth: HTTPAuthorizationCredentials) -> dict
```

Verify the bearer token and return its claims (AUX-02, AUX-03).

#### verify

```
verify(token: str) -> dict
```

Verify a token and return its claims, for callers outside a route dependency (AUX-02, AUT-10).

:raises HTTPException: 401 for a token that does not verify, 503 when the issuer cannot be reached
