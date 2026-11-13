"""Security response headers on every answer of the server (SRV-08, DD-236).

A pure-ASGI middleware — no BaseHTTPMiddleware anywhere in this server — added in
``create_app``, so the API and the mounted dashboards share one header story.

The API (``/api/...``) answers with catalog metadata: ``no-store`` keeps it out of
browser and proxy caches, ``nosniff``/``X-Frame-Options: DENY``/``frame-ancestors
'none'`` close sniffing and click-framing, and a ``default-src 'none'`` CSP promises
the JSON is never a document (it is not one, and CSP is the belt).

The dashboards (``/`` and ``/n/``, DSH-01/DSH-02) are the vendored Apache Atlas 2.4.0
UI: its ``index.html`` carries inline bootstrap scripts (one interpolates the build's
cache-bust value, so a CSP hash churns every build — hash pinning is not stable
enough for vendored files), and its require-handlebars-plugin compiles templates at
runtime with ``new Function`` — so the CSP allows ``'unsafe-inline'`` and
``'unsafe-eval'`` scripts on the dashboard documents only (DV-86; the e2e dashboard
test is the regression guard). What CSP does enforce there is the rest:
``object-src``/``base-uri``/``frame-ancestors`` closed, same-origin sources. The API
keeps ``default-src 'none'``. The webapp (7.x, nginx-served) has its own hardened CSP
(DD-159's precedent); this covers what the server process itself serves.

``Strict-Transport-Security`` rides every response when ``hsts_enabled`` (the image's
default): TLS is a start-up requirement (SRV-06, DD-234), so the server may declare
it. The dev arrangement turns it off — the mkcert CA is not in the browser trust
store, and pinning HTTPS on ``localhost`` would bite the plaintext dev surfaces ADR
039 names as relaxations.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aurelius_atlas_server.root_path import site_path

Header = tuple[str, str]

API_SECURITY_HEADERS: tuple[Header, ...] = (
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "DENY"),
    ("referrer-policy", "no-referrer"),
    ("permissions-policy", "camera=(), microphone=(), geolocation=()"),
    ("cache-control", "no-store"),
    ("content-security-policy", "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"),
)

DASHBOARD_SECURITY_HEADERS: tuple[Header, ...] = (
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "SAMEORIGIN"),
    ("referrer-policy", "no-referrer"),
    ("permissions-policy", "camera=(), microphone=(), geolocation=()"),
    (
        "content-security-policy",
        (
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'"
            "; script-src 'self' 'unsafe-inline' 'unsafe-eval'"
            "; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:"
            # Atlas's own policy allows these (HeadersUtil): jstree parses its trees in a blob worker, and a
            # browser that refuses the worker without throwing leaves the tree spinning (SRV-11, DD-364).
            "; font-src 'self' data:; worker-src 'self' blob:"
        ),
    ),
)

ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
"""Bust-versioned dashboard assets (?bust=..., DSH-02's cache busting) never change under their URL."""

HSTS_HEADER: tuple[Header, ...] = (("strict-transport-security", "max-age=31536000; includeSubDomains"),)
"""One year, all subdomains — the same pin Keycloak's realm header uses (browserSecurityHeaders)."""

DOCS_PATH = "/api/atlas/docs"
"""The Swagger UI page of the dev OpenAPI surface: served only under development (create_app), a 404 elsewhere."""

DOCS_CSP = (
    "default-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    "; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    "; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    "; img-src 'self' data: https://fastapi.tiangolo.com"
    "; font-src https://cdn.jsdelivr.net"
)
"""Swagger UI is a document: FastAPI's page loads its bundle from jsdelivr, boots with an inline script,
and takes the spec from 'self'. Development only — the surface answers on no production server."""

DOCS_HEADERS: tuple[Header, ...] = tuple(
    ("content-security-policy", DOCS_CSP) if name == "content-security-policy" else (name, value)
    for name, value in API_SECURITY_HEADERS
)
"""The API headers with the docs CSP swapped in: everything else (no-store, nosniff, framing) stays closed."""


def _is_api_path(path: str) -> bool:
    """The Atlas API namespace, the ``/api/atlas`` tree."""
    return path == "/api" or path.startswith("/api/")


def _is_busted_asset(query_string: bytes) -> bool:
    """A dashboard asset request carrying the build's cache-bust query (``?bust=...``, DSH-02)."""
    return b"bust=" in query_string


class SecurityHeadersMiddleware:
    """Stamp the security headers on every response (SRV-08, DD-236).

    :param app: the wrapped ASGI application
    :param hsts_enabled: serve ``Strict-Transport-Security`` (``ServerSettings.hsts_enabled``)
    :param dev_docs_enabled: the dev OpenAPI surface is served (``ServerSettings.is_development``), so the
        docs page carries its own CSP; off, every API path shares the strict one
    """

    def __init__(self, app: ASGIApp, *, hsts_enabled: bool = True, dev_docs_enabled: bool = False) -> None:
        self._app = app
        self._hsts = HSTS_HEADER if hsts_enabled else ()
        # Off, the docs path is a plain API answer (a 404) under the strict CSP.
        self._docs_headers = DOCS_HEADERS if dev_docs_enabled else API_SECURITY_HEADERS

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Stamp on ``http.response.start``, so every answer of the wrapped app carries the headers."""
        if scope["type"] != "http":  # lifespan and websocket pass through untouched
            await self._app(scope, receive, send)
            return

        path = site_path(scope)
        if _is_api_path(path):
            api = self._docs_headers if path == DOCS_PATH else API_SECURITY_HEADERS
            stamped: tuple[Header, ...] = api + self._hsts
            cache_assets = False
        else:
            stamped = DASHBOARD_SECURITY_HEADERS + self._hsts
            # Bust-versioned assets are immutable; an HTML document is not, even
            # when its URL carries the bust query — the page must stay fresh.
            cache_assets = _is_busted_asset(scope.get("query_string", b"")) and not path.endswith(".html")

        async def send_stamped(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in stamped:
                    headers.append(name, value)
                if cache_assets and "cache-control" not in headers:
                    headers.append("cache-control", ASSET_CACHE_CONTROL)
            await send(message)

        await self._app(scope, receive, send_stamped)
