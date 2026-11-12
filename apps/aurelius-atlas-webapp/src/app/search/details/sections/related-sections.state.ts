import { computed, inject, Injectable, signal } from "@angular/core";
import { AtlasEntitiesService, type AtlasEntity, type AtlasRelatedEntity } from "aurelius-atlas-data-access";
import type { CardSortOption } from "aurelius-atlas-ui";

import { AlertsService } from "../../../alerts/alerts.service";
import { cardDescription, cardDisplayText, cardTypeAlias } from "../shared/card";
import type { SectionDef, TypeLayout } from "./section-config";

/** The bulk read's chunk size: a browser- and edge-sized URL (DD-368). */
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
    /** Resolved card entities by guid. */
    resolved: Map<string, AtlasEntity>;
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
    /** The page grown by the scroll container: how many filtered cards show. */
    shown: number;
}

/** One card of a section's grid: a resolved entity, or a loading placeholder. */
export type SectionCard =
    | {
          kind: "card";
          guid: string;
          displayText: string;
          alias?: string;
          entity: AtlasEntity;
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
    anchor: string;
    title: string;
    /** The seed count — the count line and the stats bar (DET-17). */
    count: number;
    /** Whether the search filters the set (DET-20). */
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

/** The default sort key (DET-21: Relevance, the seed order). */
const DEFAULT_SORT = "relevance";

/**
 * The details screen's card sections (DET-17..DET-22, DD-365/DD-368): the
 * seed, the chunked bulk resolve, and the client-side filter, sort, and
 * paging of every section of the entity's layout.
 *
 * The seed is the entity's own `relationshipAttributes` (DET-17): each
 * seed key's ACTIVE entries carrying a guid, in order, deduped by guid —
 * the EDT-15 rule shared with the editor's seed. The count is the seed
 * length and shows at once, before any card resolves. The guids resolve
 * through `getEntitiesByGuids` in chunks of 25 (DET-18); until a chunk
 * answers its cards show the loading row, a failed chunk alerts once and
 * drops its cards (the count keeps them), and a guid missing from the
 * answer is a deleted relation, not an error. Search, sort, and paging run
 * client-side over what the browser holds (DD-368).
 *
 * The store is per-screen (provided by `Details`): {@link seed} re-runs on
 * every entity arrival, including the editor's save re-read (DET-17), and
 * a superseded chunk answer paints nothing (the generation guard, DET-08's
 * sibling).
 */
@Injectable()
export class RelatedSectionsState {
    private readonly entities = inject(AtlasEntitiesService);

    private readonly alerts = inject(AlertsService);

    /** The sections of the current entity's layout. */
    private readonly records = signal<SectionRecord[]>([]);

    /** The resolve generation: a re-seed drops every in-flight answer. */
    private generation = 0;

    /** The entity the last seed read ({@link endCount}'s source, DET-40). */
    private lastSeed: { entity: AtlasEntity | null } = { entity: null };

    /** The sections as the renderer draws them, in layout order. */
    readonly views = computed<SectionView[]>(() => this.records().map((record) => this.viewOf(record)));

    /**
     * (Re-)seed every section from the entity (DET-17): the count shows at
     * once and the resolve starts. A null entity or layout clears the
     * sections; a new layout or entity re-seeds from scratch — the editor's
     * save re-read rides this entry (DD-327).
     * @param entity the resolved entity, or null
     * @param layout the entity's layout, or undefined for the default
     */
    seed(entity: AtlasEntity | null, layout: TypeLayout | undefined): void {
        this.generation++;
        this.lastSeed = { entity };
        if (entity === null || layout === undefined) {
            this.records.set([]);
            return;
        }

        const records = layout.sections.map((def) => ({
            def,
            seed: this.seedOf(entity, def),
            resolved: new Map<string, AtlasEntity>(),
            failed: new Set<string>(),
            missing: new Set<string>(),
            pending: 0,
            query: null,
            text: null,
            sort: DEFAULT_SORT,
            descending: false,
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
     * The count of one `relationshipAttributes` end (DET-40, DD-519): the
     * person stats bar's per-end numbers, computed by the same seed rule
     * the sections ride — ACTIVE entries carrying a guid, deduped by guid
     * — so a stat and the merged box's cards can never disagree. The seed
     * follows the entity, like {@link seed}: the count is read from the
     * last entity passed to it.
     * @param key the `relationshipAttributes` key to count
     * @returns the deduped ACTIVE entry count, 0 with no entity or end
     */
    endCount(key: string): number {
        const entity = this.lastSeed.entity;
        if (entity === null) {
            return 0;
        }

        const stored = entity.relationshipAttributes ?? {};
        const seen = new Set<string>();
        for (const row of asRelatedList(stored[key])) {
            if (row.relationshipStatus !== undefined && row.relationshipStatus !== "ACTIVE") {
                continue; // EDT-15: a DELETED edge counts nothing
            }
            if (typeof row.guid === "string" && row.guid !== "") {
                seen.add(row.guid);
            }
        }

        return seen.size;
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
     * The count-line click while filtered (DET-20): the query and the sort
     * return to their defaults — the legacy reset link.
     * @param anchor the section's anchor
     */
    reset(anchor: string): void {
        this.update(anchor, (record) => ({
            ...record,
            query: null,
            text: null,
            sort: DEFAULT_SORT,
            descending: false,
            shown: PAGE_SIZE,
        }));
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
     * The seed of one section (DET-17): the entity's ACTIVE relationship
     * entries for the section's keys, in order, deduped by guid.
     * @param entity the resolved entity
     * @param def the section's config
     * @returns the seed entries
     */
    private seedOf(entity: AtlasEntity, def: SectionDef): SeedEntry[] {
        const stored = entity.relationshipAttributes ?? {};
        const entries: SeedEntry[] = [];
        const seen = new Set<string>();

        for (const key of def.seedKeys) {
            for (const row of asRelatedList(stored[key])) {
                if (row.relationshipStatus !== undefined && row.relationshipStatus !== "ACTIVE") {
                    continue; // EDT-15: a DELETED edge seeds nothing
                }
                if (typeof row.guid !== "string" || row.guid === "" || seen.has(row.guid)) {
                    continue;
                }
                seen.add(row.guid);
                entries.push(seedEntry(row));
            }
        }

        return entries;
    }

    /**
     * Resolve one section's seed (DET-18): the guids travel to
     * `GET /v2/entity/bulk` in chunks of 25; answers paint only while the
     * section's generation still stands.
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
            this.entities.getEntitiesByGuids(chunk).subscribe({
                next: (answer) => {
                    if (this.generation !== generation) {
                        return; // a re-seed superseded this answer
                    }
                    const byGuid = new Map(
                        (answer.entities ?? [])
                            .filter((entity) => typeof entity?.guid === "string")
                            .map((entity) => [entity.guid as string, entity]),
                    );
                    this.update(record.def.anchor, (current) => {
                        const resolved = new Map(current.resolved);
                        const missing = new Set(current.missing);
                        for (const guid of chunk) {
                            const entity = byGuid.get(guid);
                            if (entity !== undefined) {
                                resolved.set(guid, entity);
                            } else {
                                // A guid missing from the answer is a
                                // deleted relation: no card, the count
                                // keeps it (DET-18).
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
                const alias = cardTypeAlias(entity);
                return {
                    kind: "card" as const,
                    guid: entry.guid,
                    displayText: cardDisplayText(entity),
                    ...(alias !== undefined ? { alias } : {}),
                    entity,
                };
            });

        const matched = term === "" ? cards : cards.filter((card) => matches(card, term));
        const sorted = this.sorted(matched, record);

        return {
            anchor: record.def.anchor,
            title: record.def.title,
            count: record.seed.length,
            filtered: record.query !== null,
            countShown: record.query === null ? record.seed.length : sorted.length,
            loading: record.pending > 0,
            allLoaded: sorted.length <= record.shown,
            query: record.text,
            sort: record.sort,
            sortOptions: SORT_OPTIONS,
            descending: record.descending,
            cards: sorted.slice(0, record.shown),
        };
    }

    /**
     * The filtered cards in sort order (DET-21): Relevance keeps the seed
     * order, Name compares the display texts; the direction reverses.
     * @param cards the filtered cards
     * @param record the section's record
     * @returns the sorted cards
     */
    private sorted(cards: SectionCard[], record: SectionRecord): SectionCard[] {
        const sorted =
            record.sort === "name" ? [...cards].sort((a, b) => a.displayText.localeCompare(b.displayText)) : [...cards];
        return record.descending ? sorted.reverse() : sorted;
    }
}

/**
 * Whether a card matches the submitted keyword (DET-20, DD-368): the term
 * occurs, case-insensitively, in the display text, the `name` or
 * `qualifiedName` attribute, or the description text.
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
    const attributes = card.entity.attributes ?? {};
    const name = attributes["name"];
    if (typeof name === "string" && name.toLowerCase().includes(term)) {
        return true;
    }
    const qualifiedName = attributes["qualifiedName"];
    if (typeof qualifiedName === "string" && qualifiedName.toLowerCase().includes(term)) {
        return true;
    }
    return cardDescription(card.entity).toLowerCase().includes(term);
}

/**
 * The seed entry a relationship end becomes: its guid and display texts —
 * the loading card's title until the bulk answer resolves the entity.
 * @param row the relationship end
 * @returns the seed entry
 */
function seedEntry(row: AtlasRelatedEntity): SeedEntry {
    let displayText = typeof row.guid === "string" ? row.guid : "";
    if (typeof row.name === "string" && row.name !== "") {
        displayText = row.name;
    }
    if (typeof row.displayText === "string" && row.displayText !== "") {
        displayText = row.displayText;
    }

    return {
        guid: row.guid as string,
        displayText,
        ...(typeof row.typeName === "string" && row.typeName !== "" ? { typeName: row.typeName } : {}),
        ...(typeof row.name === "string" && row.name !== "" ? { name: row.name } : {}),
    };
}

/**
 * A read's `relationshipAttributes` value as a list (the editor's twin:
 * a SET end answers as a list, a SINGLE end as one object).
 * @param value the raw value
 * @returns the related entities
 */
function asRelatedList(value: unknown): AtlasRelatedEntity[] {
    if (Array.isArray(value)) {
        return value as AtlasRelatedEntity[];
    }
    if (value !== null && typeof value === "object") {
        return [value as AtlasRelatedEntity];
    }

    return [];
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
