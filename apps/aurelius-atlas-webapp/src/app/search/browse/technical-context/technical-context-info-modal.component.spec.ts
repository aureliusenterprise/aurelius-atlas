import { TestBed } from "@angular/core/testing";

import { TechnicalContextInfoModal } from "./technical-context-info-modal.component";

/**
 * Collapse the whitespace of rendered template text — the template wraps its
 * lines, so the compiler-consumed i18n nodes carry layout newlines.
 */
function normalize(text: string | undefined | null): string {
    return text?.replace(/\s+/g, " ").trim() ?? "";
}

describe("TechnicalContextInfoModal", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [TechnicalContextInfoModal] }).compileComponents();
    });

    function openFixture() {
        const fixture = TestBed.createComponent(TechnicalContextInfoModal);
        fixture.componentInstance.active.set(true);
        fixture.detectChanges();
        return fixture;
    }

    it("renders the modal card with its keyed title (BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        expect(compiled.querySelector(".modal-card-title")?.textContent?.trim()).toBe("Technical context");
    });

    it("renders the keyed description paragraph (BRW-02, BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        expect(normalize(compiled.querySelector(".modal-card-body .content > p")?.textContent)).toContain(
            "The technical part of the data governance model captures the technical implementation of data",
        );
    });

    it("renders the legacy tableData rows: icon, type name, description (BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        const rows = [...compiled.querySelectorAll(".modal-card-body tbody tr")];
        expect(rows).toHaveLength(4);

        const typeNames = rows.map((row) => normalize(row.querySelector("th")?.textContent));
        expect(typeNames).toEqual(["System", "Collection", "Dataset", "Data Field"]);

        const descriptions = rows.map((row) => normalize(row.querySelector("td:last-child")?.textContent));
        expect(descriptions[0]).toContain("computing environment");
        expect(descriptions[1]).toContain("set of datasets");
        expect(descriptions[2]).toContain("set of data fields");
        expect(descriptions[3]).toContain("single, indivisible unit of data");

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
