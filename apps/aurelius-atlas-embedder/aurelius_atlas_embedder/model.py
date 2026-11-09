"""The model: texts in, vectors of length 1 out (EMB-03, EMB-04, EMB-08, DD-429, DD-433).

The ONNX session and the tokenizer sit behind two small protocols, so the unit tests give the model fakes and need
neither ONNX Runtime nor the model's files. ``load_model`` builds the real ones; it is the only place that imports
ONNX Runtime, which has no wheels for every Python the workspace allows (DD-433).
"""

import importlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from tokenizers import Tokenizer

from aurelius_atlas_embedder.settings import EmbedderSettings

MODEL_FILE = "model.onnx"
TOKENIZER_FILE = "tokenizer.json"
PAD_TOKEN = "<pad>"  # noqa: S105 - the tokenizer's padding token, not a secret
WARM_UP = "Aurelius Atlas"
"""The text embedded once at load, so the first request does not pay for the session's start (EMB-07)."""


class InputType(StrEnum):
    """What a text is, which sets the prefix the model was trained with (EMB-03, DD-430)."""

    PASSAGE = "passage"
    QUERY = "query"


class ModelLoadError(RuntimeError):
    """The model cannot be loaded from its directory (EMB-08)."""


class Session(Protocol):
    """The part of an ONNX Runtime ``InferenceSession`` the model uses."""

    def run(self, output_names: list[str] | None, input_feed: dict[str, Any]) -> list[Any]:
        """The session's outputs for ``input_feed``."""
        ...


class Encoding(Protocol):
    """A tokenized text."""

    @property
    def ids(self) -> list[int]:
        """The token ids, padded to the batch's longest."""
        ...

    @property
    def attention_mask(self) -> list[int]:
        """1 for the text's tokens, 0 for the padding."""
        ...


class TextTokenizer(Protocol):
    """The part of a ``tokenizers.Tokenizer`` the model uses."""

    def encode_batch(self, input: list[str]) -> Sequence[Encoding]:  # noqa: A002 - the tokenizers name
        """The texts' encodings, truncated and padded alike."""
        ...


@dataclass(frozen=True)
class Embeddings:
    """The vectors of a request's texts, in their order, and the tokens the model read (EMB-02)."""

    vectors: list[list[float]]
    tokens: int


class Model:
    """A sentence-embedding model: mean pooling over the last hidden state, scaled to length 1 (EMB-03)."""

    def __init__(
        self,
        session: Session,
        tokenizer: TextTokenizer,
        input_names: frozenset[str],
        model_id: str,
        revision: str,
    ) -> None:
        """A model over ``session`` and ``tokenizer``; ``input_names`` are the session's inputs."""
        self._session = session
        self._tokenizer = tokenizer
        self._token_types = "token_type_ids" in input_names
        self.model_id = model_id
        self.revision = revision
        self.dimensions = 0
        """The vectors' length, known once the model has embedded a text."""

    def embed(self, texts: Sequence[str], input_type: InputType = InputType.PASSAGE) -> Embeddings:
        """The texts' vectors, each prefixed by ``input_type`` as the model was trained (EMB-03).

        The attention mask keeps the padding out of the mean, so a text's vector does not depend on the other texts
        in the batch (EMB-04).
        """
        encodings = self._tokenizer.encode_batch([f"{input_type.value}: {text}" for text in texts])
        ids = np.array([encoding.ids for encoding in encodings], dtype=np.int64)
        mask = np.array([encoding.attention_mask for encoding in encodings], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": mask}
        if self._token_types:
            feed["token_type_ids"] = np.zeros_like(ids)
        hidden = np.asarray(self._session.run(None, feed)[0], dtype=np.float32)
        weights = mask[..., np.newaxis].astype(np.float32)
        pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
        vectors = pooled / np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
        self.dimensions = int(vectors.shape[1])
        return Embeddings(vectors=vectors.tolist(), tokens=int(mask.sum()))


def load_model(settings: EmbedderSettings) -> Model:
    """The model in ``settings.model_dir``, warmed up by one embedding (EMB-07, EMB-08).

    Raises:
        ModelLoadError: The directory lacks the model or the tokenizer, or ONNX Runtime is not installed.
    """
    directory = Path(settings.model_dir)
    check_model_dir(directory)
    try:
        # Imported by name: it has no wheels for every Python the workspace allows, so it is not always there (DD-433).
        onnxruntime = importlib.import_module("onnxruntime")
    except ImportError as error:
        message = "ONNX Runtime is not installed: it has wheels for Python 3.11 to 3.14 (DD-433)"
        raise ModelLoadError(message) from error
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = settings.threads
    session = onnxruntime.InferenceSession(
        str(directory / MODEL_FILE), sess_options=options, providers=["CPUExecutionProvider"]
    )
    tokenizer = Tokenizer.from_file(str(directory / TOKENIZER_FILE))
    tokenizer.enable_truncation(settings.max_tokens)
    pad_id = tokenizer.token_to_id(PAD_TOKEN)
    tokenizer.enable_padding(pad_id=pad_id if pad_id is not None else 0, pad_token=PAD_TOKEN)
    model = Model(
        session,
        tokenizer,
        frozenset(entry.name for entry in session.get_inputs()),
        settings.model_id,
        settings.model_revision,
    )
    model.embed([WARM_UP])
    return model


def check_model_dir(directory: Path) -> None:
    """Fail when ``directory`` lacks the model or the tokenizer (EMB-08).

    Raises:
        ModelLoadError: A file is missing.
    """
    missing = [name for name in (MODEL_FILE, TOKENIZER_FILE) if not (directory / name).is_file()]
    if missing:
        message = f"{directory} lacks {', '.join(missing)}; the embedder never fetches its model (EMB-08)"
        raise ModelLoadError(message)
