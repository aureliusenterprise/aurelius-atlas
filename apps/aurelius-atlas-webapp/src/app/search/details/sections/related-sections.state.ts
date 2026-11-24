import { computed, inject, Injectable, signal } from "@angular/core";
import { type EntityCard, type EntityView, ViewSearchService } from "aurelius-atlas-data-access";
import type { CardFacetGroup, CardSortOption, FacetItem } from "aurelius-atlas-ui";

import { AlertsService } from "../../../alerts/alerts.service";
import { nameDisplay } from "../../meta/type-display";
import { sectionEnds, type SectionEnd } from "../shared/people";
import {
    dimensionScore,
    FACET_GROUP_TITLES,
    QUALITY_DIMENSIONS,
    QUALITY_DIMENSION_LABELS,
    qualitySortKey,
    type FacetGroupKey,
    type QualityDimension,
    type SectionDef,
    type TypeLayout,
} from "./section-config";

/** The resolve chunk size: one door request per chunk (DD-368, DD-615). */
export const CHUNK_SIZE = 25;

/** The legacy cards grid's page size (DET-22). */
export const PAGE_SIZE = 9;

/** One seed entry of a section, read off the relationship end (DET-17). */
interface SeedEntry {
    guid: string;
    displayText: string;
    typeName?: string;
    name?: string;
}

/** The section's interaction + resolve state, held in one signal value. */
interface SectionRecord {
    def: SectionDef;
    seed: SeedEntry[];
    /** Resolved door cards by guid (DD-615). */
    resolved: Map<string, EntityCard>;
    /** The guids whose chunk failed — their cards drop, the count stays (DET-18). */
    failed: Set<string>;
    /**
     * The guids a chunk answered without — deleted relations: no card,
     * the count keeps them, and no loading card stays (DET-18).
     */
    missing: Set<string>;
    /** Chunks still in flight. */
    pending: number;
    /** The submitted keyword the cards filter on; null means no filter (DET-20). */
    query: string | null;
    /**
     * The search box's text as typed (the part's model, mirrored on every
     * keystroke via the card section's `queryChange`). Held so the echo
     * survives a host re-render: the one-way binding into the part's model
     * rewrites it whenever a chunk answers mid-type, and without this
     * field the unsubmitted text would vanish.
     */
    text: string | null;
    sort: string;
    descending: boolean;
    /**
     * The popover's selected values per group (VCF-11, DD-620): one entry
     * per group, an array of values — the legacy `filters.all` shape, so
     * a group matches by OR and the groups compose by AND. A group with
     * its last untick loses its key, as the legacy service deleted it.
     */
    facetSelection: Record<string, string[]>;
    /** The page grown by the scroll container: how many filtered cards show. */
    shown: number;
}

/** One card of a section's grid: a resolved door card, or a loading placeholder. */
export type SectionCard =
    | {
          kind: "card";
          guid: string;
          displayText: string;
          card: EntityCard;
      }
    | {
          kind: "loading";
          guid: string;
          displayText: string;
          typeName?: string;
          name?: string;
      };

/** A section as the renderer draws it (the card-section component's inputs). */
export interface SectionView {
    /**
     * Marks the section's store for the screen's merged box list (7.25a,
     * DD-841): the relationship-seeded card section of DET-17..DET-22. The
     * Governance Quality Rules box carries `"gov-quality"` and its own store
     * (DET-48), and the discriminant picks which store a handler reaches.
     */
    kind: "related";
    anchor: string;
    title: string;
    /** The seed count — the count line and the stats bar (DET-17). */
    count: number;
    /** The popover's facet groups (VCF-08..VCF-12): the section's configured
     * groups with their rows, counts, and ticks over the filtered set. */
    facets: CardFacetGroup[];
    /** Whether the funnel marks the icon active — keyword, selection, or a
     * sort/direction away from its default (VCF-08, DV-169 amended). */
    filterActive: boolean;
    /** Whether the search filters the set (DET-20, VCF-13 extended to selections). */
    filtered: boolean;
    /** The count line's number: seed count, or the filtered count (DET-20). */
    countShown: number;
    /** Whether a resolve chunk is in flight — the scroll container's spinner. */
    loading: boolean;
    /** Whether the filtered set is exhausted (DET-22). */
    allLoaded: boolean;
    /** The search box's text — the card section's query input (DET-20). */
    query: string | null;
    sort: string;
    sortOptions: CardSortOption[];
    descending: boolean;
    /** The visible page of the filtered, sorted cards (DET-22). */
    cards: SectionCard[];
}

/** The sort select's options (DET-21): Relevance (the seed order) and Name. */
const SORT_OPTIONS: CardSortOption[] = [
    { key: "relevance", label: $localize`:@@search.components.sorting.relevance:Relevance` },
    // There is no catalogue key for the Name sort — the legacy select
    // rendered the raw option value titlecased, untranslated in both
    // locales; the literal keeps that rendering.
    { key: "name", label: `Name` },
];

/**
 * The sort options one section offers (DET-21, DET-59, DD-854): DET-21's
 * pair for a `"name"` section, the pair plus the five dimension sorts in
 * the legacy order for a `"score"` section — the legacy `*-cards`
 * component's `['name', 'dqscore_accuracy', …, 'dqscore_validity']` ask,
 * with the legacy's `dqscore_<dimension>` option values as the keys and
 * the `dqscore_<dimension>` catalogue keys as the labels.
 * @param def the section's config
 * @returns the select's options, in order
 */
function sortOptionsOf(def: SectionDef): CardSortOption[] {
    if (def.sorts !== "score") {
        return [...SORT_OPTIONS];
    }
    return [
        ...SORT_OPTIONS,
        ...QUALITY_DIMENSIONS.map((dimension) => ({
            key: qualitySortKey(dimension),
            label: QUALITY_DIMENSION_LABELS[dimension],
        })),
    ];
}

/** The default sort key (DET-21: Relevance, the seed order). */
const DEFAULT_SORT = "relevance";

/**
 * The details screen's card sections (DET-17..DET-22, DD-365/DD-368, DD-615):
 * the seed, the chunked resolve through the search door, and the
 * client-side filter, sort, and paging of every section of the entity's
 * layout.
 *
 * Since 16.5b the seed is the view's `sections` (VDR-03): each seed key's
 * ACTIVE ends carrying a guid, in order, deduped by guid — the same
 * {@link sectionEnds} rule the People box and the person stats count by, so
 * a seed, a stat and a box can never disagree. The count is the seed length
 * and shows at once, before any card resolves. Since 16.5d the guids resolve
 * through the search door (VCF-02, DD-615 — the legacy read its section
 * cards from the search engine): one `POST /api/aurelius/v1/search` per
 * chunk of 25, `filters.guid` the chunk and `limit` its length, no facets.
 * Until a chunk answers its cards show the loading row, a failed chunk
 * alerts once and drops its cards (the count keeps them), and a guid
 * missing from the `cards` answer is a deleted relation, not an error
 * (DET-18's rules, carried). Search, sort, and paging run client-side over
 * what the browser holds (DD-368).
 *
 * The store is per-screen (provided by `Details`): {@link seed} re-runs on
 * every entity arrival, including the editor's save re-read (DET-17), and
 * a superseded chunk answer paints nothing (the generation guard, DET-08's
 * sibling).
 */
@Injectable()
export class RelatedSectionsState {
    private readonly search = inject(ViewSearchService);

    private readonly alerts = inject(AlertsService);

    /** The sections of the current entity's layout. */
    private readonly records = signal<SectionRecord[]>([]);

    /** The resolve generation: a re-seed drops every in-flight answer. */
    private generation = 0;

    /** The view the last seed read ({@link endCount}'s source, DET-40). */
    private lastSeed: { view: EntityView | null } = { view: null };

    /** The sections as the renderer draws them, in layout order (one entry per seeded section). */
    readonly views = computed<readonly SectionView[]>(() => this.records().map((record) => this.viewOf(record)));

    /**
     * (Re-)seed every section from the view (DET-17, VDR-03): the count
     * shows at once and the resolve starts. A null view or layout clears
     * the sections; a new layout or view re-seeds from scratch — the
     * editor's save re-read rides this entry (DD-327).
     *
     * A section whose row says `seedFrom: "verdicts"` (7.25b, DD-848)
     * seeds from {@link verdicts} instead of the view's ends: the screen
     * hands the GUIDs the verdict door answered, in its order, keyed by
     * the section's anchor. Everything downstream — the chunked resolve,
     * the search, the facets, the page — is the shared card section
     * unchanged (DET-53); an anchor with no entry seeds empty.
     * @param view the read door's answer for the opened entity, or null
     * @param layout the entity's layout, or undefined for the default
     * @param verdicts seed GUIDs per anchor for the verdict-seeded boxes
     */
    seed(
        view: EntityView | null,
        layout: TypeLayout | undefined,
        verdicts: Record<string, readonly string[]> = {},
    ): void {
        this.generation++;
        this.lastSeed = { view };
        if (view === null || layout === undefined) {
            this.records.set([]);
            return;
        }

        const records = layout.sections.map((def) => ({
            def,
            seed: this.seedOf(view, def, verdicts),
            resolved: new Map<string, EntityCard>(),
            failed: new Set<string>(),
            missing: new Set<string>(),
            pending: 0,
            query: null,
            text: null,
            sort: DEFAULT_SORT,
            descending: false,
            facetSelection: {},
            shown: PAGE_SIZE,
        }));
        this.records.set(records);

        const generation = this.generation;
        for (const record of records) {
            this.resolve(record, generation);
        }
    }

    /**
     * The seed count of one section — the stats bar's number (DET-24).
     * @param anchor the section's anchor
     * @returns the seed length, or 0 when the section is not rendered
     */
    countFor(anchor: string): number {
        return this.records().find((record) => record.def.anchor === anchor)?.seed.length ?? 0;
    }

    /**
     * The count of one relationship end (DET-40, DD-519, VDR-03): the
     * person stats bar's per-end numbers, computed by the same
     * {@link sectionEnds} rule the seed and the People box ride — ACTIVE
     * ends carrying a guid, deduped by guid — so a stat and the merged
     * box's cards can never disagree. The seed follows the view, like
     * {@link seed}: the count is read from the last view passed to it.
     * @param key the relationship attribute name to count
     * @returns the deduped ACTIVE end count, 0 with no view or end
     */
    endCount(key: string): number {
        return sectionEnds(this.lastSeed.view?.sections, [key]).length;
    }

    /**
     * The search box's text on every keystroke (the card section's
     * `queryChange` model): the filter follows the typing (DD-375 — a
     * deliberate deviation: the legacy control emitted every keystroke on
     * `queryChanged` and its section ignored it, filtering only on
     * submit), and the page returns to its first size so the narrowed set
     * shows from the top.
     * @param anchor the section's anchor
     * @param text the box's text
     */
    setText(anchor: string, text: string | null): void {
        const term = text === null || text === "" ? null : text;
        this.update(anchor, (record) => ({ ...record, query: term, text: term, shown: PAGE_SIZE }));
    }

    /**
     * The submitted keyword of a section (DET-20): the submit/clear path
     * of the ui input. Since DD-375 the filter rides every keystroke, so
     * a submit of unchanged text changes nothing; the clear still lands
     * here (and on {@link setText}) and empties the box and the filter.
     * @param anchor the section's anchor
     * @param query the submitted term, or null on clear
     */
    setQuery(anchor: string, query: string | null): void {
        const term = query === null || query === "" ? null : query;
        this.update(anchor, (record) => ({ ...record, query: term, text: term, shown: PAGE_SIZE }));
    }

    /**
     * The count-line click while filtered (DET-20, VCF-13): the keyword,
     * the facet selections, and the sort return to their defaults — the
     * legacy reset link, which the demo showed clearing the ticks with the
     * keyword.
     * @param anchor the section's anchor
     */
    reset(anchor: string): void {
        this.update(anchor, (record) => ({
            ...record,
            query: null,
            text: null,
            sort: DEFAULT_SORT,
            descending: false,
            facetSelection: {},
            shown: PAGE_SIZE,
        }));
    }

    /**
     * A popover row ticked or unticked (VCF-11, DD-620): the value joins
     * or leaves its group's array — the legacy `filters.all` shape, with
     * the key deleted at the group's last untick (the legacy service's
     * rule). The page returns to its first size, as a keyword change does.
     * @param anchor the section's anchor
     * @param group the group's key
     * @param value the row's value
     * @param checked the row's new state
     */
    toggleFacet(anchor: string, group: string, value: string, checked: boolean): void {
        this.update(anchor, (record) => {
            const chosen = new Set(record.facetSelection[group] ?? []);
            if (checked) {
                chosen.add(value);
            } else {
                chosen.delete(value);
            }
            const facetSelection = { ...record.facetSelection };
            if (chosen.size === 0) {
                delete facetSelection[group];
            } else {
                facetSelection[group] = [...chosen];
            }
            return { ...record, facetSelection, shown: PAGE_SIZE };
        });
    }

    /**
     * The sort select's change (DET-21).
     * @param anchor the section's anchor
     * @param sort the selected key
     */
    setSort(anchor: string, sort: string | null): void {
        const key = sort === null || sort === "" ? DEFAULT_SORT : sort;
        this.update(anchor, (record) => ({ ...record, sort: key }));
    }

    /** The direction button's toggle (DET-21).
     * @param anchor the section's anchor
     */
    toggleDirection(anchor: string): void {
        this.update(anchor, (record) => ({ ...record, descending: !record.descending }));
    }

    /**
     * The sentinel or its button asked for the next page (DET-22): the
     * page grows by 9 over the filtered, sorted set.
     * @param anchor the section's anchor
     */
    nextPage(anchor: string): void {
        this.update(anchor, (record) => ({ ...record, shown: record.shown + PAGE_SIZE }));
    }

    /**
     * The seed of one section (DET-17, VDR-03): the view's ACTIVE ends for
     * the section's keys, in order, deduped by guid — {@link sectionEnds}.
     * A verdict-seeded row (7.25b, DD-848) answers the screen's GUIDs for
     * its anchor instead, in door order, deduped the same way; the display
     * text starts as the guid and the resolved card replaces it.
     * @param view the read door's answer for the opened entity
     * @param def the section's config
     * @param verdicts seed GUIDs per anchor, keyed by anchor (DD-848)
     * @returns the seed entries
     */
    private seedOf(view: EntityView, def: SectionDef, verdicts: Record<string, readonly string[]>): SeedEntry[] {
        if (def.seedFrom === "verdicts") {
            const seen = new Set<string>();
            return (verdicts[def.anchor] ?? [])
                .filter((guid) => (seen.has(guid) ? false : (seen.add(guid), true)))
                .map((guid) => ({ guid, displayText: guid }));
        }
        return sectionEnds(view.sections, def.seedKeys).map(seedEntry);
    }

    /**
     * Resolve one section's seed (DET-18, VCF-02, DD-615): the guids travel
     * to the search door in chunks of 25 — `filters.guid` the chunk,
     * `limit` its length, no facets; answers paint only while the section's
     * generation still stands.
     * @param record the section's record
     * @param generation the seed generation the resolve belongs to
     */
    private resolve(record: SectionRecord, generation: number): void {
        const guids = record.seed.map((entry) => entry.guid);
        if (guids.length === 0) {
            return;
        }

        this.bumpPending(record.def.anchor, Math.ceil(guids.length / CHUNK_SIZE));

        for (let start = 0; start < guids.length; start += CHUNK_SIZE) {
            const chunk = guids.slice(start, start + CHUNK_SIZE);
            this.search.search({ filters: { guid: chunk }, limit: chunk.length }).subscribe({
                next: (answer) => {
                    if (this.generation !== generation) {
                        return; // a re-seed superseded this answer
                    }
                    const byGuid = new Map(
                        (answer.cards ?? [])
                            .filter((card) => typeof card?.guid === "string")
                            .map((card) => [card.guid as string, card]),
                    );
                    this.update(record.def.anchor, (current) => {
                        const resolved = new Map(current.resolved);
                        const missing = new Set(current.missing);
                        for (const guid of chunk) {
                            const card = byGuid.get(guid);
                            if (card !== undefined) {
                                resolved.set(guid, card);
                            } else {
                                // A guid missing from the answer is a
                                // deleted relation — or one the indexer
                                // has not reached yet (DD-615):
                                // no card, the count keeps it (DET-18).
                                missing.add(guid);
                            }
                        }
                        return { ...current, resolved, missing, pending: current.pending - 1 };
                    });
                },
                error: () => {
                    if (this.generation !== generation) {
                        return;
                    }
                    this.update(record.def.anchor, (current) => {
                        const failed = new Set(current.failed);
                        for (const guid of chunk) {
                            failed.add(guid);
                        }
                        return { ...current, failed, pending: current.pending - 1 };
                    });
                    // One alert per failed chunk, the DET-13 idiom; no
                    // retry loop (DET-18). The cards the section has stay.
                    this.alerts.add({
                        severity: "error",
                        message: $localize`:@@search.services.entityDetails.retrieve:Retrieving the entity details`,
                        source: "search",
                    });
                },
            });
        }
    }

    /** Count resolve chunks in for a section before their answers arrive. */
    private bumpPending(anchor: string, chunks: number): void {
        this.update(anchor, (record) => ({ ...record, pending: record.pending + chunks }));
    }

    /**
     * Replace one section's record, keeping the others.
     * @param anchor the section's anchor
     * @param change the record's new value
     */
    private update(anchor: string, change: (record: SectionRecord) => SectionRecord): void {
        this.records.update((records) =>
            records.map((record) => (record.def.anchor === anchor ? change(record) : record)),
        );
    }

    /**
     * The view of one record: filter (DET-20), sort (DET-21), and page
     * (DET-22) over the seed order.
     * @param record the section's record
     * @returns the renderer's view
     */
    private viewOf(record: SectionRecord): SectionView {
        const term = record.query?.toLowerCase() ?? "";
        // VCF-08/VCF-13: a selection or the keyword filters the section.
        const selectionActive = Object.values(record.facetSelection).some((values) => values.length > 0);
        const cards: SectionCard[] = record.seed
            .filter((entry) => !record.failed.has(entry.guid) && !record.missing.has(entry.guid))
            .map((entry) => {
                const entity = record.resolved.get(entry.guid);
                if (entity === undefined) {
                    return {
                        kind: "loading" as const,
                        guid: entry.guid,
                        displayText: entry.displayText,
                        ...(entry.typeName !== undefined ? { typeName: entry.typeName } : {}),
                        ...(entry.name !== undefined ? { name: entry.name } : {}),
                    };
                }
                return {
                    kind: "card" as const,
                    guid: entry.guid,
                    displayText: entity.displayText,
                    card: entity,
                };
            });

        // VCF-14, DD-621: a card that has not resolved cannot be tested
        // against a value it does not carry, so it hides while any
        // selection is active — and shows as DET-18's loading row otherwise.
        const testable = selectionActive ? cards.filter((card) => card.kind === "card") : cards;
        // VCF-11: the keyword ANDs with the selections; VCF-12: the facet
        // rows count over the set both filtered.
        const matched = testable
            .filter((card) => term === "" || matches(card, term))
            .filter((card) => passesFacets(card, record.facetSelection, record.def.facets));
        const sorted = this.sorted(matched, record);
        const filtered = record.query !== null || selectionActive;
        // VCF-08 (DV-169 amended): the legacy funnel marks on the whole
        // query object, so a sort key or direction away from its default
        // marks it too — the demo's isFilterActive$ is the section's
        // queryObject differing from its default, and its sorting
        // component writes sort and direction into that object.
        const stateApplied = filtered || record.sort !== DEFAULT_SORT || record.descending;

        return {
            kind: "related",
            anchor: record.def.anchor,
            title: record.def.title,
            facets: facetGroupsOf(record, matched),
            filterActive: stateApplied,
            count: record.seed.length,
            filtered,
            countShown: filtered ? sorted.length : record.seed.length,
            loading: record.pending > 0,
            allLoaded: sorted.length <= record.shown,
            query: record.text,
            sort: record.sort,
            sortOptions: sortOptionsOf(record.def),
            descending: record.descending,
            cards: sorted.slice(0, record.shown),
        };
    }

    /**
     * The filtered cards in sort order (DET-21, DET-59): Relevance keeps
     * the seed order, Name compares the display texts, and a score section
     * orders on the sorted dimension's row (ascending, cards without that
     * row last — the door's own missing-last rule); the direction reverses.
     * @param cards the filtered cards
     * @param record the section's record
     * @returns the sorted cards
     */
    private sorted(cards: SectionCard[], record: SectionRecord): SectionCard[] {
        const sorted = [...cards];
        const dimension = scoreSectionDimension(record);
        if (dimension !== undefined) {
            sorted.sort((a, b) => compareByScore(a, b, dimension));
        } else if (record.sort === "name") {
            sorted.sort((a, b) => a.displayText.localeCompare(b.displayText));
        }
        return record.descending ? sorted.reverse() : sorted;
    }
}

/**
 * The dimension a section is sorting on (DET-59), or `undefined` for
 * Relevance, Name, and any sort key a non-score section does not offer.
 * @param record the section's record
 */
function scoreSectionDimension(record: SectionRecord): QualityDimension | undefined {
    if (record.def.sorts !== "score") {
        return undefined;
    }
    return QUALITY_DIMENSIONS.find((dimension) => qualitySortKey(dimension) === record.sort);
}

/**
 * The two cards' order on one score dimension (DET-59): the lower score
 * first — the legacy engine's ascending ask — with a card that holds no
 * usable row for the dimension last (DET-63's last place). Cards the
 * dimension cannot separate fall back to the webapp's label-sort
 * convention (DD-493): the localised display text, then the raw name.
 * @param a the first card
 * @param b the second card
 * @param dimension the sorted dimension
 * @returns the comparator's result
 */
function compareByScore(a: SectionCard, b: SectionCard, dimension: QualityDimension): number {
    const scoreA = dimensionScore(a.kind === "card" ? a.card.quality : undefined, dimension);
    const scoreB = dimensionScore(b.kind === "card" ? b.card.quality : undefined, dimension);
    if (scoreA === undefined && scoreB === undefined) {
        return compareByLabel(a, b);
    }
    if (scoreA === undefined) {
        return 1;
    }
    if (scoreB === undefined) {
        return -1;
    }
    return scoreA - scoreB || compareByLabel(a, b);
}

/**
 * The label tie-break (DET-59, DD-493): the display text with the locale's
 * collation, then the raw name the card carries.
 * @param a the first card
 * @param b the second card
 */
function compareByLabel(a: SectionCard, b: SectionCard): number {
    const byText = a.displayText.localeCompare(b.displayText);
    if (byText !== 0) {
        return byText;
    }
    const nameA = a.kind === "card" ? (a.card.name ?? "") : "";
    const nameB = b.kind === "card" ? (b.card.name ?? "") : "";
    return nameA.localeCompare(nameB);
}

/**
 * The values one card carries for one facet group (VCF-09, DD-619): a
 * chain or role key reads the card's stored derived relations of that
 * attribute — the direct ends, by name (AVS-02, LAS-05; the role keys read
 * the door's role relations, VCF-18/AVS-10); Type Name reads the card's
 * type name; Name reads its display text. A card without the field
 * contributes nothing, and one card counts a value once.
 * @param card the resolved section card
 * @param group the facet group's key
 * @returns the card's values for the group, deduplicated
 */
function facetValuesOf(card: SectionCard, group: FacetGroupKey): string[] {
    if (card.kind !== "card") {
        return [];
    }
    if (group === "typeName") {
        return [card.card.typeName];
    }
    if (group === "name") {
        return [card.card.displayText];
    }
    const relation = card.card.relations?.find((entry) => entry.attribute === group);
    return [
        ...new Set((relation?.entities ?? []).map((entity) => entity.name).filter((name) => typeof name === "string")),
    ] as string[];
}

/**
 * Whether a card passes the selected facet values (VCF-11, DD-620): the
 * legacy check-box service's shape — within a group the card matches by
 * OR over the chosen values, across groups by AND over the configured
 * groups. A group with no selection filters nothing; only the section's
 * configured groups are tested.
 * @param card the section card
 * @param selection the selected values per group
 * @param groups the section's configured groups
 * @returns whether the card carries every group's selection
 */
function passesFacets(
    card: SectionCard,
    selection: Record<string, string[]>,
    groups: readonly FacetGroupKey[],
): boolean {
    return groups.every((group) => {
        const chosen = selection[group];
        if (chosen === undefined || chosen.length === 0) {
            return true;
        }
        return facetValuesOf(card, group).some((value) => chosen.includes(value));
    });
}

/**
 * The section's popover groups (VCF-09, VCF-12, DD-619): the configured
 * groups with at least one row, each counted over the keyword-and-facet
 * filtered set — a value at zero leaves the popover (a checked row with
 * it), and the last untick returns it; a group whose last row left leaves
 * with it, as the legacy FilterService dropped empty facets (SDX-03).
 * Rows order by count, then label; the titles ride the catalogue map (DD-622).
 * @param record the section's record
 * @param filtered the cards that passed the keyword and the selections
 * @returns the groups in configured order, rows counted and ticked
 */
function facetGroupsOf(record: SectionRecord, filtered: readonly SectionCard[]): CardFacetGroup[] {
    return record.def.facets
        .map((group) => {
            const counts = new Map<string, number>();
            for (const card of filtered) {
                for (const value of facetValuesOf(card, group)) {
                    counts.set(value, (counts.get(value) ?? 0) + 1);
                }
            }
            const chosen = record.facetSelection[group] ?? [];
            const items: FacetItem[] = [...counts.entries()]
                .sort(([valueA, countA], [valueB, countB]) => countB - countA || valueA.localeCompare(valueB))
                .map(([value, count]) => ({
                    value,
                    label: group === "typeName" ? (nameDisplay(value) ?? value) : value,
                    count,
                    checked: chosen.includes(value),
                }));
            return { key: group, title: FACET_GROUP_TITLES[group], items };
        })
        .filter((group) => group.items.length > 0);
}

/**
 * Whether a card matches the submitted keyword (DET-20, DD-368, VCF-05):
 * the term occurs, case-insensitively, in the card's display text, its
 * `qualifiedName`, or its description text (the `definition` field, DD-614
 * — the door card carries no attribute map).
 * @param card the section's card
 * @param term the lowercased term
 * @returns whether the card matches
 */
function matches(card: SectionCard, term: string): boolean {
    if (card.displayText.toLowerCase().includes(term)) {
        return true;
    }
    if (card.kind === "loading") {
        // A card still resolving matches on its seed's own texts (DET-20).
        return card.name?.toLowerCase().includes(term) ?? false;
    }
    const qualifiedName = card.card.qualifiedName;
    if (typeof qualifiedName === "string" && qualifiedName.toLowerCase().includes(term)) {
        return true;
    }
    const definition = card.card.definition;
    return typeof definition === "string" && definition.toLowerCase().includes(term);
}

/**
 * The seed entry a view's section end becomes: its guid and texts — the
 * loading card's title until the door answer resolves the card. A view's
 * end names itself (VDR-02): the name, the guid as the last resort.
 * @param end the deduped ACTIVE end
 * @returns the seed entry
 */
function seedEntry(end: SectionEnd): SeedEntry {
    const name = typeof end.name === "string" && end.name !== "" ? end.name : undefined;

    return {
        guid: end.guid,
        displayText: name ?? end.guid,
        ...(typeof end.typeName === "string" && end.typeName !== "" ? { typeName: end.typeName } : {}),
        ...(name !== undefined ? { name } : {}),
    };
}

/**
 * The loading card's label (DET-18): the Aurelius `search.details.loading`
 * ("Loading {{name}}...") interpolated with the seed entry's display text —
 * the catalogue's placeholder key, so both locales carry the sentence and
 * `i18n-completeness.spec.ts` sees the same unit the bridge generated.
 * @param displayText the seed entry's display text
 * @returns the loading row's label
 */
export function loadingLabel(displayText: string): string {
    return $localize`:@@search.details.loading:Loading ${displayText}:name:...`;
}
