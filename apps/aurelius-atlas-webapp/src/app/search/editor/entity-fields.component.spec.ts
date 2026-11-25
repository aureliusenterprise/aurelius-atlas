/**
 * The entity editor's field controls (EDT-03, EDT-20, FORM-REQ-001, FORM-ERR-002):
 * the per-kind render loop that turns a resolved field into its control — text,
 * number, boolean, enum, multi and the markdown field — with the EDT-11 label, the
 * required star and the error line. Moved out of the main drawer spec at 7.49
 * (DD-875); they still drive the whole drawer, which owns the field set, the
 * signal form and the save, so the render rule ids stay attributed to the drawer.
 */
import { TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import { describe, expect, it, vi } from "vitest";

import { type AtlasTypesDef, type ViewSaveRequest } from "aurelius-atlas-data-access";

import { VIEW_POST_URL } from "../../../testing/api";
import { normalize } from "../../../testing/dom";
import {
    ALL_KINDS_ANSWER,
    ALL_KINDS_CHAIN,
    ANSWER,
    TIER_ENUM_SLICE,
    TYPEDEFS,
    arrive,
    chainFor,
    savedView,
    setup,
} from "./editor-testing";

describe("EntityEditor field controls (EDT-03, EDT-20)", () => {
    it("renders the edit form from the for-type chain (EDT-03, VDE-02)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const names = [...compiled.querySelectorAll<HTMLInputElement>("input.aurelius-editor-text")].map((input) =>
            input.id.replace("editor-", ""),
        );
        // The text inputs, in the resolved order: name first, then the rest
        // by name; the description key rides the markdown field now (EDT-20)
        // and the unique qualifiedName is dropped entirely (the form never
        // edits it). The base owner, displayName and userDescription are
        // hidden too (EDT-37), so only name is left of the base four.
        expect(names).toEqual(["name"]);

        const nameField = compiled.querySelector<HTMLInputElement>("#editor-name");
        expect(nameField?.value).toBe("genomic_variants");
        expect(nameField?.required).toBe(true);
        // The seeded source reaches the textarea one level deeper — inside
        // the markdown field (EDT-20); the read still seeds the raw string.
        expect(compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")?.value).toBe(
            "Curated variant calls.",
        );
        // The drawer title is the edit title (EDT-11's bridge strings).
        expect(normalize(compiled.querySelector(".aurelius-drawer-title")?.textContent)).toBe("Edit entity");
    });

    it("the description rides the markdown field: tabs, label seat, raw save (EDT-20)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        // The tab pair renders with Write active (the field's start, EDT-20).
        // The drawer's own Entity/History pair (HST-01) rides the subhead, so
        // this query names the field's strip, not every tab in the panel.
        const tabs = [...compiled.querySelectorAll<HTMLElement>(".aurelius-markdown-editor-tabs [role='tab']")];
        expect(tabs.map((tab) => normalize(tab.textContent))).toEqual(["Write", "Preview"]);
        expect(tabs[0]?.getAttribute("aria-selected")).toBe("true");

        // The label still reaches the textarea through the component's seat
        // (EDT-11's for="editor-<name>", UIC-26's textareaId).
        const label = compiled.querySelector('label[for="editor-description"]');
        expect(label).toBeTruthy();
        expect(compiled.querySelector("textarea#editor-description")).toBeTruthy();

        // Typing rides the source string; the save sends it unchanged (the
        // door body carries it whole — no transform between read and body).
        const area = compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")!;
        area.value = "# Headings stay source";
        area.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(VIEW_POST_URL);
        const body = post.request.body as ViewSaveRequest;
        expect(body.attributes["description"]).toBe("# Headings stay source");
        post.flush(savedView());
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalled();
    });

    it("a required field is announced, not painted (FORM-REQ-001)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // The native flag rides the schema rule, so browsers and readers see
        // it (the signal form writes it for required fields).
        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        expect(nameInput.required).toBe(true);
        const nameBlock = compiled.querySelector<HTMLElement>('[data-field="name"]')!;
        // The red star stays for the eye, aria-hidden; the words carry the
        // fact into the label a reader hears.
        expect(normalize(nameBlock.querySelector("label.label")?.textContent)).toBe("Name *(required)");
        expect(nameBlock.querySelector("label .has-text-danger")?.getAttribute("aria-hidden")).toBe("true");

        // An optional field gets neither. The prose field is the optional one
        // the form still renders (EDT-37 hid the base owner).
        const proseBlock = compiled.querySelector<HTMLElement>('[data-field="description"]')!;
        expect(compiled.querySelector("textarea#editor-description")).toBeTruthy();
        // An attribute the raw name of would be human-readable only by case
        // gets its catalogue string (EDT-33, 7-33).
        expect(normalize(proseBlock.querySelector("label.label")?.textContent)).toBe("Description");
    });

    it("the catalogue label beats the definition's displayName (EDT-03, EDT-33)", () => {
        // The precedence EDT-03 states: catalogue string, then displayName,
        // then the name. The dictionary's raw or typo'd displayNames must not
        // win over the translated string (7-33, DD-722, DV-181).
        const { fixture, compiled, httpMock } = setup();
        const defs: AtlasTypesDef = {
            ...TYPEDEFS,
            entityDefs: TYPEDEFS.entityDefs!.map((def) =>
                def.name === "Asset"
                    ? {
                          ...def,
                          attributeDefs: def.attributeDefs!.map((attribute) =>
                              attribute.name === "description"
                                  ? { ...attribute, displayName: "description" }
                                  : attribute,
                          ),
                      }
                    : def,
            ),
        };
        arrive(fixture, httpMock, ANSWER, chainFor(defs, "DataSet"));

        const block = compiled.querySelector<HTMLElement>('[data-field="description"]')!;

        expect(normalize(block.querySelector("label.label")?.textContent)).toBe("Description");
    });

    it("a required multi group names its rows and says required (FORM-REQ-001)", () => {
        const { fixture, compiled, httpMock } = setup();
        const chain = chainFor(
            {
                ...TYPEDEFS,
                entityDefs: TYPEDEFS.entityDefs!.map((def) =>
                    def.name === "Asset"
                        ? {
                              ...def,
                              attributeDefs: [
                                  ...def.attributeDefs!,
                                  { name: "tags", typeName: "array<string>", cardinality: "SET", isOptional: false },
                              ],
                          }
                        : def,
                ),
            },
            "DataSet",
        );
        arrive(fixture, httpMock, ANSWER, chain);

        const block = compiled.querySelector<HTMLElement>('[data-field="tags"]')!;
        expect(normalize(block.querySelector("label.label")?.textContent)).toBe("tags *(required)");
        expect(block.querySelector("label .has-text-danger")?.getAttribute("aria-hidden")).toBe("true");
        // The rows have no label of their own: the field name is each row's
        // accessible name.
        const row = block.querySelector<HTMLInputElement>("#editor-tags-0")!;
        expect(row.getAttribute("aria-label")).toBe("tags");
    });

    it("the markdown field passes the required and error wiring through (FORM-ERR-002, FORM-REQ-001)", () => {
        const { fixture, compiled, httpMock } = setup();
        const chain = chainFor(
            {
                ...TYPEDEFS,
                entityDefs: TYPEDEFS.entityDefs!.map((def) =>
                    def.name === "Asset"
                        ? {
                              ...def,
                              attributeDefs: def.attributeDefs!.map((attribute) =>
                                  attribute.name === "description" ? { ...attribute, isOptional: false } : attribute,
                              ),
                          }
                        : def,
                ),
            },
            "DataSet",
        );
        arrive(fixture, httpMock, ANSWER, chain);

        const area = compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")!;
        // The schema's required rule reaches the textarea through the
        // component's `required` input (the custom-control path never writes
        // the native property itself).
        expect(area.required).toBe(true);

        area.value = "";
        area.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        expect(area.getAttribute("aria-invalid")).toBe("true");
        expect(area.getAttribute("aria-describedby")).toBe("editor-description-error");
        expect(normalize(compiled.querySelector("#editor-description-error")?.textContent)).toBe("Name is required.");
    });

    /** The drawer over the all-kinds chain: every control kind the loop has
     * (EDT-03), each seeded from {@link ALL_KINDS_ANSWER} (EDT-02). The plain
     * DataSet fixtures carry none of these kinds, so these four tests are the
     * renderer's only exercise of the boolean, enum, number, date and multi
     * branches — the coverage the moved markup lost when the specs moved. */

    it("renders each field kind its own control, seeded by kind (EDT-03, EDT-02)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, ALL_KINDS_ANSWER, ALL_KINDS_CHAIN, true, undefined, TIER_ENUM_SLICE);

        // The boolean: the checkbox anatomy (Bulma's label wraps the input),
        // seeded checked from the entity's `true`.
        const checkbox = compiled.querySelector<HTMLInputElement>('[data-field="retired"] input[type="checkbox"]')!;
        expect(checkbox.checked).toBe(true);
        expect(normalize(checkbox.closest("label")?.textContent)).toBe("retired");

        // The number: its own input type, seeded 7; `null` stays its empty,
        // so a seeded text number must not reach it as text (DD-354).
        const number = compiled.querySelector<HTMLInputElement>('#editor-score[type="number"]')!;
        expect(number.value).toBe("7");

        // The date: the datetime-local input, seeded from the epoch ms —
        // local-time text, so only its presence is pinned (toDateTimeLocal's
        // shape is form-fields' own spec).
        const date = compiled.querySelector<HTMLInputElement>('#editor-when[type="datetime-local"]')!;
        expect(date.value).not.toBe("");

        // The enum: the Select's options, ordinal-sorted (the fixture ships
        // them out of order to pin the sort), and the seeded value that is not
        // one of them selects nothing — the placeholder, not a stray row.
        const select = compiled.querySelector<HTMLSelectElement>('[data-field="tier"] select')!;
        const labels = [...select.querySelectorAll("option")].map((option) => normalize(option.textContent));
        expect(labels).toEqual(["-- Please select a value --", "bronze", "silver", "gold"]);
        expect(select.value).toBe("");

        // The multi: one row per seeded value plus the blank trailing row
        // (EDT-03), each with its delete button.
        const rows = [...compiled.querySelectorAll<HTMLInputElement>('[data-field="tags"] input')];
        expect(rows.map((row) => row.value)).toEqual(["a", "b", ""]);
        expect(compiled.querySelectorAll('[data-field="tags"] button[aria-label="Delete"]')).toHaveLength(rows.length);
    });

    it("an enum pick writes the model and reaches the save (EDT-03, EDT-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, ALL_KINDS_ANSWER, ALL_KINDS_CHAIN, true, undefined, TIER_ENUM_SLICE);

        const select = compiled.querySelector<HTMLSelectElement>('[data-field="tier"] select')!;
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        select.value = "2"; // gold — the ordinal sort put it last
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();
        expect(select.value).toBe("2");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(VIEW_POST_URL);
        expect((post.request.body as ViewSaveRequest).attributes["tier"]).toBe("gold");
        post.flush(savedView());
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalled();
    });

    it("a multi delete drops the row and keeps the blank trailing one (EDT-03)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, ALL_KINDS_ANSWER, ALL_KINDS_CHAIN, true, undefined, TIER_ENUM_SLICE);

        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const deletes = [...compiled.querySelectorAll<HTMLButtonElement>('[data-field="tags"] button')];
        deletes[0]?.click(); // the "a" row
        fixture.detectChanges();

        const rows = [...compiled.querySelectorAll<HTMLInputElement>('[data-field="tags"] input')];
        expect(rows.map((row) => row.value)).toEqual(["b", ""]);

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(VIEW_POST_URL);
        expect((post.request.body as ViewSaveRequest).attributes["tags"]).toEqual(["b"]);
        post.flush(savedView());
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalled();
    });

    it("an unchecked required boolean still saves — false is a value (EDT-03, EDT-07)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, ALL_KINDS_ANSWER, ALL_KINDS_CHAIN, true, undefined, TIER_ENUM_SLICE);

        // The `required` rule skips booleans on purpose (an unchecked box is a
        // value, not a gap), so clearing it must not raise the notification.
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const checkbox = compiled.querySelector<HTMLInputElement>('[data-field="retired"] input[type="checkbox"]')!;
        checkbox.click();
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-editor-notification")).toBeNull();

        const post = httpMock.expectOne(VIEW_POST_URL);
        expect((post.request.body as ViewSaveRequest).attributes["retired"]).toBe(false);
        post.flush(savedView());
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalled();
    });
});
