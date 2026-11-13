"""The composition root: settings in, application out (DTM-01, DTM-10, DD-197, DD-209).

The app is stateless: no store, no start-up work beyond the telemetry (DD-197).
Everything it collaborates with is built elsewhere and wired here — the
factories in ``providers/`` (the verifier, the telemetry) and the routers in
``routes/`` — so this module says only *which* collaborators the app has,
never *how* they work (the shape the FastAPI example app keeps,
DD-207/DD-208/DD-209).

The seam stays the tests' (DD-200's pattern): ``auth`` is injectable.
"""

from importlib.metadata import version
from typing import Any

from aurelius_atlas_auth import KeycloakAuth
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aurelius_atlas_data2model.globals import ATLAS_ERROR_CODE, BAD_REQUEST, LOGGER, NAME
from aurelius_atlas_data2model.providers import build_auth, configure_telemetry
from aurelius_atlas_data2model.routes import HEALTH, build_router
from aurelius_atlas_data2model.settings import Data2ModelSettings


def create_app(settings: Data2ModelSettings, auth: KeycloakAuth | None = None) -> FastAPI:
    """Build the application: the providers, the routes, the error contract, the telemetry.

    Args:
        settings: The app's settings.
        auth: The token verifier; by default one built from the settings. Injectable for
            tests, which point it at a fake issuer.
    """
    verifier = auth if auth is not None else build_auth(settings)

    # The OpenAPI surface answers only under development (the dev .env sets it); production
    # serves no spec and no docs page (AUX-07, DD-557 — the server's SRV-08 posture).
    app = FastAPI(
        title=NAME,
        version=version(NAME),
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_development else None,
    )
    app.state.settings = settings
    app.state.auth = verifier

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
"""The Atlas error body every rejection of this app answers with (DTM-11, DV-79)."""

BAD_BODY = {
    "description": "A body the app will not process: the Atlas error body (DTM-11, DV-79).",
    "content": {"application/json": {"schema": ATLAS_ERROR_BODY}},
}


def _install_openapi(app: FastAPI) -> None:
    """Make the document state what the app answers, not what FastAPI would (AUX-06, DD-559).

    A body that fails the request model is the 400 of DTM-11, answered in the Atlas error
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
                    responses["400"] = dict(BAD_BODY)
        schemas = spec.get("components", {}).get("schemas", {})
        for name in ("HTTPValidationError", "ValidationError"):
            schemas.pop(name, None)
        return spec

    app.openapi = openapi


def _setup_error_handlers(app: FastAPI) -> None:
    """The app's error contract: the body rejections shaped (DTM-11, DV-79).

    Kept at the root because the mapping is the app's own contract, not any
    collaborator's — as on the lineage-model app (DD-207).
    """

    @app.exception_handler(RequestValidationError)
    def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        """A body that fails the request model is a 400 with an Atlas-shaped error body (DTM-11).

        The legacy answered a malformed extraction with a Flask ``ValueError`` — a 500;
        the port states 400 (the 8.1 spec's deviation).
        """
        first = error.errors()[0] if error.errors() else {}
        message = f"invalid extraction request: {first.get('msg', 'malformed body')}"
        LOGGER.info("Rejected extraction request: %s", message)
        return JSONResponse(status_code=BAD_REQUEST, content={"errorCode": ATLAS_ERROR_CODE, "errorMessage": message})
