"""Classification propagation against the dev Elasticsearch (PRO-03, PRO-07, PRO-10, DD-076).

The entities a classification reached are found by searching ``classificationGuids`` after a refresh.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


def data(guid: str, name: str) -> dict[str, Any]:
    """A ``p_data`` entity."""
    return {"typeName": "p_data", "guid": guid, "attributes": {"qualifiedName": name}}


@pytest.mark.covers(
    "aurelius_atlas_core.tag_propagation.TagPropagation.remove_all", rules=["PRO-03", "PRO-07", "PRO-10"]
)
async def test__a_classification_propagates_and_is_found_again_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Added to an input, it reaches the output; removing it there finds the output by search and unlists it."""
    store = EntityStore(
        sample_registry(classifications=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    process = {
        "typeName": "p_process",
        "guid": "-3",
        "attributes": {"qualifiedName": "p@cl"},
        "relationshipAttributes": {"inputs": [{"guid": "-1"}], "outputs": [{"guid": "-2"}]},
    }
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": [data("-1", "a@cl"), data("-2", "b@cl"), process]})
    )
    guids = created.guid_assignments or {}
    classifier = EntityClassifications(store)

    await classifier.add_classifications(guids["-1"], [AtlasClassification(type_name="c_pii")])
    reached = [c.entity_guid for c in await classifier.get_classifications(guids["-2"])]
    await classifier.delete_classification(guids["-1"], "c_pii")

    assert reached == [guids["-1"]]
    assert await classifier.get_classifications(guids["-2"]) == []
    assert not await store.type_in_use("c_pii")
