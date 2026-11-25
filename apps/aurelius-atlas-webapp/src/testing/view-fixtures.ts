import {
    CardBreadcrumb,
    CardQuality,
    ClassificationSource,
    EntityCard,
    EntityRelation,
    EntityView,
    RelationEntity,
    RuleScore,
} from "aurelius-atlas-data-access";

/**
 * The fixture builders every screen spec needs (AVS-01..04, ADR 064). Specs
 * used to write a full entity literal by hand wherever one was needed — a
 * hundred-plus `displayText:` blocks that pinned fields the test did not care
 * about and drifted from one another.
 *
 * Each builder fills only the fields the doors always answer (AVS-06: the
 * wire omits what it has no value for, so a builder omits the rest too) and
 * takes an override object for what the test is about. Keep them small: a
 * builder that grows every optional field back is the literal it replaced.
 */

/** The defaults every fixture entity shares (the shape a real door answers). */
const CARD_DEFAULTS: Pick<EntityCard, "guid" | "typeName" | "displayText" | "status" | "stale"> = {
    guid: "7a1b",
    typeName: "DataSet",
    displayText: "genomic_variants",
    status: "ACTIVE",
    stale: false,
};

/** A loose section seed: the guidless and `DELETED` ends fixtures carry are
 * not representable as a {@link RelationEntity}, so specs pass them as maps. */
export type SeedEnd = Record<string, unknown>;

/** One related end (the door's `RelationEntity`). */
export function end(seed: SeedEnd): RelationEntity {
    return seed as unknown as RelationEntity;
}

/** One relationship end set under an attribute (DET-17, AVS-02). */
export function ends(attribute: string, seeds: readonly SeedEnd[]): EntityRelation {
    return { attribute, entities: seeds.map(end) };
}

/** The view's sections, one per key (DET-17). */
export function sectionsOf(seeds: Record<string, readonly SeedEnd[]>): EntityRelation[] {
    return Object.entries(seeds).map(([attribute, list]) => ends(attribute, list));
}

/**
 * One catalogue card (AVS-01): a result line, chip or badge needs it.
 *
 * @param overrides the fields this test names
 * @returns the card
 */
export function card(overrides: Partial<EntityCard> = {}): EntityCard {
    return { ...CARD_DEFAULTS, name: CARD_DEFAULTS.displayText, ...overrides };
}

/**
 * One entity as a screen needs it (AVS-04): a card plus its own values and
 * sections. The details screen, the editor and the sections store all read
 * this shape — build every one of their fixtures here so a wire change is
 * fixed in one place.
 *
 * @param overrides the fields this test names
 * @returns the view
 */
export function view(overrides: Partial<EntityView> = {}): EntityView {
    const base = card(overrides);
    return {
        ...base,
        qualifiedName: `${base.displayText}@cluster`,
        classificationNames: [],
        attributes: { name: base.name, qualifiedName: base.qualifiedName },
        ...overrides,
    };
}

/** One quality dimension roll-up on a card (AVS-01, DET-56). */
export function quality(dimension: string, score: number, overrides: Partial<CardQuality> = {}): CardQuality {
    return { dimension, score, count: 1, total: 1, ...overrides };
}

/** One classification the entity carries by propagation (AVS-04, VDR-12). */
export function propagated(typeName: string, sources: readonly SeedEnd[] = []): ClassificationSource {
    return { typeName, entities: sources.map(end) };
}

/** One crumb of a card's trail (AVS-01). */
export function crumb(guid: string, name: string, typeName = "m4i_data_domain"): CardBreadcrumb {
    return { guid, name, typeName };
}

/**
 * One rule score joined onto a field's view (AVS-13, DET-65). The `rule` is
 * the rule guid the door keys its rows by, so a test that looks a score up
 * names it.
 */
export function ruleScore(rule: string, dimension: string, score: number, name = `rule-${rule}`): RuleScore {
    return { rule, name, dimension, score };
}
