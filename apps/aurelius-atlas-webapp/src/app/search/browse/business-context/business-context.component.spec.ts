import { TestBed } from "@angular/core/testing";

import { BusinessContext } from "./business-context.component";

/**
 * Collapse the whitespace of rendered template text — the template wraps its
 * lines, so the compiler-consumed i18n nodes carry layout newlines.
 */
function normalize(text: string | undefined | null): string {
    return text?.replace(/\s+/g, " ").trim() ?? "";
}

describe("BusinessContext", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [BusinessContext] }).compileComponents();
    });

    it("renders the keyed card strings (BRW-02)", () => {
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
        const fixture = TestBed.createComponent(BusinessContext);
        fixture.componentInstance.infoModalActive.set(true);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        (compiled.querySelector("aurelius-atlas-ui-modal button.delete") as HTMLButtonElement).click();
        fixture.detectChanges();

        expect(fixture.componentInstance.infoModalActive()).toBe(false);
    });

    it("carries no search affordance (BRW-06)", () => {
        const fixture = TestBed.createComponent(BusinessContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        // The info icon is the card's only button; no input, no explore link.
        expect(compiled.querySelectorAll("button")).toHaveLength(1);
        expect(compiled.querySelector("input")).toBeFalsy();
        expect(compiled.querySelector("a.button")).toBeFalsy();
    });
});
