import { ComponentFixture, TestBed } from "@angular/core/testing";

import { GovQualityList, GovQualityRow } from "./gov-quality-list.component";

/** The rows one mocked validation leaves non-compliant. */
const nonCompliant: GovQualityRow[] = [
    { message: "This entity is missing a kibanaSpace", detail: "attribute: completeness" },
    { message: "The entity has no business owner", detail: "attribute: businessOwner" },
];

describe("GovQualityList", () => {
    let fixture: ComponentFixture<GovQualityList>;

    async function setup(rows: GovQualityRow[], loading = false) {
        await TestBed.configureTestingModule({ imports: [GovQualityList] }).compileComponents();
        fixture = TestBed.createComponent(GovQualityList);
        fixture.componentRef.setInput("nonCompliant", rows);
        fixture.componentRef.setInput("loading", loading);
        fixture.detectChanges();
        return fixture.nativeElement as HTMLElement;
    }

    it("shows the spinner tag while loading (UIC-38)", async () => {
        const el = await setup([], true);

        expect(el.querySelector(".aurelius-gov-quality-loading .loader")).toBeTruthy();
        expect(el.querySelector(".dropdown")).toBeNull();
    });

    it("shows the green check when nothing is non-compliant (UIC-38)", async () => {
        const el = await setup([]);

        expect(el.querySelector(".aurelius-gov-quality-success")).toBeTruthy();
    });

    it("shows the warning with the count and the hover dropdown (UIC-38)", async () => {
        const el = await setup(nonCompliant);

        const trigger = el.querySelector(".aurelius-gov-quality-trigger");
        expect(trigger?.textContent?.trim()).toBe("2x");
        const dropdown = el.querySelector(".dropdown.is-hoverable.is-right.is-up");
        expect(dropdown).toBeTruthy();
    });

    it("lists every row: the message as the heading, the detail as the line (UIC-38)", async () => {
        const el = await setup(nonCompliant);

        const items = el.querySelectorAll(".dropdown-item");
        expect(items).toHaveLength(2);
        expect(items[0].querySelector("h6.title.is-6")?.textContent?.trim()).toBe(
            "This entity is missing a kibanaSpace",
        );
        expect(items[1].querySelector("p")?.textContent?.trim()).toBe("attribute: businessOwner");
        expect(el.querySelectorAll("hr.dropdown-separator")).toHaveLength(1);
    });

    it("is not a menu to assistive tech — the rows carry no menu roles (ROLE-MENU-MISUSE)", async () => {
        // The dropdown's container once claimed role="menu" with no
        // menuitem children, so screen readers announced a menu of nothing.
        const el = await setup(nonCompliant);

        expect(el.querySelector("[role='menu']")).toBeNull();
        expect(el.querySelector("[role='menuitem']")).toBeNull();
        // The list and its anchor are unchanged: same rows, same id.
        const menu = el.querySelector(".dropdown-menu");
        expect(menu?.getAttribute("id")).toBe("non-compliant");
        expect(el.querySelectorAll(".dropdown-item")).toHaveLength(2);
    });
});
