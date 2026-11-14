/**
 * The view family's DTOs — the wire shapes of `/api/aurelius/v1/**` (AVS-07, ADR 064).
 *
 * Field names are the camelCase aliases the server writes, mirrored from
 * `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/views.py`): keep the
 * two in step when the Python model changes (AVS-07 names this cluster as its
 * Angular reader). Fields the server leaves out are `undefined` — normalisations
 * the server applies on read are the server's, not the client's.
 */

import { AtlasEntityStatus } from "./atlas-entity";

/** One crumb of a card's trail (`CardBreadcrumb`, AVS-01). */
export type CardBreadcrumb = {
    guid: string;
    name?: string | null;
    typeName?: string | null;
};

/** One quality dimension's roll-up on a card (`CardQuality`, AVS-01). */
export type CardQuality = {
    dimension: string;
    score: number;
    count: number;
    total: number;
    ruleGuids?: string[];
};

/** One related entity (`RelationEntity`, AVS-02, AVS-04). */
export type RelationEntity = {
    guid: string;
    name?: string | null;
    typeName?: string | null;
    status?: AtlasEntityStatus | null;
};

/** The entities related under one attribute name (`EntityRelation`, AVS-02, AVS-04). */
export type EntityRelation = {
    attribute: string;
    entities?: RelationEntity[];
};

/**
 * One catalogue entity as a result line, chip or badge needs it (`EntityCard`,
 * AVS-01, ADR 064). `displayText` is the name, or the qualified name when there
 * is no name (AVS-03); `stale` is the stored document's mark (AVS-06).
 */
export type EntityCard = {
    guid: string;
    typeName: string;
    superTypeNames?: string[];
    name?: string | null;
    qualifiedName?: string | null;
    displayText: string;
    definition?: string | null;
    status: AtlasEntityStatus;
    createTime?: number | null;
    updateTime?: number | null;
    createdBy?: string | null;
    updatedBy?: string | null;
    classificationNames?: string[];
    labels?: string[];
    breadcrumb?: CardBreadcrumb[];
    relations?: EntityRelation[];
    quality?: CardQuality[];
    governed?: boolean | null;
    stale: boolean;
};

/**
 * One entity as a screen needs it (`EntityView`, AVS-04): a card plus its own
 * values, sections and business metadata. 16.5b reads the details screen from
 * it; the results page reads only the card.
 */
export type EntityView = EntityCard & {
    attributes?: Record<string, unknown>;
    businessMetadata?: Record<string, Record<string, unknown>> | null;
    sections?: EntityRelation[];
};

/** How the search door ranks (`mode`, ASV-01): words, meaning, or both. */
export type ViewSearchMode = "keyword" | "semantic" | "hybrid";

/** A value of a door field and how many matches hold it (AVR-05). */
export type FacetEntry = {
    value: string | number | boolean;
    count: number;
};

/**
 * A search door request (AVR-02, ASV-01): the query's words, the mode that
 * ranks them, the field filters, the facet names with their sizes, and the
 * page. The keys of `filters` are the door's field names; `all`, `any` and
 * `none` nest groups of them (AVR-03).
 */
export type ViewSearchRequest = {
    query?: string;
    mode?: ViewSearchMode;
    filters?: ViewSearchFilters;
    facets?: string[] | Record<string, { size?: number }>;
    sort?: Record<string, "asc" | "desc"> | Array<Record<string, "asc" | "desc">> | string;
    limit?: number;
    offset?: number;
};

/** A door filter: field values, or nested groups of filters (AVR-03). */
export type ViewSearchFilters = {
    [field: string]:
        | string
        | number
        | boolean
        | Array<string | number | boolean>
        | ViewSearchFilters
        | ViewSearchFilters[]
        | undefined;
    all?: ViewSearchFilters[];
    any?: ViewSearchFilters[];
    none?: ViewSearchFilters[];
};

/**
 * A search door answer (AVR-08): the page of cards, each asked facet's counts,
 * and how many entities matched in all.
 */
export type ViewSearchAnswer = {
    cards: EntityCard[];
    facets: Record<string, FacetEntry[]>;
    total: number;
};
