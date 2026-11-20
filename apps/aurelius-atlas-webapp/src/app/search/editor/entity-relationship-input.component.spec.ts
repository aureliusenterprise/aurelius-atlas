/**
 * The relationship picker's data wiring (EDT-14 as amended in 7.31, DD-711):
 * the view door's request body (the target type and its sub types, the limits,
 * the name-matching query, the 250 ms debounce), the client-side name-prefix
 * rule, the exclusions (the chosen and the edited entity never ride the panel),
 * the card-like row (EDT-33: name, type badge, trail), the pick path (append +
 * clear), the SINGLE rule (the box hides its input at one chip), and the chip
 * delete. The http client is the real one through HttpTestingController — the
 * picker's only dependency is ViewSearchService. The box, its combobox keyboard
 * and its accessible name are the dumb `TokenPicker`'s and are tested in the ui
 * library (UIC-44, DD-713); this spec drives them through the rendered box.
 */
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { provideRouter } from "@angular/router";
import Keycloak from "keycloak-js";

import type { EntityCard, ViewSearchAnswer } from "aurelius-atlas-data-access";

import { APP_CONFIG } from "../../tokens";

import { EntityRelationshipInput } from "./entity-relationship-input.component";
import type { RelationshipField, RelationshipPick } from "./form-fields";

const SEARCH_URL = "/api/aurelius/v1/search";

const FIELD: RelationshipField = {
    name: "inputToProcesses",
    label: "inputToProcesses",
    targetType: "Process",
    single: false,
    required: false,
    relationshipTypeName: "dataset_process_inputs",
};

const SINGLE_FIELD: RelationshipField = { ...FIELD, name: "model", label: "model", single: true };

/** One answer card of the door's population (AVS-01). */
function card(over: Partial<EntityCard>): EntityCard {
    return { guid: "g", typeName: "Process", displayText: "name", status: "ACTIVE", stale: false, ...over };
}

/**
 * A search answer (AVR-08): the first card carries a trail and a type the
 * dictionary knows (its badge reads "Generic Process" with the app's icon),
 * the second is a bare `Process` with no stored parent (no trail), and the
 * third is one the door's looser token matching answered but whose name does
 * not begin with the typed text — the panel drops it (DD-711).
 */
const ANSWER: ViewSearchAnswer = {
    cards: [
        card({
            guid: "p1",
            typeName: "m4i_generic_process",
            displayText: "load_events",
            breadcrumb: [
                { guid: "d1", name: "Sales Domain", typeName: "m4i_data_domain" },
                { guid: "s1", name: "Order Processing", typeName: "m4i_data_entity" },
            ],
        }),
        card({ guid: "p2", typeName: "Process", displayText: "load_orders", qualifiedName: "load_orders" }),
        card({ guid: "p3", typeName: "Process", displayText: "etl_load" }),
    ],
    facets: {},
    total: 3,
};

/** Every door body names the target type and its sub types (VSR-04). */
const TYPE_FILTER = { any: [{ typeName: ["Process"] }, { superTypeNames: ["Process"] }] };

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
    const input = compiled.querySelector<HTMLInputElement>(".aurelius-token-input");
    if (input === null) {
        throw new Error("the picker holds no input");
    }
    input.focus();
    input.value = text;
    input.dispatchEvent(new Event("input"));
}

/** The panel's option rows. */
function rows(compiled: HTMLElement): HTMLElement[] {
    return [...compiled.querySelectorAll<HTMLElement>('[role="option"]')];
}

/** The names the panel shows, in order. */
function names(compiled: HTMLElement): (string | undefined)[] {
    return rows(compiled).map((row) => row.querySelector(".aurelius-token-row-name")?.textContent ?? undefined);
}

describe("EntityRelationshipInput (EDT-14, EDT-33, DD-711)", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("searches the view door after the debounce (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "load");
        fixture.detectChanges();

        // The 250 ms delay is the stock select2's — no request before it.
        httpMock.expectNone(SEARCH_URL);
        vi.advanceTimersByTime(250);

        const request = httpMock.expectOne((req) => req.url === SEARCH_URL && req.method === "POST");
        expect(request.request.body).toEqual({ filters: TYPE_FILTER, limit: 10, query: "load*" });
        request.flush(ANSWER);
        fixture.detectChanges();

        // The door matches whole analysed tokens, so its looser answer gets
        // the name-prefix check here: `etl_load` never begins with the text.
        expect(names(compiled)).toEqual(["load_events", "load_orders"]);
    });

    it("strips the door's own wildcard characters from the typed text (EDT-14, DD-711)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "sa*le?");
        vi.advanceTimersByTime(250);

        // The door reads `*` and `?` as its own syntax, so a typed one must
        // not ride the query — only the wildcard the picker appends does.
        const request = httpMock.expectOne((req) => req.url === SEARCH_URL);
        expect(request.request.body).toMatchObject({ query: "sale*" });
        request.flush(ANSWER);
        fixture.detectChanges();

        // Nothing begins with the stripped text, so the panel stays shut.
        expect(names(compiled)).toEqual([]);
    });

    it("a new keystroke re-debounces and the last text wins (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "lo");
        vi.advanceTimersByTime(100);
        type(compiled, "load");
        vi.advanceTimersByTime(250);

        httpMock.expectNone((req) => req.url === SEARCH_URL && (req.body as { query?: string }).query === "lo*");
        const request = httpMock.expectOne((req) => req.url === SEARCH_URL);
        expect(request.request.body).toMatchObject({ query: "load*" });
        request.flush(ANSWER);
        fixture.detectChanges();

        // The panel holds the answer of the last text only.
        expect(names(compiled)).toEqual(["load_events", "load_orders"]);
    });

    it("drops the chosen entities and the edited entity from the panel (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup(
            FIELD,
            [{ guid: "p1", typeName: "Process", displayText: "load_events" }],
            "p2",
        );

        type(compiled, "");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();

        // p1 is chosen and p2 is the edited entity — only the third card of
        // the browse remains, and it is pickable: a card always carries a
        // guid (EDT-33), so the panel has no unpickable row.
        expect(names(compiled)).toEqual(["etl_load"]);
        expect(rows(compiled)).toHaveLength(1);
    });

    it("the row prints the name, the type badge and the trail (EDT-33)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();

        const [first, second] = rows(compiled);
        // The badge carries the dictionary display name (DD-379) with the
        // app's type icon and colour class (DD-378) — the card's badge.
        expect(first.querySelector(".aurelius-token-row-name")?.textContent).toBe("load_events");
        expect(first.querySelector(".aurelius-token-row-type")?.textContent?.trim()).toBe("Generic Process");
        expect(first.querySelectorAll(".aurelius-token-row-type fa-icon")).toHaveLength(1);
        expect(first.querySelector(".aurelius-token-row-type .icon")?.classList.contains("technical-process")).toBe(
            true,
        );
        // The stored parents, top down — the entity's own crumb is not
        // printed, because the row is the entity (VDR-06, EDT-33). The trail
        // is the Breadcrumbs component, printed plain: the row already is the
        // option's one action (UIC-11 amended, DD-714).
        const trail = first.querySelector(".aurelius-token-row-trail");
        expect(trail?.querySelectorAll("aurelius-atlas-ui-breadcrumbs li")).toHaveLength(2);
        expect([...(trail?.querySelectorAll("li") ?? [])].map((li) => li.textContent?.trim())).toEqual([
            "Sales Domain",
            "Order Processing",
        ]);
        expect(trail?.querySelectorAll("a")).toHaveLength(0);
        // A card with no stored parent draws no trail at all (VDR-11).
        expect(second.querySelector(".aurelius-token-row-type")?.textContent?.trim()).toBe("Process");
        expect(second.querySelector(".aurelius-token-row-trail")).toBeNull();
        expect(second.querySelectorAll(".aurelius-token-row-type fa-icon")).toHaveLength(0);
    });

    it("the row's accessible name is name, type, then trail (EDT-33)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();

        // The option's name is its whole text — every part plain text inside
        // the row, so the accessible name needs no aria-label. jsdom keeps no
        // space between the parts (a browser's flat string joins the row's
        // flex children with one) and never renders Bulma's CSS-drawn crumb
        // separator, so the pin is the parts and their order.
        expect(rows(compiled)[0].textContent).toBe("load_eventsGeneric ProcessSales DomainOrder Processing");
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

        rows(compiled)[1].dispatchEvent(new MouseEvent("mousedown"));
        fixture.detectChanges();

        // The card becomes the chip's value, qualified name included; the
        // row's trail never rides the value (EDT-15).
        expect(changes).toEqual([
            [{ guid: "p2", typeName: "Process", displayText: "load_orders", qualifiedName: "load_orders" }],
        ]);
        expect(compiled.querySelector<HTMLInputElement>(".aurelius-token-input")?.value).toBe("");
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

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-token-input")!;
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
        fixture.detectChanges();
        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));
        fixture.detectChanges();

        expect(changes).toEqual([
            [{ guid: "p2", typeName: "Process", displayText: "load_orders", qualifiedName: "load_orders" }],
        ]);
    });

    it("the input is the combobox with the box's aria wiring (EDT-14, DD-336)", () => {
        const { fixture, compiled, httpMock } = setup();

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-token-input")!;
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

    it("a SINGLE picker hides the input at one chip (EDT-14)", () => {
        const { compiled } = setup(SINGLE_FIELD, [{ guid: "m1", typeName: "Process", displayText: "model" }]);

        expect(compiled.querySelector(".aurelius-token-input")).toBeNull();
        expect(compiled.querySelectorAll("aurelius-atlas-ui-classification-chip")).toHaveLength(1);
    });

    it("a SINGLE picker with no chip keeps the input (EDT-14)", () => {
        const { compiled } = setup(SINGLE_FIELD, []);

        expect(compiled.querySelector(".aurelius-token-input")).toBeTruthy();
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
        const { compiled } = setup(FIELD, [{ guid: "p1", typeName: "spark_process", displayText: "load_events" }]);

        const lead = compiled.querySelector(".aurelius-token-chip .tag");
        expect(lead?.textContent?.trim()).toBe("spark_process");
    });

    it("whitespace-only text browses the target type (EDT-14, DD-343)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "   ");
        vi.advanceTimersByTime(250);

        // Whitespace is no text to search: the empty browse answers instead,
        // with no query key at all — and with no typed text the name filter
        // lifts, so all three cards ride the panel.
        const request = httpMock.expectOne((req) => req.url === SEARCH_URL);
        expect(request.request.body).toEqual({ filters: TYPE_FILTER, limit: 5 });
        request.flush(ANSWER);
        fixture.detectChanges();

        expect(rows(compiled)).toHaveLength(3);
    });

    it("a focused empty box browses five candidates before any typing (EDT-14, DD-343)", () => {
        const { fixture, compiled, httpMock } = setup();

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-token-input")!;
        expect(input.getAttribute("aria-expanded")).toBe("false");

        // Real focus opens the box (DD-335's gate) and the browse rides its
        // own debounce — no request before the 250 ms, then the empty browse
        // at limit 5 (not the typed search's 10).
        input.focus();
        fixture.detectChanges();
        vi.advanceTimersByTime(249);
        httpMock.expectNone(SEARCH_URL);
        vi.advanceTimersByTime(1);

        const request = httpMock.expectOne((req) => req.url === SEARCH_URL);
        expect(request.request.body).toEqual({ filters: TYPE_FILTER, limit: 5 });
        request.flush(ANSWER);
        fixture.detectChanges();

        expect(input.getAttribute("aria-expanded")).toBe("true");
        expect(names(compiled)).toEqual(["load_events", "load_orders", "etl_load"]);
    });

    it("typing replaces the browse — the browse request never fires (EDT-14)", () => {
        const { fixture, compiled, httpMock } = setup();

        const input = compiled.querySelector<HTMLInputElement>(".aurelius-token-input")!;
        input.focus();
        vi.advanceTimersByTime(100);
        input.value = "load";
        input.dispatchEvent(new Event("input"));
        vi.advanceTimersByTime(250);

        httpMock.expectNone((req) => req.url === SEARCH_URL && (req.body as { limit?: number }).limit === 5);
        const request = httpMock.expectOne((req) => req.url === SEARCH_URL);
        expect(request.request.body).toMatchObject({ query: "load*", limit: 10 });
        request.flush(ANSWER);
        fixture.detectChanges();

        expect(names(compiled)).toEqual(["load_events", "load_orders"]);
    });

    it("clearing typed text browses again (EDT-14, DD-343)", () => {
        const { fixture, compiled, httpMock } = setup();

        type(compiled, "load");
        vi.advanceTimersByTime(250);
        httpMock.expectOne((req) => req.url === SEARCH_URL).flush(ANSWER);
        fixture.detectChanges();

        // Backspacing to empty is the browse again, not a cleared panel.
        type(compiled, "");
        vi.advanceTimersByTime(250);
        const browse = httpMock.expectOne((req) => req.url === SEARCH_URL);
        expect(browse.request.body).toEqual({ filters: TYPE_FILTER, limit: 5 });
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

        expect(names(compiled)).toEqual([]);
    });
});
