import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { DetailsNavigation } from "./details-navigation.component";

/** The host projects the section links, as the Aurelius call sites did. */
@Component({
    imports: [DetailsNavigation],
    template: `
        <aurelius-atlas-ui-details-navigation [label]="label()" [toggleLabel]="toggleLabel()">
            <li><a href="#properties-details">Properties</a></li>
        </aurelius-atlas-ui-details-navigation>
    `,
})
class HostComponent {
    // Signal fields: under zoneless, plain host-field writes never mark
    // the view dirty (the lib's spec convention).
    readonly label = signal("Details");
    readonly toggleLabel = signal("navigation");
}

describe("DetailsNavigation", () => {
    let fixture: ComponentFixture<HostComponent>;
    let host: HostComponent;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [HostComponent],
        }).compileComponents();

        fixture = TestBed.createComponent(HostComponent);
        host = fixture.componentInstance;
        fixture.detectChanges();
    });

    const dropdown = () => (fixture.nativeElement as HTMLElement).querySelector(".dropdown.is-up.is-right");
    const button = () =>
        (fixture.nativeElement as HTMLElement).querySelector("button.button.is-text.is-large") as HTMLButtonElement;

    it("renders the up-dropdown shell with the menu and its label (UIC-18)", () => {
        expect(dropdown()).toBeTruthy();
        expect(fixture.nativeElement.querySelector("nav.menu")).toBeTruthy();
        expect(fixture.nativeElement.querySelector(".menu-label").textContent).toBe("Details");
    });

    it("projects the caller's items into the menu list (UIC-18)", () => {
        const items = fixture.nativeElement.querySelectorAll(".menu-list li");
        expect(items).toHaveLength(1);
        expect(items[0].textContent).toContain("Properties");
    });

    it("names the toggle button for assistive tech (UIC-18)", () => {
        expect(button().getAttribute("aria-label")).toBe("navigation");
        expect(button().querySelector(".icon svg")).toBeTruthy();
    });

    it("opens on toggle and closes on a second click (UIC-18)", () => {
        expect(dropdown()!.classList.contains("is-active")).toBe(false);
        expect(button().getAttribute("aria-expanded")).toBe("false");

        button().click();
        fixture.detectChanges();
        expect(dropdown()!.classList.contains("is-active")).toBe(true);
        expect(button().getAttribute("aria-expanded")).toBe("true");

        button().click();
        fixture.detectChanges();
        expect(dropdown()!.classList.contains("is-active")).toBe(false);
    });

    it("drops the button's focus on toggle, as the legacy blur did (UIC-18)", () => {
        button().focus();
        button().click();
        fixture.detectChanges();

        expect(document.activeElement).not.toBe(button());
    });

    it("localises the label from the caller (UIC-20, DD-047)", () => {
        host.label.set("Onderdelen");
        host.toggleLabel.set("navigatie");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".menu-label").textContent).toBe("Onderdelen");
        expect(button().getAttribute("aria-label")).toBe("navigatie");
    });
});
