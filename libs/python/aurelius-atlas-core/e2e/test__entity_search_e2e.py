"""Entity search against the dev Elasticsearch (SRC-05, SRC-07, DD-088, DD-089).

The search fields are mapped by the dynamic templates of their kind, and each test of the search query selects
on Elasticsearch what it selects in memory.
"""

from typing import Any

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


def item(name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """A ``w_item`` named ``name``."""
    return {"typeName": "w_item", "guid": f"-{name}", "attributes": {"qualifiedName": name, **attributes}}


def where(name: str, operator: str, value: str | None = None) -> dict[str, Any]:
    """An entity filter on one attribute."""
    return {"attributeName": name, "operator": operator, "attributeValue": value}


@pytest.mark.covers(
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.search",
    "aurelius_atlas_core.discovery_service.EntityDiscoveryService.search_with_parameters",
    rules=["SRC-05", "SRC-07"],
)
async def test__items_are_searched_by_their_typed_fields_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Numbers range, strings match case-sensitively with wildcards escaped, arrays by element, sorted and counted."""
    store = EntityStore(
        sample_registry(writes=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    item("i1", count=1, flag=True, label="a*lpha", tags=["x", "y"]),
                    item("i2", count=20, flag=False, label="Alpha", tags=["y"]),
                    item("i3", count=3, label="gamma"),
                ]
            }
        )
    )
    service = EntityDiscoveryService(store)

    async def names(**body: Any) -> list[str]:  # noqa: ANN401 - Atlas JSON
        found = (await service.search_with_parameters(SearchParameters.model_validate(body))).to_json()
        return [entity["attributes"]["qualifiedName"] for entity in found.get("entities", [])]

    item_type = {"typeName": "w_item"}
    assert await names(**item_type, sortBy="count", sortOrder="DESCENDING") == ["i2", "i3", "i1"]
    assert sorted(await names(**item_type, entityFilters=where("count", ">=", "3"))) == ["i2", "i3"]
    assert await names(**item_type, entityFilters=where("label", "contains", "*")) == ["i1"]
    assert await names(**item_type, entityFilters=where("label", "startsWith", "Al")) == ["i2"]
    assert await names(**item_type, entityFilters=where("label", "endsWith", "lpha"), sortBy="label") == ["i2", "i1"]
    assert sorted(await names(**item_type, entityFilters=where("tags", "contains", "y"))) == ["i1", "i2"]
    assert await names(**item_type, entityFilters=where("tags", "isNull")) == ["i3"]
    assert await names(**item_type, entityFilters=where("flag", "=", "true")) == ["i1"]
    assert sorted(await names(**item_type, entityFilters=where("__state", "=", "ACTIVE"))) == ["i1", "i2", "i3"]
    assert await names(typeName="s_ref", includeSubTypes=False) == []
    assert len(await names(typeName="_ALL_ENTITY_TYPES", limit=2)) == 2


@pytest.mark.covers(
    "aurelius_atlas_core.classification_search_processor.ClassificationSearchProcessor.criterion",
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.classifications_of_types",
    rules=["CSR-02", "CSR-03", "CSR-05"],
)
async def test__entities_are_searched_by_classification_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Attached and propagated, by wildcard ignoring case, by tag filters, and none."""
    store = EntityStore(
        sample_registry(classifications=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    process = {
        "typeName": "p_process",
        "guid": "-p",
        "attributes": {"qualifiedName": "p@cs"},
        "relationshipAttributes": {"inputs": [{"guid": "-a"}], "outputs": [{"guid": "-b"}]},
    }
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    {"typeName": "p_data", "guid": "-a", "attributes": {"qualifiedName": "a@cs"}},
                    {"typeName": "p_data", "guid": "-b", "attributes": {"qualifiedName": "b@cs"}},
                    {"typeName": "p_data", "guid": "-c", "attributes": {"qualifiedName": "c@cs"}},
                    process,
                ]
            }
        )
    )
    guids = created.guid_assignments or {}
    await EntityClassifications(store).add_classifications(
        guids["-a"], [AtlasClassification.model_validate({"typeName": "c_pii", "attributes": {"level": 4}})]
    )
    service = EntityDiscoveryService(store)

    async def names(**body: Any) -> list[str]:  # noqa: ANN401 - Atlas JSON
        found = (await service.search_with_parameters(SearchParameters.model_validate(body))).to_json()
        return sorted(entity["attributes"]["qualifiedName"] for entity in found.get("entities", []))

    level = {"attributeName": "level", "operator": ">", "attributeValue": "3"}
    assert await names(classification="c_pii") == ["a@cs", "b@cs", "p@cs"]
    assert await names(classification="C_P*", typeName="p_data") == ["a@cs", "b@cs"]
    assert await names(classification="c_pii", tagFilters=level) == ["a@cs", "b@cs", "p@cs"]
    assert await names(classification="_NOT_CLASSIFIED", typeName="p_data") == ["c@cs"]
    assert await names(typeName="p_data", entityFilters=where("__classificationNames", "=", "c_pii")) == ["a@cs"]


@pytest.mark.covers(
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.search",
    "aurelius_atlas_core.discovery_service.EntityDiscoveryService.search_using_full_text",
    rules=["FTX-02", "FTX-03", "FTX-04", "FTX-05"],
)
async def test__entities_are_found_by_free_text_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """The analysed text sub-fields match words in any case and by prefix, the heavier field first."""
    registry = sample_registry(classifications=True)
    with registry.update() as transient:
        transient.add_types(
            AtlasTypesDef.model_validate(
                {
                    "entityDefs": [
                        {
                            "name": "f_doc",
                            "superTypes": ["s_ref"],
                            "attributeDefs": [
                                {"name": "title", "typeName": "string", "isOptional": True, "searchWeight": 9},
                                {"name": "body", "typeName": "string", "isOptional": True},
                            ],
                        }
                    ]
                }
            )
        )
    store = EntityStore(registry, ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix))
    await store.prepare()

    def doc(name: str, title: str, body: str) -> dict[str, Any]:
        return {
            "typeName": "f_doc",
            "guid": f"-{name}",
            "attributes": {"qualifiedName": name, "title": title, "body": body},
        }

    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {"entities": [doc("d1", "Quarterly Sales", "numbers"), doc("d2", "Customers", "sales contacts")]}
        )
    )
    guids = created.guid_assignments or {}
    await EntityClassifications(store).add_classifications(
        guids["-d2"], [AtlasClassification.model_validate({"typeName": "c_pii", "attributes": {"level": 4}})]
    )
    service = EntityDiscoveryService(store)

    async def names(**body: Any) -> list[str]:  # noqa: ANN401 - Atlas JSON
        found = (await service.search_with_parameters(SearchParameters.model_validate(body))).to_json()
        return [entity["attributes"]["qualifiedName"] for entity in found.get("entities", [])]

    full_text = (
        await service.search_using_full_text("SALES", exclude_deleted_entities=True, limit=10, offset=0)
    ).to_json()

    assert await names(query="sales") == ["d1", "d2"]
    assert await names(query="CUSTOM*", typeName="f_doc") == ["d2"]
    assert await names(query="c_pii") == ["d2"]
    assert await names(query="numbers", classification="c_pii") == []
    assert [found["entity"]["attributes"]["qualifiedName"] for found in full_text["fullTextResult"]] == ["d1", "d2"]
    assert full_text["approximateCount"] == 2
    assert full_text["fullTextResult"][0]["score"] > full_text["fullTextResult"][1]["score"] > 0
