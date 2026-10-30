import { ChangeDetectionStrategy, Component, effect, inject } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router } from "@angular/router";
import { AtlasEntityHeader } from "aurelius-atlas-data-access";
import { EntityCard, InfiniteScrollContainer } from "aurelius-atlas-ui";
import { map } from "rxjs";

import { SearchState } from "../search-state";

/**
 * The results screen (SRH-02..07): the legacy `results.component` as the
 * Aurelius shape — a one-third filter column (the shell, SRH-07: the legacy
 * empty state; facets are 7.4b) and a results box with the count, the
 * infinite-scroll card list, and the no-results card.
 *
 * The URL's `?query=` is the screen's whole address (SRH-02, DD-219): on
 * arrival and on every query-parameter change the store's search follows
 * the URL (the legacy `QueryResolver` with `paramsOrQueryParamsChange`,
 * read as a signal effect). Pages accumulate in the layout-scoped store
 * (SRH-04), never in the URL.
 *
 * A card click opens the entity's details — the entry into the 7.6 skeleton
 * its deferral table assigns here (SRH-05); the card's `entityClicked` is
 * the guid, routing is the app's (DD-154).
 */
@Component({
    imports: [EntityCard, InfiniteScrollContainer],
    selector: "aurelius-atlas-webapp-search-results",
    templateUrl: "./results.component.html",
    styleUrl: "./results.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Results {
    protected readonly search = inject(SearchState);

    private readonly router = inject(Router);

    /** The count header's word ("results" / "resultaten", SRH-05). */
    protected readonly resultsWord = $localize`:@@search.results.results:results`;

    /** The "Load next page..." label (SRH-04, UIC-21's caller-supplied string). */
    protected readonly loadLabel = $localize`:@@search.components.infiniteScrollContainer.loadNextPage:Load next page...`;

    /** The filter shell's line (SRH-07, the legacy `#noFilters` twin). */
    protected readonly noFilters = $localize`:@@search.components.filter.notAvailable:No filters available.`;

    /** The no-results heading (SRH-06, the legacy `search.results.noResults`). */
    protected readonly noResultsMessage = $localize`:@@search.results.noResults:No results found`;

    /** The invitation below it (SRH-06, the legacy `search.results.anotherQuery`). */
    protected readonly anotherQueryMessage = $localize`:@@search.results.anotherQuery:Please, try to make another query.`;

    constructor() {
        // The resolver twin (SRH-02): the URL leads, the store follows —
        // on arrival and on every query-parameter change.
        const urlQuery = toSignal(inject(ActivatedRoute).queryParamMap.pipe(map((params) => params.get("query"))));
        effect(() => this.search.applyUrl(urlQuery() ?? null));
    }

    /**
     * A card's title click routes to the entity's details (SRH-05).
     * @param guid the clicked card's entity
     */
    protected openDetails(guid: string): void {
        void this.router.navigate(["/search/details", guid]);
    }

    /**
     * The card's title (SRH-05, DV-83): the header's display text, the
     * `name` attribute as its fallback — rendered straight from the hit,
     * no per-card fetch.
     * @param entity the search hit
     * @returns the name to show
     */
    protected displayName(entity: AtlasEntityHeader): string {
        const attribute = entity.attributes?.["name"];
        return entity.displayText ?? (typeof attribute === "string" ? attribute : "") ?? "";
    }

    /**
     * The `trackBy` of the card list (the legacy `trackByGuid`).
     * @param _index the row position (unused)
     * @param entity the search hit
     * @returns the entity's guid
     */
    protected trackByGuid(_index: number, entity: AtlasEntityHeader): string {
        return entity.guid ?? "";
    }
}
