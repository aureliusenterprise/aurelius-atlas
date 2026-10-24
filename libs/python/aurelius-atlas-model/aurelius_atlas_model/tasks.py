"""``AtlasTask``: deferred work, as Atlas answers it from ``admin/tasks`` (TSK-01).

Ported from Apache Atlas 2.4.0 ``org.apache.atlas.model.tasks.AtlasTask``.
"""

from enum import StrEnum
from typing import Any

from aurelius_atlas_model.base import AtlasModel, JavaInt, Timestamp

MAX_ATTEMPT_COUNT = 3
"""``AtlasTask.MAX_ATTEMPT_COUNT``: a task is ``FAILED`` from its third failed attempt (TSK-05)."""


class TaskStatus(StrEnum):
    """``AtlasTask.Status``."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class AtlasTask(AtlasModel):
    """A task: its type, creator, times, parameters, attempts, last error and status."""

    type: str | None = None
    guid: str | None = None
    created_by: str | None = None
    created_time: Timestamp | None = None
    updated_time: Timestamp | None = None
    start_time: Timestamp | None = None
    end_time: Timestamp | None = None
    parameters: dict[str, Any] | None = None
    attempt_count: JavaInt = 0
    error_message: str | None = None
    status: TaskStatus | None = None
