/**
 * Atlas patch-record DTOs — the wire shapes of `/api/atlas/admin/patches`
 * (ENS-10, APC-03).
 *
 * Field names are the camelCase Java getter names the server writes, mirrored
 * from `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/patches.py`,
 * ported from Apache Atlas 2.4.0 `org.apache.atlas.model.patches`): keep the
 * two in step when the Python model changes. The Python twin of this cluster
 * is `AtlasClient.admin.patches` (CL-11, CLW-01).
 */

/** How a patch ended (`AtlasPatch.PatchStatus`). */
export type PatchStatus = "UNKNOWN" | "APPLIED" | "SKIPPED" | "FAILED";

/**
 * The record of one applied typedef patch (`AtlasPatch`); the times are epoch
 * milliseconds.
 */
export type AtlasPatch = {
    /** The unique id of the patch. */
    id?: string | null;
    /** A description of the patch. */
    description?: string | null;
    /** The kind of patch; typedef patches use `TYPEDEF_PATCH`. */
    type?: string | null;
    /** The action the patch performs, e.g. `ADD_ATTRIBUTE`. */
    action?: string | null;
    /** The user who applied the patch. */
    updatedBy?: string | null;
    /** The user who defined the patch. */
    createdBy?: string | null;
    /** When the patch was defined, in epoch milliseconds. */
    createdTime?: number | null;
    /** When the patch was applied, in epoch milliseconds. */
    updatedTime?: number | null;
    /** How the patch ended. */
    status?: PatchStatus | null;
};
