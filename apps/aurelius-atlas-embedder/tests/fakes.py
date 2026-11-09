"""Fakes of the ONNX session and the tokenizer, so no unit test needs ONNX Runtime or the model (DD-433).

Their own module, not the conftest: the trace check collects ``tests/`` and ``e2e/`` in one session, where
``conftest`` names the e2e suite's.
"""

# ruff: noqa: INP001

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from aurelius_atlas_embedder.model import Model

PAD_ROW = [100.0, 100.0, 100.0, 100.0]
"""The fake session's hidden state on padding: large, so a mean that let it in would show."""


@dataclass(frozen=True)
class FakeEncoding:
    """A tokenized text: one id per character, padded with 0."""

    ids: list[int]
    attention_mask: list[int]


@dataclass
class FakeTokenizer:
    """One token per character, cut at ``max_tokens``, padded to the batch's longest; records what it was given."""

    max_tokens: int = 32
    seen: list[list[str]] = field(default_factory=list)

    def encode_batch(self, input: list[str]) -> list[FakeEncoding]:  # noqa: A002 - the tokenizers name
        """The texts' encodings."""
        self.seen.append(list(input))
        tokens = [[ord(character) % 50 + 1 for character in text][: self.max_tokens] for text in input]
        longest = max(len(ids) for ids in tokens)
        return [
            FakeEncoding(ids + [0] * (longest - len(ids)), [1] * len(ids) + [0] * (longest - len(ids)))
            for ids in tokens
        ]


@dataclass
class FakeSession:
    """A hidden state of 4 values per token, from its id; padding gets ``PAD_ROW``. Records each feed."""

    feeds: list[dict[str, Any]] = field(default_factory=list)

    def run(self, output_names: list[str] | None, input_feed: dict[str, Any]) -> list[Any]:
        """The fake last hidden state."""
        del output_names
        self.feeds.append(input_feed)
        ids = input_feed["input_ids"]
        rows = [[[float(i), float(i % 3), 1.0, 0.0] if i else PAD_ROW for i in sequence] for sequence in ids]
        return [np.array(rows, dtype=np.float32)]


def fake_model(*, token_types: bool = True) -> Model:
    """A model over the fakes, as the e5 export's inputs are with ``token_types``."""
    names = {"input_ids", "attention_mask"} | ({"token_type_ids"} if token_types else set())
    return Model(FakeSession(), FakeTokenizer(), frozenset(names), "intfloat/multilingual-e5-small", "rev")
