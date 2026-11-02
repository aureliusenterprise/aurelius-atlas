/**
 * Atlas entity-audit DTOs — the wire shapes of `/api/atlas/v2/entity/{guid}/audit`
 * (AUD-01..AUD-09, APC-03).
 *
 * Field names are the camelCase names the server writes, mirrored from
 * `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/audit.py`, ported
 * from Apache Atlas 2.4.0 `org.apache.atlas.model.audit.EntityAuditEventV2`):
 * keep the two in step when the Python model changes. Java serializes the event
 * with `JsonSerialize.Inclusion.ALWAYS` — every key is written, nulls included.
 * The Python twin of this cluster is `AtlasClient.entity.audit_events`
 * (CLE-10).
 */

import type { AtlasEntity } from "./atlas-entity";

/** What an audit event records (`EntityAuditEventV2.EntityAuditActionV2`). */
export type EntityAuditActionV2 =
    | "ENTITY_CREATE"
    | "ENTITY_UPDATE"
    | "ENTITY_DELETE"
    | "ENTITY_IMPORT_CREATE"
    | "ENTITY_IMPORT_UPDATE"
    | "ENTITY_IMPORT_DELETE"
    | "CLASSIFICATION_ADD"
    | "CLASSIFICATION_DELETE"
    | "CLASSIFICATION_UPDATE"
    | "PROPAGATED_CLASSIFICATION_ADD"
    | "PROPAGATED_CLASSIFICATION_DELETE"
    | "PROPAGATED_CLASSIFICATION_UPDATE"
    | "TERM_ADD"
    | "TERM_DELETE"
    | "LABEL_ADD"
    | "LABEL_DELETE"
    | "ENTITY_PURGE"
    | "BUSINESS_ATTRIBUTE_UPDATE"
    | "CUSTOM_ATTRIBUTE_UPDATE";

/** The audit format an event was written in (`EntityAuditType`). */
export type EntityAuditType = "ENTITY_AUDIT_V1" | "ENTITY_AUDIT_V2";

/**
 * `EntityAuditEventV2`: one change of an entity — the entity, when, by whom,
 * what and its details, its key, and the entity's definition.
 */
export type EntityAuditEventV2 = {
    entityId?: string | null;
    /** Epoch milliseconds. */
    timestamp?: number | null;
    user?: string | null;
    action?: EntityAuditActionV2 | null;
    details?: string | null;
    eventKey?: string | null;
    entity?: AtlasEntity | null;
    type?: EntityAuditType | null;
};
