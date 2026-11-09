"""``POST /v1/embeddings`` and ``GET /v1/models`` (EMB-01, EMB-02, EMB-05, EMB-06)."""

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from aurelius_atlas_embedder.errors import EmbedderError
from aurelius_atlas_embedder.globals import NOT_READY
from aurelius_atlas_embedder.model import Model
from aurelius_atlas_embedder.schemas import Embedding, EmbeddingRequest, EmbeddingResponse, ModelCard, ModelList, Usage

EMBEDDINGS = APIRouter(prefix="/v1")
"""The embeddings router."""

NOT_FOUND = 404


def ready_model(request: Request) -> Model:
    """The loaded model, or a 503 while it loads (EMB-07).

    Raises:
        EmbedderError: The model has not loaded yet.
    """
    model: Model | None = request.app.state.model
    if model is None:
        raise EmbedderError(NOT_READY, "The model is still loading", code="model_not_ready")
    return model


@EMBEDDINGS.post("/embeddings")
async def create_embeddings(body: EmbeddingRequest, request: Request) -> EmbeddingResponse:
    """One embedding per text, in the order sent (EMB-01, EMB-02); the model runs off the event loop."""
    model = ready_model(request)
    if body.model is not None and body.model != model.model_id:
        message = f"The model {body.model!r} does not exist; this embedder serves {model.model_id!r}"
        raise EmbedderError(NOT_FOUND, message, param="model", code="model_not_found")
    embeddings = await run_in_threadpool(model.embed, body.texts, body.input_type)
    return EmbeddingResponse(
        data=[Embedding(index=index, embedding=vector) for index, vector in enumerate(embeddings.vectors)],
        model=model.model_id,
        usage=Usage(prompt_tokens=embeddings.tokens, total_tokens=embeddings.tokens),
    )


@EMBEDDINGS.get("/models")
def list_models(request: Request) -> ModelList:
    """The served model, its dimensions and its revision (EMB-06)."""
    model = ready_model(request)
    return ModelList(data=[ModelCard(id=model.model_id, dimensions=model.dimensions, revision=model.revision)])
