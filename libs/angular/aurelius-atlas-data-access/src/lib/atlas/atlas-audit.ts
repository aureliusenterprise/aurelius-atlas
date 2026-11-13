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
import type { FilterCriteria, SortOrder } from "./atlas-search";

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

/**
 * What an admin audit records (`AuditOperation`, ADA-01): the operations of the
 * admin endpoints, not the entity actions of {@link EntityAuditActionV2}.
 */
export type AuditOperation =
    | "PURGE"
    | "EXPORT"
    | "IMPORT"
    | "IMPORT_DELETE_REPL"
    | "TYPE_DEF_CREATE"
    | "TYPE_DEF_UPDATE"
    | "TYPE_DEF_DELETE"
    | "SERVER_START"
    | "SERVER_STATE_ACTIVE";

/**
 * `AtlasAuditEntry`: one admin operation, its user, client, times, parameters
 * and result (ADA-01, ADA-04, AAC-11). The Python twin is
 * `AtlasClient.admin.audits`.
 */
export type AtlasAuditEntry = {
    guid?: string | null;
    userName?: string | null;
    operation?: AuditOperation | null;
    params?: string | null;
    /** Epoch milliseconds. */
    startTime?: number | null;
    /** Epoch milliseconds. */
    endTime?: number | null;
    clientId?: string | null;
    result?: string | null;
    resultCount?: number | null;
};

/**
 * `AuditSearchParameters`: the filters, page and order of an admin audit search
 * (ADA-04, AAC-11). No body asks for every entry.
 */
export type AuditSearchParameters = {
    auditFilters?: FilterCriteria | null;
    limit?: number | null;
    offset?: number | null;
    sortBy?: string | null;
    sortOrder?: SortOrder | null;
};

/**
 * `AuditReductionCriteria`: the default, custom and sweep agings an
 * `audits/ageout` asks for (AGE-01, AAC-11). The TTL keys keep the server's
 * `TTL` capitalisation (`ignoreDefaultAgeoutTTL`, `defaultAgeoutTTLInDays`,
 * `customAgeoutTTLInDays`).
 */
export type AuditReductionCriteria = {
    auditAgingEnabled?: boolean | null;
    defaultAgeoutEnabled?: boolean | null;
    auditSweepoutEnabled?: boolean | null;
    createEventsAgeoutAllowed?: boolean | null;
    subTypesIncluded?: boolean | null;
    ignoreDefaultAgeoutTTL?: boolean | null;
    defaultAgeoutAuditCount?: number | null;
    defaultAgeoutTTLInDays?: number | null;
    customAgeoutAuditCount?: number | null;
    customAgeoutTTLInDays?: number | null;
    customAgeoutEntityTypes?: string | null;
    customAgeoutActionTypes?: string | null;
    sweepoutEntityTypes?: string | null;
    sweepoutActionTypes?: string | null;
};
