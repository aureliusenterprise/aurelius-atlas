import { TestBed } from "@angular/core/testing";

import { GovernanceResponsibilitiesInfoModal } from "./governance-responsibilities-info-modal.component";

/**
 * Collapse the whitespace of rendered template text — the template wraps its
 * lines, so the compiler-consumed i18n nodes carry layout newlines.
 */
function normalize(text: string | undefined | null): string {
    return text?.replace(/\s+/g, " ").trim() ?? "";
}

describe("GovernanceResponsibilitiesInfoModal", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [GovernanceResponsibilitiesInfoModal],
        }).compileComponents();
    });

    function openFixture() {
        const fixture = TestBed.createComponent(GovernanceResponsibilitiesInfoModal);
        fixture.componentInstance.active.set(true);
        fixture.detectChanges();
        return fixture;
    }

    it("renders the modal card with its keyed title (BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        expect(compiled.querySelector(".modal-card-title")?.textContent?.trim()).toBe("Data governance organization");
    });

    it("renders the keyed description paragraph (BRW-02, BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        expect(normalize(compiled.querySelector(".modal-card-body .content > p")?.textContent)).toBe(
            "The data governance model captures various kinds of organizational roles with regards to data governance:",
        );
    });

    it("renders the legacy tableData rows: icon, role name, description (BRW-03)", () => {
        const compiled = openFixture().nativeElement as HTMLElement;

        const rows = [...compiled.querySelectorAll(".modal-card-body tbody tr")];
        expect(rows).toHaveLength(3);

        const typeNames = rows.map((row) => normalize(row.querySelector("th")?.textContent));
        expect(typeNames).toEqual(["Domain lead", "Data owner", "Data steward"]);

        const descriptions = rows.map((row) => normalize(row.querySelector("td:last-child")?.textContent));
        expect(descriptions[0]).toContain("implementation of data management within a data domain");
        expect(descriptions[1]).toContain("defining data entities within his or her data domain");
        expect(descriptions[2]).toContain("implementation of data management controls");

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
