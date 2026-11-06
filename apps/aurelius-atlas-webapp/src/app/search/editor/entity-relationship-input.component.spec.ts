/**
 * One relationship-attribute picker (EDT-14, DD-339): the search round trip's
 * contract (the stock parameters, the 250 ms debounce), the exclusions (the
 * chosen and the edited entity never ride the panel), the pick path (append +
 * clear, the combobox commit), the SINGLE rule (the input hides at one chip),
 * and the chip delete. The http client is the real one through
 * HttpTestingController — the picker's only dependency is SearchService.
 */
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { provideRouter } from "@angular/router";
import Keycloak from "keycloak-js";

import type { AtlasSearchResult } from "aurelius-atlas-data-access";

import { APP_CONFIG } from "../../tokens";

import { EntityRelationshipInput } from "./entity-relationship-input.component";
import type { RelationshipField, RelationshipPick } from "./form-fields";

const SEARCH_URL = "/api/atlas/v2/search/attribute";

const FIELD: RelationshipField = {
    name: "inputToProcesses",
    label: "inputToProcesses (Process)",
    targetType: "Process",
    single: false,
    required: false,
    relationshipTypeName: "dataset_process_inputs",
};

const SINGLE_FIELD: RelationshipField = { ...FIELD, name: "model", label: "model (Process)", single: true };

/** A search answer: two processes and one row without a guid to attach. */
const ANSWER: AtlasSearchResult = {
    entities: [
        { guid: "p1", typeName: "Process", displayText: "load_events" },
        { guid: "p2", typeName: "Process", displayText: "load_orders" },
        { typeName: "Process", displayText: "no-guid" },
    ],
};

function setup(field: RelationshipField = FIELD, selected: readonly RelationshipPick[] = [], editedGuid = "edited-1") {
    TestBed.configureTestingModule({
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            provideRouter([]),
            { provide: APP_CONFIG, useValue: { atlasClientId: "aurelius-atlas-server" } },
            { provide: Keycloak, useValue: { hasResourceRole: () => true } },
        ],
    });
    const fixture = TestBed.createComponent(EntityRelationshipInput);
    fixture.componentRef.setInput("field", field);
    fixture.componentRef.setInput("selected", selected);
    fixture.componentRef.setInput("editedGuid", editedGuid);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    return { fixture, compiled, httpMock: TestBed.inject(HttpTestingController) };
}

/** Type into the box's input. The real focus opens the box — the panel is
 * focus-gated (DD-335), so the helper focuses for real rather than faking it. */
function type(compiled: HTMLElement, text: string): void {
    const input = compiled.querySelector<HTMLInputElement>(".aurelius-relationship-input");
    if (input === null) {
        throw new Error("the picker holds no input");
    }
    input.focus();
    input.value = text;
    input.dispatchEvent(new Event("input"));
}

/** The panel's option rows. */
function rows(compiled: HTMLElement): HTMLButtonElement[] {
    return [...compiled.querySelectorAll<HTMLButtonElement>('[role="option"]')];
}

describe("EntityRelationshipInput (EDT-14, DD-339)", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("searches with the stock parameters after the debounce (EDT-14, DD-339)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "load");
        fixture.detectChanges();

        // The 250 ms delay is the stock select2's — no request before it.
        httpMock.expectNone(SEARCH_URL);
        vi.advanceTimersByTime(250);

        const request = httpMock.expectOne(
            (req) =>
                req.url === SEARCH_URL &&
                req.params.get("typeName") === "Process" &&
                req.params.get("attrName") === "name" &&
                req.params.get("attrValuePrefix") === "load" &&
                req.params.get("limit") === "10",
        );
        expect(request.request.method).toBe("GET");
        request.flush(ANSWER);
        fixture.detectChanges();

        expect(rows(compiled).map((row) => row.textContent?.trim())).toEqual(["load_events", "load_orders", "no-guid"]);
    });

    it("a new keystroke re-debounces and the last text wins (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "lo");
        vi.advanceTimersByTime(100);
        type(compiled, "load");
        vi.advanceTimersByTime(250);

        httpMock.expectNone((req) => req.url === SEARCH_URL && req.params.get("attrValuePrefix") === "lo");
        const request = httpMock.expectOne(
            (req) => req.url === SEARCH_URL && req.params.get("attrValuePrefix") === "load",
        );
        expect(request.request.params.get("attrValuePrefix")).toBe("load");
        request.flush(ANSWER);
        fixture.detectChanges();

        // The panel holds the answer of the last text only.
        expect(rows(compiled).map((row) => row.textContent?.trim())).toEqual(["load_events", "load_orders", "no-guid"]);
    });

    it("drops the chosen entities and the edited entity from the panel (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup(
            FIELD,
            [{ guid: "p1", typeName: "Process", displayText: "load_events" }],
            "p2",
        );

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();

        // p1 is chosen and p2 is the edited entity — only the third row (no
        // guid) and nothing else remains; the guidless row shows disabled.
        expect(rows(compiled).map((row) => row.textContent?.trim())).toEqual(["no-guid"]);
        expect(rows(compiled)[0].disabled).toBe(true);
    });

    it("a pick appends the entry and clears the input (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup();
        const changes: (readonly RelationshipPick[])[] = [];
        fixture.debugElement.componentInstance.changed.subscribe((picks: readonly RelationshipPick[]) =>
            changes.push(picks),
        );

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();

        rows(compiled)[0].dispatchEvent(new MouseEvent("mousedown"));
        fixture.detectChanges();

        expect(changes).toEqual([[{ guid: "p1", typeName: "Process", displayText: "load_events" }]]);
        expect(compiled.querySelector<HTMLInputElement>(".aurelius-relationship-input")?.value).toBe("");
    });

    it("Enter commits the active row, Down moves it (DD-336 wiring)", () => {
        const { fixture, compiled, httpMock } = setup();
        const changes: (readonly RelationshipPick[])[] = [];
        fixture.debugElement.componentInstance.changed.subscribe((picks: readonly RelationshipPick[]) =>
            changes.push(picks),
        );

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-relationship-input")!;
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
        fixture.detectChanges();
        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));
        fixture.detectChanges();

        expect(changes).toEqual([[{ guid: "p2", typeName: "Process", displayText: "load_orders" }]]);
    });

    it("the input is the combobox with the box's aria wiring (EDT-14, DD-336)", () => {
        const { fixture, compiled, httpMock } = setup();

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-relationship-input")!;
        expect(input.getAttribute("role")).toBe("combobox");
        expect(input.getAttribute("aria-autocomplete")).toBe("list");
        expect(input.getAttribute("aria-expanded")).toBe("false");
        expect(input.getAttribute("aria-labelledby")).toBe("editor-relationship-inputToProcesses-label");

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();

        expect(input.getAttribute("aria-expanded")).toBe("true");
        expect(input.getAttribute("aria-controls")).toBe("editor-relationship-inputToProcesses-listbox");
        expect(input.getAttribute("aria-activedescendant")).toBe(
            "editor-relationship-inputToProcesses-listbox-option-0",
        );
    });

    it("Escape closes the panel only, keeping the text (DD-335)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();
        const box = compiled.querySelector(".aurelius-relationship-box")!;
        expect(box.classList.contains("is-active")).toBe(true);

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-relationship-input")!;
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        fixture.detectChanges();

        // Closing is Bulma's own — the menu loses .is-active and its display:
        // none returns (the 7.7a box's rule, DD-335). The text survives.
        expect(box.classList.contains("is-active")).toBe(false);
        expect(input.getAttribute("aria-expanded")).toBe("false");
        expect(input.value).toBe("load");
    });

    it("a SINGLE picker hides the input at one chip (EDT-14)", () => {
        const { fixture, compiled } = setup(SINGLE_FIELD, [{ guid: "m1", typeName: "Process", displayText: "model" }]);

        expect(compiled.querySelector(".aurelius-relationship-input")).toBeNull();
        expect(compiled.querySelectorAll("aurelius-atlas-ui-classification-chip")).toHaveLength(1);
    });

    it("a SINGLE picker with no chip keeps the input (EDT-14)", () => {
        const { compiled } = setup(SINGLE_FIELD, []);

        expect(compiled.querySelector(".aurelius-relationship-input")).toBeTruthy();
    });

    it("the chip delete emits the full new list (EDT-14/UIC-24)", () => {
        const { fixture, compiled } = setup(FIELD, [
            { guid: "p1", typeName: "Process", displayText: "one" },
            { guid: "p2", typeName: "Process", displayText: "two" },
        ]);
        const changes: (readonly RelationshipPick[])[] = [];
        fixture.debugElement.componentInstance.changed.subscribe((picks: readonly RelationshipPick[]) =>
            changes.push(picks),
        );

        const deletes = [
            ...compiled.querySelectorAll<HTMLButtonElement>("aurelius-atlas-ui-classification-chip button"),
        ];
        deletes[0].click();

        expect(changes).toEqual([[{ guid: "p2", typeName: "Process", displayText: "two" }]]);
    });

    it("the chip leads with the entity's own typeName (EDT-14, DD-341)", () => {
        const { fixture, compiled } = setup(FIELD, [
            { guid: "p1", typeName: "spark_process", displayText: "load_events" },
        ]);

        const lead = compiled.querySelector(".aurelius-relationship-chip .tag");
        expect(lead?.textContent?.trim()).toBe("spark_process");
    });

    it("whitespace-only text browses the target type (EDT-14, DD-343)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "   ");
        vi.advanceTimersByTime(250);

        // Whitespace is no prefix to search: the empty-prefix browse answers
        // instead (the same list a focused empty box shows).
        const request = httpMock.expectOne(
            (req) =>
                req.url === SEARCH_URL && req.params.get("attrValuePrefix") === "" && req.params.get("limit") === "5",
        );
        request.flush(ANSWER);
        fixture.detectChanges();

        expect(rows(compiled)).toHaveLength(3);
    });

    it("a focused empty box browses five candidates before any typing (EDT-14, DD-343)", () => {
        const { fixture, compiled, httpMock } = setup();

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-relationship-input")!;
        expect(input.getAttribute("aria-expanded")).toBe("false");

        // Real focus opens the box (DD-335's gate) and the browse rides its
        // own debounce — no request before the 250 ms, then the empty prefix
        // with limit 5 (the browse, not the stock search's 10).
        input.focus();
        fixture.detectChanges();
        vi.advanceTimersByTime(249);
        httpMock.expectNone(SEARCH_URL);
        vi.advanceTimersByTime(1);

        const request = httpMock.expectOne(
            (req) =>
                req.url === SEARCH_URL &&
                req.params.get("typeName") === "Process" &&
                req.params.get("attrValuePrefix") === "" &&
                req.params.get("limit") === "5",
        );
        request.flush(ANSWER);
        fixture.detectChanges();

        expect(input.getAttribute("aria-expanded")).toBe("true");
        expect(rows(compiled).map((row) => row.textContent?.trim())).toEqual(["load_events", "load_orders", "no-guid"]);
    });

    it("typing replaces the browse — the browse request never fires (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup();

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-relationship-input")!;
        input.focus();
        vi.advanceTimersByTime(100);
        input.value = "load";
        input.dispatchEvent(new Event("input"));
        vi.advanceTimersByTime(250);

        httpMock.expectNone((req) => req.url === SEARCH_URL && req.params.get("limit") === "5");
        const request = httpMock.expectOne(
            (req) => req.url === SEARCH_URL && req.params.get("attrValuePrefix") === "load",
        );
        request.flush(ANSWER);
        fixture.detectChanges();

        expect(rows(compiled)).toHaveLength(3);
    });

    it("clearing typed text browses again (EDT-14, DD-343)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock
            .expectOne((req) => req.url === SEARCH_URL && req.params.get("attrValuePrefix") === "load")
            .flush(ANSWER);
        fixture.detectChanges();

        // Backspacing to empty is the browse again, not a cleared panel.
        type(compiled, "");
        vi.advanceTimersByTime(250);
        const browse = httpMock.expectOne(
            (req) =>
                req.url === SEARCH_URL && req.params.get("attrValuePrefix") === "" && req.params.get("limit") === "5",
        );
        browse.flush(ANSWER);
        fixture.detectChanges();

        expect(rows(compiled)).toHaveLength(3);
    });

    it("a failed search leaves the panel empty (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush({}, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        expect(rows(compiled)).toHaveLength(0);
    });
});
