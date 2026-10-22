"""The entity retriever against the dev Elasticsearch (ERD-03 to ERD-07, ERD-09).

Entities read back from Elasticsearch answer exactly as those read back from the in-memory documents, whose
answers the unit tests check against Atlas.
"""

from decimal import Decimal

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.testing.entity_samples import sample_entities, sample_entity, sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

R = "aurelius_atlas_core.entity_retriever.EntityRetriever"


async def seeded(store: EntityStore) -> EntityStore:
    """``store`` holding the sample entities and a table whose sizes need their digits kept."""
    exact = sample_entity(store.registry, "s_table", "x", {"qualifiedName": "x@cl", "sizes": [Decimal("0.10")]})
    await store.prepare()
    await store.write([EntityChange(entity) for entity in [*sample_entities(store.registry), exact]])
    return store


@pytest.mark.covers(
    f"{R}.entity_with_ext_info",
    f"{R}.entities_by_unique_attributes",
    f"{R}.header",
    rules=["ERD-03", "ERD-04", "ERD-05", "ERD-06", "ERD-07", "ERD-09"],
)
async def test__entities_read_from_elasticsearch_as_from_memory(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Full and minimal reads, headers and unique-attribute reads give the same JSON on both documents."""
    elastic = await seeded(
        EntityStore(sample_registry(), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix))
    )
    memory = await seeded(EntityStore(sample_registry(), MemoryEntityDocuments()))
    column_type = memory.registry.entity_type("s_column")
    assert column_type is not None

    answers = []
    for store in (elastic, memory):
        full, minimal = EntityRetriever(store), EntityRetriever(store, min_ext_info=True, ignore_relationships=True)
        answers.append(
            [
                (await full.entity_with_ext_info("t")).to_json(),
                (await minimal.entity_with_ext_info("t")).to_json(),
                (await full.entity_with_ext_info("x")).to_json(),
                (await full.header("t")).to_json(),
                (await full.entities_by_unique_attributes(column_type, [{"qualifiedName": "c2@cl"}])).to_json(),
            ]
        )

    assert answers[0] == answers[1]
    assert answers[0][2]["entity"]["attributes"]["sizes"] == [Decimal("0.10")]
