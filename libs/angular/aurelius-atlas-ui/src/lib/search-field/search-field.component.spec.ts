import { ComponentFixture, TestBed } from "@angular/core/testing";

import { SearchField } from "./search-field.component";

describe("SearchField", () => {
    let component: SearchField;
    let fixture: ComponentFixture<SearchField>;

    function input(): HTMLInputElement {
        return fixture.nativeElement.querySelector("input[type='search']");
    }

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [SearchField],
        }).compileComponents();

        fixture = TestBed.createComponent(SearchField);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders the Bulma field with a submit button (UIC-05)", () => {
        expect(fixture.nativeElement.querySelector(".field.has-addons .input")).toBeTruthy();
        expect(fixture.nativeElement.querySelector("button.button.is-success")).toBeTruthy();
    });

    it("omits the submit button on request (UIC-05)", () => {
        fixture.componentRef.setInput("withSubmitButton", false);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("button.button.is-success")).toBeNull();
    });

    it("shows the caller placeholder (DD-136)", () => {
        fixture.componentRef.setInput("placeholder", "Search...");
        fixture.detectChanges();

        expect(input().placeholder).toBe("Search...");
    });

    it("updates the model as the user types, normalising empty to null (UIC-01)", () => {
        const field = input();
        field.value = "glossary";
        field.dispatchEvent(new Event("input"));
        fixture.detectChanges();

        expect(component.query()).toBe("glossary");

        field.value = "";
        field.dispatchEvent(new Event("input"));
        fixture.detectChanges();

        expect(component.query()).toBeNull();
    });

    it("shows the model value, so two-way binding round-trips (UIC-01)", async () => {
        fixture.componentRef.setInput("query", "entity");
        fixture.detectChanges();
        // ngModel applies an external value in a microtask.
        await fixture.whenStable();

        expect(input().value).toBe("entity");
    });

    it("emits querySubmitted on the native search event (Enter), as Aurelius did (UIC-01)", () => {
        const submitted: (string | null)[] = [];
        component.querySubmitted.subscribe((query) => submitted.push(query));
        component.query.set("branch");
        fixture.detectChanges();

        input().dispatchEvent(new Event("search", { bubbles: true }));

        expect(submitted).toEqual(["branch"]);
    });

    it("submits on Enter in every browser (FORM-KBD-001)", () => {
        const submitted: (string | null)[] = [];
        component.querySubmitted.subscribe((query) => submitted.push(query));
        component.query.set("branch");
        fixture.detectChanges();

        // Firefox fires no search event for Enter — the keydown path is the
        // cross-browser submit; its preventDefault keeps Chrome's own search
        // event from adding a second emit.
        const event = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
        input().dispatchEvent(event);

        expect(submitted).toEqual(["branch"]);
        expect(event.defaultPrevented).toBe(true);
    });

    it("keeps focus on the input when the clear button destroys itself (FORM-KBD-001)", () => {
        component.query.set("branch");
        fixture.detectChanges();

        const clearButton = fixture.nativeElement.querySelector("button.delete") as HTMLElement;
        clearButton.focus();
        clearButton.click();
        fixture.detectChanges();

        // The button is gone with the query (@if); focus lands on the input
        // instead of the body.
        expect(component.query()).toBeNull();
        expect(fixture.nativeElement.querySelector("button.delete")).toBeNull();
        expect(document.activeElement).toBe(input());
    });

    it("leaves focus alone when the clear was a pointer click (no focus to save)", () => {
        component.query.set("branch");
        fixture.detectChanges();

        // A mouse click on an unfocused button (jsdom: activeElement stays
        // the body) — nothing steals focus to the input from where the
        // user's tab order stands.
        (fixture.nativeElement.querySelector("button.delete") as HTMLElement).click();
        fixture.detectChanges();

        expect(component.query()).toBeNull();
        expect(document.activeElement).not.toBe(input());
    });

    it("emits querySubmitted from the submit button (UIC-01)", () => {
        const submitted: (string | null)[] = [];
        component.querySubmitted.subscribe((query) => submitted.push(query));
        component.query.set("branch");
        fixture.detectChanges();

        (fixture.nativeElement.querySelector("button.button.is-success") as HTMLElement).click();

        expect(submitted).toEqual(["branch"]);
    });

    it("clears and re-submits null from the delete button, as Aurelius did (UIC-01)", () => {
        const submitted: (string | null)[] = [];
        component.querySubmitted.subscribe((query) => submitted.push(query));
        component.query.set("branch");
        fixture.detectChanges();

        const clearButton = fixture.nativeElement.querySelector("button.delete");
        expect(clearButton).toBeTruthy();
        clearButton.click();

        expect(component.query()).toBeNull();
        expect(submitted).toEqual([null]);
    });

    it("hides the clear button while the query is empty (UIC-01)", () => {
        expect(fixture.nativeElement.querySelector("button.delete")).toBeNull();
    });

    it("carries the ControlShell's left icon plate, as the Aurelius context's default did (UIC-01)", () => {
        // The legacy ControlShell rendered context.icon — faSearch, the
        // simple-search-input default — in an is-left plate (the demo shows
        // the cyan magnifier in the hero and every card).
        const plate = fixture.nativeElement.querySelector(".control .icon.is-left");

        expect(plate).toBeTruthy();
        expect(plate.classList.contains("has-text-info")).toBe(true);
    });

    it("names the icon buttons from the caller's labels (DD-136)", () => {
        fixture.componentRef.setInput("submitLabel", "Zoeken");
        fixture.componentRef.setInput("query", "branch");
        fixture.componentRef.setInput("clearLabel", "Wissen");
        fixture.detectChanges();

        expect(
            (fixture.nativeElement.querySelector("button.button.is-success") as HTMLElement).getAttribute("aria-label"),
        ).toBe("Zoeken");
        expect((fixture.nativeElement.querySelector("button.delete") as HTMLElement).getAttribute("aria-label")).toBe(
            "Wissen",
        );
    });
});
