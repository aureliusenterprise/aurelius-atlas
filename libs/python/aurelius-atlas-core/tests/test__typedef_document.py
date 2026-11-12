"""The type definitions as one Elasticsearch document (TDS-11, TDS-12, DD-028), on the fake client."""

from typing import cast

import pytest
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_document import (
    TYPEDEF_DOCUMENT_ID,
    TYPEDEF_INDEX,
    DocumentVersion,
    ElasticsearchTypedefDocument,
    StoredTypedefs,
    TypedefDocument,
    VersionConflictError,
    ensure_index,
)
from aurelius_atlas_model.patches import TYPEDEF_PATCH_TYPE, AtlasPatch, PatchStatus
from aurelius_atlas_model.typedef import AtlasEntityDef, AtlasTypesDef
from aurelius_atlas_store_es.testing.fake import FakeClient, already_exists
from elasticsearch import ApiError, AsyncElasticsearch


@pytest.fixture
def client() -> FakeClient:
    """A fake Elasticsearch client."""
    return FakeClient()


@pytest.fixture
def document(client: FakeClient) -> ElasticsearchTypedefDocument:
    """The typedef document on the fake client."""
    return ElasticsearchTypedefDocument(cast("AsyncElasticsearch", client))


@pytest.mark.covers("aurelius_atlas_core.typedef_document.ElasticsearchTypedefDocument.prepare", rules=["TDS-12"])
async def test__prepare_creates_the_index_behind_its_alias_once(
    client: FakeClient, document: ElasticsearchTypedefDocument
) -> None:
    """DD-028: the alias points at a versioned index, so a reindex can swap it."""
    await document.prepare()
    await document.prepare()

    assert client.aliases == {TYPEDEF_INDEX: f"{TYPEDEF_INDEX}-000001"}


@pytest.mark.covers("aurelius_atlas_core.typedef_document.ElasticsearchTypedefDocument.prepare", rules=["TDS-12"])
async def test__prepare_survives_losing_the_create_to_another_server(
    client: FakeClient, document: ElasticsearchTypedefDocument
) -> None:
    """Two servers booting on one store make the same index: the loser takes the existing path (DD-508)."""
    client.race_lost = f"{TYPEDEF_INDEX}-000001"

    await document.prepare()

    assert client.aliases == {TYPEDEF_INDEX: f"{TYPEDEF_INDEX}-000001"}
    assert client.index_settings[f"{TYPEDEF_INDEX}-000001"]["index.auto_expand_replicas"] == "0-1"


@pytest.mark.covers("aurelius_atlas_core.typedef_document.ensure_index", rules=["TDS-12"])
async def test__ensure_index_makes_an_index_and_survives_the_race(client: FakeClient) -> None:
    """True when the call made the index; False on the other server's identical create; any other error raises.

    DD-508.
    """
    elasticsearch = cast("AsyncElasticsearch", client)
    assert await ensure_index(elasticsearch, index="a-000001") is True
    assert await ensure_index(elasticsearch, index="b-000001") is True  # the loser of the same race
    client.race_lost = "b-000002"
    assert await ensure_index(elasticsearch, index="b-000002") is False

    other = ApiError("bad mapping", already_exists().meta, {"error": {"type": "mapper_parsing_exception"}})
    client.create_error = other
    with pytest.raises(ApiError):
        await ensure_index(elasticsearch, index="c-000001")


@pytest.mark.covers("aurelius_atlas_core.typedef_document.ElasticsearchTypedefDocument.prepare", rules=["IDX-02"])
async def test__the_index_expands_its_replicas_to_the_cluster(client: FakeClient) -> None:
    """One shard and at most one replica, none on a single node; an index made before gets the setting too."""
    await client.indices.create(index="old-000001", aliases={"old": {}}, settings={"number_of_shards": 1})
    await ElasticsearchTypedefDocument(cast("AsyncElasticsearch", client)).prepare()
    await ElasticsearchTypedefDocument(cast("AsyncElasticsearch", client), index="old").prepare()

    assert client.index_settings == {
        f"{TYPEDEF_INDEX}-000001": {"number_of_shards": 1, "index.auto_expand_replicas": "0-1"},
        "old-000001": {"number_of_shards": 1, "index.auto_expand_replicas": "0-1"},
    }


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_document.ElasticsearchTypedefDocument.read",
    "aurelius_atlas_core.typedef_document.ElasticsearchTypedefDocument.version",
    rules=["TDS-12"],
)
async def test__nothing_stored_reads_as_none(document: ElasticsearchTypedefDocument) -> None:
    """A missing document is not an error: the registry holds the built-in types only."""
    await document.prepare()

    assert await document.read() == (None, None)
    assert await document.version() is None


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_document.ElasticsearchTypedefDocument.write",
    "aurelius_atlas_core.typedef_document.ElasticsearchTypedefDocument.read",
    "aurelius_atlas_core.typedef_document.ElasticsearchTypedefDocument.version",
    rules=["TDS-11"],
)
async def test__writes_are_guarded_by_the_version_they_read(
    client: FakeClient, document: ElasticsearchTypedefDocument
) -> None:
    """``op_type=create`` for the first write, ``if_seq_no`` and ``if_primary_term`` after it."""
    await document.prepare()
    first = await document.write(StoredTypedefs(AtlasTypesDef(entity_defs=[AtlasEntityDef(name="t")])), None)
    second = await document.write(StoredTypedefs(AtlasTypesDef(entity_defs=[AtlasEntityDef(name="u")])), first)
    stored, version = await document.read()

    assert second == await document.version() == version
    assert second != first
    assert stored is not None
    assert [entity.name for entity in stored.types_def.entity_defs or []] == ["u"]
    assert TYPEDEF_DOCUMENT_ID in client.documents[f"{TYPEDEF_INDEX}-000001"]
    with pytest.raises(VersionConflictError):
        await document.write(StoredTypedefs(AtlasTypesDef()), first)
    with pytest.raises(VersionConflictError):
        await document.write(StoredTypedefs(AtlasTypesDef()), None)
    assert DocumentVersion(seq_no=1, primary_term=1) == second


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_document.StoredTypedefs.to_json",
    "aurelius_atlas_core.typedef_document.StoredTypedefs.from_json",
    rules=["MDL-06"],
)
async def test__the_patch_records_are_kept_next_to_the_definitions(
    client: FakeClient, document: ElasticsearchTypedefDocument
) -> None:
    """DD-031: ``typesDef`` and ``patches`` in one document; a document written before 1.5 reads with no records."""
    record = AtlasPatch(id="p-1", type=TYPEDEF_PATCH_TYPE, action="SET_SERVICE_TYPE", status=PatchStatus.APPLIED)
    await document.prepare()
    await document.write(StoredTypedefs(AtlasTypesDef(), [record]), None)
    stored, _ = await document.read()

    assert stored is not None
    assert stored.patches == [record]
    assert client.documents[f"{TYPEDEF_INDEX}-000001"][TYPEDEF_DOCUMENT_ID][0]["patches"] == [record.to_json()]
    assert StoredTypedefs.from_json({"typesDef": {}}).patches == []


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_document.TypedefDocument.prepare",
    "aurelius_atlas_core.typedef_document.TypedefDocument.read",
    "aurelius_atlas_core.typedef_document.TypedefDocument.version",
    "aurelius_atlas_core.typedef_document.TypedefDocument.write",
    rules=["TDS-11"],
)
def test__both_documents_are_typedef_documents(document: ElasticsearchTypedefDocument) -> None:
    """The store takes any ``TypedefDocument``: Elasticsearch in the server, memory in tests."""
    assert isinstance(document, TypedefDocument)
    assert isinstance(MemoryTypedefDocument(), TypedefDocument)
