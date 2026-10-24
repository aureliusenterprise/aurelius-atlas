"""Relationships against the dev Elasticsearch (REL-05, REL-06, REL-08, REL-09, REL-10).

Relationships are written with their ends in one bulk request over two indices (DD-061, DD-062), read in real time,
deleted softly and removed with a purged end.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.errors import AtlasError
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasRelationship, RelationshipStatus
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

R = "aurelius_atlas_core.relationship_store.RelationshipStore"


def entity(type_name: str, guid: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An entity as Atlas JSON."""
    return {"typeName": type_name, "guid": guid, "attributes": attributes}


@pytest.mark.covers(
    f"{R}.create", f"{R}.get_by_id", f"{R}.delete_by_id", rules=["REL-05", "REL-06", "REL-08", "REL-09", "REL-10"]
)
async def test__relationships_live_with_their_ends_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Created and listed by both ends, read at once, soft-deleted, removed when an end is purged."""
    store = EntityStore(sample_registry(), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix))
    await store.prepare()
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    entity("s_table", "-1", qualifiedName="t@cl"),
                    entity("s_database", "-2", qualifiedName="d@cl"),
                ]
            }
        )
    )
    table, database = (created.guid_assignments or {})["-1"], (created.guid_assignments or {})["-2"]
    relationships = RelationshipStore(store)

    home = await relationships.create(
        AtlasRelationship.model_validate(
            {"typeName": "s_table_home", "end1": {"guid": table}, "end2": {"guid": database}}
        )
    )
    guid = str(home.guid)
    read = await relationships.get_by_id(guid)
    ends = await store.get_many([table, database])

    assert read.end2 is not None
    assert read.end2.unique_attributes == {"qualifiedName": "d@cl"}
    assert all(found.entity.relationship_guids == [guid] for found in ends.values())
    assert await store.type_in_use("s_table_home")

    await relationships.delete_by_id(guid)
    assert (await relationships.get_by_id(guid)).status is RelationshipStatus.DELETED
    await EntityWriter(store).delete_by_id(database)
    await EntityWriter(store).purge_by_ids([database])
    with pytest.raises(AtlasError, match="invalid/not found"):
        await relationships.get_by_id(guid)
    remaining = await store.get(table)
    assert remaining is not None
    assert remaining.entity.relationship_guids is None
    assert not await store.type_in_use("s_table_home")
