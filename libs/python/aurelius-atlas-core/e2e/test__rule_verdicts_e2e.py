"""A rule's stored verdicts through the verdicts door, on the dev Elasticsearch (ASG-09, VDR-14, DD-845).

What only a real Elasticsearch shows: the paged terms read over the verdicts' index by rule GUID, in document
id order, and the door's rows over it — the read the rule page's two card lists and its chart ride (7.25b).
"""

import pytest
from aurelius_atlas_core.app_search_governance import GovernanceIndexer
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.documents_es import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_core.view_rule import ViewRuleEngine
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity
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
@pytest.mark.covers(
    "aurelius_atlas_core.documents_es.ElasticsearchEntityDocuments.verdicts_by_rule",
    "aurelius_atlas_core.view_rule.ViewRuleEngine.verdicts",
    rules=["ASG-09", "VDR-14", "AVS-12"],
)
async def test__the_verdicts_door_answers_a_rule_s_rows_from_the_worker_s_round(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Two judged datasets, one answer per verdict in id order; a rule none of answers none (ASG-09, VDR-14)."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for models_dir in (BUILTIN_MODELS_DIR, M4I_MODELS_DIR):
        await ModelLoader(types).load(models_dir)
    documents = ElasticsearchEntityDocuments(dev_store.client, entity_prefix)
    store = EntityStore(types.registry, documents)
    await store.prepare()
    writer = EntityWriter(store, user="e2e")
    response = await writer.create_or_update(
        AtlasEntitiesWithExtInfo(
            entities=[
                m4i(
                    "m4i_gov_data_quality",
                    "name-filled",
                    {
                        "qualifiedName": "m4i_dataset--e2e-name-filled",
                        "expression": "length('name', 1)",
                        "ruleType": "attribute",
                        "qualityDimension": "completeness",
                        "nonCompliantMessage": "The dataset carries no name",
                        "active": True,
                        "id": 1,
                    },
                ),
                # The second rule judges nothing of this corpus: the worker's round leaves it unheld.
                m4i(
                    "m4i_gov_data_quality",
                    "unused",
                    {
                        "qualifiedName": "m4i_system--e2e-unused",
                        "expression": "length('name', 1)",
                        "ruleType": "attribute",
                        "qualityDimension": "completeness",
                        "nonCompliantMessage": "The system carries no name",
                        "active": False,
                        "id": 2,
                    },
                ),
                m4i("m4i_dataset", "orders"),
            ]
        )
    )
    guids = {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}
    await AppSearchIndexer(documents, types.registry).run_once()
    governance = GovernanceIndexer(documents, types.registry)
    assert await governance.run_once() == 1  # ASG-06: the worker judged the dataset over the active rule

    door = ViewRuleEngine(documents)
    answer = await door.verdicts({"rule": guids["name-filled"]})
    (row,) = answer["verdicts"]
    assert row["entity"] == guids["orders"]
    assert row["compliant"] is True  # the dataset carries a name, so the rule passes it (ASG-03)
    assert row["name"] == "Name-Filled"
    assert row["message"] == "The dataset carries no name"  # the non-compliant line the document copies (AVS-12)

    assert await door.verdicts({"rule": guids["unused"]}) == {"verdicts": []}
    # An inactive rule judges nothing, and the door never reads the rule to know that (VDR-14, ADR 071 R2).
    assert await door.verdicts({"rule": guids["orders"]}) == {"verdicts": []}
