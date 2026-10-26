import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { Router, provideRouter } from "@angular/router";
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
};

function setup() {
    const navigate = vi.fn().mockResolvedValue(true);
    TestBed.configureTestingModule({
        imports: [SearchLayout],
        providers: [
            provideRouter([]),
            provideHttpClient(),
            provideHttpClientTesting(),
            { provide: APP_CONFIG, useValue: config },
            SearchState,
            { provide: Router, useValue: { navigate } },
        ],
    });
    return { navigate, httpMock: TestBed.inject(HttpTestingController) };
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

        const request = httpMock.expectOne("/api/atlas/v2/search/basic");
        expect(request.request.body).toMatchObject({ query: "genomic", limit: 10, offset: 0 });
        request.flush({ entities: [], approximateCount: 0 });

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

        const request = httpMock.expectOne("/api/atlas/v2/search/basic");
        expect(request.request.body).toMatchObject({ typeName: "_ALL_ENTITY_TYPES", query: "" });
        request.flush({ entities: [], approximateCount: 0 });
        expect(navigate).toHaveBeenCalledWith(["/search/results"], { queryParams: { query: null } });
        expect(fixture.debugElement.injector.get(SearchState).queryText()).toBe("");
    });
});
