/**
 * The classification box on its own (EDT-05, DD-335, DD-336, WFE-03, DD-804):
 * the panel's filter and order, the pick paths (mousedown, Enter with the
 * panel open and shut, the exact-name rule), the keyboard (Down/Up move the
 * active option, Escape shuts the panel), the accessible combobox wiring, the
 * disabled state with its help line, and the chip delete. The box owns the
 * typing and the panel; the chosen set rides the outputs — the editor's own
 * spec keeps the store wiring (the one door body, VDE-03).
 */
import { TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import { ClassificationCombobox } from "./classification-combobox.component";

import { normalize } from "../../../testing/dom";

function setup(suggestions: readonly string[] = ["PII", "CONFIDENTIAL"], chosen: readonly string[] = []) {
    TestBed.configureTestingModule({ imports: [ClassificationCombobox] });
    const fixture = TestBed.createComponent(ClassificationCombobox);
    fixture.componentRef.setInput("suggestions", suggestions);
    fixture.componentRef.setInput("chosen", chosen);
    fixture.componentRef.setInput("tooltips", { PII: "Personally identifiable information" });
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const added: string[] = [];
    const removed: string[] = [];
    fixture.componentInstance.added.subscribe((name) => added.push(name));
    fixture.componentInstance.removed.subscribe((name) => removed.push(name));

    return { fixture, compiled, added, removed };
}

function inputOf(compiled: HTMLElement): HTMLInputElement {
    return compiled.querySelector<HTMLInputElement>("#editor-classification-input")!;
}

function typeText(fixture: { detectChanges: () => void }, compiled: HTMLElement, text: string): void {
    const input = inputOf(compiled);
    input.value = text;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
}

function focus(fixture: { detectChanges: () => void }, compiled: HTMLElement): void {
    inputOf(compiled).dispatchEvent(new Event("focusin", { bubbles: true }));
    fixture.detectChanges();
}

/** The panel's option rows, in order. */
function items(compiled: HTMLElement): HTMLElement[] {
    return [...compiled.querySelectorAll<HTMLElement>(".aurelius-editor-classification-box .dropdown-item")];
}

describe("ClassificationCombobox (EDT-05, DD-335, DD-336, WFE-03)", () => {
    it("typing then Enter adds an exact applicable name (EDT-05)", () => {
        const { fixture, compiled, added } = setup();

        typeText(fixture, compiled, "CONFIDENTIAL");
        inputOf(compiled).dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();

        expect(added).toEqual(["CONFIDENTIAL"]);
        // A real add clears the input (the miss rule below keeps the text).
        expect(inputOf(compiled).value).toBe("");
    });

    it("a name that is not applicable is ignored and keeps its text (EDT-05)", () => {
        const { fixture, compiled, added } = setup();

        typeText(fixture, compiled, "FINANCE");
        inputOf(compiled).dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();

        expect(added).toEqual([]);
        expect(inputOf(compiled).value).toBe("FINANCE");
    });

    it("focus with no text lists the applicable types (EDT-05, DD-335)", () => {
        const { fixture, compiled } = setup(["CONFIDENTIAL"], ["PII"]);

        focus(fixture, compiled);

        // The chosen tag never reappears as a suggestion (the store excludes it).
        expect(items(compiled).map((item) => normalize(item.textContent))).toEqual(["CONFIDENTIAL"]);
    });

    it("a pick through the panel's mousedown adds the tag and closes nothing (EDT-05, DD-335)", () => {
        const { fixture, compiled, added } = setup(["CONFIDENTIAL"]);

        focus(fixture, compiled);
        // The click lands on mousedown, before the input's blur could close
        // the panel (DD-335 — the pointer path the datalist took before).
        items(compiled)[0].dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
        fixture.detectChanges();

        expect(added).toEqual(["CONFIDENTIAL"]);
        expect(inputOf(compiled).value).toBe("");
    });

    it("the panel filters to the typed text with the prefix first (EDT-05, DD-335)", () => {
        const { fixture, compiled } = setup(["PII", "CONFIDENTIAL", "PII_HIGH"]);

        typeText(fixture, compiled, "pi");
        focus(fixture, compiled);

        // A startswith match leads over a contains match (DD-336's Enter);
        // the rows show display names (DD-379 — PII is in the dictionary).
        expect(items(compiled).map((item) => normalize(item.textContent))).toEqual(["Has PII", "PII_HIGH"]);
    });

    it("Escape inside the box hides the panel (EDT-05, DD-335)", () => {
        const { fixture, compiled } = setup();

        focus(fixture, compiled);
        expect(items(compiled).length).toBeGreaterThan(0);

        inputOf(compiled).dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        fixture.detectChanges();

        // The panel is Bulma's dropdown menu, which the box's `is-active`
        // class shows and hides — Escape drops it (and the input's
        // aria-expanded) while the box keeps its focus.
        expect(compiled.querySelector(".aurelius-editor-classification-box.is-active")).toBeNull();
        expect(inputOf(compiled).getAttribute("aria-expanded")).toBe("false");
    });

    it("the input is a labelled combobox pointing at the active option (DD-336)", () => {
        const { fixture, compiled } = setup();

        const input = inputOf(compiled);
        expect(input.getAttribute("role")).toBe("combobox");
        expect(input.getAttribute("aria-autocomplete")).toBe("list");
        const label = compiled.querySelector<HTMLElement>("#editor-classifications-label")!;
        expect(input.getAttribute("aria-labelledby")).toBe(label.id);
        // With nothing typed the panel is shut, so no activedescendant yet.
        expect(input.getAttribute("aria-expanded")).toBe("false");

        focus(fixture, compiled);
        expect(input.getAttribute("aria-expanded")).toBe("true");
        expect(input.getAttribute("aria-controls")).toBe("editor-classification-listbox");
        expect(input.getAttribute("aria-activedescendant")).toBe("editor-classification-option-0");

        inputOf(compiled).dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
        fixture.detectChanges();
        expect(input.getAttribute("aria-activedescendant")).toBe("editor-classification-option-1");
    });

    it("Enter commits the keyboard-active option (DD-336)", () => {
        const { fixture, compiled, added } = setup();

        focus(fixture, compiled);
        // Down lands on the second row (CONFIDENTIAL); Enter adds it.
        inputOf(compiled).dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
        fixture.detectChanges();
        inputOf(compiled).dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));
        fixture.detectChanges();

        expect(added).toEqual(["CONFIDENTIAL"]);
    });

    it("nothing applicable disables the box and says so (DD-336)", () => {
        const { fixture, compiled } = setup([], ["PII"]);

        expect(compiled.querySelector(".aurelius-editor-classification-box.is-disabled")).toBeTruthy();
        expect(inputOf(compiled).disabled).toBe(true);
        expect(normalize(compiled.querySelector(".aurelius-editor-no-classifications")?.textContent)).toBe(
            "No classifications available",
        );
        // Chosen tags keep their delete — the box can still hand a tag back.
        expect(compiled.querySelector(".aurelius-editor-tag")).toBeTruthy();
    });

    it("the chips carry display names, tooltips, and a delete that emits (EDT-05, DD-379, UIC-16, UIC-24)", () => {
        const { compiled, removed } = setup(["CONFIDENTIAL"], ["PII"]);

        const chip = compiled.querySelector<HTMLElement>(".aurelius-editor-tag")!;
        // PII is in the dictionary (its display name shows); the value stays raw.
        expect(normalize(chip.textContent)).toBe("Has PII");
        // The tooltip rides the label tag — the chip's last tag, after the
        // hashtag lead (UIC-16).
        const labelTag = [...chip.querySelectorAll(".tag")].at(-1);
        expect(labelTag?.getAttribute("title")).toBe("Personally identifiable information");

        chip.querySelector<HTMLButtonElement>(".aurelius-classification-chip-delete")!.click();

        expect(removed).toEqual(["PII"]);
    });
});
