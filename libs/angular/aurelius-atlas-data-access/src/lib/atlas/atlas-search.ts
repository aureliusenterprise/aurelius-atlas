/**
 * Atlas search DTOs — the wire shapes of `/api/atlas/v2/search/**` (APC-11, APC-03).
 *
 * Field names are the camelCase Java getter names the server writes, mirrored
 * from `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/discovery.py`,
 * ported from Apache Atlas 2.4.0 `org.apache.atlas.model.discovery`): keep the
 * two in step when the Python model changes. Fields the server leaves out are
 * `undefined` — normalisations the server applies on read are the server's, not
 * the client's (TDM-06..13's rule, applied to searches). The Python twin of this
 * cluster is the server-client's use of the same models (CL-13).
 */

import { AtlasClassification, AtlasEntityStatus } from "./atlas-entity";

/** How a basic search is sorted (`org.apache.atlas.SortOrder`). */
export type SortOrder = "ASCENDING" | "DESCENDING";

/** How a search answered (`AtlasSearchResult.AtlasQueryType`). */
export type AtlasQueryType = "DSL" | "FULL_TEXT" | "GREMLIN" | "BASIC" | "ATTRIBUTE" | "RELATIONSHIP";

/**
 * What a filter criterion tests of an attribute (`SearchParameters.Operator`).
 * The names are the symbols the server *writes*; its `fromString` reads the
 * others (`LT`, `CONTAINS_ANY`, …) too, so only the written form is modelled.
 */
export type Operator =
    | "<"
    | ">"
    | "<="
    | ">="
    | "="
    | "!="
    | "in"
    | "like"
    | "startsWith"
    | "endsWith"
    | "contains"
    | "not_contains"
    | "containsAny"
    | "containsAll"
    | "isNull"
    | "notNull"
    | "timerange"
    | "notEmpty";

/** How criteria of a {@link FilterCriteria} group combine (`FilterCriteria.Condition`). */
export type Condition = "AND" | "OR";

/**
 * A filter: a condition over criteria (`FilterCriteria`), or one attribute test.
 * Entity filters (`entityFilters`) test the entity's attributes; tag filters
 * (`tagFilters`) test the classifications' (CSR-03).
 */
export type FilterCriteria = {
    attributeName?: string | null;
    operator?: Operator | null;
    attributeValue?: string | null;
    condition?: Condition | null;
    criterion?: FilterCriteria[] | null;
};

/**
 * What a basic search looks for, how its answer is sorted and paged
 * (`SearchParameters`, SRC-01). The Java defaults the server fills in —
 * `false` booleans, `0` limit/offset, `true` sub-type inclusion — are the
 * caller's to leave out; the client sends an absent field as its absence.
 */
export type SearchParameters = {
    query?: string | null;
    typeName?: string | null;
    classification?: string | null;
    relationshipName?: string | null;
    termName?: string | null;
    sortBy?: string | null;
    excludeDeletedEntities?: boolean;
    includeClassificationAttributes?: boolean;
    includeSubTypes?: boolean;
    includeSubClassifications?: boolean;
    excludeHeaderAttributes?: boolean;
    limit?: number;
    offset?: number;
    marker?: string | null;
    entityFilters?: FilterCriteria | null;
    tagFilters?: FilterCriteria | null;
    relationshipFilters?: FilterCriteria | null;
    /** Attribute names to answer per entity (`requestedAttributes`). */
    attributes?: string[] | null;
    sortOrder?: SortOrder | null;
};

/**
 * What a quick search looks for, without classifications (`QuickSearchParameters`,
 * QSR-01). A quick search is a basic search with facets (QSR-02).
 */
export type QuickSearchParameters = {
    query?: string | null;
    typeName?: string | null;
    entityFilters?: FilterCriteria | null;
    includeSubTypes?: boolean;
    excludeDeletedEntities?: boolean;
    offset?: number;
    limit?: number;
    attributes?: string[] | null;
    sortBy?: string | null;
    sortOrder?: SortOrder | null;
    excludeHeaderAttributes?: boolean;
};

/** Attribute names and, per entity, their values (`AttributeSearchResult`, SRC-10). */
export type AttributeSearchResult = {
    name?: string[] | null;
    values?: unknown[][] | null;
};

/** A glossary term assigned to an entity, as the header lists it (`AtlasTermAssignmentHeader`). */
export type AtlasTermAssignmentHeader = {
    termGuid?: string | null;
    relationGuid?: string | null;
    description?: string | null;
    displayText?: string | null;
    expression?: string | null;
    createdBy?: string | null;
    steward?: string | null;
    source?: string | null;
    confidence?: number;
    status?: string | null;
    qualifiedName?: string | null;
};

/**
 * An entity's identity and summary, as searches answer it
 * (`AtlasEntityHeader`, ENT-14): the struct fields plus GUID, status, display
 * text, classifications, meanings and labels.
 */
export type AtlasEntityHeader = {
    typeName?: string | null;
    attributes?: Record<string, unknown> | null;
    guid?: string | null;
    status?: AtlasEntityStatus | null;
    displayText?: string | null;
    classificationNames?: string[] | null;
    classifications?: AtlasClassification[] | null;
    meaningNames?: string[] | null;
    meanings?: AtlasTermAssignmentHeader[] | null;
    isIncomplete?: boolean | null;
    labels?: string[] | null;
};

/** An entity a full-text search found, and its score (`AtlasFullTextResult`, FTX-05). */
export type AtlasFullTextResult = {
    entity?: AtlasEntityHeader | null;
    score?: number | null;
};

/**
 * The entities a search found, and how it was asked (`AtlasSearchResult`,
 * SRC-09). `approximateCount` is the server's: `-1` where the answer does not
 * count (CSR-04), the total elsewhere.
 */
export type AtlasSearchResult = {
    queryType?: AtlasQueryType | null;
    searchParameters?: SearchParameters | null;
    queryText?: string | null;
    type?: string | null;
    classification?: string | null;
    entities?: AtlasEntityHeader[] | null;
    relations?: Record<string, unknown>[] | null;
    attributes?: AttributeSearchResult | null;
    fullTextResult?: AtlasFullTextResult[] | null;
    referredEntities?: Record<string, AtlasEntityHeader> | null;
    approximateCount?: number;
    nextMarker?: string | null;
};

/** A facet value and how many entities have it (`AtlasAggregationEntry`, QSR-03). */
export type AtlasAggregationEntry = {
    name?: string | null;
    count?: number;
};

/** A quick search's results and its facets (`AtlasQuickSearchResult`, QSR-02, QSR-03). */
export type AtlasQuickSearchResult = {
    searchResults?: AtlasSearchResult | null;
    aggregationMetrics?: Record<string, AtlasAggregationEntry[]> | null;
};

/** The terms suggested for a prefix (`AtlasSuggestionsResult`, SUG-01). */
export type AtlasSuggestionsResult = {
    suggestions?: string[] | null;
    prefixString?: string | null;
    fieldName?: string | null;
};
