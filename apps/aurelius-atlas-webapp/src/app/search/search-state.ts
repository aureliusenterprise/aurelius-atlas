import { HttpErrorResponse } from "@angular/common/http";
import { Injectable, computed, inject, signal } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import {
    EntityCard as ViewCard,
    FacetEntry,
    ViewSearchMode,
    ViewSearchRequest,
    ViewSearchService,
} from "aurelius-atlas-data-access";
import { FacetItem } from "aurelius-atlas-ui";

import { AlertsService } from "../alerts/alerts.service";
import { SearchMode, SearchModeService } from "../settings/search-mode.service";
import { nameDisplay } from "./meta/type-display";

/** The door's type-facet key (VSR-06) — the one facet the screen filters on (DD-426). */
const TYPE_FACET = "typeName";

/**
 * The facet titles (SDX-08, DD-427, DD-603): the door's facet names carry the
 * four labels the wire's `__`-prefixed keys wore — the `$localize` ids are
 * unchanged, so no dictionary key moves. An unknown facet key renders raw,
 * the legacy's missing-key answer.
 */
const FACET_TITLES: Record<string, string> = {
    [TYPE_FACET]: $localize`:@@search.components.filter.type:Type`,
    status: $localize`:@@search.components.filter.state:State`,
    owner: $localize`:@@search.components.filter.owner:Owner`,
    serviceType: $localize`:@@search.components.filter.serviceType:Service Type`,
};

/** The type facet's asked size (VSR-06): DD-093's facet counted 100 values. */
const TYPE_FACET_SIZE = 100;

/** The most entities a search by meaning answers (DD-441, DD-479). */
const MAX_NEAREST = 1000;

/** The server's code for a server without search by meaning (SBM-06, ASV-09). */
const EMBEDDING_OFF = "AURELIUS-404-00-001";

/** One sidebar facet as the results screen renders it (SDX-03). */
export type FacetView = {
    /** The door's facet key (`typeName`, `status`, `owner`, `serviceType`). */
    readonly key: string;
    /** The localised menu title (SDX-08). */
    readonly title: string;
    /** The value rows, in display order (SDX-04/05). */
    readonly items: FacetItem[];
    /** Whether the rows are checkboxes — only the type facet is (DD-426). */
    readonly selectable: boolean;
};

/** A type facet value with its last-seen count (SDX-07's seen row). */
type TypeRow = {
    readonly value: string;
    readonly count: number;
};

/**
 * The search slice's session store (SRH-02, DD-219): the query arrives from
 * the URL, pages accumulate here, and nothing in the URL grows past
 * `?query=`. Provided by the layout component — leaving the `/search`
 * subtree destroys the store, so a fresh visit to browse resets the search
 * (the legacy `NavigationEnd` reset, by construction).
 *
 * The query opens the view family's search door (VSR-03, ADR 064, POST
 * `/aurelius/v1/search`) with pages of ten (the legacy page size, SRH-04):
 * one body carries the query, the mode, the filters and the four sidebar
 * facets, and one answer carries the page of cards and every facet's counts
 * (AVR-08) — there is no second request for the sidebar, and no second
 * endpoint for a search by meaning: the stored mode names the body's `mode`
 * key (SBX-02, ASV-01, DD-602). `run` is the hero's
 * submit, `explore` the browse cards' buttons, `nextPage` the
 * infinite-scroll container's, `toggleType` the sidebar's checkbox. A
 * selected type filters entities of that type and of its sub types: the
 * door's `filters` hold an `any` of the names under `typeName` and under
 * `superTypeNames` (VSR-04, DD-600) — the documents carry the whole super
 * chain, so no typedef walk is needed. An empty query with no type
 * selection sends no filter and answers every entity (AVR-11): quick
 * search's every-entity marker left with the wire it belonged to (DD-600),
 * the demo resolver's list-everything default (DD-221) answering on its
 * own. A search the door answers with an error
 * lands in the alerts drawer (the DD-214 failure path, the legacy pipeline
 * strip's successor).
 */
@Injectable()
export class SearchState {
    private readonly door = inject(ViewSearchService);

    private readonly searchMode = inject(SearchModeService);

    private readonly alerts = inject(AlertsService);

    /** The legacy `pageSize` (the results store's 10). */
    static readonly PAGE_SIZE = 10;

    /** The cards accumulated across pages, in answer order (SRH-04, VSR-07). */
    readonly entries = signal<ViewCard[]>([]);

    /** The door's count of the current search (`total`, AVR-07). */
    readonly total = signal(0);

    /**
     * How the search field searches (SBX-01, DD-473): the stored setting
     * the settings panel writes, never in the URL.
     */
    readonly mode = this.searchMode.mode;

    /**
     * Whether the list is a search by meaning (SBW-03): Meaning or Both,
     * with a query — an empty query lists as before, whatever the mode.
     */
    readonly byMeaning = computed(() => this.mode() !== "words" && this.queryText().trim() !== "");

    /** The header's count (SBW-04, DD-479, VSR-05): the entities shown by meaning, the door's count by words. */
    readonly shownCount = computed(() => (this.byMeaning() ? this.entries().length : this.total()));

    /** The last page came back full: by meaning, the sign there is more (SBW-04, DD-479). */
    private readonly lastPageFull = signal(true);

    /** A page is in flight — the container's spinner (SRH-04). */
    readonly loading = signal(false);

    /**
     * The session type selection (SDX-04/06, DD-425): the explore buttons'
     * single filter (SRH-08) and the sidebar's checked values, one list —
     * it is sent as the comma-joined `typeName` (SRC-03) and never enters
     * the URL (DD-219 stands, DD-425).
     */
    readonly typeSelection = signal<readonly string[]>([]);

    /**
     * The type facet's visible rows (SDX-07): every value the sidebar has
     * shown for the current query, the answer's counts where the narrowed
     * answer still carries the value, the last count where it does not
     * (DD-426). Reset when the query changes.
     */
    private readonly typeRows = signal<readonly TypeRow[]>([]);

    /** The door's non-type facets of the last answer, in answer order, empty ones dropped (SDX-03/05). */
    private readonly otherFacets = signal<readonly { key: string; entries: readonly FacetEntry[] }[]>([]);

    /**
     * The sidebar's facets (SDX-03, VSR-06): the type facet first (the store
     * asks it first), then `status`, `owner` and `serviceType` as the answer
     * carries them; empty facets are not rendered (the legacy
     * `FilterService` dropped them). Only the type facet is selectable
     * (DD-426): the other three answer what quick search's aggregator
     * answered, and the door filters what the sidebar can name (SDX-05).
     */
    readonly facets = computed<FacetView[]>(() => {
        const views: FacetView[] = [];
        const rows = this.typeRows();
        if (rows.length > 0) {
            const selected = this.typeSelection();
            views.push({
                key: TYPE_FACET,
                title: FACET_TITLES[TYPE_FACET],
                selectable: true,
                items: rows.map((row) => ({
                    value: row.value,
                    label: nameDisplay(row.value) ?? row.value,
                    count: row.count,
                    checked: selected.includes(row.value),
                })),
            });
        }
        for (const facet of this.otherFacets()) {
            views.push({
                key: facet.key,
                title: FACET_TITLES[facet.key] ?? facet.key,
                selectable: false,
                items: facet.entries.map((entry) => ({
                    value: `${entry.value}`,
                    label: `${entry.value}`,
                    count: entry.count,
                })),
            });
        }
        return views;
    });

    /**
     * Every entity of the search is listed (the legacy equality, SRH-04); by
     * meaning, once a page came back short or 1,000 are shown, as a search
     * by meaning counts what it was asked for (SBW-04, DD-479, VSR-05).
     */
    readonly allLoaded = computed(() => {
        if (this.loading()) {
            return false;
        }
        if (this.byMeaning()) {
            return !this.lastPageFull() || this.entries().length >= MAX_NEAREST;
        }
        return this.entries().length >= this.total();
    });

    /** Cards render (SRH-05). */
    readonly hasResults = computed(() => this.entries().length > 0);

    /** The no-results pair renders (SRH-06): answered zero, or nothing to ask. */
    readonly noResults = computed(() => !this.loading() && this.entries().length === 0 && this.total() === 0);

    /** The search's text, `""` for the explore landings (the hero's field reads it). */
    readonly queryText = signal("");

    /** The next page's offset. */
    private offset = 0;

    /** A search has run this session (the URL effect's re-run guard). */
    private searched = false;

    /**
     * The hero's submit (SRH-01, SRH-02, SDX-06): the query is the search,
     * and the facet selection clears — the legacy `onQuerySubmitted`
     * cleared `filters` before navigating, now for the sidebar's checks
     * too (the rule SRH-02 already had for the explore filter). The layout
     * navigates to the results route alongside; the URL carries the text
     * (SRH-02, DD-219).
     * @param query the submitted query, `null` for a cleared field
     */
    run(query: string | null): void {
        this.queryText.set(query ?? "");
        this.typeSelection.set([]);
        this.restart(true);
    }

    /**
     * The resolver twin (SRH-02, the legacy `QueryResolver`): the URL's
     * `?query=` is the screen's state — on arrival and on every
     * query-parameter change the query follows the URL, and the type
     * selection survives (SDX-06: the resolver set the store's query,
     * never its filters). The resolver ran on EVERY arrival, query-less
     * included (its `query = ''` default is what lists everything, DD-221);
     * a text the store has already run re-runs nothing — the hero's submit
     * ran it, and the same-URL navigation is a no-op.
     * @param query the URL's query, empty when the parameter is absent
     */
    applyUrl(query = ""): void {
        if (query === this.queryText() && this.searched) {
            return;
        }
        this.queryText.set(query);
        this.restart(true);
    }

    /**
     * A browse card's explore button (SRH-08): the empty query and the
     * card's type in the session selection — the legacy `directTo*` set
     * the in-memory filters and navigated, the URL carried nothing. The
     * selection list is the same field the sidebar ticks (DD-425's
     * consequence: one wire field, one signal).
     * @param typeName the Atlas type to explore (DV-84's base-model mapping)
     */
    explore(typeName: string): void {
        this.queryText.set("");
        this.typeSelection.set([typeName]);
        this.restart(true);
    }

    /**
     * A checkbox of the type facet (SDX-04, UIC-34): tick and the value
     * joins the selection, untick and it leaves; the search restarts at
     * page one (SRH-04's restart rule) and the narrowed counts keep every
     * seen value visible (SDX-07, DD-426).
     * @param value the facet value's wire name
     * @param checked the checkbox's new state
     */
    toggleType(value: string, checked: boolean): void {
        const selected = this.typeSelection();
        this.typeSelection.set(checked ? [...selected, value] : selected.filter((name) => name !== value));
        this.restart(false);
    }

    constructor() {
        // A mode chosen in the settings panel searches the shown query again
        // (SBX-02); the store ends with the search subtree, and so does this.
        this.searchMode.changed.pipe(takeUntilDestroyed()).subscribe((mode) => this.modeChanged(mode));
    }

    /**
     * A new mode from the settings (SBX-02, SBW-05): a search that has a
     * query restarts at its first page, the type selection kept; without a
     * query there is nothing to search differently.
     * @param mode the stored mode
     */
    private modeChanged(mode: SearchMode): void {
        if (mode === this.mode() && this.queryText().trim() !== "") {
            this.restart(true);
        }
    }

    /**
     * Ask for the next page (SRH-04): the container's sentinel or button,
     * guarded against a flight and against the end of the list.
     */
    nextPage(): void {
        if (this.loading() || this.allLoaded()) {
            return;
        }
        this.load();
    }

    /**
     * Restart at page one (SRH-04: a query change resets the accumulated
     * list, the legacy `shareReplay` on the query object). A query change
     * also resets the facet seen set (SDX-07); a facet toggle keeps it —
     * that is what its values were kept for (DD-426).
     * @param resetFacets whether the query changed (the seen set's reset rule)
     */
    private restart(resetFacets: boolean): void {
        this.entries.set([]);
        this.total.set(0);
        this.lastPageFull.set(true);
        this.offset = 0;
        if (resetFacets) {
            this.typeRows.set([]);
            this.otherFacets.set([]);
        }
        this.load();
    }

    /**
     * The door body of the current page (VSR-03): the query's words, the
     * mode that ranks them (Words asks `keyword`, ASV-01 — an empty query
     * asks it too, as the door refuses a meaning mode without words,
     * ASV-06), the sidebar's four facets, and the page. A selection filters
     * the selected types and every type under them (VSR-04, DD-600); with
     * no selection the body carries no filter, and the door answers every
     * entity (AVR-11).
     */
    private request(): ViewSearchRequest {
        const selection = [...this.typeSelection()];
        return {
            query: this.queryText(),
            mode: this.doorMode(),
            ...(selection.length > 0
                ? { filters: { any: [{ typeName: selection }, { superTypeNames: selection }] } }
                : {}),
            facets: { typeName: { size: TYPE_FACET_SIZE }, status: {}, owner: {}, serviceType: {} },
            limit: SearchState.PAGE_SIZE,
            offset: this.offset,
        };
    }

    /**
     * The door's ranking mode (VSR-03, ASV-01): the stored mode's door name,
     * Words being `keyword`. A meaning mode needs words to embed (ASV-06), so
     * an empty query asks `keyword` whatever the stored mode is (SBW-03's
     * rule, the same one the header's count follows).
     */
    private doorMode(): ViewSearchMode {
        if (!this.byMeaning()) {
            return "keyword";
        }
        return this.mode() === "hybrid" ? "hybrid" : "semantic";
    }

    /**
     * Run the current search's next page (SDX-01, VSR-03): one door, whatever
     * the mode — the body's `mode` key names it (ASV-01, DD-602).
     */
    private load(): void {
        if (this.loading()) {
            return;
        }
        this.searched = true;
        const byMeaning = this.byMeaning();
        this.loading.set(true);
        this.door.search(this.request()).subscribe({
            next: (answer) => {
                this.total.set(answer.total);
                this.entries.update((entries) => [...entries, ...answer.cards]);
                this.lastPageFull.set(answer.cards.length >= SearchState.PAGE_SIZE);
                this.offset += SearchState.PAGE_SIZE;
                this.applyFacets(answer.facets);
                this.loading.set(false);
            },
            error: (error: unknown) => {
                this.loading.set(false);
                if (byMeaning && isEmbeddingOff(error)) {
                    this.meaningUnavailable();
                    return;
                }
                this.alerts.add({
                    severity: "error",
                    // The legacy pipeline's quiet task line ("…loading a page
                    // of search results"), as the alert's message.
                    message: $localize`:@@search.services.appSearchResults.loading:Loading a page of search results`,
                    source: "search",
                });
            },
        });
    }

    /**
     * A server without search by meaning (SBW-06): say so and store Words,
     * whose change searches again by the query's words (SBX-02).
     */
    private meaningUnavailable(): void {
        this.alerts.add({
            severity: "warning",
            message: $localize`:@@search.mode.unavailable:Search by meaning is not available on this server`,
            source: "search",
        });
        // Stored as Words: the setting's change searches again (SBX-02).
        this.searchMode.set("words");
    }

    /**
     * Fold one answer's facets into the sidebar's state (SDX-02, SDX-07,
     * VSR-06): the type facet merges with the seen rows — the answer's values
     * and counts first, in answer order, then the values the narrowed answer
     * no longer carries with their last counts (DD-426) — and the rest is
     * replaced as answered, empty facets dropped (SDX-03, the legacy
     * `FilterService`'s rule).
     * @param facets the answer's facet counts, keyed by the door's names (AVR-08)
     */
    private applyFacets(facets: Record<string, FacetEntry[]>): void {
        const fresh = (facets[TYPE_FACET] ?? []).filter((entry) => typeof entry.value === "string");
        const freshValues = new Set(fresh.map((entry) => `${entry.value}`));
        const kept = this.typeRows().filter((row) => !freshValues.has(row.value));
        this.typeRows.set([...fresh.map((entry) => ({ value: `${entry.value}`, count: entry.count })), ...kept]);
        this.otherFacets.set(
            Object.entries(facets)
                .filter(([key, entries]) => key !== TYPE_FACET && entries.length > 0)
                .map(([key, entries]) => ({ key, entries })),
        );
    }
}

/**
 * Whether a failed request is the door's answer that the server has no search
 * by meaning (SBM-06, ASV-09, VSR-08): a 404 carrying `AURELIUS-404-00-001`.
 * @param error what the request failed with
 */
function isEmbeddingOff(error: unknown): boolean {
    return (
        error instanceof HttpErrorResponse &&
        error.status === 404 &&
        (error.error as { errorCode?: string } | null)?.errorCode === EMBEDDING_OFF
    );
}
