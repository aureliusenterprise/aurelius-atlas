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

    it("shows the caller placeholder (DD-047)", () => {
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

    it("names the icon buttons from the caller's labels (DD-047)", () => {
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
