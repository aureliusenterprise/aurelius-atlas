/**
 * The entity editor's type field (EDT-04, DD-330): create mode's picker over the
 * shipped entity typedefs (VDE-02, MMS-07) and edit mode's static badge (MMS-09,
 * DD-721). The field moved out of the drawer at 7.47 (DD-873); these specs still
 * drive the whole {@link EntityEditor} — the drawer is what owns the route and the
 * pick, so a field-only render would prove less. The fixtures ride
 * `../editor-testing`; the test names are unchanged from the drawer spec, so the
 * trace stays put. The pick's navigation and the create seed it drives are the
 * drawer's, and stay specced there.
 */
import { TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";

import { normalize } from "../../../testing/dom";
import { ANSWER, arrive, arriveTypeDefs, setup } from "./editor-testing";

describe("EntityEditor type field (EDT-04, DD-330)", () => {
    it("edit mode renders the entity's type as a static badge, not a picker (EDT-04, DD-330)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(compiled.querySelector(".aurelius-editor-picker")).toBeNull();
        expect(normalize(compiled.querySelector(".aurelius-editor-type")?.textContent)).toBe("DataSet");
    });

    it("the static badge shows the entity's alias with the base type (EDT-04, MMS-09, DD-721)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, {
            ...ANSWER,
            attributes: { ...ANSWER.attributes, typeAlias: "Variant Set" },
        });

        // The alias wins as the name, the base type rides the suffix, and
        // the icon resolves off the raw type — the details header's shape.
        expect(normalize(compiled.querySelector(".aurelius-editor-type")?.textContent)).toBe("Variant Set (DataSet)");
    });

    it("create mode: the picker lists only the metamodel types (EDT-04, VDE-02, MMS-07)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true });
        arriveTypeDefs(fixture, httpMock);

        const select = compiled.querySelector<HTMLSelectElement>(".aurelius-editor-picker select");
        expect(select).toBeTruthy();
        const options = [...(select?.querySelectorAll("option") ?? [])].map((option) => option.textContent);
        // The placeholder row is the hidden option; the data rows are the
        // picker list, ordered by the label shown (DD-497). The rows ride the
        // entity typedef headers the icon map names (EDT-04 as scoped by
        // MMS-07), labelled by their dictionary display name (DD-379): the two
        // m4i types, not the base supertypes an author never creates.
        const dataRows = [...(select?.querySelectorAll("option") ?? [])]
            .filter((option) => !option.hasAttribute("hidden"))
            .map((option) => option.textContent);
        expect(dataRows).toEqual(["Collection", "Dataset"]);
        expect(options).not.toContain("AtlasGlossary");
        expect(options).not.toContain("DataSet");
        expect(options).not.toContain("Asset");
        expect(options).not.toContain("Referenceable");
        // The bare route (no type yet): the picker alone, no form (DD-330).
        expect(compiled.querySelector("form")).toBeNull();
    });

    it("the type pick navigates the drawer segment to the type (EDT-04, DD-330)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true });
        arriveTypeDefs(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const select = compiled.querySelector<HTMLSelectElement>(".aurelius-editor-picker select")!;
        const datasetIndex = [...select.querySelectorAll("option")].find(
            (option) => option.value !== "" && option.textContent === "Dataset",
        )!.value;
        select.value = datasetIndex;
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();

        // The type is part of the path: the pick is a navigation, and the
        // form appears only when the route arrives with the type (DD-330).
        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: ["create", "m4i_dataset"] } }]);
        expect(compiled.querySelector("form")).toBeNull();
        httpMock.verify(); // no entity read in create mode (EDT-02's edit-only)
    });

    it("the type field paints nothing before the read names a type (EDT-04, DD-330, DD-873)", () => {
        // The badge rides the stored entity's raw type; until the read answers
        // there is no entity to name, so neither a badge nor a picker shows.
        const { fixture, compiled } = setup();
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-editor-type")).toBeNull();
        expect(compiled.querySelector(".aurelius-editor-picker")).toBeNull();
    });
});
