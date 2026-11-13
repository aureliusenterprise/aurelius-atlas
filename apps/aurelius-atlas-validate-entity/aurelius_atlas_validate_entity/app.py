"""The composition root: settings in, application out (VE-01, VE-03, VEV-02..06, DD-197, DD-209).

Since 12.7 the app is not the mock any more (DV-67, superseded by DV-153): it
reads the governance rules from the catalogue and answers the draft's verdicts.
Everything it collaborates with is built elsewhere and wired here — the
factories in ``providers/`` (the verifier, the upstreams, the telemetry), the
door in ``verdicts``, and the routers in ``routes/`` — so this module says only
*which* collaborators the app has, never *how* they work (the shape the FastAPI
example app keeps, DD-207/DD-208/DD-209).

The seams stay the tests' (DD-201): ``auth`` and ``atlas`` are injectable. The
app builds the catalogue pool from its settings and closes the pools it built
when it stops; an injected client brings its own pool (DD-205's pattern, 8.2's).
"""

from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from importlib.metadata import version
from typing import Any

import httpx2 as httpx
from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_server_client.client import AtlasClient
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aurelius_atlas_validate_entity.errors import UpstreamError, atlas_error
from aurelius_atlas_validate_entity.globals import BAD_GATEWAY, BAD_REQUEST, LOGGER, NAME
from aurelius_atlas_validate_entity.providers import build_auth, build_upstreams, configure_telemetry, server_breaker
from aurelius_atlas_validate_entity.routes import HEALTH, build_router
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings
from aurelius_atlas_validate_entity.verdicts import VerdictEngine


def create_app(
    settings: ValidateEntitySettings,
    auth: KeycloakAuth | None = None,
    atlas: AtlasClient | None = None,
) -> FastAPI:
    """Build the application: the providers, the door, the routes, the error contract, the telemetry.

    The rule read rides one circuit breaker (VEV-06, DD-500), built by the
    upstreams' factory: repeated outages (5xx, transport) open the circuit and
    the 502 arrives without calling the catalogue, until the half-open trial
    closes it again. The mint of the app's own identity rides the same leg
    (VEV-04, DD-499): without ``SERVER_CLIENT_SECRET`` the leg is unconfigured
    and every read is refused — the app stays live, ``POST /`` answers 502.

    Args:
        settings: The app's settings.
        auth: The token verifier; by default one built from the settings. Injectable for
            tests, which point it at a fake issuer.
        atlas: The client for the catalogue server (VEV-03); by default one built from
            the settings, carrying the app's own identity. Injectable for tests, which
            point it at a mock transport.
    """
    verifier = auth if auth is not None else build_auth(settings)
    atlas_client, upstream_pools = build_upstreams(settings, atlas)
    breaker = server_breaker(settings)
    engine = VerdictEngine(atlas_client, breaker, settings.rules_cache_seconds)

    # The OpenAPI surface answers only under development (the dev .env sets it); production
    # serves no spec and no docs page (AUX-07, DD-557 — the server's SRV-08 posture).
    app = FastAPI(
        title=NAME,
        version=version(NAME),
        lifespan=_lifespan(upstream_pools),
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_development else None,
    )
    app.state.settings = settings
    app.state.auth = verifier
    app.state.atlas = atlas_client
    app.state.server_breaker = breaker
    app.state.engine = engine

    app.include_router(build_router(verifier))
    app.include_router(HEALTH)
    _setup_error_handlers(app)
    _install_openapi(app)
    configure_telemetry(app, settings)
    return app


ATLAS_ERROR_BODY: dict[str, object] = {
    "type": "object",
    "properties": {"errorCode": {"type": "string"}, "errorMessage": {"type": "string"}},
    "required": ["errorCode", "errorMessage"],
}
"""The Atlas error body every rejection of this app answers with (VEV-01, DV-79's posture)."""

BAD_DRAFT = {
    "description": "A draft the app will not read: the Atlas error body (VEV-01, DV-79).",
    "content": {"application/json": {"schema": ATLAS_ERROR_BODY}},
}


def _install_openapi(app: FastAPI) -> None:
    """Make the document state what the app answers, not what FastAPI would (AUX-06, DD-558).

    A draft the app cannot parse or read is the 400 of VEV-01, answered in the Atlas error
    body by the root's handler. FastAPI's generator promises its own 422 validation body
    instead; that entry leaves the document and the honest 400 takes its place, with the
    two validation schemas no route answers.
    """
    original = app.openapi

    def openapi() -> dict[str, Any]:
        spec = original()
        for item in spec.get("paths", {}).values():
            for operation in item.values():
                responses = operation.get("responses", {})
                if "422" in responses:
                    responses.pop("422")
                    responses["400"] = dict(BAD_DRAFT)
        schemas = spec.get("components", {}).get("schemas", {})
        for name in ("HTTPValidationError", "ValidationError"):
            schemas.pop(name, None)
        return spec

    app.openapi = openapi


def _lifespan(pools: list[httpx.AsyncClient]) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """The app's lifespan: serve, then close the httpx pools the app built (DD-205's pattern)."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        yield
        for pool in pools:
            await pool.aclose()

    return lifespan


def _setup_error_handlers(app: FastAPI) -> None:
    """The app's error contract: the catalogue failures and the rejected drafts, in Atlas bodies.

    Kept at the root because the mapping is the app's own contract (VEV-01,
    VEV-06, DV-79/DV-80's posture), not any collaborator's: the body shape is
    ``errors.atlas_error``, the statuses are the route's documented ones.
    """

    @app.exception_handler(UpstreamError)
    def upstream_error(_request: Request, error: UpstreamError) -> JSONResponse:
        """The catalogue leg's failure, answered 502 (VEV-06): never a no-rules answer."""
        LOGGER.warning("Catalogue leg failure, answered %s: %s", error.status_code, error)
        return atlas_error(error.status_code, str(error))

    @app.exception_handler(httpx.RequestError)
    def upstream_unreachable(_request: Request, error: httpx.RequestError) -> JSONResponse:
        """A catalogue that cannot be reached is a gateway failure (VEV-06, DV-80's sibling)."""
        LOGGER.warning("Catalogue %s unreachable: %s", error.request.url, error)
        return atlas_error(BAD_GATEWAY, "the catalogue is unreachable")

    @app.exception_handler(RequestValidationError)
    def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        """A draft the app cannot parse or read is a 400 with an Atlas-shaped error body (VEV-01, DV-79).

        Since 8.23 this covers both halves of VEV-01's rejection: a body that is
        not JSON at all, and a JSON body that fails the ``DraftEntity`` model
        (DD-558). The legacy let Flask crash on either — a 500; the port states
        400, the same posture lineage-model keeps for its query rejections
        (DV-73's sibling).
        """
        first = error.errors()[0] if error.errors() else {}
        message = f"invalid validation request: {first.get('msg', 'malformed body')}"
        LOGGER.info("Rejected validation request: %s", message)
        return atlas_error(BAD_REQUEST, message)
