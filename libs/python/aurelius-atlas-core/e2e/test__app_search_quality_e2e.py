"""The quality results and score totals on the dev Elasticsearch (ASQ-02 to ASQ-05), in indices of their own per
test.

What only a real Elasticsearch shows: the listings of the scores and holders, the mapping of the result and the
totals, a field page's request on ``atlas-dev-quality``, and a sort on a score field that documents without totals
take part in as 0.
"""  # noqa: D205 - one sentence

import pytest
from aurelius_atlas_core.app_search_engine import ATLAS_DEV_QUALITY, AppSearchEngine
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.app_search_quality import QualityIndexer
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


def m4i(type_name: str, key: str, values: dict[str, object] | None = None, **relations: list[str]) -> AtlasEntity:
    """An entity named after ``key`` with ``values``, and relationship attributes naming others of the request."""
    return AtlasEntity(
        type_name=type_name,
        guid=f"-{key}",
        attributes={"qualifiedName": f"e2e--{key}", "name": key.title()} | (values or {}),
        relationship_attributes={
            name: [AtlasObjectId(guid=f"-{other}") for other in others] for name, others in relations.items()
        },
    )


# impact=major, likelihood=high (a quality rule misfires; the only e2e proof, and the path churns with its increment)
@pytest.mark.high
@pytest.mark.covers(rules=["ASQ-02", "ASQ-03", "ASQ-04", "ASQ-05"])
async def test__a_scored_rule_s_result_answers_the_field_page_and_its_totals_sort_the_domains(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """A rule over a field, scored by the scanner: its result on the field page; its domain first by score."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for models_dir in (BUILTIN_MODELS_DIR, M4I_MODELS_DIR):
        await ModelLoader(types).load(models_dir)
    documents = ElasticsearchEntityDocuments(dev_store.client, entity_prefix)
    store = EntityStore(types.registry, documents)
    await store.prepare()
    writer = EntityWriter(store, user="e2e")
    rule = {"id": 3, "active": True, "qualityDimension": "Completeness", "expression": "completeness('id')"}
    response = await writer.create_or_update(
        AtlasEntitiesWithExtInfo(
            entities=[
                m4i("m4i_data_domain", "sales"),
                m4i("m4i_data_domain", "finance"),
                m4i("m4i_data_entity", "order", dataDomain=["sales"]),
                m4i("m4i_data_attribute", "order_id", dataEntity=["order"]),
                m4i("m4i_dataset", "orders"),
                m4i("m4i_field", "id", datasets=["orders"], attributes=["order_id"]),
                m4i("m4i_data_quality", "rule", rule, fields=["id"]),
            ]
        )
    )
    guids = {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}
    score = {"scoreKey": "e2e", "verdict": "PASS", "score": 0.8, "ruleGuid": guids["rule"]}
    await writer.create_or_update(
        AtlasEntitiesWithExtInfo(
            entities=[
                AtlasEntity(
                    type_name="m4i_dq_score",
                    attributes={"qualifiedName": "e2e--score"} | score | {"datasetGuid": guids["orders"]},
                )
            ]
        )
    )
    await AppSearchIndexer(documents, types.registry).run_once()
    quality = QualityIndexer(documents)

    assert await quality.run_once() > 0
    assert await quality.run_once() == 0

    page = await AppSearchEngine(documents, ATLAS_DEV_QUALITY).search(
        {
            "filters": {"all": [{"fieldguid": [guids["id"]]}]},
            "facets": {"dataqualityruledimension": {"type": "value"}},
            "sort": [{"dqscore": "desc"}],
            "result_fields": {name: {"raw": {}} for name in ("guid", "name", "dqscore", "datadomainname")},
        }
    )
    (result,) = page["results"]
    assert (result["guid"], result["name"], result["dqscore"]) == (
        {"raw": guids["rule"]},
        {"raw": "Rule"},
        {"raw": 0.8},
    )
    assert result["datadomainname"] == {"raw": "Sales"}
    assert page["facets"]["dataqualityruledimension"] == [
        {"type": "value", "data": [{"value": "Completeness", "count": 1}]}
    ]

    domains = await AppSearchEngine(documents).search(
        {
            "filters": {"typename": ["m4i_data_domain"]},
            "sort": [{"dqscore_overall": "desc"}],
            "result_fields": {"dqscore_completeness": {"raw": {}}, "dqscorecnt_overall": {"raw": {}}},
        }
    )
    assert [found["id"]["raw"] for found in domains["results"]] == [guids["sales"], guids["finance"]]
    assert [found["dqscore_completeness"]["raw"] for found in domains["results"]] == [0.8, 0.0]
    assert [found["dqscorecnt_overall"]["raw"] for found in domains["results"]] == [1.0, 0.0]
