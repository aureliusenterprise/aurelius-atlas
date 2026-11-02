/**
 * Atlas entity DTOs — the wire shapes of `/api/atlas/v2/entity/**` (DET-03, APC-03).
 *
 * Field names are the camelCase Java getter names the server writes, mirrored
 * from the Apache Atlas 2.4.0 source
 * (`intg/api/client-v2/src/main/java/org/apache/atlas/api/client/v2/model/`
 * and `repository-audit-store/src/main/java/org/apache/atlas/AtlasEntity.java`
 * — `intg/.../model/instance/AtlasEntity.java`): keep the DTOs in step with
 * `AtlasEntity.java`, `AtlasEntityWithExtInfo.java`, and `EntityREST.java`
 * when the server (increment 2.3) answers them. Timestamps are epoch
 * milliseconds as the server writes them (`createTime`, `updateTime`), ISO
 * strings for `createdOn`/`updatedOn`; fields the server leaves out are
 * `undefined` — normalisations the server applies on read are the server's,
 * not the client's (TDM-06..13's rule, applied to entities).
 */

/** An entity's lifecycle state (`AtlasEntity.STATUS`, `EntityStatus`). */
export type AtlasEntityStatus = "ACTIVE" | "DELETE_PENDING" | "PURPOSED_DELETE" | "INPUT_PHASE_COMPLETE";

/**
 * An entity reference (`AtlasObjectId`): its guid, or its type name and the
 * unique attribute values that identify it. The export request's
 * `itemsToExport` is a list of these (EXP-01); the entity routes take them too.
 */
export type AtlasObjectId = {
    guid?: string | null;
    typeName?: string | null;
    uniqueAttributes?: Record<string, unknown> | null;
};

/** A classification on an entity (`AtlasClassification`). */
export type AtlasClassification = {
    /** The entity attribute the classification is attached to, if any. */
    attributeName?: string | null;
    /** The classification type name. */
    typeName?: string | null;
    /** The classified entity's guid. */
    entityGuid?: string | null;
    entityStatus?: AtlasEntityStatus | null;
    /** Whether the classification propagates to the entity's relationships. */
    propagate?: boolean | null;
    /** How the classification propagates to other propagated classifications. */
    propagatePropagation?: "NONE" | "ONE_TO_TWO" | "TWO_TO_ONE" | "BOTH" | null;
    removePropagation?: "NONE" | "ONE_TO_TWO" | "TWO_TO_ONE" | "BOTH" | null;
    removePropagationsOnEntityDelete?: boolean | null;
    /** The periods in which the classification applies (ACL-09, ENT-13). */
    validityPeriods?: (TimeBoundary | null)[] | null;
    /** Epoch milliseconds. */
    classifyTime?: number | null;
    /** Epoch milliseconds; null while the classification is active. */
    removalTime?: number | null;
    visibility?: "VISIBLE" | "CLASSIFICATION_ONLY" | "DEPENDENT" | "OTHER" | null;
    attributes?: Record<string, unknown> | null;
};

/**
 * `TimeBoundary`: one validity period of a classification (ENT-13). The times
 * are strings in Java's `yyyy/MM/dd HH:mm:ss`; `timeZone` is a Java zone id or
 * null for the server's local time.
 */
export type TimeBoundary = {
    startTime?: string | null;
    endTime?: string | null;
    timeZone?: string | null;
};

/** The order of a `PList` (`SearchFilter.SortType`). */
export type SortType = "NONE" | "ASC" | "DESC";

/**
 * `AtlasClassification.AtlasClassifications`: a `PList` of classifications
 * (CLS-01) — the body of `GET /v2/entity/guid/{guid}/classifications`
 * (ACL-01). The paging fields carry the server's whole-list answer: the
 * `startIndex`/`pageSize`/`totalCount` of the page read.
 */
export type AtlasClassifications = {
    list?: AtlasClassification[] | null;
    startIndex?: number;
    pageSize?: number;
    totalCount?: number;
    sortBy?: string | null;
    sortType?: SortType | null;
};

/**
 * `ClassificationAssociateRequest`: one classification to attach to many
 * entities, by GUID or by type and unique-attribute sets (CLS-01, CLS-07,
 * ACL-04).
 */
export type ClassificationAssociateRequest = {
    classification?: AtlasClassification | null;
    entityGuids?: string[] | null;
    entitiesUniqueAttributes?: Record<string, unknown>[] | null;
    entityTypeName?: string | null;
};

/** A glossary term header, as carried in relationship attributes (`AtlasRelatedTermHeader`). */
export type AtlasRelatedTermHeader = {
    guid?: string | null;
    displayText?: string | null;
};

/** The `meanings` value of `relationshipAttributes` (`AtlasRelatedTerms`). */
export type AtlasRelatedTerms = {
    termNames?: string[] | null;
    meaning?: AtlasRelatedTermHeader[] | null;
};

/** The `relationshipAttributes` map; the `meanings` key carries {@link AtlasRelatedTerms}. */
export type AtlasRelationshipAttributes = Record<string, unknown> & {
    meanings?: AtlasRelatedTerms | null;
};

/**
 * One end of a relationship, collapsed (`AtlasRelatedEntity`): a reference
 * when collapsed, the entity header fields when the server expands it.
 */
export type AtlasRelatedEntity = {
    guid?: string | null;
    relationshipGuid?: string | null;
    name?: string | null;
    displayText?: string | null;
    entityStatus?: AtlasEntityStatus | null;
    proxy?: boolean | null;
    uniqueAttributes?: Record<string, unknown> | null;
    /** Present when expanded (`AtlasRelatedEntity`'s `AtlasEntityHeader` super-set). */
    typeName?: string | null;
    attributes?: Record<string, unknown> | null;
    classifications?: AtlasClassification[] | null;
    entityType?: string | null;
};

/** One relationship-end list, keyed by relationship attribute name (`AtlasRelatedEntities`). */
export type AtlasRelatedEntities = {
    /** The relationship instance's guid. */
    guid: string;
    /** The end entity, collapsed or expanded. */
    endEntity: AtlasRelatedEntity;
}[];

/**
 * An entity instance (`AtlasEntity`): the payload of the
 * `GET /v2/entity/guid/{guid}` read (DET-03, increment 2.3's surface).
 */
export type AtlasEntity = {
    guid?: string | null;
    createdBy?: string | null;
    updatedBy?: string | null;
    /** Epoch milliseconds. */
    createTime?: number | null;
    /** Epoch milliseconds. */
    updateTime?: number | null;
    version?: number | null;
    typeName?: string | null;
    status?: AtlasEntityStatus | null;
    /** The attribute map, keyed by attribute name (`AtlasEntity.attributes`). */
    attributes?: Record<string, unknown> | null;
    classificationNames?: string[] | null;
    classifications?: AtlasClassification[] | null;
    propagatedClassifications?: AtlasClassification[] | null;
    businessAttributes?: Record<string, unknown> | null;
    relationshipAttributes?: AtlasRelationshipAttributes | null;
    /** Relationship ends, keyed by relationship attribute name (`AtlasEntity.relationships`). */
    relationships?: Record<string, AtlasRelatedEntities> | null;
    /** ISO 8601, as the server writes them. */
    createdOn?: string | null;
    /** ISO 8601, as the server writes them. */
    updatedOn?: string | null;
    label?: string | null;
    meaningNames?: string[] | null;
    meanings?: AtlasRelatedTermHeader[] | null;
    contactId?: string | null;
    owner?: string | null;
    qualifiedName?: string | null;
};

/**
 * The response of `GET /v2/entity/guid/{guid}`
 * (`AtlasEntityWithExtInfo`): the entity, plus the type definitions and
 * guidance the server may carry. The server's 2.3 response drives which of
 * the optional members appear; the skeleton (DET-02) consumes none of them.
 */
export type AtlasEntityWithExtInfo = {
    entity?: AtlasEntity | null;
    /** The entities the main entity refers to, keyed by guid (ENT-10, ERD-02 — AEN-01). */
    referredEntities?: Record<string, AtlasEntity> | null;
    reftypeDefs?: unknown[] | null;
    structDefs?: unknown[] | null;
    classificationDefs?: unknown[] | null;
    guidance?: string | null;
    /** The page size of the entity's classification list, when paged. */
    totalNumberOfClassifications?: number | null;
};

/**
 * `AtlasEntitiesWithExtInfo`: the body of a bulk read or write (ENT-10) —
 * `entities` and `referredEntities`, the entities they refer to, keyed by guid.
 * `GET /v2/entity/bulk` and the bulk unique-attribute read answer it (ERD-01,
 * ERD-08); the entity writes (8.18) send it.
 */
export type AtlasEntitiesWithExtInfo = {
    entities?: AtlasEntity[] | null;
    referredEntities?: Record<string, AtlasEntity> | null;
};
