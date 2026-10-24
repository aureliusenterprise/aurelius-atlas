import { TestBed } from "@angular/core/testing";

import { BusinessContextInfoModal } from "./business-context-info-modal.component";

/**
 * Collapse the whitespace of rendered template text — the template wraps its
 * lines, so the compiler-consumed i18n nodes carry layout newlines.
 */
function normalize(text: string | undefined | null): string {
    return text?.replace(/\s+/g, " ").trim() ?? "";
}

describe("BusinessContextInfoModal", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [BusinessContextInfoModal] }).compileComponents();
    });

    function openFixture() {
        const fixture = TestBed.createComponent(BusinessContextInfoModal);
        fixture.componentInstance.active.set(true);
        fixture.detectChanges();
        return fixture;
    }

    it("renders the modal card with its keyed title (BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        expect(compiled.querySelector(".modal-card-title")?.textContent?.trim()).toBe("Business context");
    });

    it("renders the keyed description paragraph (BRW-02, BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        expect(normalize(compiled.querySelector(".modal-card-body .content > p")?.textContent)).toBe(
            "The business part of the data governance model captures data semantics and ownership for the following types of entities:",
        );
    });

    it("renders the legacy tableData rows: icon, type name, description (BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        const rows = [...compiled.querySelectorAll(".modal-card-body tbody tr")];
        expect(rows).toHaveLength(3);

        const typeNames = rows.map((row) => normalize(row.querySelector("th")?.textContent));
        expect(typeNames).toEqual(["Data Domain", "Data Entity", "Data Attribute"]);

        const descriptions = rows.map((row) => normalize(row.querySelector("td:last-child")?.textContent));
        expect(descriptions[0]).toContain("accountable for data due to their accountability");
        expect(descriptions[1]).toContain("meaning and ownership of business process data artifacts");
        expect(descriptions[2]).toContain("meaning and ownership of an atomic data point");

        // Every row carries its icon (the legacy row template's first cell).
        for (const row of rows) {
            expect(row.querySelector("span.icon fa-icon")).toBeTruthy();
        }
    });

    it("closes through the modal's close button (BRW-03)", () => {
        const fixture = openFixture();
        const compiled = fixture.nativeElement as HTMLElement;

        (compiled.querySelector(".modal-card-head button.delete") as HTMLButtonElement).click();
        fixture.detectChanges();

        expect(fixture.componentInstance.active()).toBe(false);
        expect(compiled.querySelector(".modal")).toBeFalsy();
    });
});
