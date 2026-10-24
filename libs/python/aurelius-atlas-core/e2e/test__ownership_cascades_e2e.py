"""Owned entities an update drops, against the dev Elasticsearch (OWN-01 to OWN-03).

The deletes are written with the update in one bulk request (DD-068); the referring entities are found by the
search of DD-057 and read through the request's view.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, EntityStatus
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


def request(*entities: dict[str, Any]) -> AtlasEntitiesWithExtInfo:
    """A bulk write of these entities."""
    return AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)})


@pytest.mark.covers(
    "aurelius_atlas_core.entity_writer.EntityWriter.create_or_update", rules=["OWN-01", "OWN-02", "OWN-03"]
)
async def test__an_update_deletes_the_owned_entities_it_drops_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """A plain owned column and an owned part through a relationship; a referrer of the column is changed."""
    store = EntityStore(
        sample_registry(relationships=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    writer = EntityWriter(store)
    column = {"typeName": "s_column", "guid": "-1", "attributes": {"qualifiedName": "c@cl"}}
    node = {"typeName": "r_node", "guid": "-2", "attributes": {"qualifiedName": "n@cl", "owns": [{"guid": "-1"}]}}
    part = {
        "typeName": "r_part",
        "guid": "-3",
        "attributes": {"qualifiedName": "p@cl"},
        "relationshipAttributes": {"whole": {"guid": "-2", "typeName": "r_node"}},
    }
    peer = {"typeName": "w_item", "guid": "-4", "attributes": {"qualifiedName": "i@cl", "peers": [{"guid": "-1"}]}}
    guids = (await writer.create_or_update(request(column, node, part, peer))).guid_assignments or {}

    answer = await writer.create_or_update(
        request(
            {
                "typeName": "r_node",
                "guid": guids["-2"],
                "attributes": {"qualifiedName": "n@cl", "owns": []},
                "relationshipAttributes": {"parts": []},
            }
        )
    )
    mutated = codec.loads(codec.dumps(answer.to_json()))["mutatedEntities"]
    found = await store.get_many([guids["-1"], guids["-3"]])

    assert [header["guid"] for header in mutated["DELETE"]] == [guids["-3"], guids["-1"]]
    assert [header["guid"] for header in mutated["UPDATE"]] == [guids["-2"], guids["-4"]]
    assert {found[guid].entity.state for guid in found} == {EntityStatus.DELETED}
