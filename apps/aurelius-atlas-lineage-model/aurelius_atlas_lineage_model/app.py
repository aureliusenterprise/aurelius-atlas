"""The composition root: settings in, application out (LM-01, LM-08, LM-09, DD-108, DD-118).

The app is a stateless proxy: no store, no cache (the legacy's dev ``@cached`` is
not ported), no start-up work beyond the telemetry. Everything it collaborates
with is built elsewhere and wired here — the factories in ``providers/`` (the
verifier, the upstreams, the telemetry) and the routers in ``routes/`` —
so this module says only *which* collaborators the app has, never *how* they
work (the shape the FastAPI example app keeps, DD-118/DD-119).

The seams stay the tests' (DD-111): ``auth``/``atlas``/``d2m`` are injectable.
The app builds each injected-out client's ``httpx.AsyncClient`` from its settings
and closes the pools it built when the app stops; an injected client brings its
own pool (DD-116).
"""

from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from importlib.metadata import version

import httpx2 as httpx
from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_data2model_client.client import Data2ModelClient
from aurelius_atlas_server_client.client import AtlasClient
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aurelius_atlas_lineage_model.errors import UpstreamError, atlas_error
from aurelius_atlas_lineage_model.globals import BAD_GATEWAY, BAD_REQUEST, LOGGER, NAME
from aurelius_atlas_lineage_model.providers import (
    atlas_breaker,
    build_auth,
    build_upstreams,
    configure_telemetry,
    d2m_breaker,
)
from aurelius_atlas_lineage_model.routes import HEALTH, build_router
from aurelius_atlas_lineage_model.settings import LineageModelSettings


def create_app(
    settings: LineageModelSettings,
    auth: KeycloakAuth | None = None,
    atlas: AtlasClient | None = None,
    d2m: Data2ModelClient | None = None,
) -> FastAPI:
    """Build the application: the providers, the routes, the error contract, the telemetry.

    Each upstream rides its own circuit breaker (LM-11, 8.5, DD-117), built by
    the upstreams' factory: repeated outages (5xx, transport — LM-13) open the
    circuit and the 502 of LM-12 arrives without calling the upstream, until
    the half-open trial closes it again (LM-14).

    Args:
        settings: The app's settings.
        auth: The token verifier; by default one built from the settings. Injectable for
            tests, which point it at a fake issuer.
        atlas: The client for the Atlas lineage feed (LM-04); by default one built from
            the settings. Injectable for tests, which point it at a mock transport.
        d2m: The client for the data2model extraction (LM-04); same seam as ``atlas``.
    """
    verifier = auth if auth is not None else build_auth(settings)
    atlas_client, d2m_client, upstream_pools = build_upstreams(settings, atlas, d2m)

    app = FastAPI(
        title=NAME,
        version=version(NAME),
        lifespan=_lifespan(upstream_pools),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.auth = verifier
    app.state.atlas = atlas_client
    app.state.d2m = d2m_client
    app.state.atlas_breaker = atlas_breaker(settings)
    app.state.d2m_breaker = d2m_breaker(settings)

    app.include_router(build_router(verifier))
    app.include_router(HEALTH)
    _setup_error_handlers(app)
    configure_telemetry(app, settings)
    return app


def _lifespan(pools: list[httpx.AsyncClient]) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """The app's lifespan: serve, then close the httpx pools the app built (DD-116)."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        yield
        for pool in pools:
            await pool.aclose()

    return lifespan


def _setup_error_handlers(app: FastAPI) -> None:
    """The app's error contract: the upstream statuses mapped, the query rejections shaped.

    Kept at the root because the mapping is the app's own contract (LM-05,
    LM-07, LM-12, DV-20..DV-22), not any collaborator's: the body shape is
    ``errors.atlas_error``, the statuses are the route's documented ones.
    """

    @app.exception_handler(UpstreamError)
    def upstream_error(_request: Request, error: UpstreamError) -> JSONResponse:
        """The upstream's status, mapped: 400 stays 400, anything else is a 502 (LM-05, LM-07)."""
        LOGGER.warning("Upstream failure, answered %s: %s", error.status_code, error)
        return atlas_error(error.status_code, str(error))

    @app.exception_handler(httpx.RequestError)
    def upstream_unreachable(_request: Request, error: httpx.RequestError) -> JSONResponse:
        """An upstream that cannot be reached is a gateway failure (LM-07, DV-22)."""
        LOGGER.warning("Upstream %s unreachable: %s", error.request.url, error)
        return atlas_error(BAD_GATEWAY, "the lineage service is unreachable")

    @app.exception_handler(RequestValidationError)
    def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        """A query the app will not process is a 400 with an Atlas-shaped error body (LM-07, DV-20, DV-21).

        The legacy let ``int()``, ``Enum()`` and a literal-``None`` guid crash
        Flask — a 500; the port states 400.
        """
        first = error.errors()[0] if error.errors() else {}
        message = f"invalid lineage request: {first.get('msg', 'malformed query')}"
        LOGGER.info("Rejected lineage request: %s", message)
        return atlas_error(BAD_REQUEST, message)
