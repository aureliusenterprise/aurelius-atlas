import { Injectable, computed, inject, signal } from "@angular/core";
import { AtlasEntityHeader, SearchParameters, SearchService } from "aurelius-atlas-data-access";

import { AlertsService } from "../alerts/alerts.service";

/**
 * The search slice's session store (SRH-02, DD-219): the query arrives from
 * the URL, pages accumulate here, and nothing in the URL grows past
 * `?query=`. Provided by the layout component — leaving the `/search`
 * subtree destroys the store, so a fresh visit to browse resets the search
 * (the legacy `NavigationEnd` reset, by construction).
 *
 * The query runs as a basic search (SRH-03, POST `/v2/search/basic`) with
 * pages of ten (the legacy page size, SRH-04): `run` is the hero's submit,
 * `explore` the browse cards' buttons, `nextPage` the infinite-scroll
 * container's. A search the server cannot answer (an empty query with no
 * filter is ATLAS-400-00-047, SRC-02) is never fired; a search the server
 * answers with an error lands in the alerts drawer (the DD-214 failure
 * path, the legacy pipeline strip's successor).
 */
@Injectable()
export class SearchState {
    private readonly search = inject(SearchService);

    private readonly alerts = inject(AlertsService);

    /** The legacy `pageSize` (the results store's 10). */
    static readonly PAGE_SIZE = 10;

    /** The entities accumulated across pages, in answer order (SRH-04). */
    readonly entries = signal<AtlasEntityHeader[]>([]);

    /** The server's count of the current search (`approximateCount`, SRC-09). */
    readonly approximateCount = signal(0);

    /** A page is in flight — the container's spinner (SRH-04). */
    readonly loading = signal(false);

    /** The session type filter (the explore buttons, SRH-08) — never in the URL. */
    readonly typeFilter = signal<string | null>(null);

    /** Every entity of the search is listed (the legacy equality, SRH-04). */
    readonly allLoaded = computed(() => !this.loading() && this.entries().length >= this.approximateCount());

    /** Cards render (SRH-05). */
    readonly hasResults = computed(() => this.entries().length > 0);

    /** The no-results pair renders (SRH-06): answered zero, or nothing to ask. */
    readonly noResults = computed(
        () => !this.loading() && this.entries().length === 0 && this.approximateCount() === 0,
    );

    /** The search's text, `""` for the explore landings (the hero's field reads it). */
    readonly queryText = signal("");

    /** The next page's offset. */
    private offset = 0;

    /**
     * The hero's submit (SRH-01, SRH-02): the query is the search, and the
     * explore buttons' filter clears — the legacy `onQuerySubmitted` cleared
     * `filters` before navigating. The layout navigates to the results route
     * alongside; the URL carries the text (SRH-02, DD-219).
     * @param query the submitted query, `null` for a cleared field
     */
    run(query: string | null): void {
        this.queryText.set(query ?? "");
        this.typeFilter.set(null);
        this.restart();
    }

    /**
     * The resolver twin (SRH-02, the legacy `QueryResolver`): the URL's
     * `?query=` is the screen's state — on arrival and on every
     * query-parameter change the query follows the URL, and the explore
     * buttons' session filter survives (the resolver set the store's query,
     * never its filters). A parameter already in the store re-runs nothing:
     * the hero's submit ran it, and the same-URL navigation is a no-op.
     * @param query the URL's query, `null` when the parameter is absent
     */
    applyUrl(query: string | null): void {
        if ((query ?? "") === this.queryText()) {
            return;
        }
        this.queryText.set(query ?? "");
        this.restart();
    }

    /**
     * A browse card's explore button (SRH-08): the empty query and the
     * card's session type filter — the legacy `directTo*` set the in-memory
     * filters and navigated, the URL carried nothing.
     * @param typeName the Atlas type to explore (DV-84's base-model mapping)
     */
    explore(typeName: string): void {
        this.queryText.set("");
        this.typeFilter.set(typeName);
        this.restart();
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
     * list, the legacy `shareReplay` on the query object).
     */
    private restart(): void {
        this.entries.set([]);
        this.approximateCount.set(0);
        this.offset = 0;
        this.load();
    }

    /**
     * Run the current search's next page (SRH-03). The empty query with no
     * type filter asks the server nothing — its basic search requires a
     * term or a filter (SRC-02, ATLAS-400-00-047) — and the no-results pair
     * (SRH-06) is the honest rendering of "nothing to ask".
     */
    private load(): void {
        const typeName = this.typeFilter();
        const query = this.queryText();
        if (this.loading() || (!query && !typeName)) {
            if (!this.loading()) {
                this.entries.set([]);
                this.approximateCount.set(0);
            }
            return;
        }
        this.loading.set(true);
        const parameters: SearchParameters = {
            query: query ?? "",
            ...(typeName ? { typeName } : {}),
            limit: SearchState.PAGE_SIZE,
            offset: this.offset,
            excludeDeletedEntities: true,
        };
        this.search.searchWithParameters(parameters).subscribe({
            next: (result) => {
                this.approximateCount.set(result.approximateCount ?? 0);
                const entities = result.entities ?? [];
                this.entries.update((entries) => [...entries, ...entities]);
                this.offset += SearchState.PAGE_SIZE;
                this.loading.set(false);
            },
            error: () => {
                this.loading.set(false);
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
}
