import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting, HttpTestingController } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import Keycloak from "keycloak-js";

import { SearchState } from "../search-state";
import { Browse } from "./browse.component";

describe("Browse", () => {
    let httpMock: HttpTestingController;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Browse],
            providers: [
                provideRouter([]),
                provideHttpClient(),
                provideHttpClientTesting(),
                SearchState,
                // The governance card's explore reads the session e-mail; the
                // landing spec keeps the Keycloak plumbing out of scope.
                { provide: Keycloak, useValue: { tokenParsed: {} } },
            ],
        }).compileComponents();

        httpMock = TestBed.inject(HttpTestingController);
    });

    it("creates", () => {
        expect(TestBed.createComponent(Browse).componentInstance).toBeTruthy();
    });

    it("renders the hero: title and the keyed description, keeping #browse-placeholder (BRW-01, SHL-04, DD-128)", () => {
        const fixture = TestBed.createComponent(Browse);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;

        // The i18n marker attribute is consumed by the compiler, so the rendered
        // English text is the observable proof of the @@search.browse.* keys.
        // Whitespace is collapsed: the template wraps its lines.
        const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

        expect(normalize(compiled.querySelector(".box h2.title.is-2")?.textContent)).toBe("Getting started");

        const placeholder = compiled.querySelector("#browse-placeholder");
        expect(placeholder).toBeTruthy();
        expect(normalize(placeholder?.textContent)).toBe(
            "Welcome to Aurelius Atlas! We would like to help you get started. Please pick your topic of interest below.",
        );
    });

    it("renders the three context cards in the Aurelius order (BRW-01)", () => {
        const fixture = TestBed.createComponent(Browse);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;
        const cardTitles = [...compiled.querySelectorAll(".column .card .media-content .title.is-4")].map((title) =>
            title.textContent?.replace(/\s+/g, " ").trim(),
        );

        expect(cardTitles).toEqual(["Business context", "Technical context", "Data governance organization"]);
    });

    it("renders the box and three cards top-level; the layout owns the inset (SHM-07, DD-150, DD-218)", () => {
        const fixture = TestBed.createComponent(Browse);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;

        // The legacy browse template sits top-level; the search hero insets it
        // (section.section > div.container around the outlet — the legacy
        // hero.component.html). The page does not double the wrapper (DD-218).
        expect(compiled.querySelector("section")).toBeNull();
        expect(compiled.querySelector(":scope > .box #browse-placeholder")).toBeTruthy();
        expect(compiled.querySelectorAll(":scope > .columns > .column")).toHaveLength(3);
    });

    it("issues no HTTP requests: the landing exists before its API (BRW-04)", () => {
        const fixture = TestBed.createComponent(Browse);
        fixture.detectChanges();

        // Consumes every request the component issued — the landing exists
        // before its API, so the set must be empty (asserted, not just verified).
        expect(httpMock.match(() => true)).toHaveLength(0);
    });
});
