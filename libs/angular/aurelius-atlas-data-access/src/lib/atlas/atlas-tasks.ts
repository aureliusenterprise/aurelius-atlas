/**
 * Atlas task DTOs — the wire shapes of `/api/atlas/admin/tasks` (TSK-01,
 * APC-03).
 *
 * Field names are the camelCase Java getter names the server writes, mirrored
 * from `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/tasks.py`,
 * ported from Apache Atlas 2.4.0 `org.apache.atlas.model.tasks.AtlasTask`):
 * keep the two in step when the Python model changes. The times are epoch
 * milliseconds (TDM-05). The Python twin of this cluster is
 * `AtlasClient.admin.tasks` (CL-11, CLW-06).
 */

/** The state of a task (`AtlasTask.Status`). */
export type TaskStatus = "PENDING" | "IN_PROGRESS" | "COMPLETE" | "FAILED";

/** A task: its type, creator, times, parameters, attempts, last error and status. */
export type AtlasTask = {
    type?: string | null;
    guid?: string | null;
    createdBy?: string | null;
    /** Epoch milliseconds. */
    createdTime?: number | null;
    /** Epoch milliseconds. */
    updatedTime?: number | null;
    /** Epoch milliseconds. */
    startTime?: number | null;
    /** Epoch milliseconds. */
    endTime?: number | null;
    parameters?: Record<string, unknown> | null;
    attemptCount?: number | null;
    errorMessage?: string | null;
    status?: TaskStatus | null;
};
