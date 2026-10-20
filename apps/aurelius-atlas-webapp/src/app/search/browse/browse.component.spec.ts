import { TestBed } from "@angular/core/testing";

import { Browse } from "./browse.component";

describe("Browse", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [Browse] }).compileComponents();
    });

    it("creates", () => {
        expect(TestBed.createComponent(Browse).componentInstance).toBeTruthy();
    });

    it("renders the Aurelius placeholder text, keyed to the dictionary (SHL-04, DD-039)", () => {
        const fixture = TestBed.createComponent(Browse);
        fixture.detectChanges();

        const placeholder = (fixture.nativeElement as HTMLElement).querySelector("#browse-placeholder");

        // The i18n marker attribute is consumed by the compiler, so the rendered
        // English text is the observable proof of the @@search.browse.description key.
        expect(placeholder).toBeTruthy();
        expect(placeholder?.textContent?.trim()).toBe(
            "Welcome to Aurelius Atlas! We would like to help you get started. Please pick your topic of interest below.",
        );
    });
});
