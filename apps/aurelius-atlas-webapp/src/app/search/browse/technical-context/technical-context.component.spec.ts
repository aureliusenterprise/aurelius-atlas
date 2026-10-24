import { TestBed } from "@angular/core/testing";

import { TechnicalContext } from "./technical-context.component";

/**
 * Collapse the whitespace of rendered template text — the template wraps its
 * lines, so the compiler-consumed i18n nodes carry layout newlines.
 */
function normalize(text: string | undefined | null): string {
    return text?.replace(/\s+/g, " ").trim() ?? "";
}

describe("TechnicalContext", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [TechnicalContext] }).compileComponents();
    });

    it("renders the keyed card strings (BRW-02)", () => {
        const fixture = TestBed.createComponent(TechnicalContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        expect(normalize(compiled.querySelector(".card .title.is-4")?.textContent)).toBe("Technical context");
        expect(normalize(compiled.querySelector("article.media:nth-of-type(1) .title.is-6")?.textContent)).toBe(
            "I'm searching for which data is stored on a specific technical environment",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(1) p")?.textContent)).toBe(
            "Search for keywords related to the technical metadata that you are looking for.",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(2) .title.is-6")?.textContent)).toBe(
            "I'm exploring the technical environments on which data is stored",
        );
        expect(normalize(compiled.querySelector("article.media:nth-of-type(2) p")?.textContent)).toBe(
            "Search for keywords related to the system, collection or dataset that you are looking for.",
        );
    });

    it("opens the info modal from the info icon (BRW-03)", () => {
        const fixture = TestBed.createComponent(TechnicalContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        const infoButton = compiled.querySelector<HTMLButtonElement>("button.icon")!;
        expect(infoButton.getAttribute("aria-label")).toBe("Technical context");
        infoButton.click();
        fixture.detectChanges();

        expect(fixture.componentInstance.infoModalActive()).toBe(true);
        expect(compiled.querySelector("aurelius-atlas-ui-modal .modal-card-title")?.textContent?.trim()).toBe(
            "Technical context",
        );
    });

    it("the modal's close path clears the card's open state (BRW-03, BRW-05)", () => {
        const fixture = TestBed.createComponent(TechnicalContext);
        fixture.componentInstance.infoModalActive.set(true);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        (compiled.querySelector("aurelius-atlas-ui-modal button.delete") as HTMLButtonElement).click();
        fixture.detectChanges();

        expect(fixture.componentInstance.infoModalActive()).toBe(false);
    });

    it("carries no search affordance (BRW-06)", () => {
        const fixture = TestBed.createComponent(TechnicalContext);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;

        expect(compiled.querySelectorAll("button")).toHaveLength(1);
        expect(compiled.querySelector("input")).toBeFalsy();
        expect(compiled.querySelector("a.button")).toBeFalsy();
    });
});
