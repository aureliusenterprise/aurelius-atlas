"""The entity writer against the dev Elasticsearch (EWR-06, EWR-10, EWR-13, EWR-16).

Entities written to Elasticsearch read back exactly as those written to the in-memory documents, whose answers the
unit tests check against Atlas; two writers racing on one entity both get their change in (DD-052).
"""

import asyncio
from itertools import count
from typing import Any

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntityWithExtInfo
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

W = "aurelius_atlas_core.entity_writer.EntityWriter"

CREATE = {
    "entities": [
        {"typeName": "s_database", "guid": "-1", "attributes": {"qualifiedName": "db@cl"}},
        {
            "typeName": "s_table",
            "guid": "-2",
            "attributes": {
                "qualifiedName": "t@cl",
                "db": {"guid": "-1", "typeName": "s_database"},
                "columns": [{"guid": "-3", "typeName": "s_column"}],
                "place": {"typeName": "s_place", "attributes": {"x": 1, "label": "p"}},
                "sizes": [0.10, 2],
            },
        },
    ],
    "referredEntities": {"-3": {"typeName": "s_column", "guid": "-3", "attributes": {"qualifiedName": "c@cl"}}},
}
UPDATE = {
    "entities": [
        {"typeName": "s_table", "guid": "-9", "attributes": {"qualifiedName": "t@cl", "place": {"label": "q"}}}
    ]
}


def as_json(value: Any) -> Any:  # noqa: ANN401 - Atlas JSON
    """A model's JSON as a client reads it."""
    return codec.loads(codec.dumps(value.to_json()))


async def answers(store: EntityStore) -> list[Any]:
    """Create, update and read back the sample entities; the table's GUID is the second one given."""
    writer = EntityWriter(store)
    await store.prepare()
    created = await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate(codec.loads(codec.dumps(CREATE))))
    updated = await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate(UPDATE))
    assert created.guid_assignments is not None
    table = created.guid_assignments["-2"]
    read = await EntityRetriever(store).entity_with_ext_info(table)
    return [as_json(created), as_json(updated), as_json(read)]


def numbered() -> Any:  # noqa: ANN401 - a GUID source
    """GUIDs ``n0``, ``n1``, … for both stores alike."""
    numbers = count()
    return lambda: f"n{next(numbers)}"


@pytest.mark.covers(f"{W}.create_or_update", rules=["EWR-06", "EWR-10", "EWR-13"])
async def test__entities_written_to_elasticsearch_read_back_as_from_memory(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """The same answers on both documents, timestamps aside; decimals keep their digits."""
    elastic = EntityStore(
        sample_registry(),
        ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix),
        clock=lambda: 2.0,
        new_id=numbered(),
    )
    memory = EntityStore(sample_registry(), MemoryEntityDocuments(), clock=lambda: 2.0, new_id=numbered())

    from_elastic, from_memory = await answers(elastic), await answers(memory)

    assert from_elastic == from_memory
    assert from_elastic[2]["entity"]["attributes"]["place"]["attributes"]["label"] == "q"


@pytest.mark.covers(f"{W}.update_by_unique_attributes", rules=["EWR-16"])
async def test__two_writers_racing_on_one_entity_both_get_their_change_in(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Partial updates of different attributes at once: the loser runs again on the winner's state."""
    store = EntityStore(sample_registry(), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix))
    await store.prepare()
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {"entities": [{"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "r@cl"}}]}
        )
    )
    assert created.guid_assignments is not None
    table_type = store.registry.entity_type("s_table")
    assert table_type is not None

    def update(**attributes: Any) -> Any:  # noqa: ANN401 - a coroutine
        entity = AtlasEntityWithExtInfo.model_validate({"entity": {"typeName": "s_table", "attributes": attributes}})
        return EntityWriter(store).update_by_unique_attributes(table_type, {"qualifiedName": "r@cl"}, entity)

    await asyncio.gather(update(name="named"), update(color="RED"))

    read = await EntityRetriever(store).entity_with_ext_info(created.guid_assignments["-1"])
    assert read.entity is not None
    assert (read.entity.get_attribute("name"), read.entity.get_attribute("color")) == ("named", "RED")
