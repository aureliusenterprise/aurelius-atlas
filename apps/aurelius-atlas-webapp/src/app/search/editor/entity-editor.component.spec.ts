/**
 * The entity editor drawer (EDT-01..EDT-08, EDT-10, DD-322, DD-325, DD-326):
 * the routed panel's own wiring. The specs ride the details screen's idiom:
 * a fake `ActivatedRoute` (paramMap + routeConfig carry the mode), the real
 * http client through HttpTestingController, and a spy on the Router. The
 * field builder and the merge are specced at their owner (form-fields);
 * here: the read (EDT-02), the picker (EDT-04), the tag box (EDT-05), the
 * save's two requests and navigation (EDT-06, DD-326), the invalid save
 * (EDT-07), the failed save (EDT-08), dismissal (EDT-01), and the footer's
 * shape (EDT-10).
 */
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter } from "@angular/router";
import Keycloak from "keycloak-js";
import { Subject } from "rxjs";

import type { AtlasEntityWithExtInfo, AtlasTypesDef } from "aurelius-atlas-data-access";

import { AlertsService } from "../../alerts/alerts.service";
import { APP_CONFIG } from "../../tokens";

import { EntityEditor } from "./entity-editor.component";

const ENTITY_URL = "/api/atlas/v2/entity/guid/";
const TYPEDEFS_URL = "/api/atlas/v2/types/typedefs";
const ENTITY_POST_URL = "/api/atlas/v2/entity";

/** The edit-mode entity: a DataSet with the Asset/Referenceable fields. */
const ANSWER: AtlasEntityWithExtInfo = {
    entity: {
        guid: "7a1b",
        typeName: "DataSet",
        attributes: {
            name: "genomic_variants",
            qualifiedName: "genomic_variants@cluster",
            description: "Curated variant calls.",
            owner: "analyst-3",
            displayName: "Genomic Variants",
        },
        relationshipAttributes: {},
        classifications: [{ typeName: "PII", entityGuid: "7a1b" }],
    },
    referredEntities: {},
};

/** The typedefs the picker, the supertype walk, and the tag box read. */
const TYPEDEFS: AtlasTypesDef = {
    entityDefs: [
        {
            name: "Referenceable",
            attributeDefs: [{ name: "qualifiedName", typeName: "string", isUnique: true, isOptional: false }],
        },
        {
            name: "Asset",
            superTypes: ["Referenceable"],
            attributeDefs: [
                { name: "name", typeName: "string", isOptional: false },
                { name: "description", typeName: "string" },
                { name: "owner", typeName: "string" },
                { name: "displayName", typeName: "string" },
            ],
        },
        { name: "DataSet", superTypes: ["Asset"], attributeDefs: [] },
        { name: "AtlasGlossary", attributeDefs: [] },
        { name: "__AtlasHauskeeping", attributeDefs: [] },
    ],
    classificationDefs: [
        { name: "PII", entityTypes: ["DataSet"] },
        { name: "CONFIDENTIAL", entityTypes: ["Asset"] },
        { name: "FINANCE", entityTypes: ["Process"] },
    ],
    enumDefs: [],
    structDefs: [],
    businessMetadataDefs: [],
    relationshipDefs: [],
};

/**
 * Bring the drawer up in edit mode at the given guid (or create mode with
 * `create: true`): the route parts arrive through the fake ActivatedRoute,
 * the first `detectChanges` lets the effects fire the reads. The drawer's
 * body appears only after the drawer component renders the panel, so
 * `arrive` flushes both reads and settles the screen.
 */
function setup({
    guid = "7a1b",
    create = false,
    createType = "",
}: { guid?: string; create?: boolean; createType?: string } = {}) {
    const paramMap = new Subject<ParamMap>();
    TestBed.configureTestingModule({
        imports: [EntityEditor],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            provideRouter([]),
            {
                provide: ActivatedRoute,
                useValue: {
                    paramMap,
                    routeConfig: { path: create ? "create/:type" : "edit/:guid" },
                },
            },
            { provide: APP_CONFIG, useValue: { atlasClientId: "aurelius-atlas-server" } },
            { provide: Keycloak, useValue: { hasResourceRole: () => true } },
        ],
    });
    const fixture = TestBed.createComponent(EntityEditor);
    if (!create) {
        paramMap.next(convertToParamMap({ guid }));
    } else if (createType !== "") {
        paramMap.next(convertToParamMap({ type: createType }));
    }
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    return { fixture, compiled, httpMock: TestBed.inject(HttpTestingController), paramMap };
}

/** Flush the typedefs read (every mode makes it) and settle. */
function arriveTypeDefs(fixture: { detectChanges: () => void }, httpMock: HttpTestingController, body = TYPEDEFS) {
    httpMock.expectOne(TYPEDEFS_URL).flush(body);
    fixture.detectChanges();
}

/** Flush both reads (edit mode) and settle the drawer. */
function arrive(fixture: { detectChanges: () => void }, httpMock: HttpTestingController, body = ANSWER) {
    arriveTypeDefs(fixture, httpMock);
    httpMock.expectOne((request) => request.url.startsWith(ENTITY_URL)).flush(body);
    fixture.detectChanges();
}

const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

describe("EntityEditor (EDT-01..EDT-08, EDT-10)", () => {
    it("fetches its own entity and the typedefs on arrival (EDT-02, EDT-04)", () => {
        const { httpMock } = setup();

        const entityRequest = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b");
        expect(entityRequest.request.method).toBe("GET");
        const typedefsRequest = httpMock.expectOne(TYPEDEFS_URL);
        expect(typedefsRequest.request.method).toBe("GET");
        typedefsRequest.flush(TYPEDEFS);
        entityRequest.flush(ANSWER);
    });

    it("alerts and keeps the empty drawer on a failed entity read (EDT-02)", () => {
        const { fixture, httpMock } = setup({ guid: "missing" });
        arriveTypeDefs(fixture, httpMock);

        httpMock.expectOne(`${ENTITY_URL}missing`).flush({}, { status: 404, statusText: "Not Found" });
        fixture.detectChanges();

        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(true);
        // The drawer stays open (EDT-02): the panel is still rendered.
        expect(fixture.nativeElement.querySelector('[role="dialog"]')).toBeTruthy();
    });

    it("renders the edit form from the supertype walk (EDT-03)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const names = [...compiled.querySelectorAll<HTMLInputElement>("input.aurelius-editor-text")].map((input) =>
            input.id.replace("editor-", ""),
        );
        // The text inputs, in the resolved order: name first, the description
        // key (a textarea) next, then the rest by name; the unique
        // qualifiedName is dropped entirely (the form never edits it).
        expect(names).toEqual(["name", "displayName", "owner"]);

        const nameField = compiled.querySelector<HTMLInputElement>("#editor-name");
        expect(nameField?.value).toBe("genomic_variants");
        expect(nameField?.required).toBe(true);
        expect(compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")?.value).toBe(
            "Curated variant calls.",
        );
        // The drawer title is the edit title (EDT-11's bridge strings).
        expect(normalize(compiled.querySelector(".aurelius-drawer-title")?.textContent)).toBe("Edit entity");
    });

    it("seeds the tag box from the entity's own classifications (EDT-05, DD-326)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const tags = [...compiled.querySelectorAll(".aurelius-editor-tag")].map((tag) => normalize(tag.textContent));
        expect(tags).toEqual(["PII"]);
    });

    it("edit mode renders the entity's type as static text, not a picker (EDT-04, DD-330)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(compiled.querySelector(".aurelius-editor-picker")).toBeNull();
        expect(normalize(compiled.querySelector(".aurelius-editor-type")?.textContent)).toBe("DataSet");
    });

    it("create mode: the picker lists the shipped types minus glossary and internals (EDT-04)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true });
        arriveTypeDefs(fixture, httpMock);

        const select = compiled.querySelector<HTMLSelectElement>(".aurelius-editor-picker select");
        expect(select).toBeTruthy();
        const options = [...(select?.querySelectorAll("option") ?? [])].map((option) => option.textContent);
        // The placeholder row is the hidden option; the data rows are the
        // picker list — DataSet/Asset/Referenceable, no AtlasGlossary, no __.
        const dataRows = [...(select?.querySelectorAll("option") ?? [])]
            .filter((option) => !option.hasAttribute("hidden"))
            .map((option) => option.textContent);
        expect(dataRows).toEqual(["Asset", "DataSet", "Referenceable"]);
        expect(options).not.toContain("AtlasGlossary");
        // The bare route (no type yet): the picker alone, no form (DD-330).
        expect(compiled.querySelector("form")).toBeNull();
    });

    it("the type pick navigates the drawer segment to the type (EDT-04, DD-330)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true });
        arriveTypeDefs(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const select = compiled.querySelector<HTMLSelectElement>(".aurelius-editor-picker select")!;
        const dataSetIndex = [...select.querySelectorAll("option")].find(
            (option) => option.value !== "" && option.textContent === "DataSet",
        )!.value;
        select.value = dataSetIndex;
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();

        // The type is part of the path: the pick is a navigation, and the
        // form appears only when the route arrives with the type (DD-330).
        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: ["create", "DataSet"] } }]);
        expect(compiled.querySelector("form")).toBeNull();
        httpMock.verify(); // no entity read in create mode (EDT-02's edit-only)
    });

    it("the route's type seeds the create form with a negative guid (EDT-04, DD-325, DD-330)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        // The picker stays above the form, selected at the route's type.
        expect(compiled.querySelector(".aurelius-editor-picker select")).toBeTruthy();
        const names = [...compiled.querySelectorAll<HTMLInputElement>("input.aurelius-editor-text")].map((input) =>
            input.id.replace("editor-", ""),
        );
        expect(names).toEqual(["name", "displayName", "owner"]);
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("");

        // Save with a name: the POST carries the negative temp guid and the
        // uuid qualifiedName (DD-325).
        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "fresh_table";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(ENTITY_POST_URL);
        expect(post.request.method).toBe("POST");
        // The body is the AtlasEntityWithExtInfo wrapper the client posts.
        const posted = (
            post.request.body as { entity: { guid: string; typeName: string; attributes: Record<string, unknown> } }
        ).entity;
        expect(Number(posted.guid)).toBeLessThan(0);
        expect(posted.typeName).toBe("DataSet");
        expect(String(posted.attributes["qualifiedName"])).toMatch(
            /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
        );
        expect(posted.attributes["name"]).toBe("fresh_table");
        post.flush({ guidAssignments: { [posted.guid]: "9999" }, createdEntityHeaders: [], updatedEntityHeaders: [] });
        fixture.detectChanges();

        // No tags chosen: the diff is empty and the save lands straight on
        // the entity's details (EDT-06, DD-326).
        httpMock.verify();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "9999"], drawer: null } }]);
    });

    it("switching the type re-seeds the form through the route (EDT-04, DD-330)", () => {
        const { fixture, compiled, httpMock, paramMap } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "half-typed";
        nameInput.dispatchEvent(new Event("input"));

        // Re-pick in the picker: the switch is a navigation to the new type.
        const select = compiled.querySelector<HTMLSelectElement>(".aurelius-editor-picker select")!;
        const refIndex = [...select.querySelectorAll("option")].find(
            (option) => option.value !== "" && option.textContent === "Referenceable",
        )!.value;
        select.value = refIndex;
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: ["create", "Referenceable"] } }]);

        // The router answers: the same component with the new type param. The
        // DataSet form is gone (Referenceable carries no rendered field —
        // qualifiedName never renders, EDT-03) and a save posts the new type.
        paramMap.next(convertToParamMap({ type: "Referenceable" }));
        fixture.detectChanges();
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")).toBeNull();

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        const post = httpMock.expectOne(ENTITY_POST_URL);
        const posted = (post.request.body as { entity: { typeName: string; guid: string } }).entity;
        expect(posted.typeName).toBe("Referenceable");
        expect(Number(posted.guid)).toBeLessThan(0); // a fresh seed, not the old temp entity
        post.flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
        httpMock.verify();
    });

    it("the tag box adds an applicable type on Enter and removes it (EDT-05)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const input = compiled.querySelector<HTMLInputElement>("input.aurelius-editor-classification-input")!;
        input.value = "CONFIDENTIAL"; // applies through the Asset supertype
        input.dispatchEvent(new Event("input"));
        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();

        const tags = () =>
            [...compiled.querySelectorAll(".aurelius-editor-tag")].map((tag) => normalize(tag.textContent));
        expect(tags()).toEqual(["PII", "CONFIDENTIAL"]);

        // A type that does not apply is ignored.
        input.value = "FINANCE";
        input.dispatchEvent(new Event("input"));
        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();
        expect(tags()).toEqual(["PII", "CONFIDENTIAL"]);

        // A type that does not apply keeps its text (the input is cleared
        // only on a real add).
        expect(input.value).toBe("FINANCE");
        input.value = "";

        // Remove the seeded tag through the chip's delete control (UIC-24).
        compiled.querySelectorAll<HTMLButtonElement>(".aurelius-classification-chip-delete").item(0).click();
        fixture.detectChanges();
        expect(tags()).toEqual(["CONFIDENTIAL"]);
    });

    it("a datalist pick commits through the change event (EDT-05, DD-329)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const input = compiled.querySelector<HTMLInputElement>("input.aurelius-editor-classification-input")!;
        // Picking a suggestion from the open popup fires `change`, not
        // `keyup.enter` — the real-browser add path Enter alone misses.
        input.value = "CONFIDENTIAL";
        input.dispatchEvent(new Event("input"));
        input.dispatchEvent(new Event("change"));
        fixture.detectChanges();

        const tags = () =>
            [...compiled.querySelectorAll(".aurelius-editor-tag")].map((tag) => normalize(tag.textContent));
        expect(tags()).toEqual(["PII", "CONFIDENTIAL"]);
        expect(input.value).toBe(""); // cleared on the add
    });

    it("save posts the merged entity; unchanged tags send nothing (EDT-06, DD-326)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "renamed_variants";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(ENTITY_POST_URL);
        expect(post.request.method).toBe("POST");
        const posted = (post.request.body as { entity: { guid: string; attributes: Record<string, unknown> } }).entity;
        expect(posted.guid).toBe("7a1b");
        expect(posted.attributes["name"]).toBe("renamed_variants");
        expect(posted.attributes["qualifiedName"]).toBe("genomic_variants@cluster"); // untouched passthrough
        expect(posted.attributes["owner"]).toBe("analyst-3");
        post.flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
        fixture.detectChanges();

        // The box still holds the seeded PII tag: the diff is empty, so no
        // classification call fires at all (DD-326 — the kept tags ride
        // nothing, which is exactly what the CLS-08 replace cannot survive).
        httpMock.verify();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "7a1b"], drawer: null } }]);
    });

    it("save POST-adds a gained tag and DELETEs a lost one (EDT-06, DD-326)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        // Gain CONFIDENTIAL and drop the seeded PII through the tag box.
        const tagInput = compiled.querySelector<HTMLInputElement>("input.aurelius-editor-classification-input")!;
        tagInput.value = "CONFIDENTIAL";
        tagInput.dispatchEvent(new Event("input"));
        tagInput.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();
        compiled.querySelectorAll<HTMLButtonElement>(".aurelius-classification-chip-delete").item(0).click(); // drop PII
        fixture.detectChanges();

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock.expectOne(ENTITY_POST_URL).flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
        fixture.detectChanges();

        // The gained tag rides one POST-add, stamped with the real guid.
        const add = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/classifications");
        expect(add.request.method).toBe("POST");
        expect(add.request.body).toEqual([
            { typeName: "CONFIDENTIAL", entityGuid: "7a1b", propagate: true, removePropagationsOnEntityDelete: true },
        ]);
        add.flush({});

        // The lost tag rides one DELETE.
        const del = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/classification/PII");
        expect(del.request.method).toBe("DELETE");
        del.flush({});
        fixture.detectChanges();

        httpMock.verify();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "7a1b"], drawer: null } }]);
    });

    it("an invalid save fires nothing and shows the errors (EDT-07)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        expect(httpMock.match((request) => request.method === "POST" || request.method === "PUT")).toHaveLength(0);
        const error = compiled.querySelector(".aurelius-editor-error");
        expect(normalize(error?.textContent)).toBe("Name is required.");
        // Bulma's is-danger paints the invalid control red (EDT-07, DD-332).
        expect(compiled.querySelector("#editor-name")?.classList.contains("is-danger")).toBe(true);
        const notification = compiled.querySelector<HTMLElement>(".aurelius-editor-notification");
        expect(normalize(notification?.textContent)).toBe(
            "This entity can't be saved because one or more required fields are missing.",
        );
        // The top of the form, not the bottom: it precedes the first field (DD-331).
        const firstField = compiled.querySelector(".aurelius-editor-form .aurelius-editor-field");
        expect(notification!.compareDocumentPosition(firstField!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

        // The delete dismisses it; the next Save brings it back (DD-331).
        notification!.querySelector<HTMLButtonElement>("button.delete")!.click();
        fixture.detectChanges();
        expect(compiled.querySelector(".aurelius-editor-notification")).toBeNull();

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        expect(compiled.querySelector(".aurelius-editor-notification")).toBeTruthy();
    });

    it("a refused save adds one alert and keeps the drawer (EDT-08)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock
            .expectOne(ENTITY_POST_URL)
            .flush(
                { errorCode: "ATLAS-403-00-001", errorMessage: "forbidden" },
                { status: 403, statusText: "Forbidden" },
            );
        fixture.detectChanges();

        expect(add).toHaveBeenCalledTimes(1);
        expect(add).toHaveBeenCalledWith({
            severity: "error",
            source: "search",
            message: "Saving the entity",
        });
        expect(navigate).not.toHaveBeenCalled();
        expect(fixture.nativeElement.querySelector('[role="dialog"]')).toBeTruthy();
        // The edits survive the refusal (EDT-08): the form still holds the entity.
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("genomic_variants");
    });

    it("the footer holds Save only (EDT-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const buttons = [
            ...compiled.querySelectorAll<HTMLButtonElement>('[role="dialog"] .aurelius-drawer-head button'),
        ];
        const labels = buttons.map((button) => normalize(button.textContent) || button.getAttribute("aria-label"));
        expect(labels).toEqual(["Save", "Close"]); // Save + the drawer's own X
        expect([...compiled.querySelectorAll("button")].some((b) => normalize(b.textContent) === "Delete")).toBe(false);
        expect([...compiled.querySelectorAll("button")].some((b) => normalize(b.textContent) === "Cancel")).toBe(false);
    });

    it("dismissal navigates the drawer outlet away (EDT-01)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>(".aurelius-drawer-head button.delete")!.click();
        fixture.detectChanges();

        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: null } }]);
    });

    it("the drawer titles are the bridge strings per mode (EDT-01, EDT-11)", () => {
        const edit = setup();
        arrive(edit.fixture, edit.httpMock);
        expect(normalize(edit.compiled.querySelector(".aurelius-drawer-title")?.textContent)).toBe("Edit entity");

        TestBed.resetTestingModule();
        const create = setup({ create: true });
        arriveTypeDefs(create.fixture, create.httpMock);
        expect(normalize(create.compiled.querySelector(".aurelius-drawer-title")?.textContent)).toBe(
            "Create new entity",
        );
    });
});
