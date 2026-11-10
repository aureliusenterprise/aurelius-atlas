"""Entity vectors on the dev Elasticsearch (VEC-03 to VEC-06), in indices of their own per test.

What only a real Elasticsearch shows: 9.5 rewrites the source of every document of an index that maps a vector,
unless the index was created with ``index.mapping.exclude_source_vectors: false``; and a write replaces the whole
document, so a vector a read did not return would be gone after the next write (DD-434, DD-439).
"""

from collections.abc import Sequence
from decimal import Decimal

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments, EmbeddingDimensionsError
from aurelius_atlas_core.entity_embedding import VECTOR_FIELD, source_hash
from aurelius_atlas_core.entity_embedding_indexer import EntityEmbeddingIndexer
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

MODEL = "intfloat/multilingual-e5-small"
DIMENSIONS = 3


def entity(guid: str, name: str) -> StoredEntity:
    """An entity with a name."""
    return StoredEntity(guid=guid, type_name="m4i_data_entity", attributes={"Asset.name": name})


class FakeEmbedder:
    """``[1, 0, 0]`` for texts naming a customer, ``[0, 1, 0]`` for the rest."""

    model = MODEL

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text."""
        return [[1.0, 0.0, 0.0] if "Customer" in text else [0.0, 1.0, 0.0] for text in texts]


async def opened(
    dev_store: ElasticsearchStore, prefix: str, dimensions: int = DIMENSIONS
) -> ElasticsearchEntityDocuments:
    """The entity documents of ``prefix``, prepared with vectors of ``dimensions``."""
    documents = ElasticsearchEntityDocuments(dev_store.client, prefix, embedding_dimensions=dimensions)
    await documents.prepare()
    return documents


async def nearest(dev_store: ElasticsearchStore, prefix: str, vector: list[float]) -> list[str]:
    """The GUIDs a kNN query for ``vector`` finds, nearest first."""
    response = await dev_store.client.search(
        index=f"{prefix}-entities",
        knn={"field": VECTOR_FIELD, "query_vector": vector, "k": 5, "num_candidates": 10},
        source=False,
    )
    return [hit["_id"] for hit in response["hits"]["hits"]]


@pytest.mark.covers(rules=["VEC-03"])
async def test__the_entity_index_maps_the_vector_and_refuses_other_dimensions(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """A cosine ``dense_vector`` of the configured dimensions; a start with other dimensions stops, naming both."""
    await opened(dev_store, entity_prefix)
    mapping = await dev_store.client.indices.get_mapping(index=f"{entity_prefix}-entities")
    [index] = mapping.body.values()

    vector = index["mappings"]["properties"]["embedding"]["properties"]["vector"]
    assert (vector["type"], vector["dims"], vector["similarity"]) == ("dense_vector", DIMENSIONS, "cosine")
    await opened(dev_store, entity_prefix)  # the same dimensions prepare again
    with pytest.raises(EmbeddingDimensionsError, match=r"3 dimensions.*configured for 8"):
        await opened(dev_store, entity_prefix, dimensions=8)


@pytest.mark.covers(rules=["VEC-04", "VEC-05"])
async def test__a_vector_survives_a_write_of_unchanged_text_and_goes_with_a_rename(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Read back with its vector, rewritten as read, still found by kNN; renamed, no longer."""
    documents = await opened(dev_store, entity_prefix)
    await documents.write([(entity("e", "Customer"), None)])
    await EntityEmbeddingIndexer(documents, FakeEmbedder()).run_once()

    read = (await documents.get(["e"]))["e"]
    assert read.entity.embedding is not None
    assert read.entity.embedding.vector == pytest.approx([1.0, 0.0, 0.0])
    await documents.write([(read.entity.model_copy(update={"version": 2}), read.version)])
    assert await nearest(dev_store, entity_prefix, [1.0, 0.0, 0.0]) == ["e"]

    again = (await documents.get(["e"]))["e"]
    renamed = again.entity.model_copy(update={"attributes": {"Asset.name": "Client"}})
    await documents.write([(renamed, again.version)])
    assert (await documents.get(["e"]))["e"].entity.embedding is None
    assert await nearest(dev_store, entity_prefix, [1.0, 0.0, 0.0]) == []


@pytest.mark.covers(rules=["VEC-04"])
async def test__the_listings_a_write_starts_from_carry_the_vector(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """``of_types`` returns the vector too: a write from it keeps the entity findable."""
    documents = await opened(dev_store, entity_prefix)
    await documents.write([(entity("e", "Customer"), None)])
    await EntityEmbeddingIndexer(documents, FakeEmbedder()).run_once()

    [listed] = await documents.of_types(["m4i_data_entity"])
    assert listed.entity.embedding is not None
    assert listed.entity.embedding.vector == pytest.approx([1.0, 0.0, 0.0])
    await documents.write([(listed.entity.model_copy(update={"version": 5}), listed.version)])

    assert await nearest(dev_store, entity_prefix, [1.0, 0.0, 0.0]) == ["e"]


@pytest.mark.covers(rules=["VEC-06"])
async def test__the_indexer_embeds_the_store_s_entities_and_knn_finds_them_by_meaning(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Three entities and an internal one: three embedded, the customer nearest its own vector."""
    documents = await opened(dev_store, entity_prefix)
    audit = StoredEntity(guid="a", type_name="__AtlasAuditEntry")
    await documents.write(
        [(entity("c", "Customer"), None), (entity("o", "Order"), None), (entity("p", "Product"), None), (audit, None)]
    )

    written = await EntityEmbeddingIndexer(documents, FakeEmbedder(), batch_size=2).run_once()

    assert written == 3
    assert await documents.without_embedding(MODEL, 10) == []
    assert (await documents.get(["a"]))["a"].entity.embedding is None
    assert (await nearest(dev_store, entity_prefix, [1.0, 0.0, 0.0]))[0] == "c"


@pytest.mark.covers(rules=["VEC-06"])
async def test__an_entity_changed_while_it_was_embedded_keeps_its_change(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """The indexer's write carries ``if_seq_no``: a rename in between wins, and the next round embeds it."""
    documents = await opened(dev_store, entity_prefix)
    await documents.write([(entity("e", "Customer"), None)])

    class RenamingEmbedder(FakeEmbedder):
        async def embed(self, texts: Sequence[str]) -> list[list[float]]:
            read = (await documents.get(["e"]))["e"]
            renamed = read.entity.model_copy(update={"attributes": {"Asset.name": "Order"}})
            await documents.write([(renamed, read.version)])
            return await super().embed(texts)

    assert await EntityEmbeddingIndexer(documents, RenamingEmbedder()).run_once() == 0
    assert (await documents.get(["e"]))["e"].entity.attributes == {"Asset.name": "Order"}
    assert await EntityEmbeddingIndexer(documents, FakeEmbedder()).run_once() == 1
    stored = (await documents.get(["e"]))["e"].entity
    assert stored.embedding is not None
    assert stored.embedding.source_hash == source_hash(stored)


@pytest.mark.covers(rules=["VEC-03", "VEC-04"])
async def test__an_index_stored_before_embedding_moves_to_a_new_generation_with_its_sources_as_written(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Written without vectors, then opened with them: the alias moves to ``-000002``, each source keeps its digits
    (DD-039), and the moved entities are embedded and found.
    """  # noqa: D205 - one sentence
    before = ElasticsearchEntityDocuments(dev_store.client, entity_prefix)
    await before.prepare()
    sized = entity("c", "Customer").model_copy(
        update={"attributes": {"Asset.name": "Customer", "t.size": Decimal("1.10")}}
    )
    await before.write([(sized, None), (entity("o", "Order"), None)])

    documents = await opened(dev_store, entity_prefix)
    aliased = await dev_store.client.indices.get_alias(name=f"{entity_prefix}-entities")
    await EntityEmbeddingIndexer(documents, FakeEmbedder()).run_once()
    read = (await documents.get(["c"]))["c"].entity

    assert list(aliased.body) == [f"{entity_prefix}-entities-000002"]
    assert str(read.attributes["t.size"]) == "1.10"
    assert read.embedding is not None
    assert (await nearest(dev_store, entity_prefix, [1.0, 0.0, 0.0]))[0] == "c"
    await opened(dev_store, entity_prefix)  # a second start finds the index moved and keeps it
    assert list((await dev_store.client.indices.get_alias(name=f"{entity_prefix}-entities")).body) == [
        f"{entity_prefix}-entities-000002"
    ]
