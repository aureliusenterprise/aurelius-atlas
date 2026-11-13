import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { NavigationEnd, Router, RouterOutlet } from "@angular/router";
import { filter, map, startWith } from "rxjs";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { Hero, SearchField } from "aurelius-atlas-ui";

import { canWriteEntities } from "./editor/can-write-entities";
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
    imports: [FontAwesomeModule, Hero, RouterOutlet, SearchField],
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

    /** Whether the hero's `+` shows (EDT-09, DD-324): the atlas-write grant —
     * the legacy DATA_STEWARD editor `+` (7.7's affordance, this gate). */
    protected readonly canWrite = canWriteEntities();

    /** The `+` icon. */
    protected readonly faPlus = faPlus;

    /** The `+`'s accessible name — the catalogue's create label (EDT-11). */
    protected readonly createLabel = $localize`:@@search.createEntity.newEntity:Create new entity`;

    /** The route's URL, current after every navigation (the signals below read it). */
    private readonly url = toSignal(
        this.router.events.pipe(
            filter((event): event is NavigationEnd => event instanceof NavigationEnd),
            map(() => this.router.url),
            startWith(this.router.url),
        ),
        { initialValue: this.router.url },
    );

    /**
     * The hero title's heading level (HEADING-001): the details screen
     * renders the entity name as the page's h1, so the chrome band steps
     * down to an h2 there and the page keeps one h1.
     */
    protected readonly heroTitleLevel = computed(() => (this.url().includes("/details/") ? 2 : 1));

    /**
     * The search status announced to screen readers (LR-001, WCAG 4.1.3):
     * the persistent status region in the template reads this — loading,
     * the settled count, or the no-results line. Only text changes are
     * announced, so the browse landing and detail visits stay quiet.
     */
    protected readonly searchStatus = computed(() => {
        if (this.search.loading()) {
            return $localize`:@@search.layout.status.searching:Searching`;
        }
        if (this.search.noResults()) {
            return $localize`:@@search.layout.status.noResults:No results found`;
        }
        const count = this.search.shownCount();
        if (count > 0 && this.search.entries().length > 0) {
            return $localize`:@@search.layout.status.count:${count}:count: results`;
        }
        return "";
    });

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

    /**
     * The hero's `+` was clicked (EDT-01, DD-322): open the create-mode
     * editor drawer — the `drawer` aux outlet carries `create`.
     */
    protected openCreate(): void {
        void this.router.navigate([{ outlets: { drawer: ["create"] } }]);
    }
}
