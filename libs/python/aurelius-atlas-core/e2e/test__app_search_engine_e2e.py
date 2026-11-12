"""The ``atlas-dev`` engine on the dev Elasticsearch (ASE-05 to ASE-09), in indices of their own per test.

What only a real Elasticsearch shows: the translated search runs, its words match analysed names and exact
emails, the facets and sorts read the keyword fields, and the total is exact.
"""

import pytest
from aurelius_atlas_core.app_search_engine import AppSearchEngine
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


def m4i(type_name: str, key: str, **attributes: object) -> AtlasEntity:
    """An entity named after ``key`` with ``attributes``; ``domain`` names a domain of the request by key."""
    domain = attributes.pop("domain", None)
    return AtlasEntity(
        type_name=type_name,
        guid=f"-{key}",
        attributes={"qualifiedName": f"e2e--{key}", "name": key.title()} | attributes,
        relationship_attributes={"dataDomain": [AtlasObjectId(guid=f"-{domain}")]} if domain else None,
    )


@pytest.mark.critical
@pytest.mark.covers(rules=["ASE-05", "ASE-06", "ASE-07", "ASE-08", "ASE-09"])
async def test__the_engine_searches_filters_facets_and_sorts_the_entity_index(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """A domain's entities by a filter, a definition's word, a person's email, facets by count, a name sort."""
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
                m4i("m4i_data_domain", "sales"),
                m4i("m4i_data_entity", "order", domain="sales", definition="Customer orders placed online"),
                m4i("m4i_data_entity", "invoice", domain="sales", definition="Invoices sent"),
                m4i("m4i_person", "person", name="Pat", email="jo@example.org"),
            ]
        )
    )
    guids = {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}
    await AppSearchIndexer(documents, types.registry).run_once()
    engine = AppSearchEngine(documents)

    def found(answer: dict[str, object]) -> list[str]:
        return [result["id"]["raw"] for result in answer["results"]]  # type: ignore[index, union-attr]

    domain = await engine.search(
        {
            "filters": {"all": [{"typename": ["m4i_data_entity"]}, {"deriveddatadomainguid": [guids["sales"]]}]},
            "sort": {"name": "desc"},
            "facets": {
                "deriveddatadomain": {"type": "value"},
                "sourcetype": {"type": "value"},
                "name": {"type": "value", "sort": {"value": "asc"}},
            },
        }
    )
    assert found(domain) == [guids["order"], guids["invoice"]]
    assert domain["meta"]["page"]["total_results"] == 2
    assert domain["facets"]["deriveddatadomain"] == [{"type": "value", "data": [{"value": "Sales", "count": 2}]}]
    assert [entry["value"] for entry in domain["facets"]["name"][0]["data"]] == ["Invoice", "Order"]
    assert domain["facets"]["sourcetype"] == [{"type": "value", "data": [{"value": "Business", "count": 2}]}]

    worded = await engine.search({"query": "customer", "result_fields": {"definition": {"snippet": {}}}})
    assert found(worded) == [guids["order"]]
    assert worded["results"][0]["definition"]["snippet"] == "<em>Customer</em> orders placed online"
    assert worded["results"][0]["_meta"]["score"] > 0
    assert found(await engine.search({"query": "jo@example.org"})) == [guids["person"]]  # the email, exactly
    assert found(await engine.search({"query": "jo"})) == []

    everything = await engine.search({"page": {"current": 2, "size": 3}, "sort": [{"typename": "asc"}]})
    assert everything["meta"]["page"] == {"current": 2, "total_pages": 2, "total_results": 4, "size": 3}
    assert len(everything["results"]) == 1
