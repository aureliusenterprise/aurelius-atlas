"""DSL search against the dev Elasticsearch (DSE-07, DSE-08, DSE-12, DD-242).

``like`` is a Lucene ``regexp`` on Elasticsearch: on the keyword field for the whole value, on the analysed text
sub-field for a word; these check that Lucene reads the patterns as the in-memory documents read them.
"""

from typing import Any

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


def item(name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """A ``w_item`` named ``name``."""
    return {"typeName": "w_item", "guid": f"-{name}", "attributes": {"qualifiedName": name, **attributes}}


@pytest.mark.covers(
    "aurelius_atlas_core.dsl_query_composer.DslQueryComposer.compose",
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.search",
    rules=["DSE-07", "DSE-08", "DSE-12"],
)
async def test__dsl_queries_search_the_same_on_elasticsearch(dev_store: ElasticsearchStore, entity_prefix: str) -> None:
    """Words of the text sub-field in any case, whole values in case with ``/`` escaped, arrays, sorted."""
    store = EntityStore(
        sample_registry(writes=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    item("i1", count=1, label="a*lpha", tags=["x", "y"]),
                    item("i2", count=20, label="Alpha", tags=["y"]),
                    item("i3", count=3, label="gamma"),
                    item("i4", count=4, label="x-ray/1"),
                ]
            }
        )
    )
    service = EntityDiscoveryService(store)

    async def names(query: str) -> list[str]:
        found = (await service.search_using_dsl_query(query, 0, 0)).to_json()
        return [entity["attributes"]["qualifiedName"] for entity in found.get("entities", [])]

    assert sorted(await names("w_item where label like 'a*'")) == ["i1", "i2"]
    assert await names("w_item where label like 'A*lph?'") == ["i2"]
    assert await names("w_item where label like 'RAY'") == ["i4"]
    assert await names("w_item where label like 'x-ray*'") == ["i4"]
    assert await names("w_item where label like 'X-ray*'") == []
    assert await names("w_item where label like 'x-ray/*'") == ["i4"]
    assert sorted(await names("w_item where tags = 'y'")) == ["i1", "i2"]
    assert await names("w_item where `count` > 2 orderby `count` desc") == ["i2", "i4", "i3"]  # count is a keyword
