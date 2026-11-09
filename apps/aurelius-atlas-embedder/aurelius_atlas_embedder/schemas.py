"""The request and answer shapes of OpenAI's embeddings API, with ``input_type`` (EMB-01, EMB-02, EMB-05, EMB-06)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from aurelius_atlas_embedder.model import InputType

MAX_TEXTS = 256
"""Texts per request (EMB-01, EMB-05)."""

MAX_CHARACTERS = 32_000
"""Characters per text (EMB-05); the model reads 512 tokens of it at most."""

type Text = Annotated[str, StringConstraints(min_length=1, max_length=MAX_CHARACTERS)]


class EmbeddingRequest(BaseModel):
    """``POST /v1/embeddings``: a text or a list of texts, and how to embed them (EMB-01)."""

    model_config = ConfigDict(extra="ignore")

    input: Text | Annotated[list[Text], Field(min_length=1, max_length=MAX_TEXTS)]
    model: str | None = None
    encoding_format: Literal["float"] = "float"
    input_type: InputType = InputType.PASSAGE
    """Not in OpenAI's API: what the texts are, which sets the model's prefix (DD-430)."""

    @property
    def texts(self) -> list[str]:
        """The request's texts, a single one as a list of one."""
        return [self.input] if isinstance(self.input, str) else list(self.input)


class Embedding(BaseModel):
    """One text's embedding, at its index in the request (EMB-02)."""

    object: Literal["embedding"] = "embedding"
    index: int
    embedding: list[float]


class Usage(BaseModel):
    """The tokens the model read, after truncation (EMB-02)."""

    prompt_tokens: int
    total_tokens: int


class EmbeddingResponse(BaseModel):
    """The answer to ``POST /v1/embeddings`` (EMB-02)."""

    object: Literal["list"] = "list"
    data: list[Embedding]
    model: str
    usage: Usage


class ModelCard(BaseModel):
    """The served model: OpenAI's fields, and its dimensions and revision (EMB-06)."""

    id: str
    object: Literal["model"] = "model"
    owned_by: str = "aurelius-atlas"
    dimensions: int
    revision: str


class ModelList(BaseModel):
    """The answer to ``GET /v1/models`` (EMB-06)."""

    object: Literal["list"] = "list"
    data: list[ModelCard]


class ErrorBody(BaseModel):
    """An error in OpenAI's shape (EMB-05)."""

    message: str
    type: str
    param: str | None = None
    code: str | None = None


class ErrorResponse(BaseModel):
    """The answer to a request the embedder refuses (EMB-05)."""

    error: ErrorBody
