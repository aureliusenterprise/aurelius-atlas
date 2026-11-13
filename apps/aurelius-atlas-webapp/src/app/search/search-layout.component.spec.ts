import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { NavigationEnd, Router, provideRouter } from "@angular/router";
import Keycloak from "keycloak-js";
import { Subject } from "rxjs";
import { vi } from "vitest";

import { AppConfig } from "../config";
import { APP_CONFIG } from "../tokens";
import { SearchState } from "./search-state";
import { SearchLayout } from "./search-layout.component";

const config: AppConfig = {
    keycloak: { clientId: "aurelius", realm: "atlas", url: "https://keycloak.example/" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
    appCopyright: 2022,
    appVersion: "7.11.0#abc1234",
    atlasClientId: "aurelius-atlas-server",
};

/**
 * Bring the layout up with a token (EDT-09): the fake Keycloak's
 * `hasResourceRole` answers `canWrite` for the hero's `+` — granted unless
 * a test passes `atlasWrite: false`.
 */
function setup({ atlasWrite = true, url = "/search/browse" }: { atlasWrite?: boolean; url?: string } = {}) {
    const navigate = vi.fn().mockResolvedValue(true);
    // The fake router's event stream stays open: the layout watches
    // NavigationEnd for the hero's heading level (HEADING-001), so a test
    // can push one (the real router emits it on every navigation).
    const events = new Subject<unknown>();
    const fake = { navigate, events, url };
    TestBed.configureTestingModule({
        imports: [SearchLayout],
        providers: [
            provideRouter([]),
            provideHttpClient(),
            provideHttpClientTesting(),
            { provide: APP_CONFIG, useValue: config },
            SearchState,
            { provide: Router, useValue: fake },
            {
                provide: Keycloak,
                useValue: {
                    hasResourceRole: (role: string, resource?: string) =>
                        atlasWrite && role === "atlas-write" && resource === config.atlasClientId,
                },
            },
        ],
    });
    return {
        navigate,
        httpMock: TestBed.inject(HttpTestingController),
        events,
        // The mutable handle on the fake: `Router.url` is read-only in the
        // type, but the fake is a plain object and the layout reads it.
        router: fake as { url: string },
    };
}

const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

describe("SearchLayout (SRH-01, SRH-11)", () => {
    it("renders the hero with the legacy title and the search field (SRH-01)", () => {
        setup();
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        // The design's search bar is the hero's (DD-218, superseding the
        // navbar bar DD-145 deferred): title + field, above the outlet.
        const hero = compiled.querySelector("aurelius-atlas-ui-hero");
        expect(hero).toBeTruthy();
        expect(normalize(hero?.querySelector(".title")?.textContent)).toBe("Atlas");

        const field = compiled.querySelector("aurelius-atlas-ui-search-field input");
        expect(field).toBeTruthy();
        expect(field?.getAttribute("placeholder")).toBe("Type your search");

        expect(compiled.querySelector("div.container router-outlet")).toBeTruthy();
    });

    it("the field's submit runs the search and navigates with the query (SRH-01, SRH-08)", () => {
        const { navigate, httpMock } = setup();
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        const input = compiled.querySelector<HTMLInputElement>("input[type='search']")!;
        input.value = "genomic";
        input.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.button.is-success[aria-label='Search']")!.click();
        fixture.detectChanges();

        const request = httpMock.expectOne("/api/atlas/v2/search/quick");
        expect(request.request.body).toMatchObject({ query: "genomic", limit: 10, offset: 0 });
        request.flush({ searchResults: { entities: [], approximateCount: 0 }, aggregationMetrics: {} });

        expect(navigate).toHaveBeenCalledWith(["/search/results"], { queryParams: { query: "genomic" } });
        // The store is the layout's component provider (SRH-02) — the element
        // injector sees it, the public instance does not expose it.
        expect(fixture.debugElement.injector.get(SearchState).queryText()).toBe("genomic");
    });

    it("clearing the field submits the empty query (SRH-01)", () => {
        const { navigate, httpMock } = setup();
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.debugElement.injector.get(SearchState).queryText.set("gene");
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        // The cleared field re-submits (the Aurelius clear path): the store
        // reads "", the URL drops the parameter (DD-219). The empty query
        // searches every entity (DD-221), so the request fires.
        compiled.querySelector<HTMLButtonElement>("button.delete")!.click();
        fixture.detectChanges();

        const request = httpMock.expectOne("/api/atlas/v2/search/quick");
        expect(request.request.body).toMatchObject({ typeName: "_ALL_ENTITY_TYPES", query: "" });
        request.flush({ searchResults: { entities: [], approximateCount: 0 }, aggregationMetrics: {} });
        expect(navigate).toHaveBeenCalledWith(["/search/results"], { queryParams: { query: null } });
        expect(fixture.debugElement.injector.get(SearchState).queryText()).toBe("");
    });

    it("the hero shows the create `+` with the atlas-write grant (EDT-09, DD-324)", () => {
        setup();
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        const plus = compiled.querySelector<HTMLButtonElement>("button.aurelius-create-entity");
        expect(plus).toBeTruthy();
        expect(plus?.getAttribute("aria-label")).toBe("Create new entity");
        expect(plus?.querySelector("fa-icon")).toBeTruthy();
    });

    it("the hero hides the create `+` without the grant (EDT-09)", () => {
        setup({ atlasWrite: false });
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();

        expect((fixture.nativeElement as HTMLElement).querySelector("button.aurelius-create-entity")).toBeNull();
    });

    it("the hero controls row carries the class that shrinks it (DD-550)", () => {
        setup();
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        // The scss rule that hooks on this class is what keeps the field and
        // the `+` inside the hero between 769px and ~830px (DD-550). Pin the
        // hook itself, not the pixels (repo rule: layout ships as structure).
        const level = compiled.querySelector("div.level.hero-controls");
        expect(level).toBeTruthy();
        expect(level?.querySelector(".level-item .input-bar")).toBeTruthy();
        expect(level?.querySelector(".level-right .aurelius-create-entity")).toBeTruthy();
    });

    it("the `+` opens the create-mode editor drawer (EDT-01, DD-322)", () => {
        const { navigate } = setup();
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        compiled.querySelector<HTMLButtonElement>("button.aurelius-create-entity")!.click();

        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: ["create"] } }]);
    });

    it("LR-001: the persistent status states searching, the settled count, or no results", () => {
        setup();
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        const region: HTMLElement = compiled.querySelector("output")!;
        const store = fixture.debugElement.injector.get(SearchState);
        const text = () => region.textContent?.trim();

        // Nothing has run (words mode, empty query): the store reads as an
        // empty search and the region says so; a live region only speaks on
        // CHANGE, so the resting text is never announced.
        expect(text()).toBe("No results found");

        // An in-flight search (the count line steps aside for it).
        store.loading.set(true);
        fixture.detectChanges();
        expect(text()).toBe("Searching");

        // Settled with results (words mode counts what the server said,
        // SRH-04): the count branch.
        store.loading.set(false);
        store.approximateCount.set(12);
        store.entries.set([{ guid: "g1" } as never, { guid: "g2" } as never]);
        fixture.detectChanges();
        expect(text()).toBe("12 results");

        // The server counted rows the page has not listed yet: neither
        // quiet line fits and the region stays silent (the count names
        // only what is on screen).
        store.approximateCount.set(5);
        store.entries.set([]);
        fixture.detectChanges();
        expect(text()).toBe("");

        // A settled search that lists rows the server did not count: the
        // count line needs listed rows, so it stays quiet here too.
        store.approximateCount.set(0);
        store.entries.set([{ guid: "g1" } as never]);
        fixture.detectChanges();
        expect(text()).toBe("");
    });

    it("HEADING-001: the hero steps down to an h2 on the details screen", () => {
        // The details route renders the entity name as the page's h1, so
        // the chrome band yields the h1 spot (the browse landing keeps it).
        setup({ url: "/search/details/00000000-0000-4000-8000-000000000001" });
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        expect(compiled.querySelector("aurelius-atlas-ui-hero h1")).toBeNull();
        expect(compiled.querySelector("aurelius-atlas-ui-hero h2.title")?.textContent?.trim()).toBe("Atlas");
    });

    it("HEADING-001: the hero follows the URL on navigation, in both directions", () => {
        // The heading level reads the router's events, not the URL it came
        // up with: browse -> details steps down, details -> browse steps
        // back up (the chrome band keeps the page's single h1).
        const { events, router } = setup();
        const fixture = TestBed.createComponent(SearchLayout);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        const heroTitleTag = () => compiled.querySelector("aurelius-atlas-ui-hero .title")?.tagName;
        expect(heroTitleTag()).toBe("H1");

        router.url = "/search/details/00000000-0000-4000-8000-000000000001";
        events.next(new NavigationEnd(1, "/search/browse", router.url));
        fixture.detectChanges();
        expect(heroTitleTag()).toBe("H2");

        router.url = "/search/results";
        events.next(new NavigationEnd(2, router.url, "/search/results"));
        fixture.detectChanges();
        expect(heroTitleTag()).toBe("H1");
    });
});
