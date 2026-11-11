/**
 * The quality rule form (EDT-25..EDT-27/29, EDT-31/32): the vocabulary-driven
 * branch of the editor drawer. The specs ride the drawer's idiom — the real
 * http client through HttpTestingController — over a test host that drives the
 * component's inputs and reads its `valid()` / `draftAttributes()` answers the
 * Save uses. The drawer's own wiring (the mode seam, the validate-before-save)
 * is specced at `entity-editor.component.spec.ts` (EDT-28/29); the service and
 * its cache at the data-access lib (EDT-30).
 */
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { Component, viewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import type { AtlasEntity, QualityKinds } from "aurelius-atlas-data-access";

import { QualityFields, QUALITY_FIELDS_RELATIONSHIP, QUALITY_TYPE_NAME, storedCheckKind } from "./quality-fields";

const KINDS_URL = "/api/aurelius/v1/quality/kinds";

/** The served vocabulary (QRE-01's shape, a subset of the engine's ten): the
 * kinds resource's own order, its sorted required/optional per kind, and the
 * engine's own dimension names (the form localizes them for display only).
 * `MYSTERY_CHECK` stands for a kind the catalogues do not name yet (EDT-31's
 * fallback). */
const KINDS: QualityKinds = {
    kinds: [
        {
            name: "COLUMN_IN_SET",
            dimension: "VALIDITY",
            required: ["column", "values"],
            optional: [],
            reason: "The column holds only the allowed values.",
        },
        {
            name: "COLUMN_NOT_NULL_RATIO",
            dimension: "COMPLETENESS",
            required: ["column"],
            optional: [],
            reason: "The column carries a value.",
        },
        {
            name: "COLUMN_TYPE_CASTABLE",
            dimension: "VALIDITY",
            required: ["column", "type"],
            optional: [],
            reason: "The column casts to the type.",
        },
        {
            name: "COLUMN_WITHIN_RANGE",
            dimension: "ACCURACY",
            required: ["column", "max", "min"],
            optional: [],
            reason: "The column stays within the range.",
        },
        {
            name: "MYSTERY_CHECK",
            dimension: "VALIDITY",
            required: [],
            optional: [],
            reason: "A kind newer than the catalogues.",
        },
        {
            name: "ROW_NOT_EMPTY",
            dimension: "COMPLETENESS",
            required: ["columns"],
            optional: ["minColumns"],
            reason: "The row carries its columns.",
        },
    ],
    castableTypes: ["date", "double", "int"],
    thresholdMin: 0,
    thresholdMax: 1,
};

/** A test host: the child with its drawer-side inputs set. */
@Component({
    imports: [QualityFields],
    template: `
        <aurelius-atlas-webapp-quality-fields
            [entity]="entity"
            mode="create"
            [loadingLabel]="loading"
        ></aurelius-atlas-webapp-quality-fields>
    `,
})
class CreateHost {
    readonly child = viewChild.required(QualityFields);
    entity: AtlasEntity | null = {
        guid: "-42",
        typeName: QUALITY_TYPE_NAME,
        attributes: { qualifiedName: "rule@cluster" },
    };
    readonly loading = "Retrieving the entity details";
}

/** The edit-mode host: an existing vocabulary rule seeds the form (EDT-29). */
@Component({
    imports: [QualityFields],
    template: `
        <aurelius-atlas-webapp-quality-fields
            [entity]="entity"
            mode="edit"
            [loadingLabel]="loading"
        ></aurelius-atlas-webapp-quality-fields>
    `,
})
class EditHost {
    readonly child = viewChild.required(QualityFields);
    entity: AtlasEntity = {
        guid: "r1",
        typeName: QUALITY_TYPE_NAME,
        attributes: {
            name: "total_not_null",
            qualifiedName: "total_not_null@cluster",
            id: 7,
            ruleDescription: "The field must carry a value.",
            dqcheckkind: "COLUMN_WITHIN_RANGE",
            dqcolumn: "total",
            dqmin: 0,
            dqmax: 100,
            // Foreign parameters the store materialized (EWR-09) and a stale
            // kind's leftovers: EDT-26's rule draws neither (DD-461 agrees).
            dqpattern: "leftover",
            dqvalues: ["stale"],
            dqtype: "int",
            active: true,
            threshold: 0.95,
        },
        relationshipAttributes: { fields: [{ guid: "f1", typeName: "m4i_field", relationshipStatus: "ACTIVE" }] },
    };
    readonly loading = "Retrieving the entity details";
}

/** Bring the child up and answer the kinds call (EDT-25's load on open). */
function arrive<T>(fixture: ComponentFixture<T>): HttpTestingController {
    const httpMock = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    const request = httpMock.match((req) => req.url === KINDS_URL)[0];
    request?.flush(KINDS);
    fixture.detectChanges();

    return httpMock;
}

/** Set a text input and fire its `input` event. */
function typeInto(fixture: ComponentFixture<unknown>, selector: string, value: string): void {
    const input = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>(selector)!;
    input.value = value;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
}

/** The kind Select's native control, and pick one row by its label. */
function pickOption(fixture: ComponentFixture<unknown>, selector: string, label: string): void {
    const compiled = fixture.nativeElement as HTMLElement;
    const select = compiled.querySelector<HTMLSelectElement>(`${selector} select`)!;
    const option = [...select.options].find((entry) => entry.textContent?.trim() === label)!;
    select.value = option.value;
    select.dispatchEvent(new Event("change"));
    fixture.detectChanges();
}

function textOf(fixture: ComponentFixture<unknown>, selector: string): string | null {
    const element = (fixture.nativeElement as HTMLElement).querySelector(selector);

    return element?.textContent?.replace(/\s+/g, " ").trim() ?? null;
}

/** The threshold slider's current position (EDT-32). */
function sliderValue(fixture: ComponentFixture<unknown>): string | undefined {
    return (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>("#editor-threshold-slider")?.value;
}

describe("QualityFields (EDT-25, EDT-26, EDT-27, EDT-29, EDT-31, EDT-32)", () => {
    function setupCreate(): {
        fixture: ComponentFixture<CreateHost>;
        host: CreateHost;
    } {
        TestBed.configureTestingModule({
            imports: [CreateHost],
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        const fixture = TestBed.createComponent(CreateHost);

        return { fixture, host: fixture.componentInstance };
    }

    it("loads the kinds on open and renders the kind Select over them (EDT-25)", () => {
        const { fixture } = setupCreate();
        const httpMock = TestBed.inject(HttpTestingController);
        fixture.detectChanges();

        // The loading line rides the drawer's text while the call is open.
        expect(textOf(fixture, ".aurelius-editor-loading")).toBe("Retrieving the entity details");
        const kindsRequest = httpMock.expectOne(KINDS_URL);

        kindsRequest.flush(KINDS);
        fixture.detectChanges();

        // The kind Select orders its rows by the EDT-31 human label, not the
        // resource's order — the raw engine name never shows (an unmapped
        // kind sorts by its raw name); the shared fields stand above (EDT-27).
        const kindOptions = [
            ...((fixture.nativeElement as HTMLElement).querySelectorAll<HTMLSelectElement>(
                ".aurelius-quality-kind select",
            )[0]?.options ?? []),
        ].map((option) => option.textContent?.trim());
        expect(kindOptions.slice(1)).toEqual([
            "Convertible type",
            "MYSTERY_CHECK", // EDT-31's fallback: a name the catalogues lack
            "Not empty",
            "Row filled",
            "Values from a set",
            "Within a range",
        ]);
        expect((fixture.nativeElement as HTMLElement).querySelector("#editor-name")).toBeTruthy();
        expect((fixture.nativeElement as HTMLElement).querySelector("#editor-ruleDescription")).toBeTruthy();
        // Before the first pick the form is the shared fields and the kind
        // Select only — no parameters (EDT-25).
        expect((fixture.nativeElement as HTMLElement).querySelectorAll(".aurelius-quality-param").length).toBe(0);
    });

    it("says so and offers nothing when the kinds fail (EDT-25)", () => {
        const { fixture } = setupCreate();
        const httpMock = TestBed.inject(HttpTestingController);
        fixture.detectChanges();

        httpMock.expectOne(KINDS_URL).flush({}, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        expect(textOf(fixture, ".aurelius-quality-kinds-failed")).toBe("The rule kinds could not be loaded.");
        expect((fixture.nativeElement as HTMLElement).querySelector(".aurelius-quality-kind")).toBeFalsy();
        expect(fixture.componentInstance.child().valid()).toBe(false);
    });

    it("draws the chosen kind's parameters only, required then optional (EDT-25, EDT-26)", () => {
        const { fixture } = setupCreate();
        arrive(fixture);

        pickOption(fixture, ".aurelius-quality-kind", "Row filled"); // ROW_NOT_EMPTY (EDT-31)

        // ROW_NOT_EMPTY: columns (required) then minColumns (optional) — the
        // other kinds' parameters never appear.
        const fields = [
            ...(fixture.nativeElement as HTMLElement).querySelectorAll<HTMLElement>(".aurelius-quality-param"),
        ];
        expect(fields.map((field) => field.getAttribute("data-field"))).toEqual(["dqcolumns", "dqminColumns"]);
        expect(fields[0]?.querySelector(".aurelius-quality-chips-box")).toBeTruthy(); // chips control
        expect(fields[1]?.querySelector("input[type='number'][step='1']")).toBeTruthy(); // whole number

        // The dimension line is the kind's own, read-only and localized
        // (EDT-25, EDT-31).
        expect(textOf(fixture, ".aurelius-quality-dimension-value")).toBe("Completeness");
        // The kind's description line sits above the dimension (EDT-31).
        expect(textOf(fixture, ".aurelius-quality-kind-description")).toBe(
            "Every row carries all of the chosen columns.",
        );
    });

    it("the type parameter rides a Select over the castable types (EDT-26)", () => {
        const { fixture, host } = setupCreate();
        arrive(fixture);

        pickOption(fixture, ".aurelius-quality-kind", "Convertible type");
        pickOption(fixture, ".aurelius-quality-param[data-field='dqtype']", "double");
        typeInto(fixture, "#editor-dqcolumn", "price");
        typeInto(fixture, "#editor-name", "price_is_int");

        expect(host.child().draftAttributes()).toMatchObject({
            dqcheckkind: "COLUMN_TYPE_CASTABLE",
            dqcolumn: "price",
            dqtype: "double",
        });
    });

    it("a chips box commits typed values on Enter and drops them on delete (EDT-26)", () => {
        const { fixture, host } = setupCreate();
        arrive(fixture);
        pickOption(fixture, ".aurelius-quality-kind", "Values from a set");
        typeInto(fixture, "#editor-name", "status_in_set");
        typeInto(fixture, "#editor-dqcolumn", "status");

        const box = () => (fixture.nativeElement as HTMLElement).querySelector(".aurelius-quality-chips-box")!;
        const chipLabels = () =>
            [...(fixture.nativeElement as HTMLElement).querySelectorAll(".aurelius-quality-chip")].map((chip) =>
                chip.textContent?.trim(),
            );

        // Enter commits the trimmed value; a duplicate of a held chip adds
        // nothing (the classification box's rule, DD-335).
        typeInto(fixture, ".aurelius-quality-chips-input", " open ");
        (fixture.nativeElement as HTMLElement)
            .querySelector<HTMLInputElement>(".aurelius-quality-chips-input")!
            .dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();
        expect(chipLabels()).toEqual(["open"]);

        typeInto(fixture, ".aurelius-quality-chips-input", "open");
        (fixture.nativeElement as HTMLElement)
            .querySelector<HTMLInputElement>(".aurelius-quality-chips-input")!
            .dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();
        expect(chipLabels()).toEqual(["open"]);

        typeInto(fixture, ".aurelius-quality-chips-input", "closed");
        (fixture.nativeElement as HTMLElement)
            .querySelector<HTMLInputElement>(".aurelius-quality-chips-input")!
            .dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();
        expect(chipLabels()).toEqual(["open", "closed"]);
        expect(box()).toBeTruthy();

        // Delete drops the chip; the body carries the list that is left.
        (fixture.nativeElement as HTMLElement)
            .querySelector<HTMLButtonElement>(".aurelius-quality-chip button")!
            .click();
        fixture.detectChanges();
        expect(chipLabels()).toEqual(["closed"]);
        expect(host.child().draftAttributes()).toMatchObject({ dqvalues: ["closed"] });
    });

    it("a kind switch clears the old kind's parameters (EDT-26)", () => {
        const { fixture, host } = setupCreate();
        arrive(fixture);

        pickOption(fixture, ".aurelius-quality-kind", "Within a range");
        typeInto(fixture, "#editor-dqcolumn", "total");
        typeInto(fixture, "#editor-dqmin", "0");
        typeInto(fixture, "#editor-dqmax", "100");
        typeInto(fixture, "#editor-name", "total_range");

        pickOption(fixture, ".aurelius-quality-kind", "Not empty");

        // The range controls are gone and their values with them (EDT-26's
        // clear): the draft names only the new kind's `dq` parameter.
        expect((fixture.nativeElement as HTMLElement).querySelector("#editor-dqmin")).toBeFalsy();
        expect(host.child().draftAttributes()).toEqual({
            name: "total_range",
            id: -1,
            active: true,
            threshold: 1.0,
            dqcheckkind: "COLUMN_NOT_NULL_RATIO",
            qualifiedName: "rule@cluster",
        });
    });

    it("the save body names only the kind's parameters (EDT-26, EDT-27)", () => {
        const { fixture, host } = setupCreate();
        arrive(fixture);
        pickOption(fixture, ".aurelius-quality-kind", "Not empty");
        typeInto(fixture, "#editor-name", "total_not_null");
        typeInto(fixture, "#editor-ruleDescription", "The field must carry a value.");
        typeInto(fixture, "#editor-dqcolumn", "total");
        typeInto(fixture, "#editor-threshold", "90");

        // The full minimal body (EDT-27): the shared fields, active,
        // threshold, the kind, and its one parameter. `qualifiedName` and
        // `id` ride the seeded entity because a full update demands them
        // (EVL-02); create seeds id -1 like the legacy editor.
        expect(host.child().draftAttributes()).toEqual({
            name: "total_not_null",
            ruleDescription: "The field must carry a value.",
            id: -1,
            qualifiedName: "rule@cluster",
            active: true,
            threshold: 0.9,
            dqcheckkind: "COLUMN_NOT_NULL_RATIO",
            dqcolumn: "total",
        });
        // No `dq` attribute the kind does not name: none of the other nine.
        const stored = Object.keys(host.child().draftAttributes()).filter((key) => key.startsWith("dq"));
        expect(stored).toEqual(["dqcheckkind", "dqcolumn"]);
    });

    it("an empty threshold means the engine's default and stores as 1.0 (EDT-27)", () => {
        const { fixture, host } = setupCreate();
        arrive(fixture);

        // EDT-27: the control is empty; the body carries 1.0 because the
        // store materializes an omitted optional double to 0.0 (EWR-09) and
        // that 0.0 would win the next read.
        typeInto(fixture, "#editor-name", "any_rule");
        pickOption(fixture, ".aurelius-quality-kind", "Not empty");
        typeInto(fixture, "#editor-dqcolumn", "total");

        expect(host.child().draftAttributes()["threshold"]).toBe(1.0);
        // EDT-32: the empty threshold rests the slider at the engine's 1.0,
        // and the percentage box names that default rather than sitting empty.
        expect(sliderValue(fixture)).toBe("1");
        expect((fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>("#editor-threshold")?.value).toBe(
            "100",
        );
    });

    it("a slider move fills the percent box and a typed percent moves the slider (EDT-32)", () => {
        const { fixture, host } = setupCreate();
        arrive(fixture);

        // The pair side by side (DD-494): both ride the served bounds.
        const slider = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>(
            "#editor-threshold-slider",
        )!;
        const box = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>("#editor-threshold")!;
        expect(slider.getAttribute("min")).toBe("0");
        expect(slider.getAttribute("max")).toBe("1");

        // Dragging the slider fills the box with the same threshold, as a
        // percentage (one value, both move; the stored value stays the ratio).
        slider.value = "0.75";
        slider.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        expect(box.value).toBe("75");

        // Typing a percentage moves the slider and stores the ratio.
        typeInto(fixture, "#editor-threshold", "90");
        expect(sliderValue(fixture)).toBe("0.9");
        expect(host.child().draftAttributes()["threshold"]).toBe(0.9);

        // A percentage outside the served bounds stores the nearer bound
        // (the pair's shared clamp), and leaving the field shows it.
        typeInto(fixture, "#editor-threshold", "150");
        expect(host.child().draftAttributes()["threshold"]).toBe(1);
        typeInto(fixture, "#editor-threshold", "-5");
        expect(host.child().draftAttributes()["threshold"]).toBe(0);
        box.dispatchEvent(new Event("blur"));
        fixture.detectChanges();
        expect(box.value).toBe("0");
    });

    it("active defaults checked on create and seeds from the entity on edit (EDT-27, EDT-29)", () => {
        const { fixture } = setupCreate();
        arrive(fixture);

        expect(
            (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>(".aurelius-quality-active input")
                ?.checked,
        ).toBe(true);
    });

    it("an existing rule seeds its kind, parameters, active, and threshold (EDT-29)", () => {
        TestBed.configureTestingModule({
            imports: [EditHost],
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        const fixture = TestBed.createComponent(EditHost);
        arrive(fixture);

        const compiled = fixture.nativeElement as HTMLElement;
        // The kind seeds: its parameter controls and its own dimension line
        // render (the Select's chosen row reads the same signal), localized
        // (EDT-31).
        expect(textOf(fixture, ".aurelius-quality-dimension-value")).toBe("Accuracy");
        expect(textOf(fixture, ".aurelius-quality-kind-description")).toBe(
            "Every value sits between the minimum and the maximum.",
        );
        // The kind's parameters seed under the EDT-26 controls; the foreign
        // stored attributes draw no control (EDT-26) and ride no draft.
        expect(compiled.querySelectorAll(".aurelius-quality-param").length).toBe(3);
        expect(compiled.querySelector<HTMLInputElement>("#editor-dqcolumn")?.value).toBe("total");
        expect(compiled.querySelector<HTMLInputElement>("#editor-dqmin")?.value).toBe("0");
        expect(compiled.querySelector<HTMLInputElement>("#editor-dqmax")?.value).toBe("100");
        expect(compiled.querySelector("#editor-dqpattern")).toBeFalsy();
        expect(compiled.querySelector("#editor-dqvalues")).toBeFalsy();
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("total_not_null");
        expect(compiled.querySelector<HTMLInputElement>("#editor-ruleDescription")?.value).toBe(
            "The field must carry a value.",
        );
        expect(compiled.querySelector<HTMLInputElement>("#editor-threshold")?.value).toBe("95");
        expect(compiled.querySelector<HTMLInputElement>(".aurelius-quality-active input")?.checked).toBe(true);
    });

    it("a seeded rule's draft carries the stored id and drops foreign parameters (EDT-26, EDT-29)", () => {
        TestBed.configureTestingModule({
            imports: [EditHost],
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        const fixture = TestBed.createComponent(EditHost);
        arrive(fixture);

        const draft = fixture.componentInstance.child().draftAttributes();
        expect(draft).toMatchObject({
            name: "total_not_null",
            id: 7,
            qualifiedName: "total_not_null@cluster",
            dqcheckkind: "COLUMN_WITHIN_RANGE",
            dqcolumn: "total",
            dqmin: 0,
            dqmax: 100,
            threshold: 0.95,
        });
        // The store's materialized foreign parameters (dqpattern, dqvalues,
        // dqtype) never ride the draft (EDT-27's body rule).
        expect(Object.keys(draft)).not.toContain("dqpattern");
        expect(Object.keys(draft)).not.toContain("dqvalues");
        expect(Object.keys(draft)).not.toContain("dqtype");
    });

    it("valid needs a name, a kind, and the kind's required parameters (EDT-07 in quality mode)", () => {
        const { fixture, host } = setupCreate();
        arrive(fixture);
        const child = host.child();

        expect(child.valid()).toBe(false); // nothing yet
        typeInto(fixture, "#editor-name", "total_range");
        expect(child.valid()).toBe(false); // no kind
        pickOption(fixture, ".aurelius-quality-kind", "Within a range");
        expect(child.valid()).toBe(false); // kind, no required parameters
        typeInto(fixture, "#editor-dqcolumn", "total");
        typeInto(fixture, "#editor-dqmax", "100");
        expect(child.valid()).toBe(false); // dqmin still empty
        typeInto(fixture, "#editor-dqmin", "0");
        expect(child.valid()).toBe(true);
    });

    it("a kind the catalogues do not name shows its raw name and no line (EDT-31)", () => {
        const { fixture } = setupCreate();
        arrive(fixture);

        pickOption(fixture, ".aurelius-quality-kind", "MYSTERY_CHECK");

        // The fallback state (DD-493's consequence): the raw name stands, no
        // description line shows, and the dimension still localizes.
        expect((fixture.nativeElement as HTMLElement).querySelector(".aurelius-quality-kind-description")).toBeFalsy();
        expect(textOf(fixture, ".aurelius-quality-dimension-value")).toBe("Validity");
        // The stored value keeps the engine's name (the draft, not the label).
        expect(fixture.componentInstance.child().draftAttributes()["dqcheckkind"]).toBe("MYSTERY_CHECK");
    });

    it("the notification shows the engine line ahead of a save attempt, and hides on edit (EDT-28's display half)", () => {
        const { fixture, host } = setupCreate();
        arrive(fixture);
        const child = host.child();

        child.showEngineReason("The rule needs a column.");
        fixture.detectChanges();
        expect(textOf(fixture, ".aurelius-editor-notification")).toBe("The rule needs a column.");

        // Any edit clears the line (EDT-28: "a later edit clears the line").
        typeInto(fixture, "#editor-name", "total");
        expect((fixture.nativeElement as HTMLElement).querySelector(".aurelius-editor-notification")).toBeFalsy();

        // A transport failure answers the generic line (EDT-28).
        child.showTransportFailure();
        fixture.detectChanges();
        expect(textOf(fixture, ".aurelius-editor-notification")).toBe(
            "The rule could not be checked against the server. Try again.",
        );
    });
});

describe("storedCheckKind + the type/relationship constants (EDT-25/29's seam)", () => {
    it("reads a vocabulary kind off the entity and nothing else", () => {
        expect(
            storedCheckKind({
                guid: "r1",
                typeName: QUALITY_TYPE_NAME,
                attributes: { dqcheckkind: "ROW_NOT_EMPTY" },
            }),
        ).toBe("ROW_NOT_EMPTY");
        expect(storedCheckKind({ guid: "r1", typeName: QUALITY_TYPE_NAME, attributes: {} })).toBe("");
        expect(storedCheckKind(null)).toBe("");
        expect(QUALITY_TYPE_NAME).toBe("m4i_data_quality");
        expect(QUALITY_FIELDS_RELATIONSHIP).toBe("fields");
    });
});
