/**
 * Atlas type-definition DTOs — the wire shapes of `/api/atlas/v2/types/**` (APC-03).
 *
 * Field names are the camelCase Java getter names the server writes (TDM-01), mirrored
 * from `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/typedef.py`): keep the
 * two in step when the Python model changes. Timestamps are epoch milliseconds; fields
 * the server leaves out are `undefined`, and normalisations the server applies on read
 * (empty lists, name-deduplication) are the server's, not the client's (TDM-06..13).
 */

/** The kinds of Atlas types (`org.apache.atlas.model.TypeCategory`). */
export type TypeCategory =
    | "PRIMITIVE"
    | "OBJECT_ID_TYPE"
    | "ENUM"
    | "STRUCT"
    | "CLASSIFICATION"
    | "ENTITY"
    | "ARRAY"
    | "MAP"
    | "RELATIONSHIP"
    | "BUSINESS_METADATA";

/** The `type` query parameter of a typedef search (`type_search.py`). */
export type TypeDefKindFilter =
    "CLASS" | "ENTITY" | "TRAIT" | "CLASSIFICATION" | "STRUCT" | "ENUM" | "RELATIONSHIP" | "BUSINESS_METADATA";

/** How many values an attribute or relationship end holds. */
export type Cardinality = "SINGLE" | "LIST" | "SET";

/** How an attribute is indexed. */
export type IndexType = "DEFAULT" | "STRING";

/** How the two ends of a relationship depend on each other. */
export type RelationshipCategory = "ASSOCIATION" | "AGGREGATION" | "COMPOSITION";

/** The direction in which classifications propagate over a relationship. */
export type PropagateTags = "NONE" | "ONE_TO_TWO" | "TWO_TO_ONE" | "BOTH";

/** A constraint on an attribute, such as `ownedRef` or `inverseRef`. */
export type AtlasConstraintDef = {
    type?: string | null;
    params?: Record<string, unknown> | null;
};

/** An attribute of a struct, classification, entity, relationship or business metadata type. */
export type AtlasAttributeDef = {
    name?: string | null;
    typeName?: string | null;
    isOptional?: boolean;
    cardinality?: Cardinality | null;
    valuesMinCount?: number;
    valuesMaxCount?: number;
    isUnique?: boolean;
    isIndexable?: boolean;
    includeInNotification?: boolean;
    defaultValue?: string | null;
    description?: string | null;
    searchWeight?: number;
    indexType?: IndexType | null;
    constraints?: AtlasConstraintDef[] | null;
    options?: Record<string, string> | null;
    displayName?: string | null;
};

/** What every type definition has: identity, audit fields, name and options. */
export type AtlasBaseTypeDef = {
    guid?: string | null;
    createdBy?: string | null;
    updatedBy?: string | null;
    /** Epoch milliseconds, as the server writes them. */
    createTime?: number | null;
    /** Epoch milliseconds, as the server writes them. */
    updateTime?: number | null;
    version?: number | null;
    name?: string | null;
    description?: string | null;
    typeVersion?: string | null;
    serviceType?: string | null;
    options?: Record<string, string> | null;
    /** Fixed by the definition's kind on the server, never sent (TDM-04). */
    category?: TypeCategory;
};

/** One value of an enum type. */
export type AtlasEnumElementDef = {
    value?: string | null;
    description?: string | null;
    ordinal?: number | null;
};

/** An enum type. */
export type AtlasEnumDef = AtlasBaseTypeDef & {
    elementDefs?: AtlasEnumElementDef[];
    defaultValue?: string | null;
};

/** A struct type, and the base of the types that have attributes. */
export type AtlasStructDef = AtlasBaseTypeDef & {
    attributeDefs?: AtlasAttributeDef[];
};

/** A classification type: attributes, super types and the entity types it may be applied to. */
export type AtlasClassificationDef = AtlasStructDef & {
    superTypes?: string[];
    entityTypes?: string[];
    /** Derived by the server from all classifications; ignored on create and update. */
    subTypes?: string[] | null;
};

/** An entity attribute that a relationship type adds; read-only, derived by the server. */
export type AtlasRelationshipAttributeDef = AtlasAttributeDef & {
    relationshipTypeName?: string | null;
    isLegacyAttribute?: boolean;
};

/** An entity type. */
export type AtlasEntityDef = AtlasStructDef & {
    superTypes?: string[];
    /** Derived by the server from all entity types; ignored on create and update. */
    subTypes?: string[] | null;
    /** Derived by the server from the relationship types that refer to this one. */
    relationshipAttributeDefs?: AtlasRelationshipAttributeDef[] | null;
    /** Derived by the server from the business metadata types that apply to this one. */
    businessAttributeDefs?: Record<string, AtlasAttributeDef[]> | null;
};

/** One end of a relationship type: the entity type there and the attribute it gets. */
export type AtlasRelationshipEndDef = {
    type?: string | null;
    name?: string | null;
    isContainer?: boolean;
    cardinality?: Cardinality | null;
    isLegacyAttribute?: boolean;
    description?: string | null;
};

/** A relationship type between two entity types. */
export type AtlasRelationshipDef = AtlasStructDef & {
    relationshipCategory?: RelationshipCategory | null;
    relationshipLabel?: string | null;
    propagateTags?: PropagateTags | null;
    endDef1?: AtlasRelationshipEndDef | null;
    endDef2?: AtlasRelationshipEndDef | null;
};

/** A business metadata type: attributes that apply to the entity types its options name. */
export type AtlasBusinessMetadataDef = AtlasStructDef;

/** A type definition of any kind — what `/typedef/name/{name}` and `/typedef/guid/{guid}` answer with. */
export type AtlasTypeDef =
    | AtlasEnumDef
    | AtlasStructDef
    | AtlasClassificationDef
    | AtlasEntityDef
    | AtlasRelationshipDef
    | AtlasBusinessMetadataDef;

/** The identity of a type definition, as `/v2/types/typedefs/headers` lists it. */
export type AtlasTypeDefHeader = {
    guid?: string | null;
    name?: string | null;
    serviceType?: string | null;
    category?: TypeCategory | null;
};

/**
 * Type definitions of every kind: the body and response of `/v2/types/typedefs` (TDM-13).
 * A missing list reads as empty; an explicit null round-trips.
 */
export type AtlasTypesDef = {
    enumDefs?: AtlasEnumDef[] | null;
    structDefs?: AtlasStructDef[] | null;
    classificationDefs?: AtlasClassificationDef[] | null;
    entityDefs?: AtlasEntityDef[] | null;
    relationshipDefs?: AtlasRelationshipDef[] | null;
    businessMetadataDefs?: AtlasBusinessMetadataDef[] | null;
};

/** The query parameters of `getTypedefs` / `getTypedefHeaders` (`SearchFilter`, TYR-06/07). */
export type TypeDefsFilter = {
    /** Keep only definitions of this kind (`CLASS`/`TRAIT` are the UI aliases). */
    type?: TypeDefKindFilter;
    /** Keep the definition with this exact name. */
    name?: string;
    /** Keep definitions of this service type. */
    servicetype?: string;
    /** Keep definitions that (transitively) have this super type. */
    supertype?: string;
    /** Drop definitions that (transitively) have this super type. */
    notsupertype?: string;
    /** Drop definitions of this service type. */
    notservicetype?: string;
    /** Drop definitions with this name; repeatable server-side, single-valued from the client. */
    notname?: string;
    /** Drop `__internal` types and references, as the UI asks for. */
    excludeInternalTypesAndReferences?: boolean;
};
