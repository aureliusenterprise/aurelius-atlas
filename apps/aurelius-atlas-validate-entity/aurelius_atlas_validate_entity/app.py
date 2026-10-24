"""The composition root: settings in, application out (VE-01, VE-03, DD-197, DD-209).

The app is the legacy mock (DV-67, DD-201): the entity body is never read and
the answer is the fixed document (VE-01) — no store, no upstream, no cache
(the legacy's dev ``@cached`` is not ported), no start-up work beyond the
telemetry. Everything it collaborates with is built elsewhere and wired here —
the factories in ``providers/`` (the verifier, the telemetry) and the routers
in ``routes/`` — so this module says only *which* collaborators the app has,
never *how* they work (the shape the FastAPI example app keeps,
DD-207/DD-208/DD-209).

The seam stays the tests' (DD-201): ``auth`` is injectable.
"""

from importlib.metadata import version

from aurelius_atlas_auth import KeycloakAuth
from fastapi import FastAPI

from aurelius_atlas_validate_entity.globals import NAME
from aurelius_atlas_validate_entity.providers import build_auth, configure_telemetry
from aurelius_atlas_validate_entity.routes import HEALTH, build_router
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings


def create_app(
    settings: ValidateEntitySettings,
    auth: KeycloakAuth | None = None,
) -> FastAPI:
    """Build the application: the providers, the routes, the telemetry.

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
    configure_telemetry(app, settings)
    return app
