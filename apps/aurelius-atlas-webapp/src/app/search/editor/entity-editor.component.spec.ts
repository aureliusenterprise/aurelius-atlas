/**
 * The entity editor drawer (EDT-01..EDT-08, EDT-10, EDT-19, VDE-01..VDE-11):
 * the routed panel's own wiring on the view doors (16.5c). The specs ride the
 * details screen's idiom: a fake `ActivatedRoute` (paramMap + snapshot data
 * carry the mode, DD-355), the real http client through HttpTestingController,
 * and a spy on the Router. The field builder and the merge are specced at
 * their owner (form-fields); the door store at its owner (editor-state); here:
 * the read (EDT-02, VDE-01), the picker's pick and seed (EDT-04, VDE-05, DD-330),
 * the tag box (EDT-05, VDE-03), the pickers and their door body (EDT-13..EDT-16,
 * VDE-04,
 * VDE-05), the conflict re-edit and the name-taken line (VDE-07, VDE-08), the
 * invalid save (EDT-07), the failed save (EDT-08, VDE-09), dismissal (EDT-01),
 * and the commit foot (EDT-10 amended by EDT-19, DD-347 — Delete + Save in the
 * foot, the hold mechanic specced at the directive). The History pane and its
 * specs moved to `history/history-tab.component.spec.ts` with the pane (7.46),
 * the type field's list/badge/pick specs to `type-field.component.spec.ts`
 * with the field (7.47), and the governance banner's render specs to
 * `governance-lines.component.spec.ts` with the lines (7.48); the fixtures and
 * settle helpers all four specs share live in `editor-testing.ts`.
 */
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { Router, convertToParamMap, provideRouter } from "@angular/router";

import {
    ViewEntityService,
    type AtlasTypesDef,
    type EntityView,
    type ViewForTypeAnswer,
    type ViewSaveRequest,
} from "aurelius-atlas-data-access";

import { AlertsService } from "../../alerts/alerts.service";
import { createEntityMatcher } from "../../routes";

import { EntityEditor } from "./entity-editor.component";
import {
    ATLAS_ENTITY_URL,
    CLASSIFICATION_SLICE_URL,
    ENTITY_HEADERS_URL,
    ENUM_SLICE_URL,
    RELATIONSHIP_SLICE_URL,
    VALIDATE_URL,
    VIEW_POST_URL,
    VIEW_URL,
} from "../../../testing/api";
import { provideFakeKeycloak } from "../../../testing/auth";
import { provideFakeAppConfig } from "../../../testing/config";
import { normalize } from "../../../testing/dom";
import {
    ANSWER,
    DATASET_CHAIN,
    DrawerTestHost,
    RA_ANSWER,
    TYPEDEFS,
    VALIDATION,
    arrive,
    arriveChain,
    arriveSlices,
    arriveTypeDefs,
    chainFor,
    flushValidation,
    holdDirective,
    parentAnswer,
    parentChain,
    parentSearchResult,
    raChain,
    savedView,
    setup,
    withDataSetRelationships,
} from "./editor-testing";

describe("EntityEditor (EDT-01..EDT-08, EDT-10, EDT-19, VDE-01..VDE-05)", () => {
    it("fetches its own view and its type material on arrival (EDT-02, EDT-04, VDE-01, VDE-02)", () => {
        const { fixture, httpMock } = setup();

        const viewRequest = httpMock.expectOne("/api/aurelius/v1/entity/guid/7a1b");
        expect(viewRequest.request.method).toBe("GET");
        // The small slices replace the whole-typedefs dump (VDE-02, DD-611).
        expect(httpMock.expectOne(CLASSIFICATION_SLICE_URL).request.method).toBe("GET");
        expect(httpMock.expectOne(ENUM_SLICE_URL).request.method).toBe("GET");
        expect(httpMock.expectOne(RELATIONSHIP_SLICE_URL).request.method).toBe("GET");
        expect(httpMock.expectOne(ENTITY_HEADERS_URL).request.method).toBe("GET");
        viewRequest.flush(ANSWER);
        fixture.detectChanges(); // the answer's type fires the chain read (VDE-02)
        const chainRequest = httpMock.expectOne("/api/aurelius/v1/types/for-type/DataSet");
        expect(chainRequest.request.method).toBe("GET");
        chainRequest.flush(DATASET_CHAIN);
        fixture.detectChanges();
        flushValidation(httpMock); // the open round the visible form fires (EDT-23)
    });

    it("alerts and keeps the empty drawer on a failed view read (EDT-02, VDE-01)", () => {
        const { fixture, httpMock } = setup({ guid: "missing" });
        arriveTypeDefs(fixture, httpMock);

        httpMock.expectOne(`${VIEW_URL}missing`).flush({}, { status: 404, statusText: "Not Found" });
        fixture.detectChanges();

        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(true);
        // The drawer stays open (EDT-02): the panel is still rendered.
        expect(fixture.nativeElement.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
    });

    it("opens in the wide drawer (UIC-43, DD-712)", () => {
        const { fixture } = setup();

        // The editor is the product's data-entry surface, so it asks the
        // drawer for the wide panel — a form with roomy rows gets more of a
        // large screen (7.31). The settings and alerts drawers keep narrow.
        expect(fixture.nativeElement.querySelector("dialog.aurelius-drawer-panel").classList.contains("is-wide")).toBe(
            true,
        );
    });

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

    it("seeds the tag box from the view's own classification names (EDT-05, VDE-03)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const tags = [...compiled.querySelectorAll(".aurelius-editor-tag")].map((tag) => normalize(tag.textContent));
        // The chip carries the dictionary display name (EDT-05, DD-379); the
        // seed is the view's `classificationNames` — already its own tags, so
        // the client's DD-326 propagated filter retires (VDE-03).
        expect(tags).toEqual(["Has PII"]);
    });

    it("renders a picker per relationship attribute, seeded ACTIVE-only from sections (EDT-13, EDT-15, VDE-04)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raChain());

        const blocks = [...compiled.querySelectorAll<HTMLElement>(".aurelius-editor-relationship")];
        expect(blocks.map((block) => block.dataset["field"])).toEqual(["inputToProcesses", "model"]);
        // The label is the catalogue string alone (EDT-34, 7-33, DD-724): no
        // target-type bracket — the chips lead with the type (DD-341).
        expect(normalize(blocks[0].querySelector("p.label")?.textContent)).toBe("Input to Processes");
        // The mandatory flag marks the label (EDT-13); the optional one does not.
        expect(blocks[1].querySelector("p.label .has-text-danger")).toBeNull();

        // The chips: the ACTIVE end only — the non-ACTIVE end never seeds
        // (EDT-15) — and the lead is the end's typeName (DD-341).
        const chips = [...blocks[0].querySelectorAll("aurelius-atlas-ui-classification-chip")];
        expect(chips).toHaveLength(1);
        expect(normalize(chips[0].querySelector(".tag")?.textContent)).toBe("Process");
        expect(normalize(chips[0].querySelectorAll(".tag").item(1)?.textContent)).toBe("load_events");
        expect(blocks[1].querySelector("aurelius-atlas-ui-classification-chip")).toBeNull();

        // The pickers sit after the plain fields and before the box (EDT-13).
        // The base owner field is hidden (EDT-37), so the markdown
        // description is the last plain field.
        const prose = compiled.querySelector("#editor-description")!;
        const box = compiled.querySelector(".aurelius-editor-classification-box")!;
        expect(prose.compareDocumentPosition(blocks[0]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
        expect(blocks[0].compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it("a typed search and a mousedown pick add a chip (EDT-14)", () => {
        vi.useFakeTimers();
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raChain());

        const input = compiled.querySelector<HTMLInputElement>(
            '[data-field="inputToProcesses"] .aurelius-token-input',
        )!;
        input.dispatchEvent(new Event("focusin", { bubbles: true }));
        input.value = "load";
        input.dispatchEvent(new Event("input"));
        vi.advanceTimersByTime(250);
        // The picker asks the view family's door (EDT-14 amended, DD-711).
        httpMock
            .expectOne((request) => request.url === "/api/aurelius/v1/search")
            .flush({
                cards: [
                    { guid: "p2", typeName: "Process", displayText: "load_orders", status: "ACTIVE", stale: false },
                ],
                facets: {},
                total: 1,
            });
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

    it("a parent-side picker searches only entities that hold no parent (RPS-07, DD-758)", () => {
        vi.useFakeTimers();
        const { fixture, compiled, httpMock } = setup();
        // The hierarchy pair on the DataSet stand-in: one `SET` parent end and
        // its `SINGLE` child end, the shape of the dictionary's assignment
        // relationships (HCA-01). The relationship slice is what lets the field
        // builder tell the two apart (RPS-07).
        const chain = chainFor(
            withDataSetRelationships(TYPEDEFS, [
                {
                    name: "childDataSet",
                    typeName: "array<DataSet>",
                    cardinality: "SET",
                    relationshipTypeName: "dataset_parent_assignment",
                },
                {
                    name: "parentDataSet",
                    typeName: "DataSet",
                    cardinality: "SINGLE",
                    relationshipTypeName: "dataset_parent_assignment",
                },
            ]),
            "DataSet",
        );
        arrive(fixture, httpMock, RA_ANSWER, chain, true, {
            relationshipDefs: [
                {
                    name: "dataset_parent_assignment",
                    endDef1: { type: "DataSet", name: "parentDataSet", cardinality: "SINGLE" },
                    endDef2: { type: "DataSet", name: "childDataSet", cardinality: "SET" },
                },
            ],
        });

        const search = (field: string): Record<string, unknown> => {
            const input = compiled.querySelector<HTMLInputElement>(`[data-field="${field}"] .aurelius-token-input`)!;
            input.dispatchEvent(new Event("focusin", { bubbles: true }));
            input.dispatchEvent(new Event("input"));
            vi.advanceTimersByTime(250);

            return httpMock.expectOne((request) => request.url === "/api/aurelius/v1/search").request.body as Record<
                string,
                unknown
            >;
        };

        expect(search("childDataSet")).toMatchObject({ filters: { hasParent: false } });
        // The child side must still offer every candidate: choosing one that
        // holds a parent moves the entity being edited (DD-759).
        expect(Object.keys(search("parentDataSet")["filters"] as Record<string, unknown>)).not.toContain("hasParent");
        vi.useRealTimers();
    });

    it("a filled parent disables its sibling in the same group (PME-10, DD-751)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, parentAnswer(true), parentChain());

        const domain = compiled.querySelector<HTMLElement>('[data-field="dataDomain"]')!;
        const parent = compiled.querySelector<HTMLElement>('[data-field="parentEntity"]')!;

        // The member holding the edge stays live, so the choice can be
        // deleted and switched.
        expect(domain.querySelector(".aurelius-token-box")?.classList.contains("is-disabled")).toBe(false);
        expect(domain.querySelectorAll("aurelius-atlas-ui-classification-chip")).toHaveLength(1);

        // The empty member of the same group cannot be filled: the box is
        // disabled and its input carries the flag (the rule PME-07 enforces
        // on save is impossible in the form).
        expect(parent.querySelector(".aurelius-token-box")?.classList.contains("is-disabled")).toBe(true);
        expect(parent.querySelector<HTMLInputElement>(".aurelius-token-input")?.disabled).toBe(true);

        // Nothing to pick: a focused, typed-into disabled box offers no panel
        // and asks the search door nothing. The rows stay in the DOM (Bulma
        // hides the menu), so the shut state is the box class and the aria flag.
        vi.useFakeTimers();
        const parentInput = parent.querySelector<HTMLInputElement>(".aurelius-token-input")!;
        parentInput.dispatchEvent(new Event("focusin", { bubbles: true }));
        parentInput.value = "parent";
        parentInput.dispatchEvent(new Event("input"));
        vi.advanceTimersByTime(250);
        fixture.detectChanges();
        expect(parent.querySelector(".aurelius-token-box")?.classList.contains("is-active")).toBe(false);
        expect(httpMock.match((request) => request.url === "/api/aurelius/v1/search")).toHaveLength(0);
        vi.useRealTimers();
    });

    it("clearing one parent frees the sibling in the same group (PME-10, PME-08)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, parentAnswer(true), parentChain());

        // Delete the stored domain edge → the sibling opens up (moving a
        // parent from one member to the other, PME-08's other half).
        compiled
            .querySelector<HTMLButtonElement>('[data-field="dataDomain"] .aurelius-classification-chip-delete')!
            .click();
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-editor-notification")).toBeNull();
        expect(compiled.querySelector('[data-field="dataDomain"] .aurelius-token-box.is-disabled')).toBeNull();
        expect(compiled.querySelector('[data-field="parentEntity"] .aurelius-token-box.is-disabled')).toBeNull();

        // The freed picker searches again and takes the pick (one parent of
        // the group, PME-09).
        vi.useFakeTimers();
        const parentInput = compiled.querySelector<HTMLInputElement>(
            '[data-field="parentEntity"] .aurelius-token-input',
        )!;
        parentInput.dispatchEvent(new Event("focusin", { bubbles: true }));
        parentInput.value = "parent";
        parentInput.dispatchEvent(new Event("input"));
        vi.advanceTimersByTime(250);
        httpMock.expectOne((request) => request.url === "/api/aurelius/v1/search").flush(parentSearchResult());
        fixture.detectChanges();
        compiled
            .querySelector<HTMLButtonElement>('[data-field="parentEntity"] [role="option"]')!
            .dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
        fixture.detectChanges();
        expect(
            compiled.querySelectorAll('[data-field="parentEntity"] aurelius-atlas-ui-classification-chip'),
        ).toHaveLength(1);
        // The other half of the swap closed: the emptied domain is disabled.
        expect(compiled.querySelector('[data-field="dataDomain"] .aurelius-token-box.is-disabled')).toBeTruthy();
        vi.useRealTimers();

        // The save sends exactly the parent the picker holds (PME-09).
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        const post = httpMock.expectOne(VIEW_POST_URL);
        expect((post.request.body as ViewSaveRequest).sections).toEqual([
            { attribute: "dataDomain", entities: [] },
            { attribute: "parentEntity", entities: ["e7"] },
        ]);
        post.flush(savedView());
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalled();
    });

    it("a blocked mandatory parent never holds the save (PME-10, DD-751)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, parentAnswer(true), parentChain(true));
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        // Both members of the group are mandatory; the empty one sits disabled
        // (PME-10), so the form must not demand a value the user cannot give
        // (EDT-17's rule, stood down for a blocked picker).
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-editor-notification")).toBeNull();
        expect(compiled.querySelector(".aurelius-editor-error")).toBeNull();
        expect(compiled.querySelector('[data-field="parentEntity"] .aurelius-token-box.is-danger')).toBeNull();

        const post = httpMock.expectOne(VIEW_POST_URL);
        expect((post.request.body as ViewSaveRequest).sections).toEqual([
            { attribute: "dataDomain", entities: ["d1"] },
            { attribute: "parentEntity", entities: [] },
        ]);
        post.flush(savedView());
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalled();
    });

    /** 18.5's dataset parent choice on the same DataSet stand-in (DCP-05): a
     * dataset hangs under a collection (`collections`) or under another dataset
     * (`parentDataset`), never both — the group the server refuses on save
     * (DCP-03), mirrored here from `m4i_dataset`'s two ends.
     */
    const datasetChain = (): ViewForTypeAnswer => {
        const group = [{ type: "mutuallyExclusive", params: { group: "m4i_dataset_parent" } }];

        return chainFor(
            withDataSetRelationships(TYPEDEFS, [
                {
                    name: "collections",
                    typeName: "m4i_collection",
                    cardinality: "SINGLE",
                    relationshipTypeName: "m4i_dataset_assignment",
                    constraints: group,
                },
                {
                    name: "parentDataset",
                    typeName: "m4i_dataset",
                    cardinality: "SINGLE",
                    relationshipTypeName: "m4i_dataset_parent_assignment",
                    constraints: group,
                },
            ]),
            "DataSet",
        );
    };

    /** The stored view the DCP-05 probes edit: the dataset under one parent. */
    const datasetAnswer = (underCollection: boolean): EntityView => ({
        ...ANSWER,
        attributes: { name: "genomic_variants", owner: "analyst-3" },
        sections: underCollection
            ? [
                  {
                      attribute: "collections",
                      entities: [{ guid: "c1", name: "finance", typeName: "m4i_collection", status: "ACTIVE" }],
                  },
                  { attribute: "parentDataset", entities: [] },
              ]
            : [
                  { attribute: "collections", entities: [] },
                  {
                      attribute: "parentDataset",
                      entities: [{ guid: "d1", name: "raw_orders", typeName: "m4i_dataset", status: "ACTIVE" }],
                  },
              ],
    });

    /** The DCP-05 search answer for the dataset's parent picker: one candidate. */
    const datasetParentSearchResult = (): Record<string, unknown> => ({
        cards: [{ guid: "d7", typeName: "m4i_dataset", displayText: "orders_daily", status: "ACTIVE", stale: false }],
        facets: {},
        total: 1,
    });

    it("a held collection disables the dataset's parent picker (DCP-05, PME-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, datasetAnswer(true), datasetChain());

        const collections = compiled.querySelector<HTMLElement>('[data-field="collections"]')!;
        const parent = compiled.querySelector<HTMLElement>('[data-field="parentDataset"]')!;

        // The member holding the edge stays live; the empty one cannot be
        // filled — the form cannot make the choice PME-07 refuses.
        expect(collections.querySelector(".aurelius-token-box")?.classList.contains("is-disabled")).toBe(false);
        expect(parent.querySelector(".aurelius-token-box")?.classList.contains("is-disabled")).toBe(true);
        expect(parent.querySelector<HTMLInputElement>(".aurelius-token-input")?.disabled).toBe(true);
    });

    it("a held parent dataset disables the collection picker (DCP-05, PME-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, datasetAnswer(false), datasetChain());

        const collections = compiled.querySelector<HTMLElement>('[data-field="collections"]')!;
        const parent = compiled.querySelector<HTMLElement>('[data-field="parentDataset"]')!;

        // The reverse of the rule: whichever of the two ends holds the parent,
        // the other picker is shut.
        expect(parent.querySelector(".aurelius-token-box")?.classList.contains("is-disabled")).toBe(false);
        expect(parent.querySelectorAll("aurelius-atlas-ui-classification-chip")).toHaveLength(1);
        expect(collections.querySelector(".aurelius-token-box")?.classList.contains("is-disabled")).toBe(true);
    });

    it("clearing the dataset's collection frees the parent picker (DCP-05, PME-08)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, datasetAnswer(true), datasetChain());

        // Deleting the collection edge moves the dataset between the group's
        // members, PME-08's other half.
        compiled
            .querySelector<HTMLButtonElement>('[data-field="collections"] .aurelius-classification-chip-delete')!
            .click();
        fixture.detectChanges();

        expect(compiled.querySelector('[data-field="collections"] .aurelius-token-box.is-disabled')).toBeNull();
        expect(compiled.querySelector('[data-field="parentDataset"] .aurelius-token-box.is-disabled')).toBeNull();

        vi.useFakeTimers();
        const parentInput = compiled.querySelector<HTMLInputElement>(
            '[data-field="parentDataset"] .aurelius-token-input',
        )!;
        parentInput.dispatchEvent(new Event("focusin", { bubbles: true }));
        parentInput.value = "orders";
        parentInput.dispatchEvent(new Event("input"));
        vi.advanceTimersByTime(250);
        httpMock.expectOne((request) => request.url === "/api/aurelius/v1/search").flush(datasetParentSearchResult());
        fixture.detectChanges();
        compiled
            .querySelector<HTMLButtonElement>('[data-field="parentDataset"] [role="option"]')!
            .dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
        fixture.detectChanges();
        expect(
            compiled.querySelectorAll('[data-field="parentDataset"] aurelius-atlas-ui-classification-chip'),
        ).toHaveLength(1);
        expect(compiled.querySelector('[data-field="collections"] .aurelius-token-box.is-disabled')).toBeTruthy();
        vi.useRealTimers();

        // The save carries exactly the one parent the group allows (DCP-03's
        // shape, posted willingly).
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        const post = httpMock.expectOne(VIEW_POST_URL);
        expect((post.request.body as ViewSaveRequest).sections).toEqual([
            { attribute: "collections", entities: [] },
            { attribute: "parentDataset", entities: ["d7"] },
        ]);
        post.flush(savedView());
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalled();
    });

    it("the route's type seeds the create form without a temp guid (EDT-04, VDE-05, DD-592, DD-330)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock, "DataSet");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        // The picker stays above the form, selected at the route's type.
        expect(compiled.querySelector(".aurelius-editor-picker select")).toBeTruthy();
        const names = [...compiled.querySelectorAll<HTMLInputElement>("input.aurelius-editor-text")].map((input) =>
            input.id.replace("editor-", ""),
        );
        expect(names).toEqual(["name"]); // the base owner and displayName are hidden (EDT-37)
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("");

        // Save with a name: the door body names no guid and carries the uuid
        // qualifiedName the client seeded (VDE-05, DD-592 — the negative temp
        // guid and the guidAssignments remap of DD-325 retire).
        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "fresh_table";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(VIEW_POST_URL);
        expect(post.request.method).toBe("POST");
        const body = post.request.body as ViewSaveRequest;
        expect(body.guid).toBeUndefined();
        expect(body.typeName).toBe("DataSet");
        expect(String(body.attributes["qualifiedName"])).toMatch(
            /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
        );
        expect(body.attributes["name"]).toBe("fresh_table");
        const evict = vi.spyOn(TestBed.inject(ViewEntityService), "evict");
        post.flush(savedView({ guid: "9999", updateTime: 1_700_000_090_000 }));
        fixture.detectChanges();

        // The answer carries the server's guid (AVW-06): the cache is evicted
        // at it (VDE-10) and the save lands straight on the entity's details.
        expect(evict).toHaveBeenCalledWith("9999");
        httpMock.verify();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "9999"], drawer: null } }]);
    });

    it("switching the type re-seeds the form through the route (EDT-04, DD-330)", () => {
        // `m4i_collection` (the route type) extends `m4i_dataset`, so the
        // supertype's whole typedef already sits in its chain and the switch
        // up the chain asks nothing (VDE-02 — the store holds every supertype
        // whole, and the guard skips a def already in hand).
        const { fixture, compiled, httpMock, paramMap } = setup({ create: true, createType: "m4i_collection" });
        arriveTypeDefs(fixture, httpMock, "m4i_collection", chainFor(TYPEDEFS, "m4i_collection"));
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "half-typed";
        nameInput.dispatchEvent(new Event("input"));

        // Re-pick in the picker: the switch is a navigation to the new type.
        const select = compiled.querySelector<HTMLSelectElement>(".aurelius-editor-picker select")!;
        const datasetIndex = [...select.querySelectorAll("option")].find(
            (option) => option.value !== "" && option.textContent === "Dataset",
        )!.value;
        select.value = datasetIndex;
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: ["create", "m4i_dataset"] } }]);

        // The router answers: the same component with the new type param. The
        // new type asks nothing (its def already sits in the chain the
        // collection read answered, VDE-02), the old draft is dropped, and a
        // save posts the new type fresh.
        paramMap.next(convertToParamMap({ type: "m4i_dataset" }));
        fixture.detectChanges();
        flushValidation(httpMock);
        const reseeded = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        expect(reseeded.value).toBe(""); // the half-typed draft is gone (EDT-04)

        reseeded.value = "fresh_dataset";
        reseeded.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        const post = httpMock.expectOne(VIEW_POST_URL);
        const body = post.request.body as ViewSaveRequest;
        expect(body.typeName).toBe("m4i_dataset");
        expect(body.attributes["name"]).toBe("fresh_dataset");
        expect(body.guid).toBeUndefined(); // a fresh seed, not the old draft
        post.flush(savedView({ guid: "9998", typeName: "m4i_dataset" }));
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
                provideFakeAppConfig(),
                provideFakeKeycloak({ atlasWrite: true }),
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
        arriveSlices(fixture, http);

        // The bare create route: the picker alone, no form (DD-330).
        expect(compiled.querySelector("form")).toBeNull();
        const panel = compiled.querySelector(".aurelius-drawer-panel");
        expect(panel).toBeTruthy();

        // The first pick, through the router — the typed segment arrives.
        await router.navigate([{ outlets: { drawer: ["create", "DataSet"] } }]);
        await fixture.whenStable();
        fixture.detectChanges(); // the typed route seeds the type and asks its chain (VDE-02)
        arriveChain(http, "DataSet", DATASET_CHAIN);
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
        input.value = "CONFIDENTIAL"; // applies through the Asset supertype (the chain names the lineage, VDE-02)
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

    it("save posts one door body; the tag box rides it whole (EDT-06, VDE-03, VDE-05)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "renamed_variants";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(VIEW_POST_URL);
        expect(post.request.method).toBe("POST");
        const body = post.request.body as ViewSaveRequest;
        // The update names the base view's version (AVW-04, VDE-05).
        expect(body.guid).toBe("7a1b");
        expect(body.updateTime).toBe(1_700_000_021_000);
        expect(body.attributes["name"]).toBe("renamed_variants");
        expect(body.attributes["qualifiedName"]).toBe("genomic_variants@cluster"); // untouched passthrough
        // The hidden base attributes leave the body (EDT-37): the door merge
        // (AVW-05) leaves them as stored, so no key is needed to keep them.
        expect("owner" in body.attributes).toBe(false);
        // The full tag set rides the one body (VDE-03): the door replaces it
        // wholesale, so no add/replace/delete classification calls follow.
        expect(body.classifications).toEqual(["PII"]);
        post.flush(savedView());
        fixture.detectChanges();

        httpMock.verify(); // nothing else fired: the one POST is the whole save (VDE-05)
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "7a1b"], drawer: null } }]);
    });

    it("a gained and a lost tag both ride the one body (EDT-06, VDE-03)", () => {
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
        const post = httpMock.expectOne(VIEW_POST_URL);
        // The desired set — the gained tag in, the lost one out — rides the
        // door's `classifications` key (VDE-03); the classification add/DELETE
        // pair of DD-326 retires.
        expect((post.request.body as ViewSaveRequest).classifications).toEqual(["CONFIDENTIAL"]);
        post.flush(savedView());
        fixture.detectChanges();

        httpMock.verify();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "7a1b"], drawer: null } }]);
    });

    it("save posts the pickers' full value as the door's sections (EDT-16, VDE-04)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raChain());
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        const post = httpMock.expectOne(VIEW_POST_URL);
        const body = post.request.body as ViewSaveRequest;
        // One entry per rendered picker, complete desired sets: the ACTIVE
        // end (the non-ACTIVE end was never seeded, EDT-15) and the empty
        // `model` set — the picker owns its key (VDE-04).
        expect(body.sections).toEqual([
            { attribute: "inputToProcesses", entities: ["p1"] },
            { attribute: "model", entities: [] },
        ]);
        // The picker owns its key: no attributes mirror rides the door view
        // (DD-340 retired with the Atlas read) and the untouched attributes
        // pass through.
        expect(body.attributes["inputToProcesses"]).toBeUndefined();
        expect(body.attributes["qualifiedName"]).toBe("genomic_variants@cluster");
        post.flush(savedView());
        fixture.detectChanges();

        httpMock.verify();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "7a1b"], drawer: null } }]);
    });

    it("the editor builds no picker for term assignments (EDT-36, DD-828)", () => {
        const defs: AtlasTypesDef = {
            ...TYPEDEFS,
            entityDefs: TYPEDEFS.entityDefs!.map((def) =>
                def.name === "DataSet"
                    ? {
                          ...def,
                          relationshipAttributeDefs: [
                              { name: "meanings", typeName: "array<string>", cardinality: "SET" },
                          ],
                      }
                    : def,
            ),
        };
        const view: EntityView = {
            ...ANSWER,
            sections: [{ attribute: "meanings", entities: [{ guid: "t1", name: "glossary debt", status: "ACTIVE" }] }],
        };
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, view, chainFor(defs, "DataSet"));
        vi.spyOn(TestBed.inject(Router), "navigate"); // the save's navigation, stubbed as every save spec does

        // The glossary model's end is dropped before the form builds, so the
        // picker never renders (EDT-36) — the read keeps answering the stored
        // terms, the editor just never offers to edit them.
        expect(compiled.querySelectorAll('[data-field="meanings"]')).toHaveLength(0);
        expect(compiled.querySelectorAll(".aurelius-editor-relationship")).toHaveLength(0);

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        // Nothing rides the door's `meanings` key (DD-612's own road stays
        // empty here) and no `sections` entry claims the set, so the door
        // leaves the term assignments exactly as stored (AVW-05).
        const post = httpMock.expectOne(VIEW_POST_URL);
        const body = post.request.body as ViewSaveRequest;
        expect(body.meanings).toBeUndefined();
        expect("sections" in body).toBe(false);
        post.flush(savedView());
    });

    it("an empty mandatory relationship picker blocks the save (EDT-17)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raChain(true));

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        expect(httpMock.match((request) => request.method === "POST" || request.method === "PUT")).toHaveLength(0);
        const block = compiled.querySelector<HTMLElement>('[data-field="model"]')!;
        // FORM-REQ-001: the red asterisk is silent on its own, so the block label
        // carries the word too. "model" has no catalogue key (it is a sample
        // relationship, not a dictionary attribute) so it stays the raw name
        // (DD-723), and carries no target-type bracket (EDT-34, DD-724).
        expect(normalize(block.querySelector("p.label")?.textContent)).toBe("model *(required)");
        expect(normalize(block.querySelector(".aurelius-editor-error")?.textContent)).toBe("Name is required.");
        expect(block.querySelector(".aurelius-token-box")?.classList.contains("is-danger")).toBe(true);
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

    it("an error line travels with its control (FORM-ERR-002)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raChain(true));

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        // While the reason shows, the control names its line and says it is
        // invalid — not just red paint.
        expect(nameInput.getAttribute("aria-invalid")).toBe("true");
        expect(nameInput.getAttribute("aria-describedby")).toBe("editor-name-error");
        expect(normalize(compiled.querySelector("#editor-name-error")?.textContent)).toBe("Name is required.");

        // The picker's combobox names the line under it — the same convention
        // the parent-paired label already uses (EDT-35).
        const pickerInput = compiled.querySelector<HTMLInputElement>('[data-field="model"] .aurelius-token-input')!;
        expect(pickerInput.getAttribute("aria-invalid")).toBe("true");
        expect(pickerInput.getAttribute("aria-describedby")).toBe("editor-relationship-model-error");
        expect(normalize(compiled.querySelector("#editor-relationship-model-error")?.textContent)).toBe(
            "Name is required.",
        );
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

    it("the loading region is mounted before the read answers (LR-002)", () => {
        const { fixture, compiled, httpMock } = setup();
        arriveTypeDefs(fixture, httpMock);

        // The view read is still open: the region was mounted from the first
        // paint and now carries the line — a reader already watches the place
        // the text lands in.
        const region = compiled.querySelector("output.aurelius-editor-loading");
        expect(region).toBeTruthy();
        expect(normalize(region?.textContent)).toBe("Retrieving the entity details");

        httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(ANSWER);
        fixture.detectChanges(); // the answer's type fires the chain read (VDE-02)
        arriveChain(httpMock, "DataSet", DATASET_CHAIN);
        fixture.detectChanges();
        flushValidation(httpMock); // the open round the visible form fires (EDT-23)

        // The answer clears the text, not the region: the node is the same
        // element, only emptied.
        expect(compiled.querySelector("output.aurelius-editor-loading")).toBe(region);
        expect(normalize(region?.textContent)).toBe("");
    });

    it("the save's outcome is announced, not just acted on (LR-005)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        // The store navigates on success; the spy keeps the empty test-bed
        // route table from rejecting (the navigation itself is EDT-06's).
        vi.spyOn(TestBed.inject(Router), "navigate");

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "renamed_variants";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock.expectOne(VIEW_POST_URL).flush(savedView());
        fixture.detectChanges();
        // The outcome rides an effect, which fills the line at the end of the
        // tick it was scheduled in — one more pass lets the binding re-read.
        fixture.detectChanges();

        // The persistent status line holds the outcome the navigation acted
        // on, so the reader hears it before the drawer goes away.
        expect(normalize(compiled.querySelector(".aurelius-editor-outcome")?.textContent)).toBe("Entity saved");
    });

    it("a lost version race re-edits from the stored view (VDE-07, DD-610)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        // Edit the name; leave the prose and the hidden base attributes alone.
        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "renamed_variants";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        // The door lost the race (AVW-04): 409 carrying the stored view.
        const stored: EntityView = {
            ...ANSWER,
            name: "stored_variants",
            displayText: "stored_variants",
            updateTime: 2_000_000_000_000,
            attributes: { ...ANSWER.attributes, name: "stored_variants", description: "stored summary" },
        };
        httpMock
            .expectOne(VIEW_POST_URL)
            .flush({ errorCode: "ENTITY_VERSION_CONFLICT", view: stored }, { status: 409, statusText: "Conflict" });
        fixture.detectChanges();

        // One line, no alert, no navigation (DD-591's reload-and-reedit): the
        // drawer stays open with the person's edit kept (VDE-07).
        expect(normalize(compiled.querySelector(".aurelius-editor-conflict")?.textContent)).toBe(
            "This entity changed since you opened it. Your edits are kept — save again to write them over the stored version.",
        );
        expect(compiled.querySelector(".aurelius-editor-notification")).toBeNull();
        expect(add).not.toHaveBeenCalled();
        expect(navigate).not.toHaveBeenCalled();
        expect(compiled.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("renamed_variants"); // kept
        // The untouched control answers the stored value (VDE-07): the re-seed
        // ran against the seed the old view gave. The prose textarea is the
        // untouched field — the base owner is hidden now (EDT-37).
        expect(compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")?.value).toBe(
            "stored summary",
        );

        // A second Save rides the stored updateTime (VDE-07, AVW-04).
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        const second = httpMock.expectOne(VIEW_POST_URL);
        const body = second.request.body as ViewSaveRequest;
        expect(body.updateTime).toBe(2_000_000_000_000);
        expect(body.attributes["name"]).toBe("renamed_variants");
        expect(body.attributes["description"]).toBe("stored summary");
        expect("owner" in body.attributes).toBe(false); // hidden (EDT-37)
        second.flush(savedView({ ...stored, updateTime: 2_000_000_050_000 }));
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "7a1b"], drawer: null } }]);
    });

    it("a name-taken create answers one line and keeps the drawer (VDE-08, DD-591)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock, "DataSet");
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "already_there";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock
            .expectOne(VIEW_POST_URL)
            .flush(
                { errorCode: "ENTITY_NAME_TAKEN", errorMessage: "qualifiedName already exists" },
                { status: 409, statusText: "Conflict" },
            );
        fixture.detectChanges();

        // One alert naming the taken name, the drawer open, the edits kept
        // (VDE-08) — no conflict line, no navigation (AVW-06).
        expect(add).toHaveBeenCalledTimes(1);
        expect(add).toHaveBeenCalledWith({
            severity: "error",
            source: "search",
            message: "That name is already held by another entity.",
        });
        expect(compiled.querySelector(".aurelius-editor-conflict")).toBeNull();
        expect(navigate).not.toHaveBeenCalled();
        expect(compiled.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("already_there");
    });

    it("the delete's outcome is announced, not just acted on (LR-005, VDE-11, WFE-01, WFE-02)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        // The store navigates on success; the spy keeps the empty test-bed
        // route table from rejecting (the navigation itself is EDT-19's).
        vi.spyOn(TestBed.inject(Router), "navigate");

        holdDirective(fixture).held.emit(true);
        // The delete stays on the Atlas route (VDE-11): the door does not delete.
        const request = httpMock.expectOne(`${ATLAS_ENTITY_URL}7a1b`);
        request.flush({ guidAssignments: {} });
        fixture.detectChanges();
        fixture.detectChanges(); // the outcome effect fills at the tick's end

        expect(normalize(compiled.querySelector(".aurelius-editor-outcome")?.textContent)).toBe("Entity deleted");
    });

    it("a refused delete fills no outcome line (LR-005: the alerts carry it)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        holdDirective(fixture).held.emit(true);
        const request = httpMock.expectOne(`${ATLAS_ENTITY_URL}7a1b`);
        request.flush(
            { errorCode: "ATLAS-403-00-001", errorMessage: "forbidden" },
            { status: 403, statusText: "Forbidden" },
        );
        fixture.detectChanges();
        fixture.detectChanges();

        // The refusal is an alert (EDT-08's shape), not an "Entity deleted"
        // lie on the outcome line.
        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(true);
        expect(normalize(compiled.querySelector(".aurelius-editor-outcome")?.textContent ?? "")).toBe("");
    });

    it("a reworded delete line keeps the refusal a refusal (WFE-01, DD-802)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        // Reword the refusal alert the way a copy change or a translation
        // would: the stored text no longer equals the editor's deleting
        // line. Inferring the outcome from alert text (the old effect) would
        // read this refusal as a success and lie "Entity deleted"; the tick
        // (WFE-01) never compares text, so the outcome line stays empty.
        const alerts = TestBed.inject(AlertsService);
        const original = alerts.add.bind(alerts);
        vi.spyOn(alerts, "add").mockImplementation((alert) => {
            original({ ...alert, message: "Die entiteit kan nie verwijder word nie" });
        });

        holdDirective(fixture).held.emit(true);
        const request = httpMock.expectOne(`${ATLAS_ENTITY_URL}7a1b`);
        request.flush(
            { errorCode: "ATLAS-403-00-001", errorMessage: "forbidden" },
            { status: 403, statusText: "Forbidden" },
        );
        fixture.detectChanges();
        fixture.detectChanges();

        expect(normalize(compiled.querySelector(".aurelius-editor-outcome")?.textContent ?? "")).toBe("");
    });

    it("a refused save adds one alert and keeps the drawer (EDT-08, VDE-09)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock
            .expectOne(VIEW_POST_URL)
            .flush(
                { errorCode: "ATLAS-403-00-001", errorMessage: "forbidden" },
                { status: 403, statusText: "Forbidden" },
            );
        fixture.detectChanges();

        // Any other failure of the door is the EDT-08 alert (VDE-09).
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
        vi.spyOn(TestBed.inject(Router), "navigate");

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
            .expectOne(VIEW_POST_URL)
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
        httpMock.expectOne(VIEW_POST_URL).flush(savedView());
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

    it("a completed hold deletes the entity and lands on browse (EDT-19, VDE-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-delete")!.click();
        // The directive's (held) fires true only after the hold; drive it as
        // the directive would (the hold mechanic is specced at the directive).
        const directive = holdDirective(fixture);
        directive.held.emit(true);
        fixture.detectChanges();

        const request = httpMock.expectOne(`${ATLAS_ENTITY_URL}7a1b`);
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

        httpMock.expectNone((req) => req.url.startsWith(ATLAS_ENTITY_URL) && req.method === "DELETE");
        expect(navigate).not.toHaveBeenCalled();
        expect(compiled.querySelector(".aurelius-drawer-panel")).toBeTruthy();
    });

    it("a refused delete alerts and keeps the drawer (EDT-19, EDT-08's shape)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        holdDirective(fixture).held.emit(true);
        const request = httpMock.expectOne(`${ATLAS_ENTITY_URL}7a1b`);
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

    // The governance banner (EDT-23/EDT-24, DD-446, VDE-11): it keeps the
    // Atlas validate-entity aux API and the AtlasEntity-shaped draft — the
    // adapter answers that shape from the view. The helper `arrive` already
    // settles the open round, so the debounce/line specs ride it and drive
    // only the change under test; the trigger specs flush the reads by hand
    // to watch the first round fire.
    it("validates the merged draft when the form opens (EDT-23, VDE-11)", () => {
        const { fixture, httpMock } = setup();
        arriveSlices(fixture, httpMock, false);
        httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(ANSWER);
        fixture.detectChanges(); // the answer's type fires the chain read (VDE-02)
        arriveChain(httpMock, "DataSet", DATASET_CHAIN);
        fixture.detectChanges();

        const validation = httpMock.expectOne(VALIDATE_URL);
        expect(validation.request.method).toBe("POST");
        // The body is the merged draft (EDT-21's payload): the view's entity
        // with the form's seeded values written back — the legacy's
        // opened-entity merge, not the raw view or the save wrapper (VDE-11).
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
        arriveSlices(fixture, httpMock, false);
        httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(ANSWER);
        fixture.detectChanges(); // the answer's type fires the chain read (VDE-02)
        arriveChain(httpMock, "DataSet", DATASET_CHAIN);
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
        httpMock.expectOne(VIEW_POST_URL).flush(savedView());
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

    // The banner's own render tests (the lines under the controls, the icon
    // pair, the retired key, the anyOf copies) moved with the lines to the
    // GovernanceLines spec at 7.48 (DD-874); the validate round above still
    // exercises what the drawer owns (EDT-23).

    it("a create draft is validated too, with the seeded type (EDT-23)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock, "DataSet", DATASET_CHAIN, false);
        flushValidation(httpMock);
        fixture.detectChanges();

        // The banner rides the create form as well: the open round answered
        // the corpus verdicts, and the two rendered controls carry their lines
        // — the verdicts name their attributes, not the drafted values (EDT-24
        // as amended by 12.7).
        const lines = [...compiled.querySelectorAll<HTMLElement>("[data-gov-line]")];
        expect(lines.map((line) => normalize(line.textContent))).toEqual([
            "This entity has a name",
            "This entity has a description",
        ]);
    });
});

/* ------------------------------------------------------------------ */
/* The quality-mode drawer (EDT-25, EDT-28, EDT-29, VDE-11).            */
/* ------------------------------------------------------------------ */

const KINDS_URL = "/api/aurelius/v1/quality/kinds";
const RULE_VALIDATE_URL = "/api/aurelius/v1/quality/rules/validate";

/** The vocabulary answer the quality form draws (a subset of QRE-01's). */
const QUALITY_KINDS = {
    kinds: [
        {
            name: "COLUMN_NOT_NULL_RATIO",
            dimension: "COMPLETENESS",
            required: ["column"],
            optional: [],
            reason: "The column carries a value.",
        },
        {
            name: "ROW_NOT_EMPTY",
            dimension: "COMPLETENESS",
            required: ["columns"],
            optional: ["minColumns"],
            reason: "The row carries its columns.",
        },
    ],
    castableTypes: ["int"],
    thresholdMin: 0,
    thresholdMax: 1,
};

/** The types the quality drawer's chain answers: the rule type with its
 * derived `fields` end (EDT-13's machinery) and the DataSet/Referenceable
 * lineage ends the quality mode must not draw (EDT-25). */
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

/** The stored vocabulary rule as a view (EDT-29's seed source): a kind, its
 * parameter, foreign leftovers (EWR-09's materialized dqpattern), and the
 * `fields` end among its sections. */
const RULE_ANSWER: EntityView = {
    guid: "r-1",
    typeName: "m4i_data_quality",
    qualifiedName: "total_not_null@cluster",
    name: "total_not_null",
    displayText: "total_not_null",
    status: "ACTIVE",
    updateTime: 1_700_000_000_000,
    stale: false,
    attributes: {
        name: "total_not_null",
        id: 7,
        dqcheckkind: "COLUMN_NOT_NULL_RATIO",
        dqcolumn: "total",
        dqpattern: "leftover",
        active: true,
        threshold: 0.95,
    },
    sections: [
        { attribute: "fields", entities: [{ guid: "f1", name: "total", typeName: "m4i_field", status: "ACTIVE" }] },
    ],
};

/** The legacy rule as a view (EDT-29): no kind — the generic form and no validate. */
const LEGACY_RULE_ANSWER: EntityView = {
    guid: "r-2",
    typeName: "m4i_data_quality",
    qualifiedName: "legacy_rule@cluster",
    name: "legacy_rule",
    displayText: "legacy_rule",
    status: "ACTIVE",
    updateTime: 1_700_000_000_000,
    stale: false,
    attributes: {
        name: "legacy_rule",
        id: 9,
        dataqualitytype: "pattern",
        dataqualityoperator: "regularexpression",
        expression: "^\\d+$",
        description: "A pair rule the scanner still reads (DQ-07).",
    },
    sections: [],
};

const QUALITY_CHAIN = chainFor(QUALITY_TYPEDEFS, "m4i_data_quality");

/** Set the quality form's name input (the child's, EDT-27). */
function typeRuleName(compiled: HTMLElement, fixture: { detectChanges: () => void }, value: string): void {
    const input = compiled.querySelector<HTMLInputElement>("#editor-name")!;
    input.value = value;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
}

describe("EntityEditor quality mode (EDT-25, EDT-28, EDT-29, VDE-11)", () => {
    it("opens a vocabulary rule in the quality form, not the attribute list (EDT-25, EDT-29)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-1" });
        arrive(fixture, httpMock, RULE_ANSWER, QUALITY_CHAIN);
        const kindsRequest = httpMock.expectOne(KINDS_URL);
        kindsRequest.flush(QUALITY_KINDS);
        fixture.detectChanges();

        // The kind Select stands where the attribute list would; the generic
        // description control (the markdown field, EDT-20) is gone (EDT-27).
        expect(compiled.querySelector(".aurelius-quality-kind")).toBeTruthy();
        expect(compiled.querySelector("textarea#editor-description")).toBeFalsy();
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("total_not_null");
        // Only the `fields` picker renders — the DataSet/m4i_referenceable
        // noise ends the derived chain carries stay out (EDT-25).
        const pickers = [...compiled.querySelectorAll<HTMLElement>(".aurelius-editor-relationship")];
        expect(pickers.map((picker) => picker.getAttribute("data-field"))).toEqual(["fields"]);
        expect(pickers[0]?.querySelector(".aurelius-token-chip")?.textContent).toContain("total");
    });

    it("opens a legacy rule in the generic form, unchecked (EDT-29)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-2" });
        arrive(fixture, httpMock, LEGACY_RULE_ANSWER, QUALITY_CHAIN);

        // No quality form, no kinds call; the pair attributes are not rendered
        // as editable fields either — the expression rides the save untouched
        // through the pass-through (EDT-29's last clause, proven at the save).
        expect(compiled.querySelector(".aurelius-quality-kind")).toBeFalsy();
        httpMock.expectNone(KINDS_URL);
        expect(compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")?.value).toContain(
            "A pair rule the scanner still reads (DQ-07).",
        );

        // Its Save is the door path (VDE-05): no validate call, expression rides.
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock.expectNone(RULE_VALIDATE_URL);
        const post = httpMock.expectOne(VIEW_POST_URL);
        const body = post.request.body as ViewSaveRequest;
        expect(body.attributes["expression"]).toBe("^\\d+$");
        post.flush({ ...LEGACY_RULE_ANSWER, updateTime: 1_700_000_090_000 });
        expect(navigate).toHaveBeenCalled();
    });

    it("validates before the POST, and posts the minimal quality body (EDT-28, EDT-27, VDE-11)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-1" });
        arrive(fixture, httpMock, RULE_ANSWER, QUALITY_CHAIN);
        httpMock.expectOne(KINDS_URL).flush(QUALITY_KINDS);
        fixture.detectChanges();
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        // The validate call first (EDT-28, VDE-11: quality validation stays
        // before the save): the draft's stored-rule shape.
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
        validate.flush({ valid: true, kind: "COLUMN_NOT_NULL_RATIO", dimension: "COMPLETENESS" });
        fixture.detectChanges();

        // The door save rides (VDE-05): the minimal body (no foreign dqpattern,
        // EDT-27) plus the fields picker's full value (VDE-04).
        const post = httpMock.expectOne(VIEW_POST_URL);
        const body = post.request.body as ViewSaveRequest;
        expect(body.attributes["dqpattern"]).toBeUndefined();
        expect(body.attributes["dqcheckkind"]).toBe("COLUMN_NOT_NULL_RATIO");
        expect(body.sections).toEqual([{ attribute: "fields", entities: ["f1"] }]);
        post.flush({ ...RULE_ANSWER, updateTime: 1_700_000_090_000 });
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "r-1"], drawer: null } }]);
    });

    it("an engine refusal keeps the line and posts nothing (EDT-28)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-1" });
        arrive(fixture, httpMock, RULE_ANSWER, QUALITY_CHAIN);
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
        httpMock.expectNone(VIEW_POST_URL);

        // A later edit clears the line (EDT-28); the next Save re-checks.
        typeRuleName(compiled, fixture, "total_not_null_v2");
        expect(compiled.querySelector(".aurelius-editor-notification")).toBeFalsy();
        httpMock.verify();
    });

    it("a validate transport failure answers the generic line, unchecked never saves (EDT-28)", () => {
        const { fixture, compiled, httpMock } = setup({ guid: "r-1" });
        arrive(fixture, httpMock, RULE_ANSWER, QUALITY_CHAIN);
        httpMock.expectOne(KINDS_URL).flush(QUALITY_KINDS);
        fixture.detectChanges();

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();
        httpMock.expectOne(RULE_VALIDATE_URL).flush({}, { status: 502, statusText: "Bad Gateway" });
        fixture.detectChanges();

        expect(normalize(compiled.querySelector(".aurelius-editor-notification")?.textContent)).toBe(
            "The rule could not be checked against the server. Try again.",
        );
        httpMock.expectNone(VIEW_POST_URL);
        httpMock.verify();
    });

    it("an incomplete quality form bails before the call (EDT-28/EDT-07)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "m4i_data_quality" });
        arriveTypeDefs(fixture, httpMock, "m4i_data_quality", QUALITY_CHAIN);
        httpMock.expectOne(KINDS_URL).flush(QUALITY_KINDS);
        fixture.detectChanges();

        compiled.querySelector<HTMLButtonElement>("button.aurelius-editor-save")!.click();
        fixture.detectChanges();

        httpMock.expectNone(RULE_VALIDATE_URL); // nothing drafted — nothing to check
        expect(normalize(compiled.querySelector(".aurelius-editor-notification")?.textContent)).toBe(
            "This entity can't be saved because one or more required fields are missing.",
        );
    });
});
