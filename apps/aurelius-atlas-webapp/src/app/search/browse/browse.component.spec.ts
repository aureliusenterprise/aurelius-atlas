import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting, HttpTestingController } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";

import { Browse } from "./browse.component";

describe("Browse", () => {
    let httpMock: HttpTestingController;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Browse],
            providers: [provideHttpClient(), provideHttpClientTesting()],
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

    it("insets the page content in the legacy section > container grid (SHM-07, DD-150)", () => {
        const fixture = TestBed.createComponent(Browse);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;

        // The legacy pages wrap their root in `section.section > div.container`
        // (the demo's insets come from exactly this, not hand-rolled margins).
        const section = compiled.querySelector("section.section > .container");

        expect(section).toBeTruthy();
        expect(section?.querySelector(".box #browse-placeholder")).toBeTruthy();
        expect(section?.querySelectorAll(".columns > .column")).toHaveLength(3);
    });

    it("issues no HTTP requests: the landing exists before its API (BRW-04)", () => {
        const fixture = TestBed.createComponent(Browse);
        fixture.detectChanges();

        // Consumes every request the component issued — the landing exists
        // before its API, so the set must be empty (asserted, not just verified).
        expect(httpMock.match(() => true)).toHaveLength(0);
    });
});
