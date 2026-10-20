import { TestBed } from "@angular/core/testing";

import { GovernanceResponsibilities } from "./governance-responsibilities.component";

/**
 * Collapse the whitespace of rendered template text — the template wraps its
 * lines, so the compiler-consumed i18n nodes carry layout newlines.
 */
function normalize(text: string | undefined | null): string {
    return text?.replace(/\s+/g, " ").trim() ?? "";
}

describe("GovernanceResponsibilities", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [GovernanceResponsibilities] }).compileComponents();
    });

    it("renders the keyed card strings (BRW-02)", () => {
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
        const fixture = TestBed.createComponent(GovernanceResponsibilities);
        fixture.componentInstance.infoModalActive.set(true);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        (compiled.querySelector("aurelius-atlas-ui-modal button.delete") as HTMLButtonElement).click();
        fixture.detectChanges();

        expect(fixture.componentInstance.infoModalActive()).toBe(false);
    });

    it("carries no search affordance (BRW-06)", () => {
        const fixture = TestBed.createComponent(GovernanceResponsibilities);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        expect(compiled.querySelectorAll("button")).toHaveLength(1);
        expect(compiled.querySelector("input")).toBeFalsy();
        expect(compiled.querySelector("a.button")).toBeFalsy();
    });
});
