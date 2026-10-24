"""Propagation tasks against the dev Elasticsearch (TSK-02, TSK-04, TSK-05, DD-079, DD-080).

A task is found by searching the task index after a refresh, claimed by a conditional write, and run.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


def data(guid: str, name: str) -> dict[str, Any]:
    """A ``p_data`` entity."""
    return {"typeName": "p_data", "guid": guid, "attributes": {"qualifiedName": name}}


@pytest.mark.covers(
    "aurelius_atlas_core.task_management.TaskManagement.run_pending",
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.list_tasks",
    rules=["TSK-02", "TSK-04", "TSK-05"],
)
async def test__a_task_is_claimed_and_run_on_elasticsearch(dev_store: ElasticsearchStore, entity_prefix: str) -> None:
    """Added to an input, ``c_pii`` reaches the output once its task ran; a second runner finds nothing to do."""
    store = EntityStore(
        sample_registry(classifications=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    process = {
        "typeName": "p_process",
        "guid": "-3",
        "attributes": {"qualifiedName": "p@tk"},
        "relationshipAttributes": {"inputs": [{"guid": "-1"}], "outputs": [{"guid": "-2"}]},
    }
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": [data("-1", "a@tk"), data("-2", "b@tk"), process]})
    )
    guids = created.guid_assignments or {}
    classifier = EntityClassifications(store, tasks=True)

    await classifier.add_classifications(guids["-1"], [AtlasClassification(type_name="c_pii")])
    waiting = await store.list_tasks(open_only=True)
    before = await classifier.get_classifications(guids["-2"])
    ran = await TaskManagement(store).run_pending()
    again = await TaskManagement(store).run_pending()

    assert [task.type for task, _ in waiting] == ["CLASSIFICATION_PROPAGATION_ADD"]
    assert (before, ran, again) == ([], 1, 0)
    assert [c.type_name for c in await classifier.get_classifications(guids["-2"])] == ["c_pii"]
    assert await store.list_tasks() == []
