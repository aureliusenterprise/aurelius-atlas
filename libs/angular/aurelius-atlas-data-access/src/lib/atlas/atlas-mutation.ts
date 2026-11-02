/**
 * The entity-mutation answer DTOs — the wire shape every entity write and
 * `PUT /api/atlas/admin/purge` answers (ENT-17, EDL-01, APC-03).
 *
 * Mirrored from `libs/python/aurelius-atlas-model`
 * (`aurelius_atlas_model/instance/entity_mutation_response.py` and
 * `entity_operation.py`, ported from Apache Atlas 2.4.0
 * `org.apache.atlas.model.instance.EntityMutationResponse`): keep the two in
 * step when the Python model changes. The headers reuse the
 * `AtlasEntityHeader` DTO of `atlas-search.ts` unchanged. Java's
 * `getPartialUpdatedEntities` has no `@JsonIgnore`, so the server writes the
 * `partialUpdatedEntities` key next to `mutatedEntities` — the DTO keeps both.
 */

import type { AtlasEntityHeader } from "./atlas-search";

/** What a write did to an entity (`EntityMutations.EntityOperation`). */
export type EntityOperation = "CREATE" | "UPDATE" | "PARTIAL_UPDATE" | "DELETE" | "PURGE";

/**
 * `EntityMutationResponse`: the headers of the created, updated, deleted and
 * purged entities, keyed by operation, and the guids given to new ones.
 */
export type EntityMutationResponse = {
    mutatedEntities?: Partial<Record<EntityOperation, AtlasEntityHeader[]>> | null;
    /** `guidAssignments`: caller-assigned id → server guid. */
    guidAssignments?: Record<string, string> | null;
    /** The `PARTIAL_UPDATE` headers again, as Java's getter writes them. */
    partialUpdatedEntities?: AtlasEntityHeader[] | null;
};
