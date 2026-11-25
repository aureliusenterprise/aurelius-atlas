import { computed, inject, Injectable, signal } from "@angular/core";
import {
    SearchService,
    ValidateEntityService,
    type EntityValidationResponse,
    type EntityView,
    type GovernanceVerdict,
    type SearchParameters,
} from "aurelius-atlas-data-access";
import type { CardFacetGroup, CardSortOption, FacetItem } from "aurelius-atlas-ui";

import { entityFromView } from "../../shared/entity-from-view";
import { PAGE_SIZE } from "./related-sections.state";
import { FACET_GROUP_TITLES, GOV_QUALITY_TITLE } from "./layouts";
import type { FacetGroupKey } from "./section.model";

/** The rule type's own name: the box lists the rules written for a type (DET-42). */
const RULE_TYPE_NAME = "m4i_gov_data_quality";

/**
 * The rule read's page size: the corpus is dozens of rules per type (the
 * demo's largest type carries a few dozen), so one page holds the box
 * (DD-520). No marker walk: a truncated box is an honest partial, and a
 * per-type prefix filter cannot reach one on the demo corpus.
 */
const RULE_LIMIT = 100;

/**
 * The attributes the rule search answers (DET-42 as amended by 7.25a): what a
 * row shows, plus the two fields the box's sorts and facets read (DET-45,
 * DET-46) — the rule type joined the read for the `dataqualitytype` group.
 */
const RULE_ATTRIBUTES = ["name", "ruleDescription", "qualityDimension", "ruleType", "active"] as const;

/**
 * One Governance Quality Rules row (DET-42): a rule of the opened entity's
 * type and its verdict for that record. `compliant` is the aux API's
 * verdict — true, false, or null for no verdict at all (the unread rule of
 * VEV-03, which renders no icon).
 */
export interface GovQualityRow {
    /** The rule entity's guid — the title's details link (DET-42). */
    readonly guid: string;
    /** The rule's name: the card title, the legacy card's link text. */
    readonly name: string;
    /** The rule's `ruleDescription`, the body's first line; empty when it stores none. */
    readonly description: string;
    /** The rule's dimension, titlecased by the renderer; empty when it stores none. */
    readonly dimension: string;
    /** The rule's `ruleType`; empty when it stores none (DET-42 amended, DET-46). */
    readonly ruleType: string;
    /** The rule's verdict for the opened record; null with no verdict line. */
    readonly compliant: boolean | null;
}

/**
 * The box's view as the shared card-section chrome draws it (7.25a, DD-841):
 * the chrome's inputs plus the page of rows the grid projects. The chrome's
 * own fields mirror {@link SectionView}; the rows replace the cards because
 * a governance row is a rule with a verdict, not a door card.
 */
export interface GovSectionView {
    /** Marks the box for the template and the screen's handlers (7.25a, DD-841). */
    kind: "gov-quality";
    /** The section's anchor (`gov-quality`, DET-48). */
    anchor: string;
    /** The chrome's title (the shared title key, DET-48). */
    title: string;
    /** The row count — the count line (DET-44). */
    count: number;
    /** The popover's facet groups (DET-46). */
    facets: CardFacetGroup[];
    /** Whether the funnel marks — keyword, selection, or a sort/direction off default (VCF-08, DET-44). */
    filterActive: boolean;
    /** Whether the keyword or a selection filters the rows (DET-44). */
    filtered: boolean;
    /** The count line's number: the count, or the filtered count (DET-44). */
    countShown: number;
    /** Whether a read is in flight — the scroll container's spinner (DET-44). */
    loading: boolean;
    /** Whether the filtered set is exhausted (DET-47). */
    allLoaded: boolean;
    /** The keyword input's text (DET-47). */
    query: string | null;
    sort: string;
    sortOptions: CardSortOption[];
    descending: boolean;
    /** The visible page of the filtered, sorted rows (DET-47). */
    rows: GovQualityRow[];
}

/** The state of one read round: a superseded round's answer paints nothing. */
interface GovQualityRecord {
    /** The entity this round reads for, or null for the cleared box. */
    entity: EntityView | null;
    /** The rules the search answered, sorted by name (DET-42's Relevance order). */
    rules: { guid: string; name: string; description: string; dimension: string; ruleType: string }[];
    /** The verdicts by rule guid (the aux API's join key, DD-520). */
    verdicts: Map<string, GovernanceVerdict>;
    /** Whether the rule read is in flight. */
    loading: boolean;
}

/**
 * The Governance Quality Rules box of the details screen (DET-42, DD-520):
 * the rules written for the opened entity's type, each with its verdict for
 * that record.
 *
 * The legacy box read the retired `atlas-dev-gov-quality` engine (DV-155,
 * ADR 060). The store holds the rules — the ACTIVE `m4i_gov_data_quality`
 * entities whose `qualifiedName` starts with `<typeName>--`, the rule→type
 * rule LAS-13 states — and 12.7's verdicts are the product's live answers
 * (VEV-02), so the box reads both: a basic search of the rules, and the
 * editor's own validate call over the opened entity, joined on `ruleGuid`.
 * ACTIVE is 12.2's reading (VEV-03): only a false `active` is not.
 *
 * Both calls fail quietly (DD-521, the EDT-23 swallow): no rules, no lines,
 * no alert. The store is per-screen (provided by `Details`): {@link load}
 * re-runs on every entity arrival, and a superseded round paints nothing
 * (the generation guard, DET-08's sibling).
 */
@Injectable()
export class DetailsGovQualityState {
    private readonly search = inject(SearchService);

    private readonly validateEntity = inject(ValidateEntityService);

    /** The read generation: a re-load drops every in-flight answer. */
    private generation = 0;

    private readonly record = signal<GovQualityRecord>({
        entity: null,
        rules: [],
        verdicts: new Map(),
        loading: false,
    });

    /**
     * The box's chrome state (DET-44..DET-47): the keyword, the sort and its
     * direction, the facet selections, and the grown page — the sections
     * store's shape (DD-368's client-side rule), owned by this store because
     * the box seeds from a search and a verdict call, not a relationship
     * (DD-841).
     */
    private readonly filter = signal<GovFilterState>(DEFAULT_FILTER);

    /** The rows the store holds, in Relevance order (DET-42). Empty for no entity. */
    readonly rows = computed<GovQualityRow[]>(() => {
        const { rules, verdicts } = this.record();
        return rules.map((rule) => {
            const verdict = verdicts.get(rule.guid);
            return {
                guid: rule.guid,
                name: rule.name,
                description: rule.description,
                dimension: rule.dimension,
                ruleType: rule.ruleType,
                compliant: verdict === undefined ? null : verdict.compliant === true,
            };
        });
    });

    /** Whether a read is in flight (DET-44: the chrome shows its spinner). */
    readonly loading = computed(() => this.record().loading);

    /**
     * The box as the chrome draws it (DET-44..DET-47): keyword, then facets,
     * then sort, then the visible page — the sections store's pipeline
     * (DD-368) over the rows this store holds (DD-842).
     */
    readonly view = computed<GovSectionView>(() => {
        const rows = this.rows();
        const state = this.filter();
        const term = state.query?.toLowerCase() ?? "";
        const selectionActive = Object.values(state.facetSelection).some((values) => values.length > 0);
        const matched = rows
            .filter((row) => term === "" || matchesRow(row, term))
            .filter((row) => passesFacets(row, state.facetSelection));
        const sorted = sortedRows(matched, state.sort, state.descending);
        const filtered = state.query !== null || selectionActive;
        // VCF-08 (DV-169 amended): a sort key or direction off its default
        // marks the funnel too — the demo's isFilterActive$ is the whole
        // query object differing from its default.
        const stateApplied = filtered || state.sort !== DEFAULT_SORT || state.descending;

        return {
            kind: "gov-quality",
            anchor: GOV_QUALITY_ANCHOR,
            title: GOV_QUALITY_TITLE,
            count: rows.length,
            facets: facetGroupsOf(state, matched),
            filterActive: stateApplied,
            filtered,
            countShown: filtered ? sorted.length : rows.length,
            loading: this.loading(),
            allLoaded: sorted.length <= state.shown,
            query: state.text,
            sort: state.sort,
            sortOptions: SORT_OPTIONS,
            descending: state.descending,
            rows: sorted.slice(0, state.shown),
        };
    });

    /**
     * The keyword input's text on every keystroke (DET-47, the sections
     * store's DD-375 idiom): the filter follows the typing and the page
     * returns to its first size.
     * @param text the box's text
     */
    setText(text: string | null): void {
        const term = text === null || text === "" ? null : text;
        this.filter.update((state) => ({ ...state, query: term, text: term, shown: PAGE_SIZE }));
    }

    /**
     * The keyword submit or clear (DET-47): the filter rides every keystroke
     * already (DD-375's rule, carried), so a submit of unchanged text changes
     * nothing; the clear lands here and empties box and filter.
     * @param query the submitted term, or null on clear
     */
    setQuery(query: string | null): void {
        this.setText(query);
    }

    /**
     * The count-line click (DET-44): the keyword, the selections, the sort
     * and its direction return to their defaults and the page to its first
     * size — the legacy reset link, DET-20's rule carried.
     */
    reset(): void {
        this.filter.set({ ...DEFAULT_FILTER });
    }

    /**
     * A popover row ticked or unticked (DET-46, VCF-11): the value joins or
     * leaves its group's array, the key deleted at the group's last untick,
     * and the page returns to its first size.
     * @param group the group's key
     * @param value the row's value
     * @param checked the row's new state
     */
    toggleFacet(group: string, value: string, checked: boolean): void {
        this.filter.update((state) => {
            const chosen = new Set(state.facetSelection[group] ?? []);
            if (checked) {
                chosen.add(value);
            } else {
                chosen.delete(value);
            }
            const facetSelection = { ...state.facetSelection };
            if (chosen.size === 0) {
                delete facetSelection[group];
            } else {
                facetSelection[group] = [...chosen];
            }
            return { ...state, facetSelection, shown: PAGE_SIZE };
        });
    }

    /**
     * The sort select's change (DET-45).
     * @param sort the selected key
     */
    setSort(sort: string | null): void {
        const key = sort === null || sort === "" ? DEFAULT_SORT : sort;
        this.filter.update((state) => ({ ...state, sort: key }));
    }

    /** The direction button's toggle (DET-45). */
    toggleDirection(): void {
        this.filter.update((state) => ({ ...state, descending: !state.descending }));
    }

    /**
     * The sentinel or its button asked for the next page (DET-47): nine rows
     * more, over the filtered, sorted set (DET-22's page rule).
     */
    nextPage(): void {
        this.filter.update((state) => ({ ...state, shown: state.shown + PAGE_SIZE }));
    }

    /**
     * (Re-)read the box for one entity (DET-42): the rules of its type,
     * then the verdicts over it. A null entity clears the box. Every
     * arrival — the editor's save re-read among them — re-reads from
     * scratch, the sections store's rule (DD-327's sibling). Since 16.5b
     * the opened entity arrives as the view (VDR-01): the rules search
     * reads only its type name, and the aux validate call reads only its
     * attributes (VEV-01), which the view answers as the entity GET did.
     * @param entity the read door's answer for the opened entity, or null
     */
    load(entity: EntityView | null): void {
        this.generation++;
        const generation = this.generation;
        // Every arrival re-reads from scratch, the funnel with it — the
        // sections store's rule (DD-327's sibling): a saved entity redraws
        // the box as if fresh.
        this.filter.set({ ...DEFAULT_FILTER });
        if (entity === null) {
            this.record.set({ entity: null, rules: [], verdicts: new Map(), loading: false });
            return;
        }

        this.record.set({ entity, rules: [], verdicts: new Map(), loading: true });
        this.readRules(entity, generation);
        this.readVerdicts(entity, generation);
    }

    /**
     * The rules of the entity's type (DET-42): one basic search, the
     * qualified-name prefix the server filters (DD-520). A failed answer
     * keeps the box empty and alerts nothing (DD-521); a loading flag
     * clears with the round.
     * @param entity the entity whose type names the prefix
     * @param generation the round the answer belongs to
     */
    private readRules(entity: EntityView, generation: number): void {
        const parameters: SearchParameters = {
            typeName: RULE_TYPE_NAME,
            excludeDeletedEntities: true,
            includeSubTypes: false,
            limit: RULE_LIMIT,
            attributes: [...RULE_ATTRIBUTES],
            entityFilters: {
                attributeName: "qualifiedName",
                operator: "startsWith",
                attributeValue: `${entity.typeName}--`,
            },
        };

        this.search.searchWithParameters(parameters).subscribe({
            next: (answer) => {
                if (this.generation !== generation) {
                    return; // a newer entity superseded this answer
                }
                const rules = (answer.entities ?? [])
                    .filter((header) => typeof header?.guid === "string" && header.guid !== "")
                    .filter((header) => isActive(header.attributes?.["active"]))
                    .map((header) => ({
                        guid: header.guid as string,
                        name: textOf(header.attributes?.["name"]) || textOf(header.displayText),
                        description: textOf(header.attributes?.["ruleDescription"]),
                        dimension: textOf(header.attributes?.["qualityDimension"]),
                        ruleType: textOf(header.attributes?.["ruleType"]),
                    }))
                    // The legacy's first sort option was the name (DET-42).
                    .sort((a, b) => a.name.localeCompare(b.name));
                this.record.update((current) =>
                    this.generation === generation && current.entity?.guid === entity.guid
                        ? { ...current, rules, loading: false }
                        : current,
                );
            },
            error: () => {
                // The quiet swallow (DD-521): an empty box, no alert.
                this.record.update((current) =>
                    this.generation === generation && current.entity?.guid === entity.guid
                        ? { ...current, rules: [], loading: false }
                        : current,
                );
            },
        });
    }

    /**
     * The verdicts over the opened entity (DET-42, DD-520): the editor's
     * call, unchanged (EDT-21's client). Its answer joins the rows on
     * `ruleGuid`; a failure leaves the rules iconless (the same swallow,
     * and the verdicts are the box's decoration, never its data).
     * Since 12.7a the draft rides `entityFromView` (DD-608's helper, the
     * editor's own shape): the aux API reads the type, the attributes, and
     * the picks (VEV-01 as amended, VEV-08), so a relationship rule's row
     * here answers with the ends the view carries — the same verdict the
     * editor's banner paints for the same entity (DD-632).
     * @param entity the opened entity, folded into the draft shape
     * @param generation the round the answer belongs to
     */
    private readVerdicts(entity: EntityView, generation: number): void {
        this.validateEntity.validateEntity(entityFromView(entity)).subscribe({
            next: (answer: EntityValidationResponse) => {
                if (this.generation !== generation) {
                    return;
                }
                const verdicts = new Map((answer.verdicts ?? []).map((verdict) => [verdict.ruleGuid, verdict]));
                this.record.update((current) =>
                    this.generation === generation && current.entity?.guid === entity.guid
                        ? { ...current, verdicts }
                        : current,
                );
            },
            error: () => {
                // No lines at all (the editor's rule, EDT-23): the box keeps
                // its rows, every one iconless.
                this.record.update((current) =>
                    this.generation === generation && current.entity?.guid === entity.guid
                        ? { ...current, verdicts: new Map() }
                        : current,
                );
            },
        });
    }
}

/**
 * Whether a rule is ACTIVE (VEV-03, 12.2's reading): only a false is not.
 * A missing `active`, or one stored as text, is active.
 * @param value the rule's stored `active` attribute
 */
function isActive(value: unknown): boolean {
    const bare =
        typeof value === "object" && value !== null && "raw" in value ? (value as { raw: unknown }).raw : value;

    return bare !== false;
}

/**
 * A stored text attribute as its string: bare, unwrapped from `{"raw": …}`,
 * or empty for anything else (the editor's `textOf` idiom).
 * @param value the stored attribute value
 */
function textOf(value: unknown): string {
    const bare =
        typeof value === "object" && value !== null && "raw" in value ? (value as { raw: unknown }).raw : value;

    return typeof bare === "string" ? bare : "";
}

/** The box's anchor (DET-48): the legacy `#gov-quality` id, its nav entry's target. */
export const GOV_QUALITY_ANCHOR = "gov-quality";

/** The default sort key (DET-45: Relevance, DET-42's name-read order). */
const DEFAULT_SORT = "relevance";

/**
 * The box's sort options (DET-45, DD-842): the legacy's four over the shared
 * Relevance default, in the legacy order. `Relevance`, `Dimension` and
 * `Rule Type` ride catalogue keys both catalogues carry; `Name` and
 * `Compliant` have none, so they keep the raw titlecased literal the legacy
 * select rendered (DET-21's precedent, the sort select's untranslated pair).
 */
const SORT_OPTIONS: CardSortOption[] = [
    { key: DEFAULT_SORT, label: $localize`:@@search.components.sorting.relevance:Relevance` },
    { key: "name", label: `Name` },
    { key: "dataqualityruledimension", label: $localize`:@@dataqualityruledimension:Dimension` },
    { key: "compliant", label: `Compliant` },
    { key: "dataqualitytype", label: $localize`:@@dataqualitytype:Rule Type` },
];

/** The box's facet groups in the legacy ask's order (DET-46). */
const GOV_FACETS: readonly FacetGroupKey[] = ["dataqualityruledimension", "dataqualitytype"];

/** The box's filter state — the sections store's shape, owned by this store (DD-841). */
interface GovFilterState {
    /** The submitted keyword; null means no filter (DET-47). */
    query: string | null;
    /** The input's text as typed, kept for the echo (the sections store's rule). */
    text: string | null;
    sort: string;
    descending: boolean;
    /** The selected values per group (VCF-11: OR within, AND across). */
    facetSelection: Record<string, string[]>;
    /** The page grown by the scroll container (DET-47). */
    shown: number;
}

/** The box's defaults, restored by the count line (DET-44). */
const DEFAULT_FILTER: GovFilterState = {
    query: null,
    text: null,
    sort: DEFAULT_SORT,
    descending: false,
    facetSelection: {},
    shown: PAGE_SIZE,
};

/**
 * Whether a row matches the keyword (DET-47): the term occurs,
 * case-insensitively, in the rule's name, description, dimension or rule type
 * — the texts a row carries, DET-20's rule read over the box's fields.
 * @param row the box's row
 * @param term the lowercased term
 */
function matchesRow(row: GovQualityRow, term: string): boolean {
    return (
        row.name.toLowerCase().includes(term) ||
        row.description.toLowerCase().includes(term) ||
        row.dimension.toLowerCase().includes(term) ||
        row.ruleType.toLowerCase().includes(term)
    );
}

/**
 * The values one row carries for one facet group (DET-46): the rule's
 * dimension or rule type; an empty value carries no value, so the row can
 * never match a selection of that group.
 * @param row the box's row
 * @param group the facet group's key
 */
function facetValuesOf(row: GovQualityRow, group: FacetGroupKey): string[] {
    const value = group === "dataqualityruledimension" ? row.dimension : row.ruleType;
    return value === "" ? [] : [value];
}

/**
 * Whether a row passes the selected facet values (DET-46, VCF-11): OR within
 * a group, AND across the box's groups; a group with no selection filters
 * nothing.
 * @param row the box's row
 * @param selection the selected values per group
 */
function passesFacets(row: GovQualityRow, selection: Record<string, string[]>): boolean {
    return GOV_FACETS.every((group) => {
        const chosen = selection[group];
        if (chosen === undefined || chosen.length === 0) {
            return true;
        }
        return facetValuesOf(row, group).some((value) => chosen.includes(value));
    });
}

/** The verdict's sort rank (DET-45): compliant first, refused next, no verdict last. */
function verdictRank(compliant: boolean | null): number {
    if (compliant === true) {
        return 0;
    }
    return compliant === false ? 1 : 2;
}

/**
 * Compare two text values with missing last ascending (DET-45: a missing
 * value sorts last in ascending order, so a reversed list leads with it).
 * @param a the first value
 * @param b the second value
 */
function compareText(a: string, b: string): number {
    if (a === b) {
        return 0;
    }
    if (a === "") {
        return 1;
    }
    if (b === "") {
        return -1;
    }
    return a.localeCompare(b);
}

/**
 * The box's comparator for one sort key (DET-45): Relevance keeps the read
 * order (every pair equal), the four legacy options compare the rule field
 * their key names. Ties resolve by the caller's Relevance index, so an equal
 * pair keeps its read order in either direction.
 * @param a the first row
 * @param b the second row
 * @param sort the selected key
 */
function compareRows(a: GovQualityRow, b: GovQualityRow, sort: string): number {
    if (sort === "name") {
        return compareText(a.name, b.name);
    }
    if (sort === "dataqualityruledimension") {
        return compareText(a.dimension, b.dimension);
    }
    if (sort === "dataqualitytype") {
        return compareText(a.ruleType, b.ruleType);
    }
    if (sort === "compliant") {
        return verdictRank(a.compliant) - verdictRank(b.compliant);
    }
    return 0; // relevance — the read order
}

/**
 * The filtered rows in sort order (DET-45): the comparator, the direction's
 * reversal, and Relevance order for equal pairs in both directions —
 * the stable index tiebreak the spec's last sentence asks for.
 * @param rows the filtered rows, in read order
 * @param sort the selected key
 * @param descending the direction button's state
 */
function sortedRows(rows: readonly GovQualityRow[], sort: string, descending: boolean): GovQualityRow[] {
    const indexed = rows.map((row, index) => ({ row, index }));
    const factor = descending ? -1 : 1;
    indexed.sort((a, b) => compareRows(a.row, b.row, sort) * factor || a.index - b.index);
    return indexed.map(({ row }) => row);
}

/**
 * The box's popover groups (DET-46, VCF-09..VCF-12 as the shared store
 * implements them): the configured groups with at least one row, counted over
 * the keyword-and-selection filtered set — a value at zero leaves the popover
 * with its checked row, a group whose last row left leaves with it. Rows
 * order by count, then label; the titles ride the catalogue map (DD-622's
 * map, the two keys' own units).
 * @param state the box's filter state
 * @param filtered the rows that passed the keyword and the selections
 */
function facetGroupsOf(state: GovFilterState, filtered: readonly GovQualityRow[]): CardFacetGroup[] {
    return GOV_FACETS.map((group) => {
        const counts = new Map<string, number>();
        for (const row of filtered) {
            for (const value of facetValuesOf(row, group)) {
                counts.set(value, (counts.get(value) ?? 0) + 1);
            }
        }
        const chosen = state.facetSelection[group] ?? [];
        const items: FacetItem[] = [...counts.entries()]
            .sort(([valueA, countA], [valueB, countB]) => countB - countA || valueA.localeCompare(valueB))
            .map(([value, count]) => ({ value, label: value, count, checked: chosen.includes(value) }));
        return { key: group, title: FACET_GROUP_TITLES[group], items };
    }).filter((group) => group.items.length > 0);
}
