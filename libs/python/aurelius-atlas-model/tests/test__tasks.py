"""``AtlasTask`` (TSK-01), read from ``org.apache.atlas.model.tasks.AtlasTask`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.tasks import AtlasTask, TaskStatus


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["TSK-01"])
def test__a_task_reads_and_writes_atlas_json() -> None:
    """Times as epoch milliseconds, parameters as a map, nulls left out."""
    body = {
        "type": "CLASSIFICATION_PROPAGATION_ADD",
        "guid": "g",
        "createdBy": "admin",
        "createdTime": 1000,
        "updatedTime": 1000,
        "parameters": {"entityGuid": "e"},
        "attemptCount": 0,
        "status": "PENDING",
    }

    task = AtlasTask.model_validate(body)

    assert task.status is TaskStatus.PENDING
    assert task.to_json() == body
