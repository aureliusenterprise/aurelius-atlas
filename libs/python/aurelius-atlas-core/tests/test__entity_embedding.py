"""The embedded text, its hash, the store's keeping of embeddings, and the indexer (VEC-01, VEC-02, VEC-05,
VEC-06, VEC-10), on the in-memory store and a fake embedder.
"""  # noqa: D205 - one sentence

from collections.abc import Sequence

import pytest
from aurelius_atlas_core.entity_documents import (
    ElasticsearchEntityDocuments,
    EmbeddingDimensionsError,
    LinkedKind,
    LinkedWrite,
)
from aurelius_atlas_core.entity_embedding import (
    MAX_CHARACTERS,
    embeddable,
    embedding_mapping,
    embedding_text,
    source_hash,
    text_values,
    with_current_embedding,
)
from aurelius_atlas_core.entity_embedding_indexer import EntityEmbeddingIndexer
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEmbedding, StoredEntity
from aurelius_atlas_core.testing.entity_samples import sample_entities, sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model import codec
from aurelius_atlas_store_es.testing.fake import FakeClient

E = "aurelius_atlas_core.entity_embedding"
X = "aurelius_atlas_core.entity_embedding_indexer.EntityEmbeddingIndexer"
D = "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments"
M = "aurelius_atlas_core.testing.memory.MemoryEntityDocuments"
MODEL = "intfloat/multilingual-e5-small"


def entity(guid: str = "g", type_name: str = "m4i_data_entity", **attributes: object) -> StoredEntity:
    """An entity of ``type_name`` with ``attributes`` under their qualified names."""
    return StoredEntity(guid=guid, type_name=type_name, attributes=dict(attributes))


def embedded(stored: StoredEntity, model: str = MODEL) -> StoredEntity:
    """``stored`` with an embedding of its current text."""
    return stored.model_copy(
        update={"embedding": StoredEmbedding(vector=[1.0, 0.0], model=model, source_hash=source_hash(stored))}
    )


class FakeEmbedder:
    """Answers each text with ``[len(text), 1.0]``; records the texts it was given."""

    model = MODEL

    def __init__(self) -> None:
        self.texts: list[list[str]] = []

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text."""
        self.texts.append(list(texts))
        return [[float(len(text)), 1.0] for text in texts]


@pytest.mark.covers(f"{E}.text_values", rules=["VEC-01"])
@pytest.mark.covers(f"{E}.embedding_text", rules=["VEC-01"])
def test__the_text_is_the_type_the_text_attributes_by_short_name_and_the_classifications() -> None:
    """Type first, then name, qualifiedName, description and definition by their name after the defining type."""
    stored = entity(
        **{
            "m4i_data_entity.definition": "Who our clients are",
            "Referenceable.qualifiedName": "crm--customer",
            "Asset.description": "Customers of the shop",
            "m4i_data_entity.name": "Customer",
            "Asset.name": "Customer",
            "Asset.owner": "jane",
            "m4i_data_entity.size": 12,
        }
    )

    assert text_values(stored) == ["Customer", "crm--customer", "Customers of the shop", "Who our clients are"]
    assert embedding_text(stored, ["PII", "key_data", "PII"]) == (
        "m4i_data_entity\nCustomer\ncrm--customer\nCustomers of the shop\nWho our clients are\nPII\nkey_data"
    )


@pytest.mark.covers(f"{E}.embedding_text", rules=["VEC-01"])
def test__a_text_longer_than_the_embedder_takes_is_cut() -> None:
    """At 32,000 characters, the embedder's limit."""
    stored = entity(**{"Asset.description": "x" * 40_000})

    assert len(embedding_text(stored)) == MAX_CHARACTERS


@pytest.mark.covers(f"{E}.text_values", rules=["VEC-01"])
def test__empty_and_non_text_values_are_left_out() -> None:
    """Only non-empty strings make up the text."""
    stored = entity(**{"Asset.name": " ", "Asset.description": None, "m4i_data_entity.name": 7})

    assert text_values(stored) == []
    assert embedding_text(stored) == "m4i_data_entity"


@pytest.mark.covers(f"{E}.source_hash", rules=["VEC-02"])
def test__the_hash_follows_the_text_s_parts_and_the_classifications_guids_only() -> None:
    """A name or a classification changes it; another attribute, or the classifications' order, does not."""
    base = entity(**{"Asset.name": "Customer", "Asset.owner": "jane"})
    hashed = source_hash(base)

    assert (
        source_hash(base.model_copy(update={"attributes": {"Asset.name": "Client", "Asset.owner": "jane"}})) != hashed
    )
    assert source_hash(base.model_copy(update={"classification_guids": ["c1"]})) != hashed
    assert (
        source_hash(base.model_copy(update={"attributes": {"Asset.name": "Customer", "Asset.owner": "joe"}})) == hashed
    )
    assert source_hash(base.model_copy(update={"classification_guids": ["c1", "c2"]})) == source_hash(
        base.model_copy(update={"classification_guids": ["c2", "c1"]})
    )
    assert len(hashed) == 64


@pytest.mark.covers(f"{E}.with_current_embedding", rules=["VEC-05"])
def test__an_embedding_stays_only_while_its_hash_is_the_entity_s() -> None:
    """Unchanged text keeps it; a changed name drops it; no embedding stays none."""
    current = embedded(entity(**{"Asset.name": "Customer"}))
    renamed = current.model_copy(update={"attributes": {"Asset.name": "Client"}})

    assert with_current_embedding(current) is current
    assert with_current_embedding(renamed).embedding is None
    assert with_current_embedding(entity()).embedding is None


@pytest.mark.covers(f"{E}.embeddable", rules=["VEC-06"])
def test__internal_types_get_no_embedding() -> None:
    """Atlas's own records, ``__AtlasAuditEntry`` among them, are left out."""
    assert embeddable("m4i_data_entity")
    assert not embeddable("__AtlasAuditEntry")


@pytest.mark.covers(f"{E}.embedding_mapping", rules=["VEC-03"])
def test__the_mapping_has_a_cosine_vector_of_the_dimensions_and_two_keywords() -> None:
    """The vector's dimensions are the configured ones."""
    assert embedding_mapping(384) == {
        "properties": {
            "vector": {"type": "dense_vector", "dims": 384, "similarity": "cosine", "index": True},
            "model": {"type": "keyword"},
            "sourceHash": {"type": "keyword"},
        }
    }


@pytest.mark.covers(f"{M}.write", rules=["VEC-05"])
async def test__a_write_carries_a_current_embedding_and_drops_a_stale_one() -> None:
    """Through the in-memory store: a write of unchanged text keeps the vector, a rename loses it."""
    documents = MemoryEntityDocuments()
    stored = embedded(entity(**{"Asset.name": "Customer"}))
    await documents.write([(stored, None)])
    read = (await documents.get(["g"]))["g"]

    await documents.write([(read.entity.model_copy(update={"version": 2}), read.version)])
    kept = (await documents.get(["g"]))["g"]
    renamed = kept.entity.model_copy(update={"attributes": {"Asset.name": "Client"}})
    await documents.write([(renamed, kept.version)])

    assert kept.entity.embedding == stored.embedding
    assert (await documents.get(["g"]))["g"].entity.embedding is None


@pytest.mark.covers(f"{M}.without_embedding", rules=["VEC-06"])
async def test__the_memory_store_lists_entities_without_the_model_s_embedding() -> None:
    """Missing or of another model is listed, by GUID; internal types and the model's own are not."""
    documents = MemoryEntityDocuments()
    await documents.write(
        [
            (entity("b"), None),
            (embedded(entity("a"), model="old-model"), None),
            (embedded(entity("c")), None),
            (entity("d", "__AtlasAuditEntry"), None),
        ]
    )

    assert [found.entity.guid for found in await documents.without_embedding(MODEL, 10)] == ["a", "b"]
    assert [found.entity.guid for found in await documents.without_embedding(MODEL, 1)] == ["a"]


@pytest.mark.covers(f"{X}.run_once", rules=["VEC-01", "VEC-06"])
async def test__a_round_embeds_every_entity_without_an_embedding_as_passages_in_pages() -> None:
    """Five entities in pages of two: three requests, every embedding of the entity's text and hash."""
    documents = MemoryEntityDocuments()
    await documents.write([(entity(f"e{n}", **{"Asset.name": f"Table {n}"}), None) for n in range(5)])
    embedder = FakeEmbedder()

    written = await EntityEmbeddingIndexer(documents, embedder, batch_size=2).run_once()

    assert written == 5
    assert [len(texts) for texts in embedder.texts] == [2, 2, 1]
    for n in range(5):
        stored = (await documents.get([f"e{n}"]))[f"e{n}"].entity
        assert stored.embedding is not None
        assert stored.embedding.model == MODEL
        assert stored.embedding.vector == [float(len(f"m4i_data_entity\nTable {n}")), 1.0]
        assert stored.embedding.source_hash == source_hash(stored)
    assert await EntityEmbeddingIndexer(documents, embedder).run_once() == 0


@pytest.mark.covers(f"{X}.run_once", rules=["VEC-01"])
async def test__the_text_carries_the_entity_s_classification_names() -> None:
    """The classifications are read by GUID, once per page."""
    documents = MemoryEntityDocuments()
    stored = entity("e", **{"Asset.name": "Customer"}).model_copy(update={"classification_guids": ["c1"]})
    classification = StoredClassification(guid="c1", type_name="PII", entity_guid="e")
    await documents.write(
        [(stored, None)], linked={LinkedKind.CLASSIFICATION: LinkedWrite(written=[(classification, None)])}
    )
    embedder = FakeEmbedder()

    await EntityEmbeddingIndexer(documents, embedder).run_once()

    assert embedder.texts == [["m4i_data_entity\nCustomer\nPII"]]


@pytest.mark.covers(f"{X}.run_once", rules=["VEC-06"])
async def test__an_entity_changed_while_it_was_embedded_keeps_its_change_for_a_later_round() -> None:
    """The write on the version read fails, the round ends, and the next round embeds the new text."""
    documents = MemoryEntityDocuments()
    await documents.write([(entity("e", **{"Asset.name": "Customer"}), None)])

    class ChangingEmbedder(FakeEmbedder):
        async def embed(self, texts: Sequence[str]) -> list[list[float]]:
            read = (await documents.get(["e"]))["e"]
            renamed = read.entity.model_copy(update={"attributes": {"Asset.name": "Client"}})
            await documents.write([(renamed, read.version)])
            return await super().embed(texts)

    assert await EntityEmbeddingIndexer(documents, ChangingEmbedder()).run_once() == 0
    assert (await documents.get(["e"]))["e"].entity.attributes == {"Asset.name": "Client"}
    assert await EntityEmbeddingIndexer(documents, FakeEmbedder()).run_once() == 1


@pytest.mark.covers(f"{D}.without_embedding", rules=["VEC-06"])
@pytest.mark.covers(f"{D}.write", rules=["VEC-05"])
async def test__the_elasticsearch_documents_list_entities_to_embed_and_drop_stale_embeddings() -> None:
    """On the fake client: the listing's query, and the write's check of the hash."""
    client = FakeClient()
    documents = ElasticsearchEntityDocuments(client, embedding_dimensions=2)  # type: ignore[arg-type]
    await documents.prepare()
    await documents.write([(embedded(entity("e", **{"Asset.name": "Customer"})), None)])
    read = (await documents.get(["e"]))["e"]

    renamed = read.entity.model_copy(update={"attributes": {"Asset.name": "Client"}})
    await documents.write([(renamed, read.version)])

    assert read.entity.embedding is not None
    assert (await documents.get(["e"]))["e"].entity.embedding is None
    assert [found.entity.guid for found in await documents.without_embedding(MODEL, 10)] == ["e"]


@pytest.mark.covers(f"{D}.prepare", rules=["VEC-03"])
async def test__a_new_entity_index_is_created_keeping_its_sources_and_mapping_the_vector() -> None:
    """With dimensions, ``exclude_source_vectors: false`` and the embedding mapping; without, neither."""
    client = FakeClient()
    await ElasticsearchEntityDocuments(client, embedding_dimensions=384).prepare()  # type: ignore[arg-type]
    await ElasticsearchEntityDocuments(client, prefix="plain").prepare()  # type: ignore[arg-type]

    vectors, plain = (
        client.index_settings["aurelius-atlas-entities-000001"],
        client.index_settings["plain-entities-000001"],
    )
    assert vectors["index.mapping.exclude_source_vectors"] is False
    assert "index.mapping.exclude_source_vectors" not in plain
    assert client.index_mappings["aurelius-atlas-entities-000001"]["properties"]["embedding"] == embedding_mapping(384)
    assert "embedding" not in client.index_mappings["plain-entities-000001"]["properties"]
    assert "index.mapping.exclude_source_vectors" not in client.index_settings["aurelius-atlas-relationships-000001"]


@pytest.mark.covers(f"{D}.prepare", rules=["VEC-03", "VEC-04"])
async def test__an_entity_index_stored_before_embedding_moves_to_the_next_generation() -> None:
    """Its entities are copied as stored, the alias moves to ``-000002``, the old index goes; a second start stays."""
    client = FakeClient()
    before = ElasticsearchEntityDocuments(client)  # type: ignore[arg-type]
    await before.prepare()
    await before.write([(entity("e", **{"Asset.name": "Customer"}), None)])

    await ElasticsearchEntityDocuments(client, embedding_dimensions=2).prepare()  # type: ignore[arg-type]
    await ElasticsearchEntityDocuments(client, embedding_dimensions=2).prepare()  # type: ignore[arg-type]

    assert client.aliases["aurelius-atlas-entities"] == "aurelius-atlas-entities-000002"
    assert "aurelius-atlas-entities-000001" not in client.documents
    assert client.index_settings["aurelius-atlas-entities-000002"]["index.mapping.exclude_source_vectors"] is False
    moved = await ElasticsearchEntityDocuments(client, embedding_dimensions=2).get(["e"])  # type: ignore[arg-type]
    assert moved["e"].entity.attributes == {"Asset.name": "Customer"}


@pytest.mark.covers(f"{D}.prepare", rules=["VEC-03"])
async def test__an_index_of_other_dimensions_stops_the_start() -> None:
    """Mapped for 384, configured for 768: the reason names both."""
    client = FakeClient()
    await ElasticsearchEntityDocuments(client, embedding_dimensions=384).prepare()  # type: ignore[arg-type]

    with pytest.raises(EmbeddingDimensionsError, match=r"384 dimensions.*configured for 768"):
        await ElasticsearchEntityDocuments(client, embedding_dimensions=768).prepare()  # type: ignore[arg-type]


@pytest.mark.covers("aurelius_atlas_core.entity_retriever.EntityRetriever.entity_with_ext_info", rules=["VEC-10"])
async def test__no_atlas_answer_shows_an_entity_s_embedding() -> None:
    """An embedded entity reads through the retriever as before: no ``embedding`` anywhere in its JSON."""
    documents = MemoryEntityDocuments()
    store = EntityStore(sample_registry(), documents)
    await store.write([EntityChange(sample) for sample in sample_entities(store.registry)])
    found = (await documents.get(["t"]))["t"]
    vector = StoredEmbedding(vector=[0.1, 0.2], model=MODEL, source_hash=source_hash(found.entity))
    await documents.write([(found.entity.model_copy(update={"embedding": vector}), found.version)])
    assert (await documents.get(["t"]))["t"].entity.embedding is not None

    answer = (await EntityRetriever(store).entity_with_ext_info("t")).to_json()

    assert "embedding" not in codec.dumps(answer).decode()
