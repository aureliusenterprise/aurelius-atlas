"""App Search documents on the dev Elasticsearch (ASD-02 to ASD-04), in indices of their own per test.

What only a real Elasticsearch shows: the listing's query and the mapping of the stored document, so that a term
query on a derived relation finds the entities that list it.
"""

import pytest
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasObjectId
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_typesystem.registry import TypeRegistry

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


def m4i(type_name: str, key: str, **relations: list[str]) -> AtlasEntity:
    """An entity named after ``key``, with relationship attributes naming other entities of the request by key."""
    return AtlasEntity(
        type_name=type_name,
        guid=f"-{key}",
        attributes={"qualifiedName": f"e2e--{key}", "name": key.upper()},
        relationship_attributes={
            name: [AtlasObjectId(guid=f"-{other}") for other in others] for name, others in relations.items()
        },
    )


async def hits(dev_store: ElasticsearchStore, prefix: str, field: str, value: str) -> list[str]:
    """The GUIDs of the entities whose App Search ``field`` holds ``value``."""
    response = await dev_store.client.search(
        index=f"{prefix}-entities", query={"term": {f"appSearch.{field}": value}}, source=False
    )
    return sorted(hit["_id"] for hit in response["hits"]["hits"])


@pytest.mark.covers(rules=["ASD-02", "ASD-03", "ASD-04"])
async def test__the_indexer_writes_documents_a_term_query_finds_and_a_rename_drops(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """A field joins a dataset and a data entity; each is found by the other's GUID; a renamed one is listed again."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for models_dir in (BUILTIN_MODELS_DIR, M4I_MODELS_DIR):
        await ModelLoader(types).load(models_dir)
    documents = ElasticsearchEntityDocuments(dev_store.client, entity_prefix)
    store = EntityStore(types.registry, documents)
    await store.prepare()
    response = await EntityWriter(store, user="e2e").create_or_update(
        AtlasEntitiesWithExtInfo(
            entities=[
                m4i("m4i_data_entity", "e"),
                m4i("m4i_data_attribute", "a", dataEntity=["e"]),
                m4i("m4i_dataset", "s"),
                m4i("m4i_field", "f", datasets=["s"], attributes=["a"]),
            ]
        )
    )
    guids = {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}

    assert len(await documents.without_app_search(10)) == 4
    assert await AppSearchIndexer(documents, types.registry).run_once() == 4
    assert await documents.without_app_search(10) == []
    assert await hits(dev_store, entity_prefix, "deriveddataentityguid", guids["e"]) == sorted([guids["a"], guids["s"]])
    assert await hits(dev_store, entity_prefix, "breadcrumbguid", guids["s"]) == [guids["f"]]

    await EntityWriter(store, user="e2e").update_attribute_by_guid(guids["s"], "name", "renamed")
    assert [found.entity.guid for found in await documents.without_app_search(10)] == [guids["s"]]
    await store.prepare()  # an existing index keeps its mapping and its documents
    assert await hits(dev_store, entity_prefix, "deriveddatasetguid", guids["s"]) == sorted([guids["e"], guids["f"]])
