"""Classifications against the dev Elasticsearch (CLS-02, CLS-05, CLS-09, CLS-11, CLS-12).

Instances are documents of their own index, written with their entity in one bulk request (DD-070, DD-071), read
in real time, and deleted with the entity.
"""

import pytest
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo, EntityStatus
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

C = "aurelius_atlas_core.entity_classifications.EntityClassifications"


@pytest.mark.covers(
    f"{C}.add_classifications", f"{C}.delete_classification", rules=["CLS-02", "CLS-05", "CLS-09", "CLS-11", "CLS-12"]
)
async def test__classifications_live_with_their_entity_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Added and read at once, removed, kept ``DELETED`` by a soft delete, counted for the type until purged."""
    store = EntityStore(
        sample_registry(classifications=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {"entities": [{"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@cl"}}]}
        )
    )
    guid = (created.guid_assignments or {})["-1"]
    classifier = EntityClassifications(store)

    await classifier.add_classifications(
        guid, [AtlasClassification(type_name="c_pii"), AtlasClassification(type_name="c_tabular")]
    )
    first = [found.type_name for found in await classifier.get_classifications(guid)]
    await classifier.delete_classification(guid, "c_tabular")
    await EntityWriter(store).delete_by_id(guid)
    deleted = await classifier.get_classifications(guid)
    in_use = await store.type_in_use("c_pii")
    await EntityWriter(store).purge_by_ids([guid])

    assert first == ["c_pii", "c_tabular"]
    assert [(found.type_name, found.entity_status) for found in deleted] == [("c_pii", EntityStatus.DELETED)]
    assert in_use
    assert not await store.type_in_use("c_pii")
