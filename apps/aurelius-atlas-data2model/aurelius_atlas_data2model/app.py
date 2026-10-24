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

    app = FastAPI(title=NAME, version=version(NAME), docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.auth = verifier

    app.include_router(build_router(verifier))
    app.include_router(HEALTH)
    _setup_error_handlers(app)
    configure_telemetry(app, settings)
    return app


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
