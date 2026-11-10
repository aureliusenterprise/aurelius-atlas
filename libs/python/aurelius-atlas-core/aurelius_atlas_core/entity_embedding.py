"""An entity's embedded text, the hash it is made of, and the mapping of its vector (VEC-01 to VEC-03, VEC-05).

The text is what a search by meaning matches (ADR 059); the hash says whether an embedding is still the entity's,
and the store checks it at every write (DD-435). Pure functions of a stored entity, so the store and the indexer
share them.
"""

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from aurelius_atlas_core.stored_entity import StoredEntity

EMBEDDING_FIELD = "embedding"
"""The entity document's field holding its embedding (DD-434)."""

VECTOR_FIELD = f"{EMBEDDING_FIELD}.vector"
"""The vector's field, the one a kNN query names."""

MODEL_FIELD = f"{EMBEDDING_FIELD}.model"
"""The field of the model that computed the vector."""

TEXT_ATTRIBUTES = ("name", "displayName", "qualifiedName", "description", "definition")
"""The attributes the text is made of, by their name after the defining type, in the text's order (DD-437)."""

INTERNAL_PREFIX = "__"
"""Types whose names start with it are the system's own records, which get no embedding (DD-437)."""

MAX_CHARACTERS = 32_000
"""The longest text the embedder takes (EMB-05); a longer one is cut (VEC-01)."""


def embeddable(type_name: str) -> bool:
    """Whether entities of ``type_name`` get an embedding: every type but the internal ones (VEC-06, DD-437)."""
    return not type_name.startswith(INTERNAL_PREFIX)


def text_values(entity: StoredEntity) -> list[str]:
    """The text values of the entity's text attributes, in ``TEXT_ATTRIBUTES``' order, without repeats (VEC-01).

    Attributes are stored under qualified names (DD-043), so ``Asset.name`` and ``m4i_data_entity.name`` are both
    a ``name``; within one name, the qualified names are taken in sorted order.
    """
    values: list[str] = []
    for name in TEXT_ATTRIBUTES:
        for key in sorted(key for key in entity.attributes if key.rsplit(".", 1)[-1] == name):
            value = entity.attributes[key]
            if isinstance(value, str) and value.strip() and value not in values:
                values.append(value)
    return values


def embedding_text(entity: StoredEntity, classification_names: Iterable[str] = ()) -> str:
    """The text the entity's embedding is computed from: its type, its text values, its classifications (VEC-01)."""
    lines = [entity.type_name, *text_values(entity), *sorted(set(classification_names))]
    return "\n".join(lines)[:MAX_CHARACTERS]


def source_hash(entity: StoredEntity) -> str:
    """The SHA-256 of what the entity's text is made of, its classifications by GUID (VEC-02, DD-435)."""
    made_of: list[Any] = [entity.type_name, text_values(entity), sorted(entity.classification_guids or [])]
    return hashlib.sha256(json.dumps(made_of, ensure_ascii=False).encode()).hexdigest()


def with_current_embedding(entity: StoredEntity) -> StoredEntity:
    """The entity, without its embedding unless that embedding is of its current text (VEC-05, DD-435)."""
    if entity.embedding is None or entity.embedding.source_hash == source_hash(entity):
        return entity
    return entity.model_copy(update={"embedding": None})


def embedding_mapping(dimensions: int) -> dict[str, Any]:
    """The mapping of the entity document's embedding, for vectors of ``dimensions`` (VEC-03, DD-438)."""
    return {
        "properties": {
            "vector": {"type": "dense_vector", "dims": dimensions, "similarity": "cosine", "index": True},
            "model": {"type": "keyword"},
            "sourceHash": {"type": "keyword"},
        }
    }
