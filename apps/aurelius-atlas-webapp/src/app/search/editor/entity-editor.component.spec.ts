/**
 * The entity editor drawer (EDT-01..EDT-08, EDT-10, DD-322, DD-325, DD-326):
 * the routed panel's own wiring. The specs ride the details screen's idiom:
 * a fake `ActivatedRoute` (paramMap + snapshot data carry the mode, DD-355), the real
 * http client through HttpTestingController, and a spy on the Router. The
 * field builder and the merge are specced at their owner (form-fields);
 * here: the read (EDT-02), the picker (EDT-04), the tag box (EDT-05), the
 * save's two requests and navigation (EDT-06, DD-326), the invalid save
 * (EDT-07), the failed save (EDT-08), dismissal (EDT-01), and the commit
 * foot (EDT-10 amended by EDT-19, DD-347 — Delete + Save in the foot, the
 * hold mechanic specced at the directive).
 */
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, RouterOutlet, convertToParamMap, provideRouter } from "@angular/router";
import { By } from "@angular/platform-browser";
import Keycloak from "keycloak-js";
import { Subject, of } from "rxjs";

import { Holdable } from "aurelius-atlas-ui";

import type { AtlasEntityWithExtInfo, AtlasTypesDef } from "aurelius-atlas-data-access";

import { AlertsService } from "../../alerts/alerts.service";
import { APP_CONFIG } from "../../tokens";
import { createEntityMatcher } from "../../routes";

import { EntityEditor } from "./entity-editor.component";

/** The test host for the routed-drawer specs that need a real router: the
 * `drawer` aux outlet, the way `app.component.html` carries it (DD-355). */
@Component({
    selector: "aurelius-atlas-webapp-drawer-test-host",
    imports: [RouterOutlet],
    template: `<router-outlet name="drawer" />`,
})
class DrawerTestHost {}

const ENTITY_URL = "/api/atlas/v2/entity/guid/";
const TYPEDEFS_URL = "/api/atlas/v2/types/typedefs";
const ENTITY_POST_URL = "/api/atlas/v2/entity";
const VALIDATE_URL = "/validate-entity/";

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

/** The edit-mode entity for the relationship pickers (EDT-13..EDT-17): one
 * ACTIVE edge, one DELETED tombstone, a stale `attributes` mirror of the
 * relationship key (the server's compactAttributes copy, DD-340), and an
 * empty SINGLE slot. */
const RA_ANSWER: AtlasEntityWithExtInfo = {
    entity: {
        guid: "7a1b",
        typeName: "DataSet",
        attributes: {
            name: "genomic_variants",
            qualifiedName: "genomic_variants@cluster",
            owner: "analyst-3",
            inputToProcesses: [{ guid: "p1", typeName: "Process" }],
        },
        relationshipAttributes: {
            inputToProcesses: [
                { guid: "p1", typeName: "Process", displayText: "load_events", relationshipStatus: "ACTIVE" },
                { guid: "p9", typeName: "Process", relationshipStatus: "DELETED" },
            ],
            model: null,
        },
        classifications: [],
    },
    referredEntities: {},
};

/** The typedefs with the derived relationship attributes (EDT-13): the
 * server mounts these on the defs from the shipped relationship types. */
function raTypeDefs(modelRequired = false): AtlasTypesDef {
    return {
        ...TYPEDEFS,
        entityDefs: TYPEDEFS.entityDefs!.map((def) =>
            def.name === "DataSet"
                ? {
                      ...def,
                      relationshipAttributeDefs: [
                          {
                              name: "inputToProcesses",
                              typeName: "array<Process>",
                              cardinality: "SET",
                              relationshipTypeName: "dataset_process_inputs",
                          },
                          { name: "model", typeName: "Process", isOptional: !modelRequired },
                      ],
                  }
                : def,
        ),
    };
}

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
    atlasWrite = true,
    query = {},
}: {
    guid?: string;
    create?: boolean;
    createType?: string;
    atlasWrite?: boolean;
    query?: Record<string, string>;
} = {}) {
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
                    queryParamMap: of(convertToParamMap(query)),
                    snapshot: { data: { editorMode: create ? "create" : "edit" } },
                },
            },
            { provide: APP_CONFIG, useValue: { atlasClientId: "aurelius-atlas-server" } },
            { provide: Keycloak, useValue: { hasResourceRole: () => atlasWrite } },
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

/** One governance item of the deployed 8.3 mock document (VE-02, DV-67). */
function govItem(key: string, result: string, compliant: "0" | "1") {
    return {
        result: { raw: result },
        dataqualitytype: { raw: "attribute" },
        usedattributes: { raw: [key] },
        name: { raw: `Attribute - ${key}` },
        compliant: { raw: compliant },
        _meta: { engine: "atlas-dev-gov-quality", score: 1, id: `doc-${key}` },
        id: { raw: `doc-${key}` },
    };
}

/** The deployed mock's four cards (EDT-21/EDT-24, VE-02): the drawer renders
 * the two whose keys name one of its controls (name, definition/description). */
const VALIDATION = {
    dataEntity: { items: [govItem("dataEntity", "This entity is missing a dataEntity", "0")], isNonCompliant: true },
    definition: { items: [govItem("definition", "This entity has a definition", "1")], isNonCompliant: false },
    domainLead: { items: [govItem("domainLead", "This entity is missing a domainLead", "0")], isNonCompliant: true },
    name: { items: [govItem("name", "This entity has a name", "1")], isNonCompliant: false },
};

/** Answer every validate-entity call in flight (EDT-23): the open round fires
 * as soon as the form is visible, so the helpers settle it like any other
 * read. With no call pending it matches nothing (bare create, the failed
 * read), so the helpers stay honest about the request's absence. */
function flushValidation(httpMock: HttpTestingController, body = VALIDATION): void {
    for (const request of httpMock.match((req) => req.url === VALIDATE_URL)) {
        request.flush(body);
    }
}

/** Flush the typedefs read (every mode makes it) and settle. */
function arriveTypeDefs(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    body = TYPEDEFS,
    validate = true,
) {
    httpMock.expectOne(TYPEDEFS_URL).flush(body);
    fixture.detectChanges();
    if (validate) {
        flushValidation(httpMock);
        fixture.detectChanges();
    }
}

/** Flush both reads (edit mode) and settle the drawer. */
function arrive(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    body = ANSWER,
    typedefs = TYPEDEFS,
    validate = true,
) {
    arriveTypeDefs(fixture, httpMock, typedefs, validate);
    httpMock.expectOne((request) => request.url.startsWith(ENTITY_URL)).flush(body);
    fixture.detectChanges();
    if (validate) {
        flushValidation(httpMock);
        fixture.detectChanges();
    }
}

const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

/**
 * The Delete button's hold directive instance, so a spec can fire `held`
 * the way the pointer sweep would (the hold timing itself is specced at the
 * directive, not re-tested here).
 */
function holdDirective(fixture: ComponentFixture<EntityEditor>): Holdable {
    return fixture.debugElement.query(By.directive(Holdable)).injector.get(Holdable);
}

describe("EntityEditor (EDT-01..EDT-08, EDT-10, EDT-19)", () => {
    it("fetches its own entity and the typedefs on arrival (EDT-02, EDT-04)", () => {
        const { fixture, httpMock } = setup();

        const entityRequest = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b");
        expect(entityRequest.request.method).toBe("GET");
        const typedefsRequest = httpMock.expectOne(TYPEDEFS_URL);
        expect(typedefsRequest.request.method).toBe("GET");
        typedefsRequest.flush(TYPEDEFS);
        entityRequest.flush(ANSWER);
        fixture.detectChanges();
        flushValidation(httpMock); // the open round the visible form fires (EDT-23)
    });

    it("alerts and keeps the empty drawer on a failed entity read (EDT-02)", () => {
        const { fixture, httpMock } = setup({ guid: "missing" });
        arriveTypeDefs(fixture, httpMock);

        httpMock.expectOne(`${ENTITY_URL}missing`).flush({}, { status: 404, statusText: "Not Found" });
        fixture.detectChanges();

        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(true);
        // The drawer stays open (EDT-02): the panel is still rendered.
        expect(fixture.nativeElement.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
    });

    it("renders the edit form from the supertype walk (EDT-03)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const names = [...compiled.querySelectorAll<HTMLInputElement>("input.aurelius-editor-text")].map((input) =>
            input.id.replace("editor-", ""),
        );
        // The text inputs, in the resolved order: name first, then the rest
        // by name; the description key rides the markdown field now (EDT-20)
        // and the unique qualifiedName is dropped entirely (the form never
        // edits it).
        expect(names).toEqual(["name", "displayName", "owner"]);

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
        const tabs = [...compiled.querySelectorAll<HTMLElement>('[role="tab"]')];
        expect(tabs.map((tab) => normalize(tab.textContent))).toEqual(["Write", "Preview"]);
        expect(tabs[0]?.getAttribute("aria-selected")).toBe("true");

        // The label still reaches the textarea through the component's seat
        // (EDT-11's for="editor-<name>", UIC-26's textareaId).
        const label = compiled.querySelector('label[for="editor-description"]');
        expect(label).toBeTruthy();
        expect(compiled.querySelector("textarea#editor-description")).toBeTruthy();

        // Typing rides the source string; the save sends it unchanged (EDT-06
        // untouched — no transform between read and body).
        const area = compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")!;
        area.value = "# Headings stay source";
        area.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(ENTITY_POST_URL);
        const posted = (post.request.body as { entity: { attributes: Record<string, unknown> } }).entity;
        expect(posted.attributes["description"]).toBe("# Headings stay source");
        post.flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalled();
    });

    it("seeds the tag box from the entity's own classifications (EDT-05, DD-326)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const tags = [...compiled.querySelectorAll(".aurelius-editor-tag")].map((tag) => normalize(tag.textContent));
        // The chip carries the dictionary display name (EDT-05, DD-379).
        expect(tags).toEqual(["Has PII"]);
    });

    it("renders a picker per relationship attribute, in order, seeded ACTIVE-only (EDT-13, EDT-15)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raTypeDefs());

        const blocks = [...compiled.querySelectorAll<HTMLElement>(".aurelius-editor-relationship")];
        expect(blocks.map((block) => block.dataset["field"])).toEqual(["inputToProcesses", "model"]);
        expect(normalize(blocks[0].querySelector("p.label")?.textContent)).toBe("inputToProcesses (Process)");
        // The mandatory flag marks the label (EDT-13); the optional one does not.
        expect(blocks[1].querySelector("p.label .has-text-danger")).toBeNull();

        // The chips: the ACTIVE edge only — the DELETED tombstone never seeds
        // (EDT-15) — and the lead is the entity's own typeName (DD-341).
        const chips = [...blocks[0].querySelectorAll("aurelius-atlas-ui-classification-chip")];
        expect(chips).toHaveLength(1);
        expect(normalize(chips[0].querySelector(".tag")?.textContent)).toBe("Process");
        expect(normalize(chips[0].querySelectorAll(".tag").item(1)?.textContent)).toBe("load_events");
        expect(blocks[1].querySelector("aurelius-atlas-ui-classification-chip")).toBeNull();

        // The pickers sit after the plain fields and before the box (EDT-13).
        const owner = compiled.querySelector("#editor-owner")!;
        const box = compiled.querySelector(".aurelius-editor-classification-box")!;
        expect(owner.compareDocumentPosition(blocks[0]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
        expect(blocks[0].compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it("a typed search and a mousedown pick add a chip (EDT-14)", () => {
        vi.useFakeTimers();
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raTypeDefs());

        const input = compiled.querySelector<HTMLInputElement>(
            '[data-field="inputToProcesses"] .aurelius-relationship-input',
        )!;
        input.dispatchEvent(new Event("focusin", { bubbles: true }));
        input.value = "load";
        input.dispatchEvent(new Event("input"));
        vi.advanceTimersByTime(250);
        httpMock
            .expectOne((request) => request.url === "/api/atlas/v2/search/attribute")
            .flush({ entities: [{ guid: "p2", typeName: "Process", displayText: "load_orders" }] });
        fixture.detectChanges();

        compiled
            .querySelector<HTMLButtonElement>('[data-field="inputToProcesses"] [role="option"]')!
            .dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
        fixture.detectChanges();

        const chips = [
            ...compiled.querySelectorAll('[data-field="inputToProcesses"] aurelius-atlas-ui-classification-chip'),
        ];
        expect(chips.map((chip) => normalize(chip.querySelectorAll(".tag").item(1)?.textContent))).toEqual([
            "load_events",
            "load_orders",
        ]);

        // The chip's delete drops it back (EDT-14/UIC-24).
        chips[1].querySelector<HTMLButtonElement>(".aurelius-classification-chip-delete")!.click();
        fixture.detectChanges();
        expect(
            compiled.querySelectorAll('[data-field="inputToProcesses"] aurelius-atlas-ui-classification-chip'),
        ).toHaveLength(1);
        vi.useRealTimers();
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

    it("keeps the same drawer across the first type pick (EDT-04, DD-330, DD-355)", async () => {
        // The symptom this pins: the drawer replayed its slide-in when the
        // first type arrived, because `create` and `create/:type` were two
        // configs and the router rebuilt the component across them. This
        // drives a real navigation (the fake-ActivatedRoute specs above
        // cannot see the router's own reuse decision). The route table
        // here is the shape DD-355 settled on: one matcher config, the
        // mode in its data. routes.spec pins that the production table
        // matches this shape.
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            imports: [DrawerTestHost, EntityEditor],
            providers: [
                provideHttpClient(),
                provideHttpClientTesting(),
                provideRouter([
                    {
                        matcher: createEntityMatcher,
                        outlet: "drawer",
                        data: { editorMode: "create" },
                        loadComponent: () => Promise.resolve(EntityEditor),
                    },
                ]),
                { provide: APP_CONFIG, useValue: { atlasClientId: "aurelius-atlas-server" } },
                { provide: Keycloak, useValue: { hasResourceRole: () => true } },
            ],
        });

        const fixture = TestBed.createComponent(DrawerTestHost);
        const compiled = fixture.nativeElement as HTMLElement;
        const router = TestBed.inject(Router);
        const http = TestBed.inject(HttpTestingController);

        fixture.detectChanges();
        await router.navigate([{ outlets: { drawer: ["create"] } }]);
        await fixture.whenStable(); // the loadComponent promise and the route activation
        fixture.detectChanges();
        http.expectOne(TYPEDEFS_URL).flush(TYPEDEFS);
        fixture.detectChanges();

        // The bare create route: the picker alone, no form (DD-330).
        expect(compiled.querySelector("form")).toBeNull();
        const panel = compiled.querySelector(".aurelius-drawer-panel");
        expect(panel).toBeTruthy();

        // The first pick, through the router — the typed segment arrives.
        await router.navigate([{ outlets: { drawer: ["create", "DataSet"] } }]);
        await fixture.whenStable();
        fixture.detectChanges();

        // The same panel element survived (a rebuild would be a new node,
        // and the drawer would replay its slide-in), now showing the form.
        expect(compiled.querySelector(".aurelius-drawer-panel")).toBe(panel);
        expect(compiled.querySelector("form")).toBeTruthy();
        flushValidation(http); // the open round the visible form fires (EDT-23)
        http.verify();
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
        // The chips carry the dictionary display names (EDT-05, DD-379);
        // CONFIDENTIAL is outside the dictionary and stays raw.
        expect(tags()).toEqual(["Has PII", "CONFIDENTIAL"]);

        // A type that does not apply is ignored.
        input.value = "FINANCE";
        input.dispatchEvent(new Event("input"));
        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        fixture.detectChanges();
        expect(tags()).toEqual(["Has PII", "CONFIDENTIAL"]);

        // A type that does not apply keeps its text (the input is cleared
        // only on a real add).
        expect(input.value).toBe("FINANCE");
        input.value = "";

        // Remove the seeded tag through the chip's delete control (UIC-24).
        compiled.querySelectorAll<HTMLButtonElement>(".aurelius-classification-chip-delete").item(0).click();
        fixture.detectChanges();
        expect(tags()).toEqual(["CONFIDENTIAL"]);
    });

    it("the suggestion panel filters on typing and a pick adds the tag (EDT-05, DD-335)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const input = compiled.querySelector<HTMLInputElement>("input.aurelius-editor-classification-input")!;
        const items = () =>
            [...compiled.querySelectorAll<HTMLButtonElement>(".aurelius-editor-classification-box .dropdown-item")].map(
                (item) => normalize(item.textContent),
            );

        // Focus with no text lists the applicable types (PII already chosen,
        // so only CONFIDENTIAL applies; FINANCE never does).
        input.dispatchEvent(new Event("focusin", { bubbles: true }));
        fixture.detectChanges();
        expect(items()).toEqual(["CONFIDENTIAL"]);

        // The chosen tag does not reappear as a suggestion; a pick through
        // the panel's mousedown adds it and clears the input (DD-335 — the
        // pointer commits before blur, the path the datalist took before).
        const item = compiled.querySelector<HTMLButtonElement>(".aurelius-editor-classification-box .dropdown-item")!;
        item.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
        fixture.detectChanges();
        const tags = () =>
            [...compiled.querySelectorAll(".aurelius-editor-tag")].map((tag) => normalize(tag.textContent));
        expect(tags()).toEqual(["Has PII", "CONFIDENTIAL"]);

        // Escape inside the box hides the panel, not the drawer (DD-335).
        input.dispatchEvent(new Event("focusin", { bubbles: true }));
        fixture.detectChanges();
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        fixture.detectChanges();
        expect(compiled.querySelector(".aurelius-editor-classification-box .dropdown-item")).toBeNull();
        expect(compiled.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
    });

    it("the panel filters to the typed text (EDT-05, DD-335)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const input = compiled.querySelector<HTMLInputElement>("input.aurelius-editor-classification-input")!;
        input.value = "conf"; // matches CONFIDENTIAL, not PII
        input.dispatchEvent(new Event("input"));
        input.dispatchEvent(new Event("focusin", { bubbles: true }));
        fixture.detectChanges();

        const items = [
            ...compiled.querySelectorAll<HTMLButtonElement>(".aurelius-editor-classification-box .dropdown-item"),
        ];
        expect(items.map((item) => normalize(item.textContent))).toEqual(["CONFIDENTIAL"]);
    });

    it("the input is a labelled combobox pointing at the active option (EDT-05, DD-336)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock);

        const input = compiled.querySelector<HTMLInputElement>("#editor-classification-input")!;
        expect(input.getAttribute("role")).toBe("combobox");
        expect(input.getAttribute("aria-autocomplete")).toBe("list");
        // The label names it (no unlabeled-field ambiguity for a reader).
        const label = compiled.querySelector<HTMLElement>("#editor-classifications-label")!;
        expect(input.getAttribute("aria-labelledby")).toBe(label.id);
        // With nothing typed the panel is shut, so no activedescendant yet.
        expect(input.getAttribute("aria-expanded")).toBe("false");

        input.dispatchEvent(new Event("focusin", { bubbles: true }));
        fixture.detectChanges();
        // PII and CONFIDENTIAL apply to DataSet; Down moves the active row.
        expect(input.getAttribute("aria-expanded")).toBe("true");
        expect(input.getAttribute("aria-controls")).toBe("editor-classification-listbox");
        expect(input.getAttribute("aria-activedescendant")).toBe("editor-classification-option-0");
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
        fixture.detectChanges();
        expect(input.getAttribute("aria-activedescendant")).toBe("editor-classification-option-1");
    });

    it("Enter commits the keyboard-active option (EDT-05, DD-336)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock);

        const input = compiled.querySelector<HTMLInputElement>("#editor-classification-input")!;
        input.dispatchEvent(new Event("focusin", { bubbles: true }));
        fixture.detectChanges();
        // Down lands on the second row (CONFIDENTIAL); Enter adds it.
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
        fixture.detectChanges();
        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));
        fixture.detectChanges();

        const tags = [...compiled.querySelectorAll(".aurelius-editor-tag")].map((tag) => normalize(tag.textContent));
        expect(tags).toEqual(["CONFIDENTIAL"]);
    });

    it("a type with nothing applicable disables the box and says so (EDT-05, DD-336)", () => {
        // Referenceable has no applicable classification among the defs.
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "Referenceable" });
        arriveTypeDefs(fixture, httpMock);

        expect(compiled.querySelector(".aurelius-editor-classification-box.is-disabled")).toBeTruthy();
        expect(compiled.querySelector<HTMLInputElement>("#editor-classification-input")!.disabled).toBe(true);
        expect(compiled.querySelector(".aurelius-editor-no-classifications")).toBeTruthy();
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

    it("save posts the pickers' full value and drops the attributes mirror (EDT-16, DD-340)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raTypeDefs());
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(ENTITY_POST_URL);
        const posted = post.request.body as {
            entity: {
                attributes: Record<string, unknown>;
                relationshipAttributes: Record<string, unknown>;
            };
        };
        // The rendered keys carry their full value: the ACTIVE entry list (the
        // DELETED tombstone never echoes) and null for the empty SINGLE slot.
        expect(posted.entity.relationshipAttributes["inputToProcesses"]).toEqual([
            {
                guid: "p1",
                typeName: "Process",
                displayText: "load_events",
                relationshipType: "dataset_process_inputs",
                relationshipStatus: "ACTIVE",
            },
        ]);
        expect(posted.entity.relationshipAttributes["model"]).toBeNull();
        // The picker owns its key: the stale `attributes` mirror is gone and
        // the untouched attributes pass through (DD-340's re-attach rule).
        expect(posted.entity.attributes["inputToProcesses"]).toBeUndefined();
        expect(posted.entity.attributes["qualifiedName"]).toBe("genomic_variants@cluster");
        post.flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
        fixture.detectChanges();

        httpMock.verify();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "7a1b"], drawer: null } }]);
    });

    it("an empty mandatory relationship picker blocks the save (EDT-17)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raTypeDefs(true));

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        expect(httpMock.match((request) => request.method === "POST" || request.method === "PUT")).toHaveLength(0);
        const block = compiled.querySelector<HTMLElement>('[data-field="model"]')!;
        expect(normalize(block.querySelector("p.label")?.textContent)).toBe("model (Process) *");
        expect(normalize(block.querySelector(".aurelius-editor-error")?.textContent)).toBe("Name is required.");
        expect(block.querySelector(".aurelius-relationship-box")?.classList.contains("is-danger")).toBe(true);
        expect(normalize(compiled.querySelector(".aurelius-editor-notification")?.textContent)).toBe(
            "This entity can't be saved because one or more required fields are missing.",
        );
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
        expect(fixture.nativeElement.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
        // The edits survive the refusal (EDT-08): the form still holds the entity.
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("genomic_variants");
    });

    it("an in-flight save spins the button and the status line ends with the answer (EDT-18, DD-342)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const saveButton = () => compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!;
        expect(saveButton().disabled).toBe(false);
        expect(saveButton().classList.contains("is-loading")).toBe(false);
        expect(compiled.querySelector(".aurelius-editor-busy")).toBeNull();

        // In flight: the button is busy and the status line is live (EDT-18).
        saveButton().click();
        fixture.detectChanges();
        expect(saveButton().disabled).toBe(true);
        expect(saveButton().classList.contains("is-loading")).toBe(true);
        expect(saveButton().getAttribute("aria-busy")).toBe("true");
        const busy = compiled.querySelector<HTMLElement>(".aurelius-editor-busy");
        // The native <output> carries the status role implicitly (S6819).
        expect(busy?.tagName).toBe("OUTPUT");
        expect(normalize(busy?.textContent)).toBe("Saving the entity");

        // A refusal ends the state with the drawer open (EDT-08's path).
        httpMock
            .expectOne(ENTITY_POST_URL)
            .flush(
                { errorCode: "ATLAS-403-00-001", errorMessage: "forbidden" },
                { status: 403, statusText: "Forbidden" },
            );
        fixture.detectChanges();
        expect(saveButton().disabled).toBe(false);
        expect(saveButton().classList.contains("is-loading")).toBe(false);
        expect(saveButton().hasAttribute("aria-busy")).toBe(false);
        expect(compiled.querySelector(".aurelius-editor-busy")).toBeNull();

        // A success ends it too, through the navigation (EDT-06's path).
        saveButton().click();
        fixture.detectChanges();
        expect(saveButton().disabled).toBe(true);
        httpMock.expectOne(ENTITY_POST_URL).flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
        fixture.detectChanges();
        expect(compiled.querySelector(".aurelius-editor-busy")).toBeNull();
    });

    it("the head carries only the X; the foot holds Delete and Save (EDT-10, EDT-19, DD-347)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const head = [
            ...compiled.querySelectorAll<HTMLButtonElement>(
                "dialog.aurelius-drawer-panel .aurelius-drawer-head button",
            ),
        ].map((button) => normalize(button.textContent) || button.getAttribute("aria-label"));
        expect(head).toEqual(["Close"]); // the drawer's own X — Save left the head

        const foot = [
            ...compiled.querySelectorAll<HTMLButtonElement>(
                "dialog.aurelius-drawer-panel .aurelius-drawer-foot button",
            ),
        ];
        expect(foot.map((button) => normalize(button.textContent))).toEqual(["Delete", "Save"]);
        expect(compiled.querySelector(".aurelius-editor-foot")).toBeTruthy();
        // The pair rides Bulma's own group container (DD-350): it carries
        // the spacing between the buttons and their right alignment.
        const actions = compiled.querySelector(".aurelius-editor-actions");
        expect(actions?.classList.contains("buttons")).toBe(true);
        expect(actions?.classList.contains("is-right")).toBe(true);
        // Normally sized: Bulma's normal size is the absence of a class.
        expect(foot.every((button) => !button.classList.contains("is-small"))).toBe(true);
        expect([...compiled.querySelectorAll("button")].some((b) => normalize(b.textContent) === "Cancel")).toBe(false);
    });

    it("the foot hides Delete in create mode (EDT-19: nothing to delete yet)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true });
        arriveTypeDefs(fixture, httpMock);

        expect(compiled.querySelector("button.aurelius-editor-delete")).toBeNull();
        expect(normalize(compiled.querySelector("button.aurelius-editor-save")?.textContent)).toBe("Save");
    });

    it("Delete carries the hold donut sized to the hold (EDT-19)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const del = compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-delete");
        // Destructive, and it reads that way (EDT-19).
        expect(del?.classList.contains("is-danger")).toBe(true);
        // The donut is the SVG ring stroke with a unit path, so the CSS
        // animation can draw it with one dashoffset sweep.
        const circle = del?.querySelector("svg.aurelius-hold-donut circle");
        expect(circle?.getAttribute("pathLength")).toBe("1");
        // The ring's animation and the directive's clock share one number.
        expect(del?.style.getPropertyValue("--aurelius-hold-duration")).toBe("3s");
        // The tooltip is the vendored Aurelius string, plural for three.
        expect(del?.getAttribute("title")).toBe("Hold for 3 seconds");
    });

    it("a completed hold deletes the entity and lands on browse (EDT-19)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-delete")!.click();
        // The directive's (held) fires true only after the hold; drive it as
        // the directive would (the hold mechanic is specced at the directive).
        const directive = holdDirective(fixture);
        directive.held.emit(true);
        fixture.detectChanges();

        const request = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b");
        expect(request.request.method).toBe("DELETE");
        // In flight the Delete is the acting button: spinner, busy, disabled,
        // and the status line names the delete (EDT-18, DD-342).
        const del = compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-delete");
        expect(del?.classList.contains("is-loading")).toBe(true);
        expect(del?.getAttribute("aria-busy")).toBe("true");
        expect(del?.disabled).toBe(true);
        expect(normalize(compiled.querySelector(".aurelius-editor-busy")?.textContent)).toBe("Deleting the entity");
        request.flush({ guidAssignments: {} });
        fixture.detectChanges();

        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "browse"], drawer: null } }]);
    });

    it("a premature release does nothing (EDT-19: the hold is the confirm)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        holdDirective(fixture).held.emit(false);
        fixture.detectChanges();

        httpMock.expectNone((req) => req.url.startsWith("/api/atlas/v2/entity/guid/7a1b") && req.method === "DELETE");
        expect(navigate).not.toHaveBeenCalled();
        expect(compiled.querySelector(".aurelius-drawer-panel")).toBeTruthy();
    });

    it("a refused delete alerts and keeps the drawer (EDT-19, EDT-08's shape)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        holdDirective(fixture).held.emit(true);
        const request = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b");
        request.flush(
            { errorCode: "ATLAS-403-00-001", errorMessage: "forbidden" },
            { status: 403, statusText: "Forbidden" },
        );
        fixture.detectChanges();

        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(true);
        expect(navigate).not.toHaveBeenCalled();
        expect(compiled.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
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

    // The governance banner (EDT-23/EDT-24, DD-446). The helper `arrive`
    // already settles the open round, so the debounce/line specs ride it and
    // drive only the change under test; the trigger specs flush the reads by
    // hand to watch the first round fire.
    it("validates the merged draft when the form opens (EDT-23)", () => {
        const { fixture, httpMock } = setup();
        arriveTypeDefs(fixture, httpMock);
        httpMock.expectOne((request) => request.url.startsWith(ENTITY_URL)).flush(ANSWER);
        fixture.detectChanges();

        const validation = httpMock.expectOne(VALIDATE_URL);
        expect(validation.request.method).toBe("POST");
        // The body is the merged draft (EDT-21's payload): the read's entity
        // with the form's seeded values written back — the legacy's
        // opened-entity merge, not the raw read or the save wrapper.
        const draft = validation.request.body as { typeName: string; attributes: Record<string, unknown> };
        expect(draft.typeName).toBe("DataSet");
        expect(draft.attributes["name"]).toBe("genomic_variants");
        expect(draft.attributes["description"]).toBe("Curated variant calls.");
        validation.flush(VALIDATION);
    });

    it("a change re-validates once, debounced 200 ms (EDT-23)", () => {
        vi.useFakeTimers();
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        expect(httpMock.match((request) => request.url === VALIDATE_URL)).toHaveLength(0); // the open round settled

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "renamed_variants";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();

        vi.advanceTimersByTime(100);
        expect(httpMock.match((request) => request.url === VALIDATE_URL)).toHaveLength(0); // not yet
        vi.advanceTimersByTime(120);
        const pending = httpMock.match((request) => request.url === VALIDATE_URL);
        expect(pending).toHaveLength(1);
        const draft = pending[0].request.body as { attributes: Record<string, unknown> };
        expect(draft.attributes["name"]).toBe("renamed_variants"); // the draft, not the opened entity
        pending[0].flush(VALIDATION);
        vi.useRealTimers();
    });

    it("a failed validation renders no lines, alerts nothing, and keeps the drawer usable (EDT-23)", () => {
        const { fixture, compiled, httpMock } = setup();
        arriveTypeDefs(fixture, httpMock);
        httpMock.expectOne((request) => request.url.startsWith(ENTITY_URL)).flush(ANSWER);
        fixture.detectChanges();
        vi.spyOn(TestBed.inject(Router), "navigate"); // the save's navigation, as every save spec stubs it

        httpMock.expectOne(VALIDATE_URL).flush({ errorCode: "ATLAS-500" }, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        // The quiet swallow (DD-446): no lines, no alert, the drawer intact.
        expect(compiled.querySelectorAll("[data-gov-line]")).toHaveLength(0);
        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(false);
        expect(compiled.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();

        // And the form still saves (the drawer stays usable).
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock.expectOne(ENTITY_POST_URL).flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
    });

    it("a newer draft drops the in-flight validation (EDT-23: the generation guard)", () => {
        vi.useFakeTimers();
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "first-edit";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        vi.advanceTimersByTime(250);
        const stale = httpMock.expectOne(VALIDATE_URL);

        // The next change while the first is still unanswered: the older call
        // is dropped, and its answer can never land.
        nameInput.value = "second-edit";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        vi.advanceTimersByTime(250);
        expect(stale.cancelled).toBe(true);
        const fresh = httpMock.expectOne(VALIDATE_URL);
        expect((fresh.request.body as { attributes: Record<string, unknown> }).attributes["name"]).toBe("second-edit");
        expect(() => stale.flush(VALIDATION)).toThrow(); // the superseded answer cannot overwrite

        fresh.flush(VALIDATION);
        fixture.detectChanges();
        expect(compiled.querySelectorAll("[data-gov-line]")).toHaveLength(2); // the fresh answer renders
        vi.useRealTimers();
    });

    it("renders one banner line per card that names a control, nothing for the rest (EDT-24)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // The mock answers four cards (VE-02); the DataSet drawer renders
        // controls for two of them — the `definition` card names the
        // description key (the pair, DD-320). The unanswered-for keys
        // (`dataEntity`, `domainLead`) render nowhere (DD-446).
        const lines = [...compiled.querySelectorAll<HTMLElement>("[data-gov-line]")];
        expect(lines).toHaveLength(2);
        // The DOM order is the form's (EDT-03's rank): the name control's
        // line first, the description control's after it.
        expect(lines.map((line) => normalize(line.textContent))).toEqual([
            "This entity has a name",
            "This entity has a definition",
        ]);

        // The lines sit under their own control, at the legacy's small size,
        // with the success icon (compliant "1") in Bulma's icon seat.
        const nameLine = lines.find((line) => line.closest(".aurelius-editor-field")?.querySelector("#editor-name"));
        expect(normalize(nameLine?.textContent)).toBe("This entity has a name");
        expect(nameLine?.classList.contains("is-size-7")).toBe(true);
        expect(nameLine?.querySelector(".icon.has-text-success svg")).toBeTruthy();
        const definitionLine = lines.find((line) =>
            line.closest(".aurelius-editor-field")?.querySelector("textarea#editor-description"),
        );
        expect(normalize(definitionLine?.textContent)).toBe("This entity has a definition");
        expect(definitionLine?.querySelector(".icon.has-text-success svg")).toBeTruthy();
    });

    it("a non-compliant card paints the warning icon (EDT-24)", () => {
        const { fixture, compiled, httpMock } = setup();
        arriveTypeDefs(fixture, httpMock);
        httpMock.expectOne((request) => request.url.startsWith(ENTITY_URL)).flush(ANSWER);
        fixture.detectChanges();

        httpMock.expectOne(VALIDATE_URL).flush({
            name: { items: [govItem("name", "This entity is missing a name", "0")], isNonCompliant: true },
        });
        fixture.detectChanges();

        const line = compiled.querySelector<HTMLElement>("[data-gov-line]")!;
        expect(normalize(line.textContent)).toBe("This entity is missing a name");
        expect(line.querySelector(".icon.has-text-warning svg")).toBeTruthy();
        expect(line.querySelector(".icon.has-text-success")).toBeNull();
    });

    it("a create draft is validated too, with the seeded type (EDT-23)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock);

        // The banner rides the create form as well: the open round answered
        // the mock's cards, and the two rendered controls carry their lines —
        // the mock's verdicts name the keys, not the drafted values (EDT-24).
        const lines = [...compiled.querySelectorAll<HTMLElement>("[data-gov-line]")];
        expect(lines.map((line) => normalize(line.textContent))).toEqual([
            "This entity has a name",
            "This entity has a definition",
        ]);
    });
});

/* ------------------------------------------------------------------ */
/* The quality-mode drawer (EDT-25, EDT-28, EDT-29, DET-37).            */
/* ------------------------------------------------------------------ */

const KINDS_URL = "/api/aurelius/v1/quality/kinds";
const RULE_VALIDATE_URL = "/api/aurelius/v1/quality/rules/validate";

/** The vocabulary answer the quality form draws (a subset of QRE-01's). */
const QUALITY_KINDS = {
    kinds: [
        {
            name: "COLUMN_NOT_NULL_RATIO",
            dimension: "completeness",
            required: ["column"],
            optional: [],
            reason: "The column carries a value.",
        },
        {
            name: "ROW_NOT_EMPTY",
            dimension: "completeness",
            required: ["columns"],
            optional: ["minColumns"],
            reason: "The row carries its columns.",
        },
    ],
    castableTypes: ["int"],
    thresholdMin: 0,
    thresholdMax: 1,
};

/** The typedefs the quality drawer reads: the rule type with its derived
 * `fields` end (EDT-13's machinery) and the DataSet/Referenceable noise ends
 * the quality mode must not draw (EDT-25). */
const QUALITY_TYPEDEFS: AtlasTypesDef = {
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
            ],
        },
        { name: "DataSet", superTypes: ["Asset"] },
        { name: "m4i_field", attributeDefs: [{ name: "name", typeName: "string" }] },
        {
            name: "m4i_referenceable",
            superTypes: ["Referenceable"],
            relationshipAttributeDefs: [{ name: "meanings", typeName: "array<m4i_field>", cardinality: "SET" }],
        },
        {
            name: "m4i_data_quality",
            superTypes: ["DataSet", "m4i_referenceable"],
            attributeDefs: [{ name: "ruleDescription", typeName: "string" }],
            relationshipAttributeDefs: [
                {
                    name: "fields",
                    typeName: "array<m4i_field>",
                    cardinality: "SET",
                    relationshipTypeName: "m4i_data_quality_field_assignment",
                },
            ],
        },
    ],
    classificationDefs: [],
    enumDefs: [],
    structDefs: [],
    businessMetadataDefs: [],
    relationshipDefs: [],
};

/** The stored vocabulary rule (EDT-29's seed source): a kind, its
 * parameter, and foreign leftovers (EWR-09's materialized dqpattern). */
const RULE_ANSWER: AtlasEntityWithExtInfo = {
    entity: {
        guid: "r-1",
        typeName: "m4i_data_quality",
        attributes: {
            name: "total_not_null",
            qualifiedName: "total_not_null@cluster",
            id: 7,
            dqcheckkind: "COLUMN_NOT_NULL_RATIO",
            dqcolumn: "total",
            dqpattern: "leftover",
            active: true,
            threshold: 0.95,
        },
        relationshipAttributes: {
            fields: [{ guid: "f1", typeName: "m4i_field", displayText: "total", relationshipStatus: "ACTIVE" }],
        },
        classifications: [],
    },
    referredEntities: {},
};

/** The legacy rule (EDT-29): no kind — the generic form and no validate. */
const LEGACY_RULE_ANSWER: AtlasEntityWithExtInfo = {
    entity: {
        guid: "r-2",
        typeName: "m4i_data_quality",
        attributes: {
            name: "legacy_rule",
            qualifiedName: "legacy_rule@cluster",
            id: 9,
            dataqualitytype: "pattern",
            dataqualityoperator: "regularexpression",
            expression: "^\\d+$",
            description: "A pair rule the scanner still reads (DQ-07).",
        },
        classifications: [],
    },
    referredEntities: {},
};

/** Set the quality form's name input (the child's, EDT-27). */
function typeRuleName(compiled: HTMLElement, fixture: { detectChanges: () => void }, value: string): void {
    const input = compiled.querySelector<HTMLInputElement>("#editor-name")!;
    input.value = value;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
}

describe("EntityEditor quality mode (EDT-25, EDT-28, EDT-29, DET-37)", () => {
    it("opens a vocabulary rule in the quality form, not the attribute list (EDT-25, EDT-29)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-1" });
        arrive(fixture, httpMock, RULE_ANSWER, QUALITY_TYPEDEFS);
        const kindsRequest = httpMock.expectOne(KINDS_URL);
        kindsRequest.flush(QUALITY_KINDS);
        fixture.detectChanges();

        // The kind Select stands where the attribute list would; the generic
        // description control (the markdown field, EDT-20) is gone (EDT-27).
        expect(compiled.querySelector(".aurelius-quality-kind")).toBeTruthy();
        expect(compiled.querySelector("textarea#editor-description")).toBeFalsy();
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("total_not_null");
        // Only the `fields` picker renders — the DataSet/m4i_referenceable
        // noise ends the derived typedefs carry stay out (EDT-25).
        const pickers = [...compiled.querySelectorAll<HTMLElement>(".aurelius-editor-relationship")];
        expect(pickers.map((picker) => picker.getAttribute("data-field"))).toEqual(["fields"]);
        expect(pickers[0]?.querySelector(".aurelius-relationship-chip")?.textContent).toContain("total");
    });

    it("opens a legacy rule in the generic form, unchecked (EDT-29)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-2" });
        arrive(fixture, httpMock, LEGACY_RULE_ANSWER, QUALITY_TYPEDEFS);

        // No quality form, no kinds call; the pair attributes are not rendered
        // as editable fields either — the expression rides the save untouched
        // through the pass-through (EDT-29's last clause, proven at the save).
        expect(compiled.querySelector(".aurelius-quality-kind")).toBeFalsy();
        httpMock.expectNone(KINDS_URL);
        expect(compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")?.value).toContain(
            "A pair rule the scanner still reads (DQ-07).",
        );

        // Its Save is the EDT-06 path: no validate call, expression rides.
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock.expectNone(RULE_VALIDATE_URL);
        const post = httpMock.expectOne(ENTITY_POST_URL);
        const posted = (post.request.body as { entity: { attributes: Record<string, unknown> } }).entity;
        expect(posted.attributes["expression"]).toBe("^\\d+$");
        post.flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
        expect(navigate).toHaveBeenCalled();
    });

    it("validates before the POST, and posts the minimal quality body (EDT-28, EDT-27)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-1" });
        arrive(fixture, httpMock, RULE_ANSWER, QUALITY_TYPEDEFS);
        httpMock.expectOne(KINDS_URL).flush(QUALITY_KINDS);
        fixture.detectChanges();
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        // The validate call first (EDT-28): the draft's stored-rule shape.
        const validate = httpMock.expectOne(RULE_VALIDATE_URL);
        expect(validate.request.method).toBe("POST");
        expect(validate.request.body).toMatchObject({
            name: "total_not_null",
            id: 7,
            qualifiedName: "total_not_null@cluster",
            dqcheckkind: "COLUMN_NOT_NULL_RATIO",
            dqcolumn: "total",
            active: true,
            threshold: 0.95,
        });
        validate.flush({ valid: true, kind: "COLUMN_NOT_NULL_RATIO", dimension: "completeness" });
        fixture.detectChanges();

        // The EDT-06 save rides: the minimal body (no foreign dqpattern,
        // EDT-27) plus the fields picker's full value (EDT-16).
        const post = httpMock.expectOne(ENTITY_POST_URL);
        const posted = (
            post.request.body as {
                entity: { attributes: Record<string, unknown>; relationshipAttributes: Record<string, unknown> };
            }
        ).entity;
        expect(posted.attributes["dqpattern"]).toBeUndefined();
        expect(posted.attributes["dqcheckkind"]).toBe("COLUMN_NOT_NULL_RATIO");
        expect(posted.relationshipAttributes["fields"]).toEqual([
            {
                guid: "f1",
                typeName: "m4i_field",
                displayText: "total",
                relationshipType: "m4i_data_quality_field_assignment",
                relationshipStatus: "ACTIVE",
            },
        ]);
        post.flush({ createdEntityHeaders: [], updatedEntityHeaders: [] });
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "r-1"], drawer: null } }]);
    });

    it("an engine refusal keeps the line and posts nothing (EDT-28)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-1" });
        arrive(fixture, httpMock, RULE_ANSWER, QUALITY_TYPEDEFS);
        httpMock.expectOne(KINDS_URL).flush(QUALITY_KINDS);
        fixture.detectChanges();

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock.expectOne(RULE_VALIDATE_URL).flush({ valid: false, reason: "The rule needs a column." });
        fixture.detectChanges();

        // The reason rides the notification place (EDT-07's) and no POST fires.
        expect(normalize(compiled.querySelector(".aurelius-editor-notification")?.textContent)).toBe(
            "The rule needs a column.",
        );
        httpMock.expectNone(ENTITY_POST_URL);

        // A later edit clears the line (EDT-28); the next Save re-checks.
        typeRuleName(compiled, fixture, "total_not_null_v2");
        expect(compiled.querySelector(".aurelius-editor-notification")).toBeFalsy();
        httpMock.verify();
    });

    it("a validate transport failure answers the generic line, unchecked never saves (EDT-28)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-1" });
        arrive(fixture, httpMock, RULE_ANSWER, QUALITY_TYPEDEFS);
        httpMock.expectOne(KINDS_URL).flush(QUALITY_KINDS);
        fixture.detectChanges();

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock.expectOne(RULE_VALIDATE_URL).flush({}, { status: 502, statusText: "Bad Gateway" });
        fixture.detectChanges();

        expect(normalize(compiled.querySelector(".aurelius-editor-notification")?.textContent)).toBe(
            "The rule could not be checked against the server. Try again.",
        );
        httpMock.expectNone(ENTITY_POST_URL);
        httpMock.verify();
    });

    it("an incomplete quality form bails before the call (EDT-28/EDT-07)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "m4i_data_quality" });
        arriveTypeDefs(fixture, httpMock, QUALITY_TYPEDEFS);
        httpMock.expectOne(KINDS_URL).flush(QUALITY_KINDS);
        fixture.detectChanges();

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        httpMock.expectNone(RULE_VALIDATE_URL); // nothing drafted — nothing to check
        expect(normalize(compiled.querySelector(".aurelius-editor-notification")?.textContent)).toBe(
            "This entity can't be saved because one or more required fields are missing.",
        );
    });

    it("the rules box's + preselects the open field in the fields picker (DET-37)", () => {
        const { fixture, compiled, httpMock } = setup({
            create: true,
            createType: "m4i_data_quality",
            query: { dqField: "f9", dqFieldLabel: "total" },
        });
        arriveTypeDefs(fixture, httpMock, QUALITY_TYPEDEFS);
        httpMock.expectOne(KINDS_URL).flush(QUALITY_KINDS);
        fixture.detectChanges();

        // The create route carries the type fixed (DD-330, no picker round)
        // and the seed pick rides the fields picker as one chip (EDT-13's
        // pick shape, DET-37).
        const picker = compiled.querySelector<HTMLElement>(".aurelius-editor-relationship");
        expect(picker?.getAttribute("data-field")).toBe("fields");
        expect(picker?.querySelector(".aurelius-relationship-chip")?.textContent).toContain("total");
    });
});
