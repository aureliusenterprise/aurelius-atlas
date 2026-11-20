import { faCogs } from "@fortawesome/free-solid-svg-icons";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import { TokenPicker, type TokenChip, type TokenRow } from "./token-picker.component";

const CHIPS: TokenChip[] = [
    { key: "a", label: "load_events", leadLabel: "Process" },
    { key: "b", label: "orders", leadLabel: "DataSet" },
];

const ROWS: TokenRow[] = [
    {
        key: "r1",
        name: "load_events",
        type: "Generic Process",
        icon: faCogs,
        iconClass: "technical-process",
        trail: [{ guid: "d1", name: "Sales Domain", typeName: "m4i_data_domain" }],
    },
    { key: "r2", name: "load_orders", type: "Process" },
];

function setup(
    rows: readonly TokenRow[] = ROWS,
    chips: readonly TokenChip[] = [],
): {
    fixture: ComponentFixture<TokenPicker>;
    compiled: HTMLElement;
} {
    const fixture = TestBed.createComponent(TokenPicker);
    fixture.componentRef.setInput("rows", rows);
    fixture.componentRef.setInput("selected", chips);
    fixture.componentRef.setInput("label", "Related processes");
    fixture.componentRef.setInput("idBase", "tp");
    fixture.detectChanges();
    return { fixture, compiled: fixture.nativeElement as HTMLElement };
}

/** Focus the box's input for real — the panel is focus-gated (DD-335). */
function focusInput(compiled: HTMLElement): HTMLInputElement {
    const input = compiled.querySelector<HTMLInputElement>(".aurelius-token-input");
    if (input === null) {
        throw new Error("the box holds no input");
    }
    input.focus();
    return input;
}

function rowsOf(compiled: HTMLElement): HTMLElement[] {
    return [...compiled.querySelectorAll<HTMLElement>('[role="option"]')];
}

describe("TokenPicker (UIC-44, DD-713)", () => {
    it("renders the chips inside the box and the input beside them (UIC-44)", () => {
        const { compiled } = setup(ROWS, CHIPS);

        expect(compiled.querySelectorAll(".aurelius-token-box aurelius-atlas-ui-classification-chip")).toHaveLength(2);
        expect(compiled.querySelector(".aurelius-token-input")).toBeTruthy();
        // The lead word the caller gave the chip is printed (DD-189's term lead).
        expect(compiled.querySelector(".aurelius-token-chip .tag")?.textContent?.trim()).toBe("Process");
    });

    it("keeps the panel shut until the box holds focus (DD-335)", () => {
        const { fixture, compiled } = setup();

        // The panel is Bulma's own: its rows stay in the DOM and its CSS
        // hides the menu, so the shut state is the class and the aria flag.
        expect(compiled.querySelector(".aurelius-token-box")?.classList.contains("is-active")).toBe(false);

        const input = focusInput(compiled);
        expect(input.getAttribute("aria-expanded")).toBe("false");
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-token-box")?.classList.contains("is-active")).toBe(true);
        expect(rowsOf(compiled)).toHaveLength(2);
        expect(compiled.querySelector<HTMLInputElement>(".aurelius-token-input")?.getAttribute("aria-expanded")).toBe(
            "true",
        );
    });

    it("closes the panel when focus leaves the box (DD-335)", () => {
        const { fixture, compiled } = setup();
        const input = focusInput(compiled);
        fixture.detectChanges();

        input.dispatchEvent(
            new FocusEvent("focusout", {
                bubbles: true,
                relatedTarget: document.body,
            }),
        );
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-token-box")?.classList.contains("is-active")).toBe(false);
    });

    it("prints the name, the badge and the trail of a row (EDT-33)", () => {
        const { fixture, compiled } = setup();
        focusInput(compiled);
        fixture.detectChanges();

        const [first, second] = rowsOf(compiled);
        expect(first.querySelector(".aurelius-token-row-name")?.textContent).toBe("load_events");
        expect(first.querySelector(".aurelius-token-row-type")?.textContent?.trim()).toBe("Generic Process");
        expect(first.querySelector(".aurelius-token-row-type .icon")?.classList.contains("technical-process")).toBe(
            true,
        );
        // The trail is the Breadcrumbs component, printed plain (DD-714).
        const trail = first.querySelector(".aurelius-token-row-trail");
        expect(trail?.textContent).toContain("Sales Domain");
        // A row with no badge and no trail draws neither (the caller decides).
        expect(second.querySelector(".aurelius-token-row-trail")).toBeNull();
    });

    it("prints the trail with the Breadcrumbs component and no links (DD-714)", () => {
        const { fixture, compiled } = setup([
            {
                key: "r",
                name: "n",
                trail: [
                    { guid: "a", name: "Alpha", typeName: "t" },
                    { guid: "b", name: "Beta", typeName: "t" },
                ],
            },
        ]);
        focusInput(compiled);
        fixture.detectChanges();

        const trail = rowsOf(compiled)[0].querySelector(".aurelius-token-row-trail");
        expect(trail?.querySelector("aurelius-atlas-ui-breadcrumbs nav.breadcrumb")).toBeTruthy();
        // The row is the option's one action, so its trail holds no nested
        // activation: plain crumbs, no anchors (UIC-11 amended, DD-714).
        expect(trail?.querySelectorAll("a")).toHaveLength(0);
        expect(trail?.textContent).toContain("Alpha");
        expect(trail?.textContent).toContain("Beta");
    });

    it("emits typed on every keystroke", () => {
        const { fixture, compiled } = setup();
        const typed: string[] = [];
        fixture.debugElement.componentInstance.typed.subscribe((value: string) => typed.push(value));

        const input = focusInput(compiled);
        input.value = "load";
        input.dispatchEvent(new Event("input"));

        expect(typed).toEqual(["load"]);
    });

    it("shows the caller's text in the input (the caller holds it)", () => {
        const { fixture, compiled } = setup();
        fixture.componentRef.setInput("text", "load");
        fixture.detectChanges();

        expect(compiled.querySelector<HTMLInputElement>(".aurelius-token-input")?.value).toBe("load");
    });

    it("emits the row on a mousedown pick (DD-335)", () => {
        const { fixture, compiled } = setup();
        const picked: TokenRow[] = [];
        fixture.debugElement.componentInstance.picked.subscribe((row: TokenRow) => picked.push(row));
        focusInput(compiled);
        fixture.detectChanges();

        rowsOf(compiled)[1].dispatchEvent(new MouseEvent("mousedown"));

        expect(picked.map((row) => row.key)).toEqual(["r2"]);
    });

    it("is a div option, so the row can carry a printed trail (DD-714)", () => {
        const { compiled } = setup();

        // The picker owns the keyboard (DD-336) and the rows are never tab
        // stops; a div role="option" is the combobox pattern's own shape.
        const row = rowsOf(compiled)[0];
        expect(row.tagName).toBe("DIV");
        expect(row.getAttribute("tabindex")).toBeNull();
    });

    it("the input is the combobox with the box's aria wiring (DD-336)", () => {
        const { fixture, compiled } = setup();
        fixture.componentRef.setInput("labelId", "tp-label");
        fixture.detectChanges();

        const input = focusInput(compiled);
        expect(input.getAttribute("role")).toBe("combobox");
        expect(input.getAttribute("aria-autocomplete")).toBe("list");
        expect(input.getAttribute("aria-labelledby")).toBe("tp-label");
        expect(input.getAttribute("aria-controls")).toBeNull();

        fixture.detectChanges();

        expect(input.getAttribute("aria-controls")).toBe("tp-listbox");
        expect(input.getAttribute("aria-activedescendant")).toBe("tp-listbox-option-0");
    });

    it("Down moves the active row and Enter commits it (DD-336)", () => {
        const { fixture, compiled } = setup();
        const picked: TokenRow[] = [];
        fixture.debugElement.componentInstance.picked.subscribe((row: TokenRow) => picked.push(row));
        const input = focusInput(compiled);
        fixture.detectChanges();

        input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
        fixture.detectChanges();
        expect(rowsOf(compiled)[1].classList.contains("is-active")).toBe(true);

        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));

        expect(picked.map((row) => row.key)).toEqual(["r2"]);
    });

    it("Up from the first row wraps to the last (DD-336)", () => {
        const { fixture, compiled } = setup();
        const input = focusInput(compiled);
        fixture.detectChanges();

        input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
        fixture.detectChanges();

        expect(rowsOf(compiled)[1].classList.contains("is-active")).toBe(true);
    });

    it("Escape closes the panel and keeps the text (DD-335)", () => {
        const { fixture, compiled } = setup();
        fixture.componentRef.setInput("text", "load");
        const input = focusInput(compiled);
        fixture.detectChanges();

        input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-token-box")?.classList.contains("is-active")).toBe(false);
        expect(input.getAttribute("aria-expanded")).toBe("false");
        expect(input.value).toBe("load");
    });

    it("returns the highlight to the first row when the rows change (DD-336)", () => {
        const { fixture, compiled } = setup();
        const input = focusInput(compiled);
        fixture.detectChanges();
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
        fixture.detectChanges();
        expect(rowsOf(compiled)[1].classList.contains("is-active")).toBe(true);

        // A new answer starts the highlight over: the old row's key may not
        // even exist in the new list.
        fixture.componentRef.setInput("rows", [...ROWS]);
        fixture.detectChanges();

        expect(rowsOf(compiled)[0].classList.contains("is-active")).toBe(true);
    });

    it("a single box hides its input at one chip and keeps it while empty", () => {
        const empty = setup([], []);
        empty.fixture.componentRef.setInput("single", true);
        empty.fixture.detectChanges();
        expect(empty.compiled.querySelector(".aurelius-token-input")).toBeTruthy();
        expect(empty.compiled.querySelector<HTMLInputElement>(".aurelius-token-input")?.placeholder).toBe("");

        empty.fixture.componentRef.setInput("singlePlaceholder", "Select a relationship...");
        empty.fixture.detectChanges();
        expect(empty.compiled.querySelector<HTMLInputElement>(".aurelius-token-input")?.placeholder).toBe(
            "Select a relationship...",
        );

        const full = setup([], [CHIPS[0]]);
        full.fixture.componentRef.setInput("single", true);
        full.fixture.detectChanges();

        expect(full.compiled.querySelector(".aurelius-token-input")).toBeNull();
        expect(full.compiled.querySelectorAll("aurelius-atlas-ui-classification-chip")).toHaveLength(1);
    });

    it("a disabled box takes the disabled look and offers no panel (UIC-44)", () => {
        const { fixture, compiled } = setup();
        fixture.componentRef.setInput("disabled", true);
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-token-box")?.classList.contains("is-disabled")).toBe(true);
        // The input is a real disabled control, so no keyboard or pointer can
        // reach a pick.
        expect(compiled.querySelector<HTMLInputElement>(".aurelius-token-input")?.disabled).toBe(true);

        // Focus cannot open the suggest panel: there is nothing to suggest.
        // Bulma's own pattern keeps the rows in the DOM and hides the menu,
        // so the shut state is the class and the aria flag, not the rows.
        focusInput(compiled);
        fixture.detectChanges();
        expect(compiled.querySelector(".aurelius-token-box")?.classList.contains("is-active")).toBe(false);
        expect(compiled.querySelector<HTMLInputElement>(".aurelius-token-input")?.getAttribute("aria-expanded")).toBe(
            "false",
        );
    });

    it("a disabled box drops its placeholder and keeps the chip deletable (UIC-44, UIC-24)", () => {
        const { fixture, compiled } = setup(ROWS, [CHIPS[0]]);
        fixture.componentRef.setInput("single", true);
        fixture.componentRef.setInput("disabled", true);
        fixture.componentRef.setInput("singlePlaceholder", "Select a relationship...");
        fixture.detectChanges();

        // The full single box's input is gone, so the box paints disabled and
        // the one chip left can still be handed back — disabling the control
        // does not freeze the value.
        expect(compiled.querySelector(".aurelius-token-box")?.classList.contains("is-disabled")).toBe(true);
        const removed: TokenChip[] = [];
        fixture.debugElement.componentInstance.removed.subscribe((chip: TokenChip) => removed.push(chip));
        compiled.querySelectorAll<HTMLButtonElement>("aurelius-atlas-ui-classification-chip button")[0].click();
        expect(removed.map((chip) => chip.key)).toEqual(["a"]);
    });

    it("a disabled empty box shows no placeholder (UIC-44)", () => {
        const { fixture, compiled } = setup();
        fixture.componentRef.setInput("single", true);
        fixture.componentRef.setInput("singlePlaceholder", "Select a relationship...");
        fixture.componentRef.setInput("disabled", true);
        fixture.detectChanges();

        // A muted "Select a relationship..." on a control that cannot take a
        // pick invites the interaction it forbids.
        expect(compiled.querySelector<HTMLInputElement>(".aurelius-token-input")?.placeholder).toBe("");
    });

    it("paints the danger state and names the error line (FORM-ERR-002)", () => {
        const { fixture, compiled } = setup();
        fixture.componentRef.setInput("invalid", true);
        fixture.componentRef.setInput("errorId", "tp-error");
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-token-box")?.classList.contains("is-danger")).toBe(true);
        const input = compiled.querySelector<HTMLInputElement>(".aurelius-token-input")!;
        expect(input.getAttribute("aria-invalid")).toBe("true");
        expect(input.getAttribute("aria-describedby")).toBe("tp-error");
    });

    it("emits the chip whose delete was clicked (UIC-24)", () => {
        const { fixture, compiled } = setup(ROWS, CHIPS);
        const removed: TokenChip[] = [];
        fixture.debugElement.componentInstance.removed.subscribe((chip: TokenChip) => removed.push(chip));

        compiled.querySelectorAll<HTMLButtonElement>("aurelius-atlas-ui-classification-chip button")[0].click();

        expect(removed.map((chip) => chip.key)).toEqual(["a"]);
    });

    it("numbers its ids from idBase, so two pickers never share one (DD-336)", () => {
        const { fixture, compiled } = setup();
        fixture.componentRef.setInput("idBase", "second");
        fixture.detectChanges();

        expect(compiled.querySelector('[role="listbox"]')?.id).toBe("second-listbox");
        expect(compiled.querySelector(".aurelius-token-input")?.id).toBe("second-input");
    });
});
