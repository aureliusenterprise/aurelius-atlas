"""Relationship attributes against the dev Elasticsearch (REL-11, REL-12, REL-14, REL-17, REL-19).

An entity write creates relationships with its entities in one bulk request (DD-066); reads find them through the
ends' lists in real time; replacing one deletes it softly; deleting a whole deletes its parts through them.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


def entity(type_name: str, guid: str, relationships: dict[str, Any] | None = None, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401
    """An entity as Atlas JSON."""
    return {"typeName": type_name, "guid": guid, "attributes": attributes, "relationshipAttributes": relationships}


def request(*entities: dict[str, Any]) -> AtlasEntitiesWithExtInfo:
    """A bulk write of these entities."""
    return AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)})


async def read(store: EntityStore, guid: str) -> dict[str, Any]:
    """The entity as ``GET /entity/guid`` answers it."""
    found = await EntityRetriever(store).entity_with_ext_info(guid)
    return codec.loads(codec.dumps(found.to_json()))["entity"]


@pytest.mark.covers(
    "aurelius_atlas_core.relationship_mapper.RelationshipMapper.map",
    rules=["REL-11", "REL-12", "REL-14", "REL-17", "REL-19"],
)
async def test__relationship_attributes_live_as_relationships_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Created with their entities, read from both ends, replaced softly, and followed by a delete's cascade."""
    store = EntityStore(
        sample_registry(relationships=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    writer = EntityWriter(store)
    created = await writer.create_or_update(
        request(
            entity("s_database", "-1", qualifiedName="d1@cl"),
            entity("s_database", "-2", qualifiedName="d2@cl"),
            entity("r_node", "-3", qualifiedName="n@cl", keeper={"guid": "-1", "typeName": "s_database"}),
            entity("r_part", "-4", {"whole": {"guid": "-3", "typeName": "r_node"}}, qualifiedName="p@cl"),
        )
    )
    guids = created.guid_assignments or {}
    node, part = guids["-3"], guids["-4"]

    first = await read(store, node)
    await writer.create_or_update(
        request(entity("r_node", node, qualifiedName="n@cl", keeper={"guid": guids["-2"], "typeName": "s_database"}))
    )
    moved = await read(store, guids["-1"])
    deleted = await writer.delete_by_id(node)

    assert first["attributes"]["keeper"]["guid"] == guids["-1"]
    assert [found["guid"] for found in first["relationshipAttributes"]["parts"]] == [part]
    assert [found["relationshipStatus"] for found in moved["relationshipAttributes"]["kept"]] == ["DELETED"]
    answer = codec.loads(codec.dumps(deleted.to_json()))
    assert [header["guid"] for header in answer["mutatedEntities"]["DELETE"]] == [node, part]
