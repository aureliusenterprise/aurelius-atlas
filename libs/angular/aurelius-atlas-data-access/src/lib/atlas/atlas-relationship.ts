/**
 * Atlas relationship DTOs — the wire shapes of `/api/atlas/v2/relationship/**`
 * (REL-01..REL-08, APC-03).
 *
 * Field names are the camelCase names the server writes, mirrored from
 * `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/instance/
 * relationship.py`, `relationship_with_ext_info.py`, and
 * `relationship_status.py`, ported from Apache Atlas 2.4.0
 * `org.apache.atlas.model.instance.AtlasRelationship`): keep the two in step
 * when the Python model changes. `AtlasStruct`'s two fields are inlined. The
 * Python twin of this cluster is `AtlasClient.relationship` (CLR-01..04).
 */

import type { AtlasClassification, AtlasObjectId } from "./atlas-entity";
import type { AtlasEntityHeader } from "./atlas-search";
import type { PropagateTags } from "./atlas-typedef";

/** Whether a relationship is active or soft-deleted (`AtlasRelationship.Status`). */
export type RelationshipStatus = "ACTIVE" | "DELETED";

/**
 * `AtlasRelationship`: a struct (its `typeName` and `attributes`, inlined) with
 * a guid, its two ends, a label, tag propagation, a status and audit fields.
 */
export type AtlasRelationship = {
    guid?: string | null;
    homeId?: string | null;
    provenanceType?: number | null;
    /** The struct's type name — the relationship type (`AtlasStruct.typeName`). */
    typeName?: string | null;
    /** The relationship attributes (`AtlasStruct.attributes`). */
    attributes?: Record<string, unknown> | null;
    end1?: AtlasObjectId | null;
    end2?: AtlasObjectId | null;
    label?: string | null;
    propagateTags?: PropagateTags | null;
    status?: RelationshipStatus | null;
    createdBy?: string | null;
    updatedBy?: string | null;
    /** Epoch milliseconds. */
    createTime?: number | null;
    /** Epoch milliseconds. */
    updateTime?: number | null;
    version?: number | null;
    propagatedClassifications?: AtlasClassification[] | null;
    blockedPropagatedClassifications?: AtlasClassification[] | null;
};

/**
 * `AtlasRelationshipWithExtInfo`: the relationship and, when
 * `extendedInfo=true` was asked, `referredEntities` — the headers of the
 * entities it relates, keyed by guid. `GET .../guid/{guid}` always answers
 * this wrapper, flag or no flag (REL-06).
 */
export type AtlasRelationshipWithExtInfo = {
    relationship?: AtlasRelationship | null;
    referredEntities?: Record<string, AtlasEntityHeader> | null;
};
