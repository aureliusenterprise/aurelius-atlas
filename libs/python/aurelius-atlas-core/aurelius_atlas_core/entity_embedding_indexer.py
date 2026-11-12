"""``EntityEmbeddingIndexer``: embeds the entities without a current embedding (VEC-06, DD-436).

Each round asks the store for a page of entities without an embedding of the embedder's model, embeds their texts
as passages, and writes each entity with its embedding on the version it read. A whole write, not a partial update:
Elasticsearch rewrites the source of a partial update, and the store keeps its documents' bytes (DD-039). An entity
changed in between keeps its write and waits for a later round, so two servers embedding at once only lose work. The
same rounds backfill the entities stored before embedding was on, and re-embed every entity when the model changes.

An entity's text holds its App Search document's names (EMC-01); while the App Search indexer runs, an entity
waits for its document, so it is embedded once with them (EMC-04, DD-540).
"""

from collections.abc import Sequence
from typing import Protocol

from aurelius_atlas_core.entity_documents import EntityDocuments, LinkedKind, VersionedEntity
from aurelius_atlas_core.entity_embedding import embedding_text, source_hash
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEmbedding

DEFAULT_BATCH_SIZE = 32
"""Entities per page, and per request to the embedder."""


class Embedder(Protocol):
    """Computes the embeddings of passages with one model (VEC-09)."""

    @property
    def model(self) -> str:
        """The model's id, recorded with each embedding."""
        ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in their order."""
        ...


class EntityEmbeddingIndexer:
    """Embeds the entities of ``documents`` that lack an embedding of ``embedder``'s model."""

    def __init__(
        self,
        documents: EntityDocuments,
        embedder: Embedder,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        wait_for_documents: bool = False,
    ) -> None:
        """An indexer over ``documents``, embedding ``batch_size`` entities at a time; with ``wait_for_documents``,
        none awaiting its App Search document (EMC-04).
        """  # noqa: D205 - one sentence
        self._documents = documents
        self._embedder = embedder
        self._batch_size = batch_size
        self._wait_for_documents = wait_for_documents

    async def run_once(self) -> int:
        """Embed page after page until none is left, or a page writes nothing; how many embeddings were written.

        A page whose every write met a changed entity ends the round: the next one reads them again.
        """
        written = 0
        while True:
            page = await self._documents.without_embedding(
                self._embedder.model, self._batch_size, wait_for_documents=self._wait_for_documents
            )
            if not page:
                return written
            put = await self._embed(page)
            written += put
            if put == 0 or len(page) < self._batch_size:
                return written

    async def _embed(self, page: list[VersionedEntity]) -> int:
        names = await self._classification_names(page)
        texts = [embedding_text(found.entity, names.get(found.entity.guid, ())) for found in page]
        vectors = await self._embedder.embed(texts)
        model = self._embedder.model
        results = await self._documents.write(
            [
                (
                    found.entity.model_copy(
                        update={
                            "embedding": StoredEmbedding(
                                vector=vector, model=model, source_hash=source_hash(found.entity)
                            )
                        }
                    ),
                    found.version,
                )
                for found, vector in zip(page, vectors, strict=True)
            ]
        )
        return sum(1 for result in results if result.written)

    async def _classification_names(self, page: list[VersionedEntity]) -> dict[str, list[str]]:
        """Each entity's classification type names, read with one request for the page (VEC-01)."""
        guids = [guid for found in page for guid in found.entity.classification_guids or []]
        linked = await self._documents.get_linked(LinkedKind.CLASSIFICATION, guids) if guids else {}
        names: dict[str, list[str]] = {}
        for found in page:
            names[found.entity.guid] = [
                classification.type_name
                for guid in found.entity.classification_guids or []
                if guid in linked and isinstance(classification := linked[guid][0], StoredClassification)
            ]
        return names
