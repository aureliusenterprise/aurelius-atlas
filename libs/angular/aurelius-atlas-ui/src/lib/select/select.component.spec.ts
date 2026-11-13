import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Select } from "./select.component";

// A type alias (not an interface) — the implicit index signature Select's
// row constraint (Record<string, unknown>) requires.
type Row = { name: string; kind: string };

describe("Select", () => {
    let component: Select<Row>;
    let fixture: ComponentFixture<Select<Row>>;

    const rows: Row[] = [
        { name: "Glossary", kind: "term" },
        { name: "Domain", kind: "domain" },
    ];

    function control(): HTMLSelectElement {
        return fixture.nativeElement.querySelector("div.select select");
    }

    function optionLabels(): string[] {
        return [...control().querySelectorAll("option")].map((option) =>
            (option.textContent?.trim() ?? "").replace(/\u00a0/g, " "),
        );
    }

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Select],
        }).compileComponents();

        fixture = TestBed.createComponent<Select<Row>>(Select);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders the Bulma field with label and fullwidth select (UIC-14)", () => {
        fixture.componentRef.setInput("options", rows);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".field.has-addons")).toBeTruthy();
        expect(fixture.nativeElement.querySelector("label.label")).toBeTruthy();
        expect(fixture.nativeElement.querySelector("div.select.is-fullwidth")).toBeTruthy();
        expect(control()).toBeTruthy();
    });

    it("pairs the label and control by id (UIC-14)", () => {
        fixture.detectChanges();

        const label = fixture.nativeElement.querySelector("label.label");
        expect(label.getAttribute("for")).toBe(control().getAttribute("id"));
        expect(control().getAttribute("aria-labelledby")).toBe(label.getAttribute("id"));
    });

    it("shows the legacy default chrome (UIC-15)", () => {
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("label.label").textContent.trim()).toBe("Title");
        // No rows by default, so the placeholder carries the no-data message.
        expect(optionLabels()[0]).toBe("-- No data available --");
    });

    it("hides the search button on request, plain dropdown (DD-164)", () => {
        fixture.componentRef.setInput("options", rows);
        fixture.componentRef.setInput("searchVisible", false);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("button.button.is-info")).toBeNull();
        expect(control()).toBeTruthy();
    });

    it("switches the placeholder between the null-input and no-data messages (UIC-14)", () => {
        fixture.componentRef.setInput("options", rows);
        fixture.detectChanges();

        expect(optionLabels()[0]).toBe("-- Please select a value --");
        fixture.componentRef.setInput("options", []);
        fixture.detectChanges();

        expect(optionLabels()[0]).toBe("-- No data available --");
    });

    it("renders one option per row that has a display value (UIC-14)", () => {
        fixture.componentRef.setInput("options", [...rows, { name: "", kind: "skipped" }]);
        fixture.componentRef.setInput("displayField", "name");
        fixture.detectChanges();

        expect(optionLabels()).toEqual(["-- Please select a value --", "Glossary", "Domain"]);
    });

    it("formats option labels as timestamps on request (UIC-14)", () => {
        fixture.componentRef.setInput("options", [{ name: "2024-01-31T10:20:30Z", kind: "ts" }]);
        fixture.componentRef.setInput("isTimestamp", true);
        fixture.detectChanges();

        // Bulma's date pipe pattern, 'dd MMM y, HH:mm:ss'.
        expect(optionLabels()[1]).toMatch(/31 Jan 2024, \d{2}:\d{2}:\d{2}/);
    });

    it("selects a row on change, two-way binding the model (UIC-14)", () => {
        fixture.componentRef.setInput("options", rows);
        fixture.detectChanges();

        const select = control();
        select.value = "1";
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();

        expect(component.value()).toBe(rows[1]);
    });

    it("clears the model when the placeholder is chosen (UIC-14)", async () => {
        fixture.componentRef.setInput("options", rows);
        fixture.componentRef.setInput("value", rows[0]);
        fixture.detectChanges();
        // ngModel applies an external value in a microtask.
        await fixture.whenStable();

        const select = control();
        expect(select.value).toBe("0");
        select.value = "";
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();

        expect(component.value()).toBeNull();
    });

    it("shows the placeholder in the control while nothing is chosen (UIC-14, DD-344)", async () => {
        fixture.componentRef.setInput("options", rows);
        fixture.detectChanges();
        await fixture.whenStable();

        // A null model must land the control on the placeholder option, not on
        // nothing: the option's empty value has to be a real attribute, or the
        // control renders an empty box (live-probed in the editor's drawer).
        expect(control().selectedIndex).toBe(0);
        expect(optionLabels()[0]).toBe("-- Please select a value --");
    });

    it("shows the model's row as selected, so two-way binding round-trips (UIC-14)", async () => {
        fixture.componentRef.setInput("options", rows);
        fixture.componentRef.setInput("value", rows[1]);
        fixture.detectChanges();
        await fixture.whenStable();

        expect(control().value).toBe("1");
    });

    it("paints the danger state and the required help when invalid (UIC-14)", () => {
        fixture.componentRef.setInput("options", rows);
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector("div.select.is-danger")).toBeNull();
        expect(fixture.nativeElement.querySelector("p.help.is-danger")).toBeNull();

        fixture.componentRef.setInput("invalid", true);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("div.select.is-danger")).toBeTruthy();
        expect(fixture.nativeElement.querySelector("p.help.is-danger").textContent.trim()).toBe(
            "Please select a value",
        );
    });

    it("names the required help from the caller (DD-136)", () => {
        fixture.componentRef.setInput("invalid", true);
        fixture.componentRef.setInput("requiredErrorMessage", "Kies een waarde");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("p.help.is-danger").textContent.trim()).toBe("Kies een waarde");
    });

    it("disables the control and the search button (UIC-14)", async () => {
        fixture.componentRef.setInput("options", rows);
        fixture.componentRef.setInput("disabled", true);
        fixture.detectChanges();
        // ngModel applies the disabled state in a microtask.
        await fixture.whenStable();

        expect(control().disabled).toBe(true);
        const button: HTMLButtonElement = fixture.nativeElement.querySelector("button.button.is-info");
        expect(button.disabled).toBe(true);
        expect(button.classList.contains("is-static")).toBe(true);
    });

    it("emits searchRequested from the search button (DD-155, UIC-14)", () => {
        fixture.detectChanges();
        const requested: number[] = [];
        component.searchRequested.subscribe(() => requested.push(1));

        fixture.nativeElement.querySelector("button.button.is-info").click();

        expect(requested).toEqual([1]);
    });

    it("names the search button from the caller (DD-136)", () => {
        fixture.componentRef.setInput("searchLabel", "Zoeken");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("button.button.is-info").getAttribute("aria-label")).toBe("Zoeken");
    });

    it("shows the loading spinner on the search button and stays inert (UIC-14)", () => {
        fixture.detectChanges();
        const requested: number[] = [];
        component.searchRequested.subscribe(() => requested.push(1));

        fixture.componentRef.setInput("searchLoading", true);
        fixture.detectChanges();

        const button: HTMLButtonElement = fixture.nativeElement.querySelector("button.button.is-info");
        expect(button.classList.contains("is-loading")).toBe(true);
        expect(button.getAttribute("aria-busy")).toBe("true");

        button.click();
        expect(requested).toEqual([]);
    });

    it("omits the label chrome when the label is empty (UIC-14)", () => {
        fixture.componentRef.setInput("label", "");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("label.label")).toBeNull();
        expect(fixture.nativeElement.querySelector(".field.is-marginless")).toBeTruthy();
    });

    it("drops the dangling label reference when the label is empty (FORM-LABEL-001)", () => {
        fixture.componentRef.setInput("label", "");
        fixture.detectChanges();

        // The label element only renders with a label; the reference must
        // leave with it, or a reader lands on an id that is not in the DOM.
        expect(control().hasAttribute("aria-labelledby")).toBe(false);

        fixture.componentRef.setInput("label", "Title");
        fixture.detectChanges();

        expect(control().getAttribute("aria-labelledby")).toBe(control().getAttribute("id") + "-label");
    });

    it("marks the control required only when the caller requires it (FORM-STATE-001)", () => {
        fixture.detectChanges();

        // An optional dropdown carries nothing — the hard-coded
        // aria-required="true" lied for every field.
        expect(control().getAttribute("aria-required")).toBeNull();

        fixture.componentRef.setInput("required", true);
        fixture.detectChanges();

        expect(control().getAttribute("aria-required")).toBe("true");
    });

    it("announces the required error line (FORM-ERR-001)", () => {
        fixture.componentRef.setInput("options", rows);
        fixture.detectChanges();

        // A valid control names no error line.
        expect(control().getAttribute("aria-invalid")).toBeNull();
        expect(control().getAttribute("aria-describedby")).toBeNull();

        fixture.componentRef.setInput("invalid", true);
        fixture.detectChanges();

        expect(control().getAttribute("aria-invalid")).toBe("true");
        const error = fixture.nativeElement.querySelector("p.help.is-danger") as HTMLElement;
        expect(control().getAttribute("aria-describedby")).toBe(error.id);
        expect(error.id).toBe(control().getAttribute("id") + "-error");
    });
});
