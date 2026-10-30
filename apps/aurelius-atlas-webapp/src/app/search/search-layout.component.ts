import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { Router, RouterOutlet } from "@angular/router";
import { Hero, SearchField } from "aurelius-atlas-ui";

import { APP_CONFIG } from "../tokens";
import { SearchState } from "./search-state";

/**
 * The search subtree's chrome (SRH-01, DD-218): the legacy
 * `SearchComponent` — the hero band the routed screens sit under, its title
 * row carrying the global search field (the legacy `simple-search-input`
 * lived here, in the hero, never in the navbar — DD-145's wording, superseded).
 *
 * Submitting runs the search and navigates `search/results?query=` (the
 * legacy `onQuerySubmitted`; a cleared field submits `null`, the empty
 * query). The field reads the store's query, so a back-navigation into the
 * subtree shows the query the URL carries (the results screen keeps store
 * and URL in step, SRH-02).
 *
 * The store is provided HERE, not at the root (SRH-02, DD-219): leaving the
 * subtree destroys it, and a fresh visit to browse starts from an empty
 * search — the legacy `NavigationEnd` store reset, by construction.
 */
@Component({
    imports: [Hero, RouterOutlet, SearchField],
    selector: "aurelius-atlas-webapp-search",
    templateUrl: "./search-layout.component.html",
    styleUrl: "./search-layout.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
    providers: [SearchState],
})
export class SearchLayout {
    protected readonly search = inject(SearchState);

    private readonly router = inject(Router);

    /** The hero's title: the legacy `search.component.html` carries the
     * literal `title="Atlas"`, not the app name (the demo shows it). */
    protected readonly heroTitle = "Atlas";

    /** The field's placeholder (SRH-01, the legacy `search.browse.searchPlaceholder`). */
    protected readonly searchPlaceholder = $localize`:@@search.browse.searchPlaceholder:Type your search`;

    /**
     * The hero field's submit (SRH-01, SRH-08): run the search, carry the
     * text in the URL (DD-219). The results screen's URL effect sees the
     * same text and re-runs nothing (SRH-02's guard).
     * @param query the submitted query, `null` for a cleared field
     */
    protected onQuerySubmitted(query: string | null): void {
        this.search.run(query);
        void this.router.navigate(["/search/results"], {
            queryParams: { query: query || null },
        });
    }
}
