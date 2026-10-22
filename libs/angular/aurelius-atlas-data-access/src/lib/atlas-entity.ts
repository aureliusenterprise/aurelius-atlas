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

/** A classification on an entity (`AtlasClassification`). */
export type AtlasClassification = {
    /** The entity attribute the classification is attached to, if any. */
    attributeName?: string | null;
    /** The classification type name. */
    typeName?: string | null;
    /** The classified entity's guid. */
    entityGuid?: string | null;
    propagatePropagation?: "NONE" | "ONE_TO_TWO" | "TWO_TO_ONE" | "BOTH" | null;
    removePropagation?: "NONE" | "ONE_TO_TWO" | "TWO_TO_ONE" | "BOTH" | null;
    /** Epoch milliseconds. */
    classifyTime?: number | null;
    /** Epoch milliseconds; null while the classification is active. */
    removalTime?: number | null;
    visibility?: "VISIBLE" | "CLASSIFICATION_ONLY" | "DEPENDENT" | "OTHER" | null;
    attributes?: Record<string, unknown> | null;
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
    reftypeDefs?: unknown[] | null;
    structDefs?: unknown[] | null;
    classificationDefs?: unknown[] | null;
    guidance?: string | null;
    /** The page size of the entity's classification list, when paged. */
    totalNumberOfClassifications?: number | null;
};
