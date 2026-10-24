"""``StoredTask``: a task as stored, Atlas's task vertex and the claim that runs it (TSK-01, DD-079, DD-080)."""

from typing import Any

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.tasks import AtlasTask, TaskStatus


class StoredTask(AtlasModel):
    """One document of the task index; times in epoch milliseconds; ``claimed_until`` the lease of its runner."""

    guid: str
    type: str
    created_by: str | None = None
    created_time: int = 0
    updated_time: int = 0
    start_time: int | None = None
    end_time: int | None = None
    parameters: dict[str, Any] | None = None
    attempt_count: int = 0
    error_message: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    claimed_until: int | None = None
    write_id: str | None = None

    def to_task(self) -> AtlasTask:
        """The task as ``admin/tasks`` answers it."""
        return AtlasTask.model_validate(
            {
                "type": self.type,
                "guid": self.guid,
                "createdBy": self.created_by,
                "createdTime": self.created_time,
                "updatedTime": self.updated_time,
                "startTime": self.start_time,
                "endTime": self.end_time,
                "parameters": self.parameters,
                "attemptCount": self.attempt_count,
                "errorMessage": self.error_message,
                "status": self.status,
            }
        )
