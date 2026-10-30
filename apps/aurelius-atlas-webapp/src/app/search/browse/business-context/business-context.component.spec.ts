import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import { vi } from "vitest";

import { SearchState } from "../../search-state";
import { BusinessContext } from "./business-context.component";

/**
 * Collapse the whitespace of rendered template text — the template wraps its
 * lines, so the compiler-consumed i18n nodes carry layout newlines.
 */
function normalize(text: string | undefined | null): string {
    return text?.replace(/\s+/g, " ").trim() ?? "";
}

/** The card with its search-slice collaborators: the store, the router, HTTP. */
function setup() {
    const navigate = vi.fn().mockResolvedValue(true);
    TestBed.configureTestingModule({
        imports: [BusinessContext],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            SearchState,
            { provide: Router, useValue: { navigate } },
        ],
    });
    return { navigate, httpMock: TestBed.inject(HttpTestingController) };
}

/**
 * Consume the basic-search request the store fired, asserting its body, and
 * answer it empty.
 */
function expectSearch(httpMock: HttpTestingController, body: Record<string, unknown>) {
    const request = httpMock.expectOne((req) => req.url === "/api/atlas/v2/search/basic" && req.method === "POST");
    expect(request.request.body).toMatchObject(body);
    request.flush({ entities: [], approximateCount: 0 });
}

describe("BusinessContext", () => {
    it("renders the keyed card strings (BRW-02)", () => {
        setup();
        const fixture = TestBed.createComponent(BusinessContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        expect(normalize(compiled.querySelector(".card .title.is-4")?.textContent)).toBe("Business context");
        expect(normalize(compiled.querySelector("article.media:nth-of-type(1) .title.is-6")?.textContent)).toBe(
            "I'm searching for the meaning of data within a specific business context",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(1) p")?.textContent)).toBe(
            "Search for keywords related to the data domain or data entity that you are looking for.",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(2) .title.is-6")?.textContent)).toBe(
            "I'm exploring the meaning of data in a business context",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(2) p")?.textContent)).toBe(
            "Click the button below to see a list of all data domains.",
        );
    });

    it("opens the info modal from the info icon (BRW-03)", () => {
        setup();
        const fixture = TestBed.createComponent(BusinessContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        // The modal's host element always renders; its content is conditional
        // on `active`, so the Bulma modal is the closed-state witness.
        expect(compiled.querySelector(".modal")).toBeFalsy();

        const infoButton = compiled.querySelector<HTMLButtonElement>("button.icon")!;
        expect(infoButton.getAttribute("aria-label")).toBe("Business context");
        infoButton.click();
        fixture.detectChanges();

        expect(fixture.componentInstance.infoModalActive()).toBe(true);
        expect(compiled.querySelector("aurelius-atlas-ui-modal .modal-card-title")?.textContent?.trim()).toBe(
            "Business context",
        );
    });

    it("the modal's close path clears the card's open state (BRW-03, BRW-05)", () => {
        setup();
        const fixture = TestBed.createComponent(BusinessContext);
        fixture.componentInstance.infoModalActive.set(true);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        (compiled.querySelector("aurelius-atlas-ui-modal button.delete") as HTMLButtonElement).click();
        fixture.detectChanges();

        expect(fixture.componentInstance.infoModalActive()).toBe(false);
    });

    it("carries the card's search field and explore button (SRH-08)", () => {
        setup();
        const fixture = TestBed.createComponent(BusinessContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        // DD-143 supersedes the BRW-06 ban for these controls: the affordances
        // are the search slice's, delivered here.
        const field = compiled.querySelector("aurelius-atlas-ui-search-field input");
        expect(field).toBeTruthy();
        expect(field?.getAttribute("placeholder")).toBe("Search for keywords");

        const explore = [...compiled.querySelectorAll("button.button.is-success")].find((button) =>
            button.textContent?.includes("Start browsing data domains"),
        );
        expect(explore).toBeTruthy();
    });

    it("the field's submit runs the query and navigates with it (SRH-08)", () => {
        const { navigate, httpMock } = setup();
        const fixture = TestBed.createComponent(BusinessContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        const input = compiled.querySelector<HTMLInputElement>("input[type='search']")!;
        input.value = "domain";
        input.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.button.is-success[aria-label='Search']")!.click();
        fixture.detectChanges();

        expectSearch(httpMock, { query: "domain", limit: 10, offset: 0, excludeDeletedEntities: true });
        expect(navigate).toHaveBeenCalledWith(["/search/results"], { queryParams: { query: "domain" } });
    });

    it("the explore button searches the AtlasGlossary type, no URL query (SRH-08, DV-84)", () => {
        const { navigate, httpMock } = setup();
        const fixture = TestBed.createComponent(BusinessContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        const explore = [...compiled.querySelectorAll<HTMLButtonElement>("button.button.is-success")].find((button) =>
            button.textContent?.includes("Start browsing data domains"),
        )!;
        explore.click();
        fixture.detectChanges();

        // The legacy directToConceptual's filter read as Atlas's model
        // (DV-84): the empty query and typeName=AtlasGlossary ride the
        // session store, the URL carries nothing (DD-219).
        expectSearch(httpMock, { query: "", typeName: "AtlasGlossary", limit: 10, offset: 0 });
        expect(navigate).toHaveBeenCalledWith(["/search/results"]);
    });
});
