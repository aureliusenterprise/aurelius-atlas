"""Entity search against the dev Elasticsearch (SRC-05, SRC-07, DD-088, DD-089).

The search fields are mapped by the dynamic templates of their kind, and each test of the search query selects
on Elasticsearch what it selects in memory.
"""

from typing import Any

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
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
