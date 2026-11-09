"""The composition root: settings in, application out (EMB-01, EMB-07, EMB-08).

The model loads in the app's start-up, before uvicorn accepts a connection: a directory without the model, or a
Python without ONNX Runtime, stops the process instead of serving a model that never comes (EMB-08). Until then the
app holds no model, and the readiness probe and the embeddings answer 503 (EMB-07).

The loader is injectable, so the unit tests give the app a fake model (DD-433).
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from aurelius_atlas_embedder.errors import install_error_handlers
from aurelius_atlas_embedder.globals import LOGGER, NAME
from aurelius_atlas_embedder.model import Model, load_model
from aurelius_atlas_embedder.routes import EMBEDDINGS, HEALTH
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

    app = FastAPI(title=NAME, version=version(NAME), docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.model = None
    app.include_router(EMBEDDINGS)
    app.include_router(HEALTH)
    install_error_handlers(app)
    return app
