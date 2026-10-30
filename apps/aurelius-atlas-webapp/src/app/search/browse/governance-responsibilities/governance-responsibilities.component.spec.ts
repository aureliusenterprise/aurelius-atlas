import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import Keycloak from "keycloak-js";
import { vi } from "vitest";

import { SearchState } from "../../search-state";
import { GovernanceResponsibilities } from "./governance-responsibilities.component";

/**
 * Collapse the whitespace of rendered template text — the template wraps its
 * lines, so the compiler-consumed i18n nodes carry layout newlines.
 */
function normalize(text: string | undefined | null): string {
    return text?.replace(/\s+/g, " ").trim() ?? "";
}

/**
 * The card with its search-slice collaborators. The Keycloak token carries
 * the e-mail the explore button searches (the legacy `credentials.email`,
 * DV-84).
 */
function setup(email = "ada@example.org") {
    const navigate = vi.fn().mockResolvedValue(true);
    TestBed.configureTestingModule({
        imports: [GovernanceResponsibilities],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            SearchState,
            { provide: Router, useValue: { navigate } },
            { provide: Keycloak, useValue: { tokenParsed: { email } } },
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

/** The card's explore button, found by its label (the field's submit shares the class). */
function exploreButton(compiled: HTMLElement): HTMLButtonElement {
    return [...compiled.querySelectorAll<HTMLButtonElement>("button.button.is-success")].find((button) =>
        button.textContent?.includes("Start browsing people"),
    )!;
}

describe("GovernanceResponsibilities", () => {
    it("renders the keyed card strings (BRW-02)", () => {
        setup();
        const fixture = TestBed.createComponent(GovernanceResponsibilities);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        expect(normalize(compiled.querySelector(".card .title.is-4")?.textContent)).toBe(
            "Data governance organization",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(1) .title.is-6")?.textContent)).toBe(
            "I'm searching for the data governance responsibilities of a specific person",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(1) p")?.textContent)).toBe(
            "Search for the name or email address of the person you are looking for.",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(2) .title.is-6")?.textContent)).toBe(
            "I'm exploring who has data governance responsibilities within my organization",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(2) p")?.textContent)).toBe(
            "Click the button below to see a list of all people with data governance responsibilities.",
        );
    });

    it("opens the info modal from the info icon (BRW-03)", () => {
        setup();
        const fixture = TestBed.createComponent(GovernanceResponsibilities);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        const infoButton = compiled.querySelector<HTMLButtonElement>("button.icon")!;
        expect(infoButton.getAttribute("aria-label")).toBe("Data governance organization");
        infoButton.click();
        fixture.detectChanges();

        expect(fixture.componentInstance.infoModalActive()).toBe(true);
        expect(compiled.querySelector("aurelius-atlas-ui-modal .modal-card-title")?.textContent?.trim()).toBe(
            "Data governance organization",
        );
    });

    it("the modal's close path clears the card's open state (BRW-03, BRW-05)", () => {
        setup();
        const fixture = TestBed.createComponent(GovernanceResponsibilities);
        fixture.componentInstance.infoModalActive.set(true);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        (compiled.querySelector("aurelius-atlas-ui-modal button.delete") as HTMLButtonElement).click();
        fixture.detectChanges();

        expect(fixture.componentInstance.infoModalActive()).toBe(false);
    });

    it("carries the card's search field and explore button (SRH-08)", () => {
        setup();
        const fixture = TestBed.createComponent(GovernanceResponsibilities);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        // DD-143 supersedes the BRW-06 ban for these controls: the affordances
        // are the search slice's, delivered here.
        const field = compiled.querySelector("aurelius-atlas-ui-search-field input");
        expect(field).toBeTruthy();
        expect(field?.getAttribute("placeholder")).toBe("Search for keywords");
        expect(exploreButton(compiled)).toBeTruthy();
    });

    it("the field's submit runs the query and navigates with it (SRH-08)", () => {
        const { navigate, httpMock } = setup();
        const fixture = TestBed.createComponent(GovernanceResponsibilities);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        const input = compiled.querySelector<HTMLInputElement>("input[type='search']")!;
        input.value = "ada";
        input.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.button.is-success[aria-label='Search']")!.click();
        fixture.detectChanges();

        // DV-84: a plain query, no Person-type filter — Atlas has none.
        expectSearch(httpMock, { query: "ada", limit: 10, offset: 0, excludeDeletedEntities: true });
        expect(navigate).toHaveBeenCalledWith(["/search/results"], { queryParams: { query: "ada" } });
    });

    it("the explore button searches the signed-in e-mail (SRH-08, DV-84)", () => {
        const { navigate, httpMock } = setup("ada@example.org");
        const fixture = TestBed.createComponent(GovernanceResponsibilities);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        exploreButton(compiled).click();
        fixture.detectChanges();

        // The legacy directToUser: the token's e-mail as the query term,
        // carried in the URL the way the legacy navigated it.
        expectSearch(httpMock, { query: "ada@example.org", limit: 10, offset: 0 });
        expect(navigate).toHaveBeenCalledWith(["/search/results"], {
            queryParams: { query: "ada@example.org" },
        });
    });
});
