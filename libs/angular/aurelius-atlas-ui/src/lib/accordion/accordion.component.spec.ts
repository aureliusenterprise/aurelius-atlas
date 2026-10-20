import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Accordion } from "./accordion.component";

describe("Accordion", () => {
    let component: Accordion;
    let fixture: ComponentFixture<Accordion>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Accordion],
        }).compileComponents();

        fixture = TestBed.createComponent(Accordion);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("starts collapsed (UIC-01)", () => {
        expect(component.expanded()).toBe(false);
        expect(fixture.nativeElement.querySelector(".card-content")).toBeNull();
    });

    it("expands and shows the content slot (UIC-01)", () => {
        component.expand();
        fixture.detectChanges();

        expect(component.expanded()).toBe(true);
        expect(fixture.nativeElement.querySelector(".card-content")).toBeTruthy();
    });

    it("collapses and hides the content slot (UIC-01)", () => {
        component.expand();
        component.collapse();
        fixture.detectChanges();

        expect(component.expanded()).toBe(false);
        expect(fixture.nativeElement.querySelector(".card-content")).toBeNull();
    });

    it("toggles from collapsed to expanded and back (UIC-01)", () => {
        component.toggle();
        expect(component.expanded()).toBe(true);

        component.toggle();
        expect(component.expanded()).toBe(false);
    });

    it("names the toggle button for assistive tech, overridable by the caller (UIC-04)", () => {
        const button = fixture.nativeElement.querySelector(".card-header-icon");
        expect(button.getAttribute("aria-label")).toBe("Toggle content");

        fixture.componentRef.setInput("ariaLabel", "Show lineage");
        fixture.detectChanges();

        expect(button.getAttribute("aria-label")).toBe("Show lineage");
    });

    it("toggles through the header button click (UIC-10)", () => {
        const button: HTMLElement = fixture.nativeElement.querySelector(".card-header-icon");
        button.click();
        fixture.detectChanges();

        expect(component.expanded()).toBe(true);
        expect(fixture.nativeElement.querySelector(".card-content")).toBeTruthy();
    });
});
