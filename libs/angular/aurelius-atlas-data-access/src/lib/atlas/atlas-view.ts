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
import { AtlasTypeDef } from "./atlas-typedef";

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

/**
 * One non-compliant governance verdict on a card (`CardVerdict`, AVS-11, DD-838): the rule it refuses,
 * named, and the message. These are the rows the card's governance mark counts and lists (VCF-19); the
 * compliant verdicts stay in their index (ASG-03).
 */
export type CardVerdict = {
    rule: string;
    name: string;
    message: string;
};

/**
 * One stored governance verdict of a rule, as the verdicts door answers it
 * (`RuleVerdict`, AVS-12, DD-846, VDR-14): the judged entity, the verdict, and
 * the rule name and message the verdict document copied. `compliant` is the
 * document's `"1"` or `"0"` as a boolean, `null` for a document holding
 * neither — which the rule page draws in neither list (DET-51).
 */
export type RuleVerdict = {
    entity: string;
    compliant: boolean | null;
    name: string;
    message: string;
};

/**
 * The answer of `POST /api/aurelius/v1/rule/verdicts` (`RuleVerdictsAnswer`,
 * AVS-12): the rule's stored verdict rows, in the store's document id order
 * (ASG-09).
 */
export type RuleVerdictsAnswer = {
    verdicts: RuleVerdict[];
};

/**
 * One quality result of an entity, as the read door joins it (`RuleScore`, AVS-13, DD-863): the rule GUID,
 * its name, its dimension and the score it gave this entity (ASQ-02). A field's rules scored on it answer
 * one row each, in the store's score GUID order (ASQ-09, VDR-16) — the rows the field page's rule cards
 * print (DET-65).
 */
export type RuleScore = {
    rule: string;
    name: string;
    dimension: string;
    score: number;
};

/**
 * One related entity (`RelationEntity`, AVS-02, AVS-04).
 *
 * `breadcrumb` holds the trail its document stored, top down, so a propagation source's row can show where the
 * source sits (VDR-12, DD-836). Only a related entity read with a document that has parents carries it: a
 * section's end or a source with no trail answers none.
 */
export type RelationEntity = {
    guid: string;
    name?: string | null;
    typeName?: string | null;
    status?: AtlasEntityStatus | null;
    breadcrumb?: CardBreadcrumb[] | null;
};

/** The entities related under one attribute name (`EntityRelation`, AVS-02, AVS-04). */
export type EntityRelation = {
    attribute: string;
    entities?: RelationEntity[];
};

/**
 * One classification the entity carries by propagation, and the entities it came from
 * (`ClassificationSource`, AVS-04 as amended by 16.5b, VDR-12). An empty `entities`
 * means the store no longer has the source: the tag stays, its origin is unknown.
 */
export type ClassificationSource = {
    typeName: string;
    entities?: RelationEntity[];
};

/**
 * One catalogue entity as a result line, chip or badge needs it (`EntityCard`,
 * AVS-01, ADR 064). `displayText` is the name, or the qualified name when there
 * is no name (AVS-03); `typeAlias` is the author's alias of the type, the badge
 * name in place of `typeName` (AVS-01 as amended by 18.1, MMS-09); `stale` is
 * the stored document's mark (AVS-06).
 */
export type EntityCard = {
    guid: string;
    typeName: string;
    superTypeNames?: string[];
    name?: string | null;
    qualifiedName?: string | null;
    displayText: string;
    typeAlias?: string | null;
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
    /**
     * The refused governance verdicts the door joined (`CardVerdict`, AVS-11, VDR-13), in rule-name order
     * and capped. The card's governance mark shows them (VCF-19); `governed` is the judged mark (AVS-01).
     */
    verdicts?: CardVerdict[];
    governed?: boolean | null;
    stale: boolean;
    /** Whether the entity holds any parent (RPS-06, DD-758). The card answers the
     * stored boolean; a card from an older door omits it, which reads as unknown. */
    hasParent?: boolean;
    /**
     * The classifications propagation brought, each with the entities it came from (`ClassificationSource`,
     * VDR-12 as amended by DD-836): every door that reads them fills it, so a result line names its tags too.
     */
    propagatedClassifications?: ClassificationSource[];
};

/**
 * One entity as a screen needs it (`EntityView`, AVS-04): a card plus its own
 * values, sections and business metadata. 16.5b reads the details screen from
 * it; the results page reads only the card. The propagated tags ride the card
 * (VDR-12, DD-836), so both screens read them from there.
 */
export type EntityView = EntityCard & {
    attributes?: Record<string, unknown>;
    businessMetadata?: Record<string, Record<string, unknown>> | null;
    sections?: EntityRelation[];
    /**
     * The quality results that reach the entity (`RuleScore`, AVS-13, VDR-16): only the read door fills
     * them, for a field, beside the verdicts it joins. Like `sections` it is the view's own — a card never
     * carries it — and a view the door did not join answers none.
     */
    ruleScores?: RuleScore[];
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

/**
 * One `sections` entry of a mutation-door body (AVW-09, VDE-04): the relationship
 * attribute and its full desired end list. Each end is its GUID, or a `{guid,
 * status: "DELETED"}` remove intent (the door reads a DELETED status as removal).
 */
export type ViewSectionInput = {
    attribute: string;
    entities: Array<string | { guid: string; status?: string | null }>;
};

/**
 * A mutation-door body (AVW-02, VDE-05): one entity's desired state as a view.
 * `typeName` and `attributes` are required; `guid` makes it an update and `updateTime`
 * names the view it edited (AVW-04). The sets are complete desired states — a set the
 * body omits is left unchanged (AVW-05) — the tags as names, the term assignments as
 * term GUIDs, and the ends as {@link ViewSectionInput} entries. The door ignores what
 * a view carries but a write cannot set (the breadcrumb, quality, `stale`).
 */
export type ViewSaveRequest = {
    guid?: string | null;
    typeName: string;
    attributes: Record<string, unknown>;
    updateTime?: number | null;
    classifications?: string[];
    labels?: string[];
    meanings?: string[];
    sections?: ViewSectionInput[];
};

/**
 * A lost-update conflict (AVW-04, DD-591): the door's answer when the stored entity
 * changed since the edited view was read. Besides the error code it carries the
 * stored view — the material the editor re-edits from (VDE-07). It rides a 409, so
 * the client surfaces it apart from {@link AtlasErrorBody}.
 */
export type ViewConflict = {
    errorCode: string;
    view: EntityView;
};

/**
 * The answer of the form-slice door `GET /api/aurelius/v1/types/for-type/{name}`
 * (AVW-11, VDE-02): the named entity type and its supertype chain, each one a whole
 * typedef with the attributes it declares — enough to build one type's form.
 */
export type ViewForTypeAnswer = {
    type: AtlasTypeDef;
    superTypes: AtlasTypeDef[];
};
