"""The composition root: settings in, application out (EMB-01, EMB-07, EMB-08).

The model loads in the app's start-up, before uvicorn accepts a connection: a directory without the model, or a
Python without ONNX Runtime, stops the process instead of serving a model that never comes (EMB-08). Until then the
app holds no model, and the readiness probe and the embeddings answer 503 (EMB-07).

The loader is injectable, so the unit tests give the app a fake model (DD-433).
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from aurelius_atlas_embedder.errors import install_error_handlers
from aurelius_atlas_embedder.globals import LOGGER, NAME
from aurelius_atlas_embedder.model import Model, load_model
from aurelius_atlas_embedder.routes import EMBEDDINGS, HEALTH
from aurelius_atlas_embedder.schemas import ErrorResponse
from aurelius_atlas_embedder.settings import EmbedderSettings

type ModelLoader = Callable[[EmbedderSettings], Model]


def create_app(settings: EmbedderSettings, loader: ModelLoader = load_model) -> FastAPI:
    """Build the application: the routes, the error shape, and the model's load at start-up.

    Args:
        settings: The app's settings.
        loader: Builds the model from the settings; by default the ONNX model in ``settings.model_dir``.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        model = await run_in_threadpool(loader, settings)
        LOGGER.info("Serving %s at %s, %d dimensions", model.model_id, model.revision, model.dimensions)
        app.state.model = model
        yield
        app.state.model = None

    app = FastAPI(
        title=NAME,
        version=version(NAME),
        # The OpenAPI surface answers only under development (``serve`` sets it); production
        # serves no spec and no docs page (AUX-07, DD-557 — the server's SRV-08 posture).
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.model = None
    app.include_router(EMBEDDINGS)
    app.include_router(HEALTH)
    install_error_handlers(app)
    _install_openapi(app)
    return app


def _install_openapi(app: FastAPI) -> None:
    """Make the document state what the app answers, not what FastAPI would (AUX-06, DD-559).

    A request that fails validation is the 422 of EMB-05, answered in OpenAI's error shape
    (``errors.install_error_handlers``) — not the validation body FastAPI's generator names.
    The schema of the 422 becomes the app's ``ErrorResponse`` and FastAPI's now-unused
    validation models leave ``components/schemas``.
    """
    original = app.openapi

    def openapi() -> dict[str, Any]:
        spec = original()
        for item in spec.get("paths", {}).values():
            for operation in item.values():
                responses = operation.get("responses", {})
                if "422" in responses:
                    responses["422"]["content"] = {
                        "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                    }
        schemas = spec.get("components", {}).get("schemas", {})
        for unused in ("HTTPValidationError", "ValidationError"):
            schemas.pop(unused, None)
        refusal = ErrorResponse.model_json_schema(ref_template="#/components/schemas/{model}")
        for name, definition in refusal.pop("$defs", {}).items():
            schemas.setdefault(name, definition)
        schemas.setdefault("ErrorResponse", refusal)
        return spec

    app.openapi = openapi
