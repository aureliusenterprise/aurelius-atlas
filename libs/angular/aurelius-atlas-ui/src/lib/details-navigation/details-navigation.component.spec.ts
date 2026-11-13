import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { DetailsNavigation } from "./details-navigation.component";

/** The host projects the section links, as the Aurelius call sites did. */
@Component({
    imports: [DetailsNavigation],
    template: `
        <aurelius-atlas-ui-details-navigation [label]="label()" [toggleLabel]="toggleLabel()">
            <ul class="menu-list">
                <li><a href="#properties-details">Properties</a></li>
            </ul>
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

    it("keeps the toggle's focus across a toggle (DETAILS-NAV-FOCUS)", () => {
        // The legacy blurred on toggle; a keyboard reader lost its place.
        // The focus must stay on the trigger, whose aria-expanded is the
        // state the reader announces.
        button().focus();
        button().click();
        fixture.detectChanges();
        expect(document.activeElement).toBe(button());

        button().click();
        fixture.detectChanges();
        expect(document.activeElement).toBe(button());
        expect(dropdown()!.classList.contains("is-active")).toBe(false);
    });

    it("closes on Escape and returns the focus to the toggle (DETAILS-NAV-FOCUS, 2.4.7)", () => {
        button().click();
        fixture.detectChanges();
        expect(dropdown()!.classList.contains("is-active")).toBe(true);

        // The keydown starts on a projected item, as it does for a reader
        // tabbing the open menu.
        const link = fixture.nativeElement.querySelector(".menu-list a") as HTMLElement;
        link.focus();
        link.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
        fixture.detectChanges();

        expect(dropdown()!.classList.contains("is-active")).toBe(false);
        expect(button().getAttribute("aria-expanded")).toBe("false");
        expect(document.activeElement).toBe(button());
    });

    it("is not a menu to assistive tech — the container carries no role=menu (ROLE-MENU-MISUSE)", () => {
        // The dropdown's container once claimed role="menu" while holding
        // plain links, so screen readers announced a menu with no items.
        button().click();
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("[role='menu']")).toBeNull();
        expect(fixture.nativeElement.querySelector("[role='menuitem']")).toBeNull();
        // The menu stays what the shell always was: a labelled nav of links.
        expect(fixture.nativeElement.querySelector("nav.menu")).toBeTruthy();
        expect(fixture.nativeElement.querySelector(".menu-list a")).toBeTruthy();
    });

    it("localises the label from the caller (UIC-20, DD-136)", () => {
        host.label.set("Onderdelen");
        host.toggleLabel.set("navigatie");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".menu-label").textContent).toBe("Onderdelen");
        expect(button().getAttribute("aria-label")).toBe("navigatie");
    });
});
