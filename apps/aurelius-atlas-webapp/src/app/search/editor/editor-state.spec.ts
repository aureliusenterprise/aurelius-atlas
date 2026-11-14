/**
 * The editor drawer's store on the view doors (VDE-01, VDE-05..VDE-10,
 * DD-608..DD-612): the read through `ViewEntityService`, the save as one door
 * POST (edit and create), the conflict re-edit, the name-taken line, a refusal
 * alert, and the success evict, tick, and navigation. The store is the door's
 * only caller, so the specs ride the real clients through
 * HttpTestingController — the wire each rule names is the one under test.
 */
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { Router, provideRouter } from "@angular/router";

import { ViewEntityService, type EntityView, type ViewSaveRequest } from "aurelius-atlas-data-access";

import { AlertsService } from "../../alerts/alerts.service";
import { EditorState } from "./editor-state";
import { EntitySaved } from "./entity-saved";

const VIEW_URL = "/api/aurelius/v1/entity/guid/";
const VIEW_POST_URL = "/api/aurelius/v1/entity";
const ATLAS_DELETE_URL = "/api/atlas/v2/entity/guid/7a1b";

/** The view the read door answers (VDE-01). */
function view(overrides: Partial<EntityView> = {}): EntityView {
    return {
        guid: "7a1b",
        typeName: "DataSet",
        qualifiedName: "genomic_variants@cluster",
        displayText: "genomic_variants",
        status: "ACTIVE",
        createTime: 1_700_000_000_000,
        updateTime: 1_700_000_021_000,
        classificationNames: ["PII"],
        stale: false,
        attributes: { name: "genomic_variants", owner: "analyst-3" },
        sections: [
            { attribute: "inputToProcesses", entities: [{ guid: "p1", name: "load_events", status: "ACTIVE" }] },
        ],
        ...overrides,
    };
}

/** One door body the shape the store posts (VDE-05). */
function body(overrides: Partial<ViewSaveRequest> = {}): ViewSaveRequest {
    return {
        guid: "7a1b",
        typeName: "DataSet",
        updateTime: 1_700_000_021_000,
        attributes: { name: "renamed_variants" },
        classifications: ["PII"],
        ...overrides,
    };
}

function setup() {
    TestBed.configureTestingModule({
        providers: [EditorState, provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    const state = TestBed.inject(EditorState);
    return { state, httpMock: TestBed.inject(HttpTestingController) };
}

describe("EditorState on the view doors (VDE-01, VDE-05..VDE-11)", () => {
    it("reads its entity through the read door and seeds the tag box (VDE-01, VDE-03)", () => {
        const { state, httpMock } = setup();

        state.loadEntity("7a1b");
        expect(state.loading()).toBe(true);
        const request = httpMock.expectOne(`${VIEW_URL}7a1b`);
        expect(request.request.method).toBe("GET");
        request.flush(view());

        expect(state.loading()).toBe(false);
        expect(state.view()?.guid).toBe("7a1b");
        // The tag box starts at the view's own names (VDE-03) — no client
        // propagated filter to retire (VDR-05).
        expect(state.chosen()).toEqual(["PII"]);
        // The Atlas-shaped draft the form reads answers from the view (DD-608).
        expect(state.entity()?.attributes?.["name"]).toBe("genomic_variants");
        httpMock.verify();
    });

    it("the second read of the same guid asks nothing — the cache serves it (VDE-01, DD-605)", () => {
        const { state, httpMock } = setup();

        state.loadEntity("7a1b");
        httpMock.expectOne(`${VIEW_URL}7a1b`).flush(view());
        state.loadEntity("7a1b");
        // No second request: the read door's client answers (VDR-07).
        httpMock.verify();
        expect(state.view()?.guid).toBe("7a1b");
    });

    it("a failed read alerts and keeps the drawer's empty state (EDT-02, VDE-01)", () => {
        const { state, httpMock } = setup();
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");

        state.loadEntity("missing");
        httpMock.expectOne(`${VIEW_URL}missing`).flush({}, { status: 404, statusText: "Not Found" });

        expect(state.loading()).toBe(false);
        expect(state.view()).toBeNull();
        expect(add).toHaveBeenCalledWith({
            severity: "error",
            source: "search",
            message: "Retrieving the entity details",
        });
    });

    it("an update save is one door POST carrying the base's version (VDE-05, AVW-04)", () => {
        const { state, httpMock } = setup();
        state.view.set(view());
        vi.spyOn(TestBed.inject(Router), "navigate"); // the success path navigates

        state.save(body());
        const request = httpMock.expectOne(VIEW_POST_URL);
        expect(request.request.method).toBe("POST");
        // One request carries everything: attributes, tags, ends (VDE-03/04/05).
        expect(request.request.body).toEqual(body());
        request.flush(view({ updateTime: 1_700_000_090_000 }));
        httpMock.verify(); // no classification add/delete pair follows (DD-326 retired)
    });

    it("a create save names no guid (VDE-05, DD-592)", () => {
        const { state, httpMock } = setup();

        state.beginCreate("DataSet");
        state.save({
            typeName: "DataSet",
            attributes: { name: "fresh", qualifiedName: "uuid-1" },
            classifications: [],
        });
        const request = httpMock.expectOne(VIEW_POST_URL);
        const posted = request.request.body as ViewSaveRequest;
        expect("guid" in posted).toBe(false);
        // The answer carries the server's guid (AVW-06): it is evicted and
        // the drawer lands on the entity's details (VDE-10).
        const evict = vi.spyOn(TestBed.inject(ViewEntityService), "evict");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        request.flush(view({ guid: "9999", updateTime: 1_700_000_090_000 }));
        expect(evict).toHaveBeenCalledWith("9999");
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "9999"], drawer: null } }]);
    });

    it("a success evicts the saved guid, fires the tick, and navigates (VDE-10, DD-327)", () => {
        const { state, httpMock } = setup();
        state.view.set(view());
        const evict = vi.spyOn(TestBed.inject(ViewEntityService), "evict");
        const saved = TestBed.inject(EntitySaved);
        const before = saved.latest()?.seq ?? 0;
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        state.save(body());
        httpMock.expectOne(VIEW_POST_URL).flush(view({ updateTime: 1_700_000_090_000 }));

        // The eviction runs before the tick, so the details re-read asks the door.
        expect(evict).toHaveBeenCalledWith("7a1b");
        expect(saved.latest()?.seq).toBeGreaterThan(before);
        expect(saved.latest()?.guid).toBe("7a1b");
        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "7a1b"], drawer: null } }]);
    });

    it("a lost version race re-edits from the stored view (VDE-07, DD-610)", () => {
        const { state, httpMock } = setup();
        const before = view();
        state.view.set(before);
        state.chosen.set(["PII"]);
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const stored = view({ updateTime: 2_000_000_000_000, classificationNames: ["PII", "APPROVED"] });
        state.save(body());
        httpMock
            .expectOne(VIEW_POST_URL)
            .flush({ errorCode: "ENTITY_VERSION_CONFLICT", view: stored }, { status: 409, statusText: "Conflict" });

        // No alert, no navigation (DD-591's reload-and-reedit): the base moves
        // to the stored view and the event waits for the component.
        expect(add).not.toHaveBeenCalled();
        expect(navigate).not.toHaveBeenCalled();
        expect(state.view()?.updateTime).toBe(2_000_000_000_000);
        expect(state.conflict()).toEqual({ from: before, to: stored });
        // The tag box answers the stored set (VDE-07): nothing was removed.
        expect(state.chosen()).toEqual(["PII", "APPROVED"]);

        // A second Save rides the stored updateTime — it merges onto the base.
        state.conflictHandled();
        expect(state.conflict()).toBeNull();
        state.save(body({ updateTime: 2_000_000_000_000 }));
        httpMock.expectOne(VIEW_POST_URL).flush(stored);
    });

    it("a taken name answers its own line and keeps the drawer open (VDE-08, AVW-06)", () => {
        const { state, httpMock } = setup();
        state.beginCreate("DataSet");
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        state.save({
            typeName: "DataSet",
            attributes: { name: "already_there", qualifiedName: "dup" },
            classifications: [],
        });
        httpMock
            .expectOne(VIEW_POST_URL)
            .flush(
                { errorCode: "ENTITY_NAME_TAKEN", errorMessage: "qualifiedName already exists" },
                { status: 409, statusText: "Conflict" },
            );

        // One alert naming the taken name — not the conflict path, no navigation.
        expect(add).toHaveBeenCalledTimes(1);
        expect(add).toHaveBeenCalledWith({
            severity: "error",
            source: "search",
            message: "That name is already held by another entity.",
        });
        expect(state.conflict()).toBeNull();
        expect(navigate).not.toHaveBeenCalled();
    });

    it("any other failure is the one EDT-08 alert (VDE-09)", () => {
        const { state, httpMock } = setup();
        state.view.set(view());
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        state.save(body());
        httpMock
            .expectOne(VIEW_POST_URL)
            .flush(
                { errorCode: "ATLAS-403-00-001", errorMessage: "forbidden" },
                { status: 403, statusText: "Forbidden" },
            );

        expect(add).toHaveBeenCalledTimes(1);
        expect(add).toHaveBeenCalledWith({ severity: "error", source: "search", message: "Saving the entity" });
        expect(state.saving()).toBe(false);
        expect(navigate).not.toHaveBeenCalled();
    });

    it("the delete stays on the Atlas route and lands on browse (VDE-11, EDT-19)", () => {
        const { state, httpMock } = setup();
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        state.delete("7a1b");
        const request = httpMock.expectOne(ATLAS_DELETE_URL);
        expect(request.request.method).toBe("DELETE");
        request.flush({ guidAssignments: {} });

        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "browse"], drawer: null } }]);
    });

    it("a create seeds no temporary guid and clears the tag box (VDE-05, DD-592)", () => {
        const { state } = setup();
        state.chosen.set(["PII"]);

        state.beginCreate("DataSet");

        expect(state.selectedTypeName()).toBe("DataSet");
        expect(state.typeName()).toBe("DataSet"); // the form renders the picked type
        expect(state.chosen()).toEqual([]);
        // The draft carries the client's qualified name and no guid.
        expect(state.entity()?.guid).toBeUndefined();
        expect(state.entity()?.attributes?.["qualifiedName"]).toMatch(
            /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
        );
    });

    it("the chain read caches by name so a re-pick asks nothing (VDE-02, DD-611)", () => {
        const { state, httpMock } = setup();

        state.loadChain("DataSet");
        httpMock
            .expectOne("/api/aurelius/v1/types/for-type/DataSet")
            .flush({ type: { name: "DataSet" }, superTypes: [{ name: "Asset" }, { name: "Referenceable" }] });
        expect(state.chainDefs().map((def) => def.name)).toEqual(["DataSet", "Asset", "Referenceable"]);

        // Already in hand: the guard asks nothing (a re-pick of the same type).
        state.loadChain("DataSet");
        state.loadChain("Asset"); // a supertype the door already answered whole
        httpMock.verify();
    });

    it("the three slices feed the tag box, the enums, and the picker (VDE-02, DD-611)", () => {
        const { state, httpMock } = setup();

        state.loadSlices();
        httpMock
            .expectOne("/api/atlas/v2/types/typedefs?type=CLASSIFICATION")
            .flush({ classificationDefs: [{ name: "PII", entityTypes: ["DataSet"] }, { name: "FINANCE" }] });
        httpMock.expectOne("/api/atlas/v2/types/typedefs?type=ENUM").flush({ enumDefs: [{ name: "RiskLevel" }] });
        httpMock
            .expectOne("/api/atlas/v2/types/typedefs/headers?type=ENTITY")
            .flush([{ name: "DataSet" }, { name: "AtlasGlossary" }, { name: "__Internal" }]);

        expect(state.classificationDefs().map((def) => def.name)).toEqual(["PII", "FINANCE"]);
        expect(state.enumsByName().has("RiskLevel")).toBe(true);
        // The picker drops the glossary types and the internals (EDT-04).
        expect(state.pickerTypes().map((row) => row.name)).toEqual(["DataSet"]);
    });

    it("a slice failure alerts once and leaves its list empty (VDE-02)", () => {
        const { state, httpMock } = setup();
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");

        state.loadSlices();
        httpMock
            .expectOne("/api/atlas/v2/types/typedefs?type=CLASSIFICATION")
            .flush({}, { status: 500, statusText: "Server Error" });
        httpMock.expectOne("/api/atlas/v2/types/typedefs?type=ENUM").flush({ enumDefs: [] });
        httpMock.expectOne("/api/atlas/v2/types/typedefs/headers?type=ENTITY").flush([]);

        expect(state.classificationDefs()).toEqual([]);
        expect(add).toHaveBeenCalledWith({
            severity: "error",
            source: "search",
            message: "Retrieving the classification type definition",
        });
    });

    it("a tag add and remove move the chosen names the door body carries (VDE-03, EDT-05)", () => {
        const { state } = setup();
        state.chosen.set(["PII"]);

        state.addClassification("CONFIDENTIAL");
        expect(state.chosen()).toEqual(["PII", "CONFIDENTIAL"]);
        state.addClassification("PII"); // already held — no repeat
        expect(state.chosen()).toEqual(["PII", "CONFIDENTIAL"]);
        state.removeClassification("PII");
        expect(state.chosen()).toEqual(["CONFIDENTIAL"]);
    });
});
