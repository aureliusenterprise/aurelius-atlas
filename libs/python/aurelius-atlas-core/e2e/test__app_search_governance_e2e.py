"""The governance verdicts on the dev Elasticsearch (ASG-03 to ASG-06), in indices of their own per test.

What only a real Elasticsearch shows: the listing of the entities to judge by their marks, the verdicts' index and
its mapping, the details cards' and a rule page's requests on ``atlas-dev-gov-quality``, and a relationship added
judged again after a round.
"""

import pytest
from aurelius_atlas_core.app_search_engine import ATLAS_DEV_GOV_QUALITY, AppSearchEngine
from aurelius_atlas_core.app_search_governance import GovernanceIndexer
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


def m4i(type_name: str, key: str, values: dict[str, object] | None = None) -> AtlasEntity:
    """An entity named after ``key`` with ``values``."""
    return AtlasEntity(
        type_name=type_name,
        guid=f"-{key}",
        attributes={"qualifiedName": f"e2e--{key}", "name": key.title()} | (values or {}),
    )


@pytest.mark.critical
@pytest.mark.covers(rules=["ASG-03", "ASG-04", "ASG-05", "ASG-06"])
async def test__a_rule_s_verdicts_answer_the_details_cards_and_the_rule_page(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """A rule over the datasets: one in a collection meets it, one not until it joins one and a round has run."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for models_dir in (BUILTIN_MODELS_DIR, M4I_MODELS_DIR):
        await ModelLoader(types).load(models_dir)
    documents = ElasticsearchEntityDocuments(dev_store.client, entity_prefix)
    store = EntityStore(types.registry, documents)
    await store.prepare()
    writer = EntityWriter(store, user="e2e")
    rule = {
        "qualifiedName": "m4i_dataset--e2e-collected",
        "expression": "length('collections', 1)",
        "ruleType": "relationship",
        "qualityDimension": "completeness",
        "nonCompliantMessage": "This dataset should be in a collection",
        "active": True,
        "id": 1,
    }
    collected = m4i("m4i_dataset", "orders")
    collected.relationship_attributes = {"collections": [AtlasObjectId(guid="-sales")]}
    response = await writer.create_or_update(
        AtlasEntitiesWithExtInfo(
            entities=[
                m4i("m4i_collection", "sales"),
                collected,
                m4i("m4i_dataset", "loose"),
                m4i("m4i_gov_data_quality", "collected", rule),
            ]
        )
    )
    guids = {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}
    indexer = AppSearchIndexer(documents, types.registry)
    governance = GovernanceIndexer(documents, types.registry)
    await indexer.run_once()

    assert await governance.run_once() == 2
    assert await governance.run_once() == 0

    engine = AppSearchEngine(documents, ATLAS_DEV_GOV_QUALITY)
    cards = await engine.search(
        {
            "facets": {"dataqualityruledimension": {"type": "value"}, "dataqualitytype": {"type": "value"}},
            "page": {"current": 1, "size": 9},
            "filters": {"all": [{"entity_guid": [guids["loose"]]}]},
            "sort": {"compliant": "asc"},
        }
    )
    (card,) = cards["results"]
    assert (card["id"]["raw"], card["compliant"]["raw"], card["noncompliant_message"]["raw"]) == (
        f"{guids['loose']}--{guids['collected']}",
        "0",
        "This dataset should be in a collection",
    )
    assert cards["facets"]["dataqualitytype"] == [{"type": "value", "data": [{"value": "relationship", "count": 1}]}]

    def tab(compliant: str) -> dict[str, object]:
        return {
            "page": {"current": 1, "size": 1000},
            "result_fields": {"entity_guid": {"raw": {}}},
            "filters": {"all": [{"compliant": [compliant]}, {"guid": [guids["collected"]]}]},
        }

    met = await engine.search(tab("1"))
    assert [found["entity_guid"]["raw"] for found in met["results"]] == [guids["orders"]]

    joined = AtlasEntity(
        type_name="m4i_dataset",
        guid=guids["loose"],
        attributes={"qualifiedName": "e2e--loose", "name": "Loose"},
        relationship_attributes={"collections": [AtlasObjectId(guid=guids["sales"])]},
    )
    await writer.create_or_update(AtlasEntitiesWithExtInfo(entities=[joined]))
    await indexer.run_once()
    assert await governance.run_once() >= 1

    met = await engine.search(tab("1") | {"sort": {"entity_guid": "asc"}})
    assert sorted(found["entity_guid"]["raw"] for found in met["results"]) == sorted([guids["orders"], guids["loose"]])
    assert (await engine.search(tab("0")))["meta"]["page"]["total_results"] == 0
