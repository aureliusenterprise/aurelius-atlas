import { ViewportScroller } from "@angular/common";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter, type UrlTree } from "@angular/router";
import { By } from "@angular/platform-browser";
import Keycloak from "keycloak-js";
import { Subject } from "rxjs";
import { faPenToSquare } from "@fortawesome/free-solid-svg-icons";

import type { EntityRelation, EntityView, RelationEntity } from "aurelius-atlas-data-access";
import { Breadcrumbs, PropertiesItem } from "aurelius-atlas-ui";

import modelFixture from "../../../../tests/fixtures/lineage-graph.extract.json";

import { AlertsService } from "../../alerts/alerts.service";
import { VersionService } from "../../shell/version.service";
import { APP_CONFIG } from "../../tokens";
import { EntityWritten } from "../editor/entity-written";

import { Details } from "./details.component";

/**
 * The details screen on its data spine (DET-08..DET-13, 7.20, VDR-01): the
 * route's guid drives one `GET /api/aurelius/v1/entity/guid/{guid}` — the
 * view family's read door (ADR 064) — the header/description/properties
 * bind to the view that answers (DET-09..DET-11, VDR-04..VDR-06), and every
 * no-entity state keeps the 7.6 empty shape (DET-02, VDR-08). The specs
 * ride the results screen's idiom: a `paramMap` Subject so a guid change is
 * observable, `expectOne` + `flush` for the arrival, `detectChanges` to let
 * the effects and signals settle.
 */
const VIEW_URL = "/api/aurelius/v1/entity/guid/";

/** The layout dispatch's typedef read (DET-15): `/v2/types/typedef/name/{name}`. */
const TYPEDEF_URL = "/api/atlas/v2/types/typedef/name/";

/** The read door's answer for the fixture entity: two renderable properties. */
const ANSWER: EntityView = {
    guid: "7a1b",
    typeName: "DataSet",
    displayText: "genomic_variants",
    name: "genomic_variants",
    qualifiedName: "genomic_variants@cluster",
    status: "ACTIVE",
    stale: false,
    classificationNames: ["PII", "CONFIDENTIAL"],
    attributes: {
        name: "genomic_variants",
        qualifiedName: "genomic_variants@cluster",
        description: "Curated variant calls.",
        owner: "analyst-3",
    },
};

/** The view minus its classification names — the chip-less variant (VDR-05). */
const NO_CHIPS: EntityView = { ...ANSWER, classificationNames: [] };

/** The view with a tag propagation brought (VDR-12, DV-197): own names stay
 *  PII/CONFIDENTIAL, and PII additionally rides in as a propagated entry.
 *  The first source sits under a stored parent (its row shows the path, not
 *  the type, DD-836); the second has none and so shows its name alone. */
const PROPAGATED: EntityView = {
    ...ANSWER,
    propagatedClassifications: [
        {
            typeName: "PII",
            entities: [
                {
                    guid: "src-1",
                    name: "source_table",
                    typeName: "m4i_dataset",
                    status: "ACTIVE",
                    breadcrumb: [{ guid: "dom-1", name: "Genomics", typeName: "m4i_data_domain" }],
                },
                { guid: "src-2", name: "other_table", typeName: "Process", status: "ACTIVE" },
            ],
        },
    ],
};

/**
 * Bring the screen up at the given guid: the paramMap Subject carries the
 * address (a guid change is then observable), and the first
 * `detectChanges` lets the URL effect fire the read. The fake Keycloak
 * answers `canWrite` for the editor pencil (EDT-09): granted unless a
 * test passes `atlasWrite: false`.
 */
function setup(guid = "7a1b", { atlasWrite = true }: { atlasWrite?: boolean } = {}) {
    const paramMap = new Subject<ParamMap>();
    // The router's fragment feed (DD-381): a plain Subject — toSignal seeds
    // the initial null, and the deep-link test pushes after creation.
    const fragment$ = new Subject<string | null>();
    TestBed.configureTestingModule({
        imports: [Details],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            provideRouter([]),
            { provide: ActivatedRoute, useValue: { paramMap, fragment: fragment$ } },
            { provide: APP_CONFIG, useValue: { atlasClientId: "aurelius-atlas-server" } },
            {
                provide: Keycloak,
                useValue: { hasResourceRole: (role: string) => atlasWrite && role === "atlas-write" },
            },
            // The lineage box's save flow reads the version (VER-01, DD-725);
            // the screen's own reads are what this spec verifies, so the
            // version never leaves this stub (its fetch is its service's spec).
            { provide: VersionService, useValue: { version: signal("7.34.0#abc1234") } },
        ],
    });
    const fixture = TestBed.createComponent(Details);
    paramMap.next(convertToParamMap({ guid }));
    fixture.detectChanges(); // the URL effect runs, the request fires
    const compiled = fixture.nativeElement as HTMLElement;
    return {
        fixture,
        compiled,
        paramMap,
        fragment: fragment$,
        httpMock: TestBed.inject(HttpTestingController),
    };
}

/** Deliver the view for the in-flight read and settle the screen. */
function arrive(fixture: { detectChanges: () => void }, httpMock: HttpTestingController, body = ANSWER) {
    httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(body);
    fixture.detectChanges();
    settleTypeDefs(httpMock);
}

/**
 * One view section carrying the given ends. The fixture ends stay loose
 * (`Record<string, unknown>`) on purpose: the guidless and DELETED entries
 * the fixtures carry are not representable as a `RelationEntity`.
 */
function ends(attribute: string, seed: readonly Record<string, unknown>[]): EntityRelation {
    return { attribute, entities: seed as unknown as RelationEntity[] };
}

/** The view's sections, one per key in ``seeds``. */
function sectionsOf(seeds: Record<string, readonly Record<string, unknown>[]>): EntityRelation[] {
    return Object.entries(seeds).map(([attribute, seed]) => ends(attribute, seed));
}

/**
 * Settle the DET-15 layout walk: a type that is not one of the seven reads
 * its typedef; every fixture type here is `DataSet` or `m4i_*` with no
 * layout of its own to walk, so a "no typedef" answer (the built-in
 * error, DET-15) ends the walk and keeps the default layout.
 */
function settleTypeDefs(httpMock: HttpTestingController): void {
    for (const request of httpMock.match((r) => r.url.startsWith(TYPEDEF_URL))) {
        request.flush({}, { status: 404, statusText: "Not Found" });
    }
}

const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

describe("Details data spine (DET-08..DET-13)", () => {
    it("fetches the entity by guid on arrival (DET-08, VDR-01)", () => {
        const { httpMock } = setup("g-42");

        const request = httpMock.expectOne("/api/aurelius/v1/entity/guid/g-42");
        expect(request.request.method).toBe("GET");
        request.flush(ANSWER);
    });

    it("re-fetches on a guid change and ignores a stale answer (DET-08, DD-318)", () => {
        const { fixture, compiled, paramMap, httpMock } = setup("first");

        // Two reads in flight: the first guid's answer arrives after the
        // screen moved on, and must not paint (the legacy
        // EntityDetailsService.latestEntityId guard).
        const first = httpMock.expectOne("/api/aurelius/v1/entity/guid/first");
        paramMap.next(convertToParamMap({ guid: "second" }));
        fixture.detectChanges();
        const second = httpMock.expectOne("/api/aurelius/v1/entity/guid/second");

        first.flush(ANSWER); // stale: its entity names a different screen
        fixture.detectChanges();
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("Entity type");

        second.flush({ ...ANSWER, guid: "second", attributes: { name: "second" } });
        fixture.detectChanges();
        settleTypeDefs(httpMock);
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("second");
    });

    it("issues exactly one read per guid: no second client (DET-08)", () => {
        const { fixture, compiled, httpMock } = setup();

        const requests = httpMock.match((request) => request.url.startsWith(VIEW_URL));
        expect(requests).toHaveLength(1);
        requests[0].flush(ANSWER);
        fixture.detectChanges();
        settleTypeDefs(httpMock);

        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("genomic_variants");
    });

    it("binds the header: title, type-name line, one chip per classification (DET-09)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("genomic_variants");
        const typeLine = compiled.querySelector(".aurelius-details-type");
        expect(typeLine?.querySelector("aurelius-atlas-ui-type-name")).toBeTruthy();
        expect(normalize(typeLine?.textContent)).toContain("DataSet");

        // The chips carry the dictionary display names (DET-09, DD-379);
        // CONFIDENTIAL is outside the dictionary and stays raw, as the
        // legacy's missing translate key rendered it.
        const chips = [...compiled.querySelectorAll(".aurelius-details-classifications .control")].map((control) =>
            normalize(control.textContent),
        );
        expect(chips).toEqual(["Has PII", "CONFIDENTIAL"]);
    });

    it("falls back: no name, qualifiedName titles; neither, the localized label (DET-09)", () => {
        const { fixture, compiled, paramMap, httpMock } = setup();
        arrive(fixture, httpMock, {
            ...ANSWER,
            name: undefined,
            displayText: "qualified@only",
            attributes: { qualifiedName: "qualified@only" },
        });
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("qualified@only");

        // With neither attribute the fallback title returns (DET-02 shape
        // restored): the same localized chrome label the 7.6 skeleton rode.
        paramMap.next(convertToParamMap({ guid: "blank" }));
        fixture.detectChanges();
        arriveSecond(fixture, httpMock, { ...ANSWER, guid: "blank", name: undefined, attributes: {} });
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("Entity type");
    });

    it("renders no chips when the entity carries none (DET-09)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, NO_CHIPS);

        expect(compiled.querySelector(".aurelius-details-classifications")).toBeNull();
    });

    it("marks a propagated tag in the same chip row and names its sources (DET-09, VDR-12, DV-197)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, PROPAGATED);

        // One row carries both kinds (DD-834): the entity's own chips first,
        // the propagated one after them — and it is the chip's own marker.
        const controls = [...compiled.querySelectorAll(".aurelius-details-classifications .control")];
        expect(controls).toHaveLength(3);
        expect(normalize(controls[2].textContent)).toContain("Has PII");
        const marker = controls[2].querySelector(".tag.is-primary.dropdown.is-hoverable");
        expect(marker).toBeTruthy();
        expect(marker?.getAttribute("title")).toBe("Is propagated");
        // A source row shows what a card line shows (DD-836): the type icon,
        // the name, and the path it sits on in place of the type name.
        const sources = [...controls[2].querySelectorAll(".aurelius-details-source")];
        expect(sources).toHaveLength(2);
        expect(normalize(sources[0].querySelector(".aurelius-details-source-name")?.textContent)).toBe("source_table");
        // The icon wears the type map's family ink, as a badge's or a crumb's
        // does (DET-26) — a DataSet's icon is `technical`.
        const sourceIcon = sources[0].querySelector(".aurelius-details-source-icon fa-icon");
        expect(sourceIcon).toBeTruthy();
        expect(sourceIcon?.classList.contains("technical")).toBe(true);
        // The path is the stored parents only — the source's own name is the
        // row's, so the crumb trail of the row must not repeat it.
        expect(normalize(sources[0].querySelector(".aurelius-details-source-path")?.textContent)).toBe("Genomics");
        expect(sources[0].querySelectorAll(".aurelius-details-source-path .breadcrumb li")).toHaveLength(1);
        // No stored parent, no path (DD-630) — and no type line either, which
        // the review took out of the row.
        expect(normalize(sources[1].querySelector(".aurelius-details-source-name")?.textContent)).toBe("other_table");
        expect(sources[1].querySelector(".aurelius-details-source-path")).toBeNull();
        expect(sources[1].querySelector(".aurelius-details-source-icon")).toBeNull();
        expect(compiled.querySelector(".aurelius-details-source-type")).toBeNull();
    });

    it("routes to the source's details when its row is clicked (VDR-12, DV-197)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, PROPAGATED);

        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        // The row is a container — a button cannot hold the trail's links
        // (DD-836) — and the source's activation is its name button, which
        // carries the icon and stays the keyboard path (VDR-12).
        const row = compiled.querySelector(".aurelius-details-source") as HTMLElement;
        expect(row.tagName).toBe("DIV");
        const name = row.querySelector("button.aurelius-details-source-name") as HTMLButtonElement;
        expect(name.querySelector(".aurelius-details-source-icon fa-icon")).toBeTruthy();
        name.click();

        expect(navigate).toHaveBeenCalledTimes(1);
        expect(navigate).toHaveBeenCalledWith(["/search/details", "src-1"]);
    });

    it("routes to a breadcrumb of the source's path, not to the source (VDR-12, DD-836)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, PROPAGATED);

        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        // The trail rides inside the row with its links on: a crumb names its
        // own entity, and its click must not also open the source.
        const crumb = compiled.querySelector(".aurelius-details-source-path .breadcrumb a") as HTMLAnchorElement;
        expect(crumb).toBeTruthy();
        crumb.click();

        expect(navigate).toHaveBeenCalledTimes(1);
        expect(navigate).toHaveBeenCalledWith(["/search/details", "dom-1"]);
    });

    it("still marks a propagated tag whose source the store lost (VDR-12)", () => {
        const { fixture, compiled, httpMock } = setup();
        // The door answers the name with no entities: the tag stays the
        // entity's to show, only its origin is unknown.
        arrive(fixture, httpMock, {
            ...ANSWER,
            classificationNames: [],
            propagatedClassifications: [{ typeName: "PII", entities: [] }],
        });

        const controls = [...compiled.querySelectorAll(".aurelius-details-classifications .control")];
        expect(controls).toHaveLength(1);
        expect(controls[0].querySelector(".tag.is-primary.dropdown.is-hoverable")).toBeTruthy();
        expect(controls[0].querySelector(".aurelius-details-source")).toBeNull();
    });

    it("shows the description from the description attribute (DET-10, SPA-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(normalize(compiled.querySelector(".aurelius-details-description")?.textContent)).toBe(
            "Curated variant calls.",
        );
    });

    it("shows the legacy placeholder when the attribute does not exist (DET-10, DD-321)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, { ...ANSWER, name: "no-description", attributes: { name: "no-description" } });

        // The legacy description component's noDescription template: an
        // italic centered line in place of the markdown block.
        expect(compiled.querySelector(".aurelius-details-description")).toBeNull();
        expect(normalize(compiled.querySelector(".aurelius-details-description-empty")?.textContent)).toBe(
            "No description available.",
        );
    });

    it("renders the description as markdown (DET-10, DD-321)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, {
            ...ANSWER,
            attributes: { ...ANSWER.attributes, description: "Curated **variant** calls." },
        });

        const box = compiled.querySelector(".aurelius-details-description");
        // The asterisks are gone and the emphasis landed as markup.
        expect(normalize(box?.textContent)).toBe("Curated variant calls.");
        expect(box!.querySelector("strong")!.textContent).toBe("variant");
    });

    it("shows the prose the one attribute holds and keeps it out of the rows (DET-10, DET-11, DD-320, SPA-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, {
            ...ANSWER,
            name: "atlas-typed",
            attributes: { name: "atlas-typed", description: "A seeded description." },
        });

        // 18.8 (ADR 070) retired the second prose key: the box shows
        // `description` (DET-10) and the table drops it (DD-320 — the shown
        // key appears once on the screen, the blacklist's own mechanism).
        expect(normalize(compiled.querySelector(".aurelius-details-description")?.textContent)).toBe(
            "A seeded description.",
        );
        expect(compiled.querySelectorAll(".aurelius-details-properties tbody tr")).toHaveLength(0);
        expect(normalize(compiled.querySelector(".aurelius-details-property-count")?.textContent)).toBe("0");

        // The zero-row swap (DET-11): the legacy shell shows the noData line
        // in place of the table, headers included.
        expect(compiled.querySelector("table.aurelius-details-properties")).toBeNull();
        expect(normalize(compiled.querySelector(".aurelius-details-properties-empty")?.textContent)).toBe(
            "No data available",
        );
    });

    it("shows no placeholder while rows render (DET-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(compiled.querySelector("table.aurelius-details-properties")).toBeTruthy();
        expect(compiled.querySelectorAll(".aurelius-details-properties tbody tr")).toHaveLength(1);
        expect(compiled.querySelector(".aurelius-details-properties-empty")).toBeNull();
    });

    it("renders the filtered, sorted property rows and the count (DET-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // name and qualifiedName are blacklisted (the legacy filter) and the
        // shown description leaves the table (DD-320): owner is the renderable
        // one.
        const rows = [...compiled.querySelectorAll(".aurelius-details-properties tbody tr")].map((row) =>
            normalize(row.querySelector("td")?.textContent),
        );
        expect(rows).toEqual(["owner"]);
        expect(normalize(compiled.querySelector(".aurelius-details-property-count")?.textContent)).toBe("1");
    });

    it("routes the details screen when a property link is clicked (DET-11, DET-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        // VDR-04: the section's ends merge into the table as a link array —
        // the row the Atlas GET's merged relationshipAttributes answered. A read
        // end carries its type and state (AVS-04), which is what marks it as the
        // entity's own relationship attribute rather than a card's derived pair.
        arrive(fixture, httpMock, {
            ...ANSWER,
            sections: [
                ends("upstreamDatasets", [{ guid: "linked-1", displayText: "Upstream", typeName: "m4i_dataset" }]),
            ],
        });

        // Sorted rows: owner, upstreamDatasets — the shown description leaves
        // the table (DD-320), so the link is the second, and the only one whose
        // value is a guid array (DET-11).
        const rows = [...compiled.querySelectorAll(".aurelius-details-properties tbody tr")];
        expect(rows.map((row) => normalize(row.querySelector("td")?.textContent))).toEqual([
            "owner",
            "upstreamDatasets",
        ]);

        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const items = fixture.debugElement.queryAll(By.directive(PropertiesItem));
        (items[1].componentInstance as PropertiesItem).itemClicked.emit("linked-1");

        expect(navigate).toHaveBeenCalledWith(["/search/details", "linked-1"]);
    });

    it("renders the view's stored trail with its own crumb active, and routes a crumb click (DET-12, VDR-06, DD-606)", () => {
        const { fixture, compiled, httpMock } = setup("current");
        // The seam of 7.20 (DD-317) is filled: the door answers the view
        // with the index document's stored breadcrumb, top down (VDR-06).
        arrive(fixture, httpMock, {
            ...ANSWER,
            guid: "current",
            breadcrumb: [
                { guid: "g1", name: "Genomics", typeName: "m4i_data_domain" },
                { guid: "g2", name: null, typeName: "m4i_dataset" },
                { guid: "g3", name: null, typeName: null },
            ],
        });

        const crumbs = [...compiled.querySelectorAll("nav.breadcrumb li")];
        // The stored trail plus the opened entity's own crumb last, marked
        // active (DD-606). Each crumb shows its name, or its type, or its
        // guid — g2 lost its name (ASU-02), g3 both (VDR-06's fallbacks),
        // and the opened entity leads with its own name.
        expect(crumbs.map((crumb) => normalize(crumb.textContent))).toEqual([
            "Genomics",
            "m4i_dataset",
            "g3",
            "genomic_variants",
        ]);
        expect(crumbs[3].classList.contains("is-active")).toBe(true);
        // Icons ride the app's type map (DET-26's resolver): the mapped
        // domain crumb draws one, the unmapped DataSet crumb stays text-only.
        expect(crumbs[0].querySelector("fa-icon svg")).toBeTruthy();
        expect(crumbs[3].querySelector(".icon")).toBeNull();

        // The routing contract is proven at the component boundary: the
        // lib's emit reaches the screen's router call, the lib never routes.
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const trail = fixture.debugElement.query(By.directive(Breadcrumbs)).componentInstance as Breadcrumbs;
        trail.itemClicked.emit("g2");
        expect(navigate).toHaveBeenCalledWith(["/search/details", "g2"]);
    });

    it("an entity without a stored parent shows no trail (VDR-06 amended, VDR-11, DD-630)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock); // ANSWER carries no breadcrumb

        // The legacy guard draws no trail for a parentless entity: the one
        // crumb would repeat the title right above it (DD-630).
        expect(compiled.querySelector("nav.breadcrumb")).toBeNull();
    });

    it("shows the localized loading line while the first read is in flight (DET-13)", () => {
        const { compiled } = setup();

        // The bridge string (SHL-08, DD-144): search.services.entityDetails.retrieve.
        expect(normalize(compiled.querySelector(".aurelius-details-loading")?.textContent)).toBe(
            "Retrieving the entity details",
        );
    });

    it("hides the loading line once the entity arrives (DET-13)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(compiled.querySelector(".aurelius-details-loading")).toBeNull();
    });

    it("keeps the empty state and alerts on a failed read (DET-13, ALR-05)", () => {
        const { fixture, compiled, httpMock } = setup();
        // The store strips its merge key from the feed rows, so the
        // feature's own call is what the spec pins.
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");

        httpMock.expectOne(`${VIEW_URL}7a1b`).flush({ error: "boom" }, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("Entity type");
        expect(compiled.querySelectorAll(".aurelius-details-properties tbody tr")).toHaveLength(0);
        expect(add).toHaveBeenCalledWith({
            severity: "error",
            source: "search",
            message: "Retrieving the entity details",
        });
    });

    it("answers a 404 with the empty state and no alert (DET-13, ALR-05)", () => {
        const { fixture, compiled, httpMock } = setup("missing");

        httpMock.expectOne(`${VIEW_URL}missing`).flush({}, { status: 404, statusText: "Not Found" });
        fixture.detectChanges();

        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("Entity type");
        expect(compiled.querySelector(".aurelius-details-loading")).toBeNull();
        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(false);
    });

    it("keeps the guid from the route as the screen's address (DET-01, DET-07)", () => {
        const { fixture, httpMock } = setup("guid-from-route");
        httpMock.expectOne("/api/aurelius/v1/entity/guid/guid-from-route").flush(ANSWER);

        const crumbs = fixture.debugElement.query(By.directive(Breadcrumbs)).componentInstance as Breadcrumbs;
        expect(crumbs.activeGuid()).toBe("guid-from-route");
    });

    it("shows the editor pencil with the atlas-write grant (EDT-09, DD-324)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pencil = compiled.querySelector<HTMLButtonElement>("button.aurelius-details-edit");
        expect(pencil).toBeTruthy();
        expect(pencil?.getAttribute("aria-label")).toBe("Edit entity");
        expect(pencil?.querySelector("fa-icon")).toBeTruthy();

        // The glyph is the demo header's edit icon — FA's `fa-edit`, i.e.
        // FA6 `faPenToSquare` (DD-346): the rendered icon input, pinned by
        // identity — earlier glyphs rendered here unnoticed until a user
        // compared the button against the demo.
        const icon = fixture.debugElement.query(By.css("button.aurelius-details-edit fa-icon"));
        expect(icon.componentInstance.icon()).toBe(faPenToSquare);
    });

    it("hides the editor pencil without the grant (EDT-09)", () => {
        const { fixture, compiled, httpMock } = setup("7a1b", { atlasWrite: false });
        arrive(fixture, httpMock);

        expect(compiled.querySelector("button.aurelius-details-edit")).toBeNull();
    });

    it("the pencil opens the editor drawer at edit/:guid (EDT-01, DD-322)", () => {
        const { fixture, compiled, httpMock } = setup("pencil-guid");
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLButtonElement>("button.aurelius-details-edit")!.click();

        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: ["edit", "pencil-guid"] } }]);
    });

    it("the editor's save tick re-reads this screen's entity (DD-327)", () => {
        const { fixture, compiled, httpMock } = setup("saved-guid");
        arrive(fixture, httpMock);

        TestBed.inject(EntityWritten).notify("saved-guid", "saved");
        fixture.detectChanges();

        // The still-mounted screen re-reads the saved entity: the save tick
        // evicts the cached view first (VDR-07, DD-605), so the door answers
        // again (the drawer save never changed this URL, so the router
        // reused the component).
        const second = httpMock.expectOne("/api/aurelius/v1/entity/guid/saved-guid");
        expect(second.request.method).toBe("GET");
        second.flush({ ...ANSWER, attributes: { name: "renamed_after_save" } });
        fixture.detectChanges();
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("renamed_after_save");
    });

    it("a save tick for another guid reads nothing (DD-327)", () => {
        const { fixture, compiled, httpMock } = setup("saved-guid");
        arrive(fixture, httpMock);

        TestBed.inject(EntityWritten).notify("some-other-guid", "saved");
        fixture.detectChanges();

        httpMock.expectNone("/api/aurelius/v1/entity/guid/saved-guid");
        // The screen's own read is already flushed above; nothing else fires
        // and the rendered entity stays as it arrived.
        httpMock.verify();
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("genomic_variants");
    });
});

/** A related-entity end of a seeded view section (VDR-03). */
function end(guid: string, displayText: string): Record<string, unknown> {
    return { guid, displayText, typeName: "m4i_data_attribute", name: displayText };
}

/** A related-entity end naming one type (7.21c's lineage ends). */
function endOf(guid: string, typeName: string, displayText: string): Record<string, unknown> {
    return { guid, displayText, typeName, name: displayText };
}

/** A person end of a seeded view section, or of a bulk answer's edges. */
function person(guid: string, displayText: string): Record<string, unknown> {
    return { guid, displayText, typeName: "person" };
}

/** The m4i entity's view, overridable per spec. */
function m4iEntity(overrides: Partial<EntityView> = {}): EntityView {
    return {
        guid: "m4i-1",
        typeName: "m4i_data_entity",
        displayText: "variants_entity",
        name: "variants_entity",
        qualifiedName: "variants@cluster",
        status: "ACTIVE",
        stale: false,
        attributes: {
            name: "variants_entity",
            qualifiedName: "variants@cluster",
            description: "A governed entity.",
        },
        sections: sectionsOf({
            attributes: [end("a1", "gene_symbol"), end("a2", "chromosome")],
            businessOwner: [person("p1", "Ada")],
            steward: [person("p2", "Lin"), person("p2", "Lin again")],
            domainLead: [person("p3", "Ada Lead")],
        }),
        ...overrides,
    };
}

/** The read door's answer for a card; the shape every section fixture builds on. */
function doorCard(guid: string, typeName: string, displayText: string, extra: Record<string, unknown> = {}) {
    return {
        guid,
        typeName,
        displayText,
        qualifiedName: `${displayText}@cluster`,
        status: "ACTIVE",
        stale: false,
        ...extra,
    };
}

/** A search door answer for the given cards (VCF-02, DD-615). */
function doorAnswer(cards: Record<string, unknown>[]): Record<string, unknown> {
    return { cards, facets: {}, total: cards.length };
}

/** The door answer for the two seeded attributes; extra overrides per guid. */
function attributesAnswer(overrides: Record<string, Record<string, unknown>> = {}): Record<string, unknown> {
    return doorAnswer([
        doorCard("a1", "m4i_data_attribute", "gene_symbol", {
            definition: "HGNC symbol.",
            ...overrides["a1"],
        }),
        doorCard("a2", "m4i_data_attribute", "chromosome", {
            definition: "The pair.",
            ...overrides["a2"],
        }),
    ]);
}

/**
 * The m4i dataset body with its lineage ends (DET-32): one process on
 * `outputFromProcesses` (a producer) and the same on `inputToProcesses` (a
 * consumer), no fields and no children.
 */
function m4iDataset(overrides: Partial<EntityView> = {}): EntityView {
    return {
        guid: "ds-1",
        typeName: "m4i_dataset",
        displayText: "hourly_index",
        name: "hourly_index",
        qualifiedName: "hourly_index@cluster",
        status: "ACTIVE",
        stale: false,
        attributes: { name: "hourly_index", qualifiedName: "hourly_index@cluster" },
        sections: sectionsOf({
            outputFromProcesses: [endOf("pr-1", "m4i_generic_process", "build_index")],
            inputToProcesses: [endOf("pr-1", "m4i_generic_process", "build_index")],
        }),
        ...overrides,
    };
}

/** The door answer for the dataset's two lineage sections: the one process. */
function processAnswer(): Record<string, unknown> {
    return doorAnswer([doorCard("pr-1", "m4i_generic_process", "build_index", { definition: "Indexes it." })]);
}

/** The m4i process body: the three forward ends of DET-33's row. */
function m4iProcess(overrides: Partial<EntityView> = {}): EntityView {
    return {
        guid: "pr-1",
        typeName: "m4i_generic_process",
        displayText: "build_index",
        name: "build_index",
        qualifiedName: "build_index@cluster",
        status: "ACTIVE",
        stale: false,
        attributes: { name: "build_index", qualifiedName: "build_index@cluster" },
        sections: sectionsOf({
            system: [endOf("sy-1", "m4i_system", "elastic1")],
            inputs: [endOf("ds-1", "m4i_dataset", "raw_logs")],
            outputs: [endOf("ds-2", "m4i_dataset", "hourly_index")],
        }),
        ...overrides,
    };
}

/**
 * The m4i person body (DET-39..DET-43): the five responsibility ends,
 * one duplicate Data Owner entity (dedup), one DELETED steward attribute
 * (counts nothing), and a `ProcessOwner` end the box never lists (DV-154).
 * `email` is the one property the Other stat counts.
 */
function m4iPerson(overrides: Partial<EntityView> = {}): EntityView {
    return {
        guid: "pe-1",
        typeName: "m4i_person",
        displayText: "Ada",
        name: "Ada",
        qualifiedName: "ada@corp",
        status: "ACTIVE",
        stale: false,
        attributes: { name: "Ada", qualifiedName: "ada@corp", email: "ada@example.com" },
        sections: sectionsOf({
            domainLead: [endOf("d1", "m4i_data_domain", "genomics")],
            businessOwnerEntity: [
                endOf("e1", "m4i_data_entity", "variants"),
                endOf("e2", "m4i_data_entity", "samples"),
                endOf("e2", "m4i_data_entity", "samples"),
            ],
            businessOwnerAttribute: [endOf("a1", "m4i_data_attribute", "gene_symbol")],
            stewardEntity: [endOf("e3", "m4i_data_entity", "reports")],
            stewardAttribute: [
                {
                    guid: "a2",
                    displayText: "chromosome",
                    typeName: "m4i_data_attribute",
                    status: "DELETED",
                },
                endOf("a3", "m4i_data_attribute", "coverage"),
            ],
            ProcessOwner: [endOf("po1", "m4i_generic_process", "build_index")],
        }),
        ...overrides,
    };
}

/** The door answer for the person's merged roles box: the five seeded ends. */
function personEndsAnswer(): Record<string, unknown> {
    return doorAnswer([
        doorCard("d1", "m4i_data_domain", "genomics"),
        doorCard("e1", "m4i_data_entity", "variants"),
        doorCard("e2", "m4i_data_entity", "samples"),
        doorCard("e3", "m4i_data_entity", "reports"),
        doorCard("a1", "m4i_data_attribute", "gene_symbol"),
        doorCard("a3", "m4i_data_attribute", "coverage"),
    ]);
}

/**
 * Bring a person up fully: the entity, the roles box's chunk, and the rule
 * box's two calls (the search of `rules`, the empty verdicts) all settle.
 */
function arrivePerson(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    body: EntityView = m4iPerson(),
    rules: Record<string, unknown>[] = [],
): void {
    arrive(fixture, httpMock, body);
    for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
        request.flush(personEndsAnswer());
    }
    for (const request of httpMock.match((r) => r.url === "/api/atlas/v2/search/basic")) {
        request.flush({ entities: rules });
    }
    for (const request of httpMock.match((r) => r.url === "/validate-entity/")) {
        request.flush({ verdicts: [], unreadRules: [] });
    }
    fixture.detectChanges();
}

/** Deliver an m4i entity's read, its sections' first door chunk, and the box's call. */
function arriveSections(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    body: EntityView = m4iEntity(),
    answer: Record<string, unknown> = attributesAnswer(),
    rules: Record<string, unknown>[] = [],
) {
    arrive(fixture, httpMock, body);
    for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
        request.flush(answer);
    }
    // The dataset/process layouts carry the Lineage Model box (LDG-09): its
    // own call lands with the layout. The layouts specced here have no
    // model — the 204 keeps every section test at the box's empty state,
    // and httpMock.verify() stays honest (the box's drawing is its own spec).
    for (const request of httpMock.match((r) => r.url === "/lineage-model/")) {
        request.flush(null, { status: 204, statusText: "No Content" });
    }
    // DET-48 (7.25a): every m4i page now carries the Governance Quality
    // Rules box, so its two reads land with the layout too. The section
    // specs below do not read the box — the empty answer keeps it titled and
    // empty, and httpMock.verify() honest.
    for (const request of httpMock.match((r) => r.url === "/api/atlas/v2/search/basic")) {
        request.flush({ entities: rules });
    }
    for (const request of httpMock.match((r) => r.url === "/validate-entity/")) {
        request.flush({ verdicts: [], unreadRules: [] });
    }
    fixture.detectChanges();
}

/** Type a keyword in one section's box and submit it (the UIC-21 input). */
function submitKeyword(
    fixture: { detectChanges: () => void },
    compiled: HTMLElement,
    anchor: string,
    term: string,
): void {
    const search = compiled.querySelector<HTMLInputElement>(`#${anchor} input[type='search']`)!;
    search.value = term;
    search.dispatchEvent(new Event("input"));
    fixture.detectChanges();
    search.dispatchEvent(new Event("search"));
    fixture.detectChanges();
}

describe("Details m4i sections (DET-15..DET-26)", () => {
    it("an m4i entity renders its layout's boxes and not the default's (DET-15)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        // The layout's two section boxes with the legacy anchors, the
        // People box beside the description, and no default-layout chrome.
        expect(compiled.querySelector("#related-attributes")).toBeTruthy();
        expect(compiled.querySelector("#related-entities")).toBeTruthy();
        expect(compiled.querySelector("#people-details")).toBeTruthy();
        expect(normalize(compiled.querySelector("#people-details h2")?.textContent)).toBe("People");
        // No typedef read: the name is one of the seven (DET-15's direct hit).
        httpMock.verify();
    });

    it("the seed renders count and cards; the count rides the seed (DET-17)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arrive(fixture, httpMock, m4iEntity());
        fixture.detectChanges(); // count first, ahead of the cards (DET-17)

        const box = compiled.querySelector<HTMLElement>("#related-attributes");
        expect(normalize(box?.querySelector("h6")?.textContent)).toBe("2 result(s)");
        expect(box?.querySelector("aurelius-atlas-ui-entity-card .loader")).toBeTruthy(); // loading cards (DET-18)

        for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
            request.flush(attributesAnswer());
        }
        // The Governance Quality Rules box reads too (DET-48): this spec
        // watches the Data Attributes box, so its empty answers only keep
        // the mock honest.
        for (const request of httpMock.match((r) => r.url === "/api/atlas/v2/search/basic")) {
            request.flush({ entities: [] });
        }
        for (const request of httpMock.match((r) => r.url === "/validate-entity/")) {
            request.flush({ verdicts: [], unreadRules: [] });
        }
        fixture.detectChanges();

        const titles = [...(box?.querySelectorAll("aurelius-atlas-ui-entity-card .title.is-4 a") ?? [])].map((link) =>
            normalize(link.textContent),
        );
        expect(titles).toEqual(["gene_symbol", "chromosome"]);
        httpMock.verify();
    });

    it("the cards sit in columns capped at three across (DET-22, DD-377)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        // Bulma's sizing helpers, not a min-width: a bare column shares the
        // row with every sibling (six long names rendered one word per
        // line). Half on a tablet, a third on a desktop, full on a phone.
        const columns = [...compiled.querySelectorAll("#related-attributes .aurelius-card-section-grid > .column")];
        expect(columns.length).toBeGreaterThan(0);
        for (const column of columns) {
            expect(column.classList.contains("is-half-tablet")).toBe(true);
            expect(column.classList.contains("is-one-third-desktop")).toBe(true);
        }
    });

    it("a card body shows the trail, chips, the description, and a flat people row (DET-19, VCF-01, VCF-05)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({ sections: [ends("attributes", [end("a1", "gene_symbol")])] }),
            doorAnswer([
                doorCard("a1", "m4i_data_attribute", "gene_symbol", {
                    name: "gene_symbol",
                    definition: "HGNC **symbol**.",
                    classificationNames: ["PII"],
                    breadcrumb: [{ guid: "e", name: "variants_entity", typeName: "m4i_data_entity" }],
                    relations: [
                        { attribute: "m4i_person", entities: [{ guid: "p2", name: "Lin", typeName: "m4i_person" }] },
                    ],
                }),
            ]),
        );

        const card = compiled.querySelector("#related-attributes aurelius-atlas-webapp-catalogue-card")!;
        // The trail (VCF-01): the stored crumb plus the card's own active crumb.
        expect(
            [...card.querySelectorAll(".aurelius-card-trail li")].map((crumb) => normalize(crumb.textContent)),
        ).toEqual(["variants_entity", "gene_symbol"]);
        expect(normalize(card.querySelector(".field.is-grouped .control")?.textContent)).toBe("Has PII");
        expect(card.querySelector(".aurelius-card-description strong")?.textContent).toBe("symbol"); // markdown (DET-10 sibling)
        // The flat people row (VCF-06, DD-617): one label, no roles.
        expect(normalize(card.querySelector(".aurelius-people-row")?.textContent)).toBe("People : Lin");
        // No quality column (DET-19: the DQ column has no source).
        expect(card.querySelector(".quality")).toBeNull();
        httpMock.verify();
    });

    it("a card title click routes the screen to the card's guid (DET-19)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled
            .querySelector<HTMLAnchorElement>("#related-attributes aurelius-atlas-ui-entity-card .title.is-4 a")!
            .click();

        expect(navigate).toHaveBeenCalledWith(["/search/details", "a1"]);
    });

    it("the People box links the owner and steward rows, deduped, and routes (DET-23)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const rows = [...compiled.querySelectorAll<HTMLElement>("#people-details .aurelius-people-row")].map((row) =>
            normalize(row.textContent),
        );
        // Legacy order; the steward's duplicate guid is deduped (DET-23).
        // The part renders "Label" + " : " (DD-374, the demo's "Owner(s) :")
        // + the links.
        expect(rows).toEqual(["Domain Lead(s) : Ada Lead", "Data Owner(s) : Ada", "Data Steward(s) : Lin"]);

        compiled.querySelector<HTMLAnchorElement>("#people-details .aurelius-people-row a")!.click();
        expect(navigate).toHaveBeenCalledWith(["/search/details", "p3"]);
    });

    it("a People box with no people shows the italic line (DET-23)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({ sections: [ends("attributes", [end("a1", "gene_symbol"), end("a2", "chromosome")])] }),
        );

        expect(compiled.querySelector("#people-details .aurelius-people-row")).toBeNull();
        const empty = compiled.querySelector(".aurelius-people-empty");
        expect(normalize(empty?.textContent)).toBe("No people assigned.");
        expect(empty?.classList.contains("is-italic")).toBe(true);
    });

    it("the keyword filter narrows the cards and the count line resets them (DET-20)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        submitKeyword(fixture, compiled, "related-attributes", "chromosome");

        const box = compiled.querySelector<HTMLElement>("#related-attributes");
        expect(box?.querySelectorAll("aurelius-atlas-ui-entity-card")).toHaveLength(1);
        // The count line becomes the filtered count as a reset link.
        const reset = box?.querySelector<HTMLAnchorElement>("a.aurelius-card-section-reset");
        expect(normalize(reset?.textContent)).toBe("1 result(s)");

        reset!.click();
        fixture.detectChanges();
        expect(box?.querySelectorAll("aurelius-atlas-ui-entity-card")).toHaveLength(2);
        expect(normalize(box?.querySelector("h6")?.textContent)).toBe("2 result(s)");
    });

    it("the keyword narrows the cards as it is typed, before any submit (DET-20, DD-375)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        const search = compiled.querySelector<HTMLInputElement>("#related-attributes input[type='search']")!;
        search.value = "chromosome";
        search.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        // No `search` event: typing alone filters (DD-375).
        const box = compiled.querySelector<HTMLElement>("#related-attributes");
        expect(box?.querySelectorAll("aurelius-atlas-ui-entity-card")).toHaveLength(1);
        expect(normalize(box?.querySelector("a.aurelius-card-section-reset")?.textContent)).toBe("1 result(s)");

        // Backspacing to empty restores them.
        search.value = "";
        search.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        expect(box?.querySelectorAll("aurelius-atlas-ui-entity-card")).toHaveLength(2);
    });

    it("the placeholder is the Aurelius keyword string (DET-20)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        const search = compiled.querySelector<HTMLInputElement>("#related-attributes input[type='search']");
        expect(search?.getAttribute("placeholder")).toBe("Search for keywords");
    });

    it("the funnel opens the popover and a tick filters the cards and the count line (VCF-08..VCF-13, VCF-18)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity(),
            doorAnswer([
                doorCard("a1", "m4i_data_attribute", "gene_symbol", {
                    relations: [
                        { attribute: "steward", entities: [{ guid: "p1", name: "Ada", typeName: "m4i_person" }] },
                    ],
                }),
                doorCard("a2", "m4i_data_attribute", "chromosome"),
            ]),
        );

        // The entity's Data Attributes box asks the role groups (VCF-10, VCF-18);
        // only Ada's stewards group has rows, so it is the one group on offer
        // and the empty lead and owner groups left the popover (VCF-12).
        const funnel = compiled.querySelector<HTMLButtonElement>("#related-attributes .aurelius-card-section-funnel")!;
        expect(funnel.getAttribute("aria-label")).toBe("Filter");
        expect(funnel.classList.contains("is-primary")).toBe(false);

        funnel.click();
        fixture.detectChanges();
        const menu = compiled.querySelector<HTMLElement>(
            "#related-attributes .aurelius-card-section-filter .dropdown-menu",
        );
        expect([...menu!.querySelectorAll(".menu-label")].map((label) => normalize(label.textContent))).toEqual([
            "Data Steward(s)",
        ]);
        const box = menu!.querySelector<HTMLInputElement>("input[type='checkbox']")!;
        expect(normalize(box.closest("label")?.textContent)).toBe("Ada (1)");

        box.click();
        fixture.detectChanges();
        const attributes = compiled.querySelector<HTMLElement>("#related-attributes");
        // Only the card carrying the ticked person stays; the count line
        // and the funnel follow the filtered set (VCF-13, VCF-08).
        expect(attributes?.querySelectorAll("aurelius-atlas-ui-entity-card")).toHaveLength(1);
        expect(normalize(attributes?.querySelector("a.aurelius-card-section-reset")?.textContent)).toBe("1 result(s)");
        expect(funnel.classList.contains("is-primary")).toBe(true);

        // The reset link clears the tick with the keyword and the sort (VCF-13).
        attributes!.querySelector<HTMLAnchorElement>("a.aurelius-card-section-reset")!.click();
        fixture.detectChanges();
        expect(attributes?.querySelectorAll("aurelius-atlas-ui-entity-card")).toHaveLength(2);
        expect(normalize(attributes?.querySelector("h6")?.textContent)).toBe("2 result(s)");
        expect(funnel.classList.contains("is-primary")).toBe(false);
    });

    it("Name sorts the cards by display text; the direction reverses (DET-21)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        const select = compiled.querySelector<HTMLSelectElement>("#related-attributes select")!;
        select.value = "name";
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();

        const titles = () =>
            [...compiled.querySelectorAll("#related-attributes .title.is-4 a")].map((link) =>
                normalize(link.textContent),
            );
        expect(titles()).toEqual(["chromosome", "gene_symbol"]);

        compiled.querySelector<HTMLButtonElement>("#related-attributes .aurelius-card-section-direction")!.click();
        fixture.detectChanges();
        expect(titles()).toEqual(["gene_symbol", "chromosome"]);
    });

    it("the grid pages at 9; the load button extends the page (DET-22)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        const many = Array.from({ length: 10 }, (_, index) => end(`g${index}`, `name-${index}`));
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({ sections: [ends("attributes", many)] }),
            doorAnswer(
                many.map((row) => doorCard(row["guid"] as string, "m4i_data_attribute", row["displayText"] as string)),
            ),
        );

        expect(compiled.querySelectorAll("#related-attributes aurelius-atlas-ui-entity-card")).toHaveLength(9);
        const load = [...compiled.querySelectorAll<HTMLButtonElement>("#related-attributes button")].find(
            (button) => normalize(button.textContent) === "Load next page...",
        );
        expect(load).toBeTruthy(); // the sentinel's button — one page remains

        load!.click();
        fixture.detectChanges();
        expect(compiled.querySelectorAll("#related-attributes aurelius-atlas-ui-entity-card")).toHaveLength(10);
        expect(
            [...compiled.querySelectorAll("#related-attributes button")].some(
                (button) => normalize(button.textContent) === "Load next page...",
            ),
        ).toBe(false); // the filtered set is exhausted
    });

    it("a failed chunk alerts once and keeps the section's count (DET-18)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        arrive(fixture, httpMock, m4iEntity());
        fixture.detectChanges();

        for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
            request.flush({ error: "boom" }, { status: 500, statusText: "Server Error" });
        }
        fixture.detectChanges();

        expect(add).toHaveBeenCalledWith({
            severity: "error",
            source: "search",
            message: "Retrieving the entity details",
        });
        // The cards the chunk carried drop; the count keeps them (DET-18).
        expect(normalize(compiled.querySelector("#related-attributes h6")?.textContent)).toBe("2 result(s)");
        expect(compiled.querySelectorAll("#related-attributes aurelius-atlas-ui-entity-card")).toHaveLength(0);
        httpMock.expectNone("/api/aurelius/v1/search"); // no retry loop (DD-615)
    });

    it("the stats bar carries the layout's counts and #hrefs (DET-24)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        const stats = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item")].map((item) => {
            const heading = item.querySelector("p.heading a")!;
            return [
                normalize(heading.textContent) ?? "",
                heading.getAttribute("href") ?? "",
                normalize(item.querySelector("p.title")?.textContent) ?? "",
            ];
        });
        expect(stats).toEqual([
            ["Data Attributes", "#related-attributes", "2"],
            ["Child Entities", "#related-entities", "0"],
            // DET-58 (7.25c): the score stat in the legacy place — the
            // sourceless view (no `quality` rows on the fixture) shows the
            // layout's `Unavailable` word, never a zero (DET-63).
            ["Data Quality", "#data-quality", "Unavailable"],
            ["Properties", "#properties-details", "0"],
        ]);
        // Still no Governance Quality Rules stat — the box carries no stat
        // on this layout (DET-24's rule predates 7.25a, unchanged).
        expect(stats.some(([label]) => label.includes("Governance"))).toBe(false);
    });

    it("the side navigation links each box by router URL and anchor (DET-25, DD-381)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        // The items are routerLinks over the current route with the box id
        // as the URL fragment (DD-381): the href is a real address (the
        // keyboard and middle-click path), and the anchor rides the URL.
        // With no route configured, the router serialises the current (root)
        // tree with the fragment grafted on.
        const items = [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) => [
            normalize(link.textContent),
            link.getAttribute("href"),
        ]);
        expect(items).toEqual([
            ["Description", "/#description-details"],
            ["People", "/#people-details"],
            ["Data Attributes", "/#related-attributes"],
            ["Child Entities", "/#related-entities"],
            // DET-58 (7.25c): the score link, in the legacy slot before the
            // governance box's entry.
            ["Data Quality", "/#data-quality"],
            // DET-48 (7.25a): the box's entry, in the legacy slot before the properties.
            ["Governance Quality Rules", "/#gov-quality"],
            ["Properties", "/#properties-details"],
        ]);
    });

    it("a score view draws the box's scored dimension rows in the fixed order (DET-56, DET-64)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({
                quality: [
                    { dimension: "overall", score: 0.9, count: 5, total: 5 },
                    { dimension: "validity", score: 0.5, count: 2, total: 4 },
                    { dimension: "accuracy", score: 0.75, count: 1, total: 2 },
                    { dimension: "timeliness", score: 0.4, count: 1, total: 3 },
                    { dimension: "completeness", score: 0.25, count: 0, total: 1 },
                ],
            }),
        );

        // DET-56: the box in the layout's place (DET-57 — after Child
        // Entities), its title the layout's own key's text.
        const box = compiled.querySelector("#data-quality");
        expect(box).toBeTruthy();
        expect(normalize(box?.querySelector("h2")?.textContent)).toBe("Data Quality");
        // The scored dimensions in the fixed order, `overall` left out:
        // each the pie, the percent, the dimension word, the count. DET-64's
        // gate: the roll-up counts completeness 0, so the legacy's own truthy
        // count gate prints no row for it (LAS-12's 0-count dimensions).
        const rows = [...(box?.querySelectorAll(".quality-dimension") ?? [])];
        expect(rows.map((row) => normalize(row.textContent))).toEqual([
            "75% Accuracy (1)",
            "40% Timeliness (1)",
            "50% Validity (2)",
        ]);
        // Each row carries the UIC-36 pie.
        expect(rows.every((row) => row.querySelector("aurelius-atlas-ui-data-quality-pie"))).toBe(true);
    });

    it("a sourceless view shows the score box's placeholder and no rows (DET-56, DET-63)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        // An `overall` row with count 0 is sourceless (DET-63).
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({
                quality: [{ dimension: "overall", score: 0.5, count: 0, total: 1 }],
            }),
        );

        const box = compiled.querySelector("#data-quality");
        expect(box?.querySelector(".quality-dimension")).toBeNull();
        expect(normalize(box?.querySelector(".aurelius-quality-not-available")?.textContent)).toBe(
            "No data quality results available",
        );
    });

    it("the score stat shows the overall percent, then the word at count 0 (DET-58)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({
                quality: [
                    { dimension: "overall", score: 0.75, count: 4, total: 4 },
                    { dimension: "accuracy", score: 0.75, count: 4, total: 4 },
                ],
            }),
        );

        const scoreStat = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item")].find(
            (item) => item.querySelector("p.heading a")?.getAttribute("href") === "#data-quality",
        )!;
        // DET-58: the percent to one decimal at most, never a count.
        expect(normalize(scoreStat.querySelector("p.title")?.textContent)).toBe("75%");
    });

    // The field page's Data Quality Rules box (DET-65, DET-66, DD-865): the
    // screen hands the view's own rule score rows to the sections store, and
    // the store joins them by GUID — no extra call, no poll, no client-side
    // roll-up (DET-62's rule).
    describe("the field rules box' score rows (DET-65, DET-66, DET-62)", () => {
        /** The m4i field body (DET-16's row): the rules end, two scored rules. */
        function m4iField(overrides: Partial<EntityView> = {}): EntityView {
            return {
                guid: "fl-1",
                typeName: "m4i_field",
                displayText: "chromosome_pos",
                name: "chromosome_pos",
                qualifiedName: "variants.chromosome_pos",
                status: "ACTIVE",
                stale: false,
                attributes: { name: "chromosome_pos", qualifiedName: "variants.chromosome_pos" },
                sections: sectionsOf({
                    dataQuality: [
                        endOf("r1", "m4i_data_quality", "Not null"),
                        endOf("r2", "m4i_data_quality", "Range"),
                    ],
                }),
                ...overrides,
            };
        }

        /** The door answer for the box's two rules (DET-18). */
        function rulesAnswer(): Record<string, unknown> {
            return doorAnswer([
                doorCard("r1", "m4i_data_quality", "Not null", { definition: "Never null." }),
                doorCard("r2", "m4i_data_quality", "Range", { definition: "Inside the range." }),
            ]);
        }

        /** One of the field view's rule score rows (AVS-13). */
        function score(rule: string, dimension: string, value: number): Record<string, unknown> {
            return { rule, name: `rule-${rule}`, dimension, score: value };
        }

        it("paints the view's rows on the matching cards without a second request (DET-65, DET-62)", () => {
            const { fixture, compiled, httpMock } = setup("fl-1");
            arriveSections(
                fixture,
                httpMock,
                m4iField({
                    ruleScores: [score("r1", "Accuracy", 0.892), score("r2", "Completeness", 1)] as never,
                }),
                rulesAnswer(),
            );

            // DET-65: one row per scored card — the percent at
            // `percent: '1.0-1'`, the dimension lowercased, no count.
            const rows = [...compiled.querySelectorAll("#related-rules .aurelius-card-scores .quality-dimension")];
            expect(rows.map((row) => normalize(row.textContent))).toEqual(["89.2% accuracy", "100% completeness"]);
            expect(rows.every((row) => row.querySelector("aurelius-atlas-ui-data-quality-pie"))).toBe(true);
            // DET-66: the box's sort select holds its four options.
            const sort = compiled.querySelector<HTMLSelectElement>("#related-rules select")!;
            expect([...sort.options].map((option) => normalize(option.textContent))).toEqual([
                "Relevance",
                "Name",
                "Dimension",
                "Quality Score",
            ]);
            // DET-62: the rows ride the view — the render asks nothing beyond
            // the read door's answer.
            httpMock.expectNone("/api/aurelius/v1/search");
            httpMock.verify();
        });

        it("an unscored rule keeps its card and prints no row (DET-65, DV-207)", () => {
            const { fixture, compiled, httpMock } = setup("fl-1");
            arriveSections(
                fixture,
                httpMock,
                m4iField({ ruleScores: [score("r1", "Accuracy", 0.5)] as never }),
                rulesAnswer(),
            );

            const boxes = [...compiled.querySelectorAll("#related-rules aurelius-atlas-webapp-catalogue-card")];
            expect(boxes).toHaveLength(2); // DET-35's seed stands: r2 has no score
            expect(boxes[0].querySelector(".aurelius-card-scores")).toBeTruthy();
            expect(boxes[1].querySelector(".aurelius-card-scores")).toBeNull();
            // DET-36/DD-867: the stat stays the section count, not the score rows.
            const rulesStat = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item")].find(
                (item) => item.querySelector("p.heading a")?.getAttribute("href") === "#related-rules",
            )!;
            expect(normalize(rulesStat.querySelector("p.title")?.textContent)).toBe("2");
            httpMock.verify();
        });

        it("a dataset pays the rules rows nothing (DET-65)", () => {
            const { fixture, compiled, httpMock } = setup("ds-1");
            arriveSections(
                fixture,
                httpMock,
                m4iDataset({ ruleScores: [score("r1", "Accuracy", 0.5)] as never }),
                processAnswer(),
            );

            // DET-57's score box keeps its roll-up, and no box on a dataset
            // page prints a rule score row: the read door joins none (VDR-16).
            expect(compiled.querySelector("#data-quality .aurelius-card-scores")).toBeNull();
            expect(compiled.querySelector(".aurelius-card-scores")).toBeNull();
            httpMock.verify();
        });

        it("the score box, the stats bar, and the navigation keep their places (DET-56, DET-58, DET-36)", () => {
            const { fixture, compiled, httpMock } = setup("fl-1");
            arriveSections(
                fixture,
                httpMock,
                m4iField({
                    quality: [
                        { dimension: "overall", score: 0.946, count: 2, total: 2 },
                        { dimension: "accuracy", score: 0.892, count: 1, total: 2 },
                        { dimension: "completeness", score: 1, count: 1, total: 2 },
                    ],
                    ruleScores: [score("r1", "Accuracy", 0.892)] as never,
                }),
                rulesAnswer(),
            );

            // DET-56/DET-57: the field's score box in its legacy place, its
            // own roll-up rows unaffected by the rules box' joined rows.
            const scoreBox = compiled.querySelector("#data-quality")!;
            expect(
                [...scoreBox.querySelectorAll(".quality-dimension")].map((row) => normalize(row.textContent)),
            ).toEqual(["89.2% Accuracy (1)", "100% Completeness (1)"]);
            // DET-36/DD-867: the stats bar keeps its place — Data Quality
            // percent, then Data Quality Rules seed count.
            const stats = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item")].map(
                (item) => [
                    normalize(item.querySelector("p.heading")?.textContent ?? ""),
                    normalize(item.querySelector("p.title")?.textContent ?? ""),
                ],
            );
            expect(stats).toEqual([
                ["Data Attributes", "0"],
                ["Child Fields", "0"],
                ["Data Quality", "94.6%"],
                ["Data Quality Rules", "2"],
                ["Properties", "0"],
            ]);
            // DET-25: the navigation keeps its entries in legacy order.
            const nav = [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) =>
                normalize(link.textContent),
            );
            expect(nav).toEqual([
                "Description",
                "Data Attributes",
                "Child Fields",
                "Data Quality",
                "Data Quality Rules",
                "Governance Quality Rules",
                "Properties",
            ]);
            // DET-65: the score box and the rules card never compete — the
            // card's own row prints in its box, and DET-60's roll-up stays
            // away from the rules cards (a rule carries no totals, ASQ-04).
            const rulesCards = [...compiled.querySelectorAll("#related-rules aurelius-atlas-webapp-catalogue-card")];
            expect(rulesCards[0].querySelectorAll(".quality-dimension")).toHaveLength(1);
            expect(rulesCards[1].querySelector(".aurelius-card-scores")).toBeNull();
            httpMock.verify();
        });
    });

    it("a score render asks nothing beyond the read (DET-62)", () => {
        const { fixture, httpMock } = setup("m4i-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({
                quality: [{ dimension: "overall", score: 0.9, count: 5, total: 5 }],
            }),
        );
        // DET-62: the box and the stat read the view already held — the
        // render adds no call beyond the layout's own reads.
        httpMock.expectNone("/api/aurelius/v1/search");
        httpMock.verify();
    });

    it("a navigation item's click is a router navigation to its anchor (DET-25, DD-381)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        // The whole DD-380 bug was a bare `#href` that the browser resolved
        // against <base href="/"> and the router answered with the landing
        // page. A routerLink cannot repeat it: the click goes through the
        // router, and the address names the section.
        const router = TestBed.inject(Router);
        const targets: UrlTree[] = [];
        vi.spyOn(router, "navigateByUrl").mockImplementation((url) => {
            targets.push(url as UrlTree);
            return { catch: () => undefined } as never;
        });

        compiled.querySelector<HTMLAnchorElement>(".aurelius-details-nav .menu-list a")!.click();

        expect(targets).toHaveLength(1);
        expect(router.serializeUrl(targets[0])).toBe("/#description-details");
    });

    it("a stats heading routes its anchor as the URL fragment (DET-24, DET-25, DD-381)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        // The lib cancels its bare `#href` on the emit (UIC-19, DD-154) and
        // the screen routes the fragment — the same URL a side-navigation
        // item carries, so both bars name the section in the address.
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const stats = [...compiled.querySelectorAll<HTMLAnchorElement>(".aurelius-details-stats p.heading a")];
        stats[0].click();

        expect(navigate).toHaveBeenCalledWith([], expect.objectContaining({ fragment: "related-attributes" }));
    });

    it("a deep link lands its anchor once the box is on the page (DET-25, DD-381)", () => {
        // A cold arrival at …/details/<guid>#related-attributes: the
        // router's own jump runs at NavigationEnd, before the entity
        // answered, so the box is not there yet. The screen's landing
        // effect (DD-381) scrolls it through the ViewportScroller — the
        // router's own seam, navbar offset included — on the render that
        // brings the box, once.
        const { fixture, httpMock, fragment } = setup("m4i-1");
        // jsdom has no window.scrollTo, so the spy records without scrolling.
        const landed: string[] = [];
        vi.spyOn(TestBed.inject(ViewportScroller), "scrollToAnchor").mockImplementation((anchor) => {
            landed.push(anchor);
        });

        fragment.next("related-attributes");
        fixture.detectChanges();
        // Nothing to land on yet: the entity has not answered.
        expect(landed).toEqual([]);

        arriveSections(fixture, httpMock);
        TestBed.tick(); // the after-render phase runs the landing effect

        expect(landed).toEqual(["related-attributes"]);

        // The anchor stays landed: re-renders do not re-jump (DD-381).
        TestBed.tick();
        expect(landed).toEqual(["related-attributes"]);
    });

    it("the header badge shows the alias with the base type; the cards ride the card shape (DET-26, DV-167)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({
                attributes: {
                    name: "variants_entity",
                    qualifiedName: "variants@cluster",
                    description: "A governed entity.",
                    typeAlias: "Data Entity",
                },
            }),
        );

        // The header badge: the alias with the base type beside it, both
        // by display name — the legacy's alias is stored already
        // translated and its suffix pipes `typeName | translate`
        // (DET-26, DD-379).
        expect(normalize(compiled.querySelector(".aurelius-details-type")?.textContent)).toBe(
            "Data Entity (Data Entity)",
        );
        // The header badge leads with the type's icon (DET-26, DD-378):
        // an m4i_data_entity is the table glyph in the business family.
        const headerIcon = compiled.querySelector(".aurelius-details-type .icon-text > .icon");
        expect(headerIcon).toBeTruthy();
        expect(headerIcon!.classList.contains("business")).toBe(true);
        expect(headerIcon!.querySelector("fa-icon svg")).toBeTruthy();
        // The card badges (DD-616, MMS-09): the shared rich card badges
        // the card's own `typeAlias` when it carries one — these fixtures
        // carry none, so each badge shows the type's display name.
        const badges = [
            ...compiled.querySelectorAll("#related-attributes aurelius-atlas-ui-entity-card .media-right"),
        ].map((badge) => normalize(badge.textContent));
        expect(badges).toEqual(["Data Attribute", "Data Attribute"]);
        // Every card badge carries its type's icon too (DET-19, DD-378):
        // both fixture cards are m4i_data_attribute — the tag glyph,
        // business family.
        const cardIcons = [...compiled.querySelectorAll("#related-attributes .media-right .icon")];
        expect(cardIcons).toHaveLength(2);
        for (const icon of cardIcons) {
            expect(icon.classList.contains("business")).toBe(true);
            expect(icon.querySelector("fa-icon svg")).toBeTruthy();
        }
    });

    it("a type outside the icon map renders a plain badge (DET-26, DD-378)", () => {
        // The default-layout ANSWER is a DataSet: the legacy's
        // `iconsByType[typeName]` answers nothing, and its template's
        // *ngIf rendered no icon — the badge stays text-only.
        const { fixture, compiled, httpMock } = setup("ds-1");
        arrive(fixture, httpMock);

        const typeLine = compiled.querySelector(".aurelius-details-type");
        expect(normalize(typeLine?.textContent)).toBe("DataSet");
        expect(typeLine?.querySelector(".icon")).toBeNull();
    });

    it("an m4i attribute shows its People box and its Fields section (DET-16, DET-23)", () => {
        const { fixture, compiled, httpMock } = setup("attr-1");
        arriveSections(
            fixture,
            httpMock,
            {
                guid: "attr-1",
                typeName: "m4i_data_attribute",
                displayText: "gene_symbol",
                name: "gene_symbol",
                status: "ACTIVE",
                stale: false,
                attributes: { name: "gene_symbol" },
                sections: [ends("fields", [end("f1", "chromosome_pos")])],
            },
            doorAnswer([doorCard("f1", "m4i_field", "chromosome_pos")]),
        );

        // The attribute page carries a People box (the spec table and the
        // legacy page both); with no people ends it shows the empty line.
        expect(compiled.querySelector("#people-details")).toBeTruthy();
        expect(normalize(compiled.querySelector(".aurelius-people-empty")?.textContent)).toBe("No people assigned.");
        expect(normalize(compiled.querySelector("#related-fields h2")?.textContent)).toBe("Fields");
        expect(compiled.querySelectorAll("#related-fields aurelius-atlas-ui-entity-card")).toHaveLength(1);
    });

    it("the save re-read re-seeds the sections (DET-17, DD-327)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        TestBed.inject(EntityWritten).notify("m4i-1", "saved");
        fixture.detectChanges();
        httpMock.expectOne("/api/aurelius/v1/entity/guid/m4i-1").flush(m4iEntity({ sections: [] }));
        fixture.detectChanges();
        // The re-read re-loads the Governance Quality Rules box too (DET-44):
        // its second round lands here.
        for (const request of httpMock.match((r) => r.url === "/api/atlas/v2/search/basic")) {
            request.flush({ entities: [] });
        }
        for (const request of httpMock.match((r) => r.url === "/validate-entity/")) {
            request.flush({ verdicts: [], unreadRules: [] });
        }
        fixture.detectChanges();

        // The new entity has no ends: every section re-seeds to zero.
        expect(normalize(compiled.querySelector("#related-attributes h6")?.textContent)).toBe("0 result(s)");
        httpMock.verify();
    });

    it("a DataSet keeps the DET-14 default shape while its walk runs (DET-15)", async () => {
        const { fixture, compiled, httpMock } = setup("ds-1");
        // Delivered without settling the walk: this spec rides it to the end.
        httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(ANSWER);
        fixture.detectChanges();

        // The default layout's boxes — no section boxes, no People box.
        expect(compiled.querySelector("#related-fields")).toBeNull();
        expect(compiled.querySelector("#people-details")).toBeNull();
        expect(compiled.querySelector("table.aurelius-details-properties")).toBeTruthy();
        expect(normalize(compiled.querySelector(".aurelius-details-property-count")?.textContent)).toBe("1");

        // Settle the DET-15 walk: DataSet's typedef names two plain
        // supertypes; each answers the built-in error and ends its branch.
        for (let round = 0; round < 3; round++) {
            for (const request of httpMock.match((r) => r.url.startsWith(TYPEDEF_URL))) {
                if (request.request.url === `${TYPEDEF_URL}DataSet`) {
                    request.flush({ category: "ENTITY_DEF", name: "DataSet", superTypes: ["Asset", "Process"] });
                } else {
                    request.flush({}, { status: 404, statusText: "Not Found" });
                }
            }
            await new Promise((resolve) => setTimeout(resolve));
            fixture.detectChanges();
        }

        // The walk ends at the default layout: the screen still renders it.
        expect(compiled.querySelector("table.aurelius-details-properties")).toBeTruthy();
        expect(compiled.querySelector("#related-fields")).toBeNull();
        httpMock.verify();
    });

    it("an m4i dataset renders the Producers and Consumers boxes (DET-32)", () => {
        const { fixture, compiled, httpMock } = setup("ds-1");
        arriveSections(fixture, httpMock, m4iDataset(), processAnswer());

        // DET-32: the two lineage boxes after Child Datasets, each seeded
        // from the dataset's own end and resolved to the one process card.
        const producers = compiled.querySelector("#related-producers");
        const consumers = compiled.querySelector("#related-consumers");
        expect(producers).toBeTruthy();
        expect(consumers).toBeTruthy();
        expect(normalize(producers?.querySelector("h2")?.textContent)).toBe("Producers");
        expect(normalize(consumers?.querySelector("h2")?.textContent)).toBe("Consumers");
        expect(compiled.querySelectorAll("#related-producers aurelius-atlas-ui-entity-card")).toHaveLength(1);
        expect(compiled.querySelectorAll("#related-consumers aurelius-atlas-ui-entity-card")).toHaveLength(1);
        expect(normalize(producers?.querySelector("aurelius-atlas-ui-entity-card")?.textContent)).toContain(
            "build_index",
        );
        // The card body is the uniform one (DET-19): the seeded definition text.
        expect(producers?.querySelector("aurelius-atlas-ui-entity-card")?.textContent).toContain("Indexes it.");

        // LDG-09: the Lineage Model box sits after Child Datasets and before
        // Producers — the legacy page's position. The box's own call answers
        // the 204 here (arriveSections), so it rests at the empty message;
        // its states and drawing are the box's own spec.
        const lineage = compiled.querySelector("#lineage-model");
        expect(lineage).toBeTruthy();
        expect(lineage?.querySelector("aurelius-atlas-webapp-lineage-model")).toBeTruthy();
        const boxIds = [...compiled.querySelectorAll(".box[id], section[id]")].map((box) => box.id);
        expect(boxIds.slice(boxIds.indexOf("related-datasets"), boxIds.indexOf("related-producers") + 1)).toEqual([
            "related-datasets",
            "lineage-model",
            "related-producers",
        ]);

        // DET-32/LDG-32: the stats bar carries the counts in the legacy
        // order with the Lineage Model entry before Producers; its value
        // reads the box's state, and the 204 arriveSections answered rests
        // at "Unavailable". DET-58 (7.25c): the score stat in its legacy
        // slot after Consumers — the sourceless fixture shows the word.
        const stats = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item")].map((item) => {
            const heading = item.querySelector("p.heading a")!;
            return [
                normalize(heading.textContent) ?? "",
                heading.getAttribute("href") ?? "",
                normalize(item.querySelector("p.title")?.textContent) ?? "",
            ];
        });
        expect(stats).toEqual([
            ["Fields", "#related-fields", "0"],
            ["Child Datasets", "#related-datasets", "0"],
            ["Lineage Model", "#lineage-model", "Unavailable"],
            ["Producers", "#related-producers", "1"],
            ["Consumers", "#related-consumers", "1"],
            ["Data Quality", "#data-quality", "Unavailable"],
            ["Properties", "#properties-details", "0"],
        ]);

        // DET-32/LDG-32: the side navigation carries the links in the
        // legacy positions, the lineage link between Child Datasets and
        // Producers (DD-383's hold-out ended), and DET-58's score link
        // before the governance box's.
        const items = [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) =>
            normalize(link.textContent),
        );
        expect(items).toEqual([
            "Description",
            "Fields",
            "Child Datasets",
            "Lineage Model",
            "Producers",
            "Consumers",
            "Data Quality",
            "Governance Quality Rules",
            "Properties",
        ]);
        // No People box on this layout (DET-16's row).
        expect(compiled.querySelector("#people-details")).toBeNull();
    });

    it("an m4i process renders the eighth layout's three boxes (DET-33)", () => {
        const { fixture, compiled, httpMock } = setup("pr-1");
        arriveSections(
            fixture,
            httpMock,
            m4iProcess(),
            doorAnswer([
                doorCard("sy-1", "m4i_system", "elastic1"),
                doorCard("ds-1", "m4i_dataset", "raw_logs"),
                doorCard("ds-2", "m4i_dataset", "hourly_index"),
            ]),
        );

        // DET-33: the three section boxes with the legacy anchors; no
        // People box (the legacy page has none — DET-23's field case).
        expect(normalize(compiled.querySelector("#related-systems h2")?.textContent)).toBe("Systems");
        expect(normalize(compiled.querySelector("#related-inputs h2")?.textContent)).toBe("Inputs");
        expect(normalize(compiled.querySelector("#related-outputs h2")?.textContent)).toBe("Outputs");
        expect(compiled.querySelector("#people-details")).toBeNull();
        expect(compiled.querySelectorAll("#related-systems aurelius-atlas-ui-entity-card")).toHaveLength(1);
        expect(compiled.querySelectorAll("#related-inputs aurelius-atlas-ui-entity-card")).toHaveLength(1);
        expect(compiled.querySelectorAll("#related-outputs aurelius-atlas-ui-entity-card")).toHaveLength(1);

        // LDG-09: the Lineage Model box sits after Systems and before Inputs
        // — the legacy process page's position (empty here: arriveSections
        // answers the box's call with the 204).
        const lineage = compiled.querySelector("#lineage-model aurelius-atlas-webapp-lineage-model");
        expect(lineage).toBeTruthy();
        const boxIds = [...compiled.querySelectorAll(".box[id], section[id]")].map((box) => box.id);
        expect(boxIds.slice(boxIds.indexOf("related-systems"), boxIds.indexOf("related-inputs") + 1)).toEqual([
            "related-systems",
            "lineage-model",
            "related-inputs",
        ]);

        // DET-33/LDG-32: the stats bar of the row carries the lineage stat
        // between Systems and Inputs (the process pair's keys), reading the
        // box's 204 state.
        const stats = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item")].map((item) => {
            const heading = item.querySelector("p.heading a")!;
            return [
                normalize(heading.textContent) ?? "",
                heading.getAttribute("href") ?? "",
                normalize(item.querySelector("p.title")?.textContent) ?? "",
            ];
        });
        expect(stats).toEqual([
            ["Systems", "#related-systems", "1"],
            ["Lineage Model", "#lineage-model", "Unavailable"],
            ["Inputs", "#related-inputs", "1"],
            ["Outputs", "#related-outputs", "1"],
            ["Properties", "#properties-details", "0"],
        ]);

        // DET-33/LDG-32: the navigation of the row carries the lineage link
        // in the legacy slot.
        const items = [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) =>
            normalize(link.textContent),
        );
        expect(items).toEqual([
            "Description",
            "Systems",
            "Lineage Model",
            "Inputs",
            "Outputs",
            "Governance Quality Rules",
            "Properties",
        ]);

        // No typedef read: the name is a direct dispatch hit (DET-15).
        httpMock.expectNone(TYPEDEF_URL);
    });

    it("the Lineage Model stat follows the box's fetch state (LDG-32, DD-400)", () => {
        const { fixture, compiled, httpMock } = setup("ds-1");
        arrive(fixture, httpMock, m4iDataset());
        for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
            request.flush(processAnswer());
        }
        fixture.detectChanges();

        const statValue = () => {
            const item = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item")].find(
                (entry) => normalize(entry.querySelector("p.heading a")?.textContent) === "Lineage Model",
            );
            return normalize(item?.querySelector("p.title")?.textContent) ?? "";
        };

        // Pending: the box's call is in flight — the stat is blank, never a
        // count and never a spinner (LDG-32's shape).
        expect(statValue()).toBe("");
        const lineageCall = httpMock.expectOne((request) => request.url === "/lineage-model/");

        // A model that draws reads "Available" — the page's fetch state
        // (DD-400), not the box's internals: the stat is on the bar while
        // the box renders its diagram below.
        lineageCall.flush({ model: modelFixture.model, metadata: modelFixture.metadata });
        fixture.detectChanges();
        expect(statValue()).toBe("Available");
    });
});

/** One rule header of the person box's search answer (DET-42). */
function govRule(guid: string, name: string, extra: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        guid,
        typeName: "m4i_gov_data_quality",
        displayText: name,
        attributes: { name, qualityDimension: "COMPLETENESS", ...extra },
    };
}

describe("Details person page (DET-39..DET-43)", () => {
    it("a person renders the tenth layout, without a description box (DET-39)", () => {
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrivePerson(fixture, httpMock);

        // The roles box and the rule box, the legacy ids; the description
        // box the nine older layouts draw is absent here (the legacy
        // person template never carried one), and so is its nav entry.
        expect(compiled.querySelector("#description-details")).toBeNull();
        expect(compiled.querySelector("#governance-roles")).toBeTruthy();
        expect(compiled.querySelector("#gov-quality")).toBeTruthy();
        // The grouped bar replaces the flat one (DD-518): the four boxes.
        expect(compiled.querySelector(".aurelius-details-stats")).toBeNull();
        expect(compiled.querySelectorAll(".aurelius-details-stats-group")).toHaveLength(4);
        // No People box on the person page either (the layout row says so).
        expect(compiled.querySelector("#people-details")).toBeNull();
        httpMock.verify();
    });

    it("the grouped stats bar counts the four headed boxes (DET-40, DD-519)", () => {
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrivePerson(fixture, httpMock);

        const groups = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats-group")].map((box) => [
            normalize(box.querySelector(":scope > p.heading")?.textContent),
            [...box.querySelectorAll<HTMLElement>(".level-item")].map((item) => [
                normalize(item.querySelector("p.heading a")?.textContent),
                item.querySelector<HTMLAnchorElement>("p.heading a")!.getAttribute("href"),
                normalize(item.querySelector("p.title")?.textContent),
            ]),
        ]);
        // The legacy order and counts: the duplicate entity dedupes, the
        // DELETED edge counts nothing, the merged box holds the rest. The
        // headings are routerLinks (the nav items' shape, DD-381), so the
        // href is a real address with the fragment grafted on.
        expect(groups).toEqual([
            ["Domain Lead", [["Data Domains", "/#governance-roles", "1"]]],
            [
                "Data Owner",
                [
                    ["Data Entities", "/#governance-roles", "2"],
                    ["Data Attributes", "/#governance-roles", "1"],
                ],
            ],
            [
                "Data Steward",
                [
                    ["Data Entities", "/#governance-roles", "1"],
                    ["Data Attributes", "/#governance-roles", "1"],
                ],
            ],
            ["Other", [["Properties", "/#properties-details", "1"]]],
        ]);
    });

    it("the roles box merges the five ends and skips ProcessOwner (DET-41, DV-154)", () => {
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrivePerson(fixture, httpMock);

        const box = compiled.querySelector<HTMLElement>("#governance-roles");
        // The five seeded ends, deduped (e2 twice): six cards. The
        // `ProcessOwner` end seeds nothing — the legacy box never lists it.
        expect(normalize(box?.querySelector("h6")?.textContent)).toBe("6 result(s)");
        const titles = [...(box?.querySelectorAll(".title.is-4 a") ?? [])].map((link) => normalize(link.textContent));
        expect(titles).toEqual(["genomics", "variants", "samples", "gene_symbol", "reports", "coverage"]);
        expect(titles).not.toContain("build_index");
    });

    it("a grouped stat heading scrolls its box only (DET-40, DET-25, DV-156)", () => {
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrivePerson(fixture, httpMock);

        // The headings are routerLinks over the current route (the
        // navigation items' shape, DD-381): the click goes through the
        // router and the address names the section. Scroll only — the
        // retired facet filter (DV-156) has no handler to call.
        const router = TestBed.inject(Router);
        const targets: UrlTree[] = [];
        vi.spyOn(router, "navigateByUrl").mockImplementation((url) => {
            targets.push(url as UrlTree);
            return { catch: () => undefined } as never;
        });

        const groups = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats-group")];
        groups[1].querySelector<HTMLAnchorElement>("p.heading a")!.click();
        groups[3].querySelector<HTMLAnchorElement>("p.heading a")!.click();

        expect(targets.map((target) => router.serializeUrl(target))).toEqual([
            "/#governance-roles",
            "/#properties-details",
        ]);

        // The roles box stayed unfiltered: still the six cards.
        expect(compiled.querySelectorAll("#governance-roles aurelius-atlas-ui-entity-card")).toHaveLength(6);
    });

    it("the side navigation carries the person's three entries (DET-43)", () => {
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrivePerson(fixture, httpMock);

        const items = [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) => [
            normalize(link.textContent),
            link.getAttribute("href"),
        ]);
        // The legacy order, and no Description entry: the page has no such
        // box to scroll to (DET-39).
        expect(items).toEqual([
            ["Governance Responsibilities", "/#governance-roles"],
            ["Governance Quality Rules", "/#gov-quality"],
            ["Properties", "/#properties-details"],
        ]);
    });

    it("the rule box lists the type's rules with their verdicts (DET-42, DV-155)", () => {
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrive(fixture, httpMock, m4iPerson());
        for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
            request.flush(personEndsAnswer());
        }
        const search = httpMock.expectOne("/api/atlas/v2/search/basic");
        search.flush({
            entities: [
                govRule("r2", "Person has a name", { ruleDescription: "A name is stored." }),
                govRule("r1", "Person has an email address"),
                govRule("r3", "Person has a role"),
            ],
        });
        httpMock.expectOne("/validate-entity/").flush({
            verdicts: [
                {
                    ruleGuid: "r1",
                    ruleName: "Person has an email address",
                    attribute: "email",
                    dimension: "COMPLETENESS",
                    compliant: false,
                    message: "no email",
                },
                {
                    ruleGuid: "r2",
                    ruleName: "Person has a name",
                    attribute: "name",
                    dimension: "COMPLETENESS",
                    compliant: true,
                    message: "ok",
                },
            ],
            unreadRules: [{ ruleGuid: "r3", ruleName: "Person has a role", error: "no attribute" }],
        });
        fixture.detectChanges();

        // Name-ordered cards; the description line rides the rule that
        // stores one; the verdicts mark success, warning, and the unread
        // rule draws no icon at all (VEV-03).
        const box = compiled.querySelector<HTMLElement>("#gov-quality");
        const titles = [...(box?.querySelectorAll(".title.is-4 a") ?? [])].map((link) => normalize(link.textContent));
        expect(titles).toEqual(["Person has a name", "Person has a role", "Person has an email address"]);
        expect(normalize(box?.querySelector(".aurelius-gov-quality-description")?.textContent)).toBe(
            "A name is stored.",
        );
        const icons = [...(box?.querySelectorAll(".aurelius-gov-quality-verdict .icon") ?? [])].map((icon) =>
            icon.classList.contains("has-text-success")
                ? "ok"
                : icon.classList.contains("has-text-warning")
                  ? "warn"
                  : "?",
        );
        expect(icons).toEqual(["ok", "warn"]);
        httpMock.verify();
    });

    it("a rule title opens the rule's page (DET-42, DET-06)", () => {
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrivePerson(fixture, httpMock, m4iPerson(), [govRule("r1", "Person has a name")]);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        compiled.querySelector<HTMLAnchorElement>("#gov-quality .title.is-4 a")!.click();
        expect(navigate).toHaveBeenCalledWith(["/search/details", "r1"]);
    });

    it("a failed rule read leaves the box titled and empty, no alert (DET-42, DD-521)", () => {
        const { fixture, compiled, httpMock } = setup("pe-1");
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        arrive(fixture, httpMock, m4iPerson());
        for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
            request.flush(personEndsAnswer());
        }
        httpMock.expectOne("/api/atlas/v2/search/basic").flush({}, { status: 500, statusText: "Server Error" });
        httpMock.expectOne("/validate-entity/").flush({}, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        expect(normalize(compiled.querySelector("#gov-quality h2")?.textContent)).toBe("Governance Quality Rules");
        expect(compiled.querySelectorAll("#gov-quality aurelius-atlas-ui-entity-card")).toHaveLength(0);
        expect(add).not.toHaveBeenCalled();
        httpMock.verify();
    });

    it("the person's box stays closed for a type without the layout (DET-39)", () => {
        // The guard effect reads the layout: a person-shaped entity of an
        // unmapped type asks for nothing (the default layout, DET-14).
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrive(fixture, httpMock, { ...m4iPerson(), typeName: "person" });
        fixture.detectChanges();

        expect(compiled.querySelector("#gov-quality")).toBeNull();
        httpMock.expectNone("/api/atlas/v2/search/basic");
        httpMock.expectNone("/validate-entity/");
        httpMock.verify();
    });
});

/**
 * The box of the screen, drawn by the shared card section: the chrome's
 * count line, keyword, sort, funnel and grid, on every layout that carries
 * it (DET-44..DET-48). The store's own specs cover the pipeline; these pin
 * the screen's wiring — the handlers, and that the box sits last.
 */
describe("Details Governance Quality Rules section (DET-44..DET-48, DD-841)", () => {
    /** The three rules the chrome turns on: two dimensions, two types, one refused. */
    function chromeRules(): Record<string, unknown>[] {
        return [
            govRule("r1", "Alpha rule", { ruleType: "COLUMN", ruleDescription: "A column is filled." }),
            govRule("r2", "bravo rule", {
                qualityDimension: "ACCURACY",
                ruleType: "TABLE",
            }),
            govRule("r3", "Charlie rule", { qualityDimension: "ACCURACY", ruleType: "TABLE" }),
        ];
    }

    /** Bring a person up with the three seed rules. */
    function arriveBox() {
        const { fixture, compiled, httpMock } = setup("pe-1");
        arrive(fixture, httpMock, m4iPerson());
        for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
            request.flush(personEndsAnswer());
        }
        httpMock.expectOne("/api/atlas/v2/search/basic").flush({ entities: chromeRules() });
        httpMock.expectOne("/validate-entity/").flush({
            verdicts: [
                {
                    ruleGuid: "r2",
                    ruleName: "bravo rule",
                    attribute: "",
                    dimension: "ACCURACY",
                    compliant: false,
                    message: "",
                },
            ],
            unreadRules: [],
        });
        fixture.detectChanges();
        return { fixture, compiled, httpMock };
    }

    it("the chrome draws its count line, sorts and facets on the person page (DET-44, DET-45, DET-46)", () => {
        const { compiled } = arriveBox();

        const box = compiled.querySelector<HTMLElement>("#gov-quality")!;
        expect(normalize(box.querySelector("h2")?.textContent)).toBe("Governance Quality Rules");
        // The count line carries the whole set and is the reset link (DET-44).
        const count = box.querySelector<HTMLAnchorElement>("h6.aurelius-card-section-count a")!;
        expect(count.classList.contains("aurelius-card-section-reset")).toBe(true);
        expect(normalize(count.textContent)).toBe("3 result(s)");
        // The four legacy sorts, Relevance first (DET-45), the raw literals
        // the catalogues carry no key for (DET-21's precedent).
        expect([...box.querySelectorAll<HTMLOptionElement>("select option")].map((option) => option.value)).toEqual([
            "relevance",
            "name",
            "dataqualityruledimension",
            "compliant",
            "dataqualitytype",
        ]);
        // The funnel carries the two rule groups (DET-46).
        const funnel = box.querySelector<HTMLButtonElement>(".aurelius-card-section-funnel")!;
        expect(funnel.classList.contains("is-primary")).toBe(false);
        funnel.click();
        const menus = [...box.querySelectorAll<HTMLElement>(".dropdown-menu .menu-label")].map((label) =>
            normalize(label.textContent),
        );
        expect(menus).toEqual(["Dimension", "Rule Type"]);
        expect([...box.querySelectorAll(".dropdown-menu input[type='checkbox']")]).toHaveLength(4);
    });

    it("the count line clears the keyword, the tick, the sort and the page (DET-44)", async () => {
        const { fixture, compiled } = arriveBox();
        const box = compiled.querySelector<HTMLElement>("#gov-quality")!;
        const titles = () => [...box.querySelectorAll(".title.is-4 a")].map((link) => normalize(link.textContent));
        expect(titles()).toEqual(["Alpha rule", "bravo rule", "Charlie rule"]);

        // A facet tick narrows the rows first — the popover counts over the
        // keyword-filtered set (VCF-12), so the tick comes before the typing.
        box.querySelector<HTMLButtonElement>(".aurelius-card-section-funnel")!.click();
        const accuracy = [...box.querySelectorAll<HTMLElement>(".dropdown-menu label")].find(
            (label) => normalize(label.textContent) === "ACCURACY (2)",
        )!;
        accuracy.querySelector<HTMLInputElement>("input[type='checkbox']")!.click();
        fixture.detectChanges();
        expect(titles()).toEqual(["bravo rule", "Charlie rule"]);
        expect(normalize(box.querySelector("a.aurelius-card-section-reset")?.textContent)).toBe("2 result(s)");

        // The keyword narrows the rows further, as it is typed (DET-47).
        const search = box.querySelector<HTMLInputElement>("input[type='search']")!;
        search.value = "alpha";
        search.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        expect(titles()).toEqual([]);
        expect(normalize(box.querySelector("a.aurelius-card-section-reset")?.textContent)).toBe("0 result(s)");

        // The sort and its direction join the filtered state.
        const select = box.querySelector<HTMLSelectElement>("select")!;
        select.value = "dataqualitytype";
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();
        box.querySelector<HTMLButtonElement>(".aurelius-card-section-direction")!.click();
        fixture.detectChanges();
        expect(
            box.querySelector<HTMLButtonElement>(".aurelius-card-section-funnel")!.classList.contains("is-primary"),
        ).toBe(true);

        // The count line is the reset: every control returns and the whole
        // set shows again (DET-44, DET-20's rule).
        box.querySelector<HTMLAnchorElement>("a.aurelius-card-section-reset")!.click();
        fixture.detectChanges();
        // The cleared keyword reaches the input through the search field's
        // ngModel, which writes on a microtask.
        await fixture.whenStable();
        expect(search.value).toBe("");
        expect(titles()).toEqual(["Alpha rule", "bravo rule", "Charlie rule"]);
        expect(normalize(box.querySelector("h6")?.textContent)).toBe("3 result(s)");
        expect(box.querySelector<HTMLSelectElement>("select")!.value).toBe("relevance");
        expect(
            box.querySelector<HTMLButtonElement>(".aurelius-card-section-funnel")!.classList.contains("is-primary"),
        ).toBe(false);
        // The tick the reset dropped: reopening shows nothing checked.
        box.querySelector<HTMLButtonElement>(".aurelius-card-section-funnel")!.click();
        expect(
            [...box.querySelectorAll<HTMLInputElement>(".dropdown-menu input[type='checkbox']")].some(
                (input) => input.checked,
            ),
        ).toBe(false);
    });

    it("the facet filter and the sort drive the rows through the screen (DET-45, DET-46)", () => {
        const { fixture, compiled } = arriveBox();
        const box = compiled.querySelector<HTMLElement>("#gov-quality")!;
        const titles = () => [...box.querySelectorAll(".title.is-4 a")].map((link) => normalize(link.textContent));

        // The dimension facet keeps its two rows (DET-46).
        box.querySelector<HTMLButtonElement>(".aurelius-card-section-funnel")!.click();
        const accuracy = [...box.querySelectorAll<HTMLElement>(".dropdown-menu label")].find(
            (label) => normalize(label.textContent) === "ACCURACY (2)",
        )!;
        accuracy.querySelector<HTMLInputElement>("input[type='checkbox']")!.click();
        fixture.detectChanges();
        expect(titles()).toEqual(["bravo rule", "Charlie rule"]);

        // The verdict sort puts the passed rule first, the refused one next,
        // and the unread rule last (DET-45).
        const select = box.querySelector<HTMLSelectElement>("select")!;
        select.value = "compliant";
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();
        expect(titles()).toEqual(["bravo rule", "Charlie rule"]);
        // A keyword reaching the name the facet hid cannot return it (DET-47).
        const search = box.querySelector<HTMLInputElement>("input[type='search']")!;
        search.value = "alpha";
        search.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        expect(titles()).toEqual([]);
    });

    // One page per test: TestBed configures once per test, so the loop sits
    // at describe level and emits a test per layout.
    const pages: { guid: string; entity: EntityView; answer?: Record<string, unknown> }[] = [
        { guid: "m4i-1", entity: m4iEntity() },
        { guid: "ds-1", entity: m4iDataset(), answer: doorAnswer([]) },
        { guid: "pr-1", entity: m4iProcess(), answer: doorAnswer([]) },
        { guid: "pe-1", entity: m4iPerson(), answer: personEndsAnswer() },
    ];
    for (const page of pages) {
        it(`the ${page.entity.typeName} page draws the box last, with its nav entry (DET-48, DD-841)`, () => {
            // The legacy pages the box closed: it joins the layout's section
            // list in the legacy slot — after the last card box (and the
            // Lineage Model box, which the dataset and process pages seat
            // before it) and before the Properties accordion.
            const { fixture, compiled, httpMock } = setup(page.guid);
            arriveSections(fixture, httpMock, page.entity, page.answer ?? attributesAnswer());

            const box = compiled.querySelector<HTMLElement>("#gov-quality");
            expect(box, page.entity.typeName).toBeTruthy();
            expect(box?.classList.contains("aurelius-details-section"), page.entity.typeName).toBe(true);
            // Last of the section boxes, directly before the Properties block —
            // the legacy order of the nine templates.
            const landmarks = [
                ...compiled.querySelectorAll<HTMLElement>(".aurelius-details-section, #properties-details"),
            ].map((node) => node.id);
            expect(landmarks.slice(-2), page.entity.typeName).toEqual(["gov-quality", "properties-details"]);
            // The nav entry, in the same slot.
            const nav = [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) => [
                normalize(link.textContent),
                link.getAttribute("href"),
            ]);
            expect(nav.at(-2), page.entity.typeName).toEqual(["Governance Quality Rules", "/#gov-quality"]);
            expect(nav.at(-1)![1], page.entity.typeName).toBe("/#properties-details");
            // The box read for the page: the search and the verdict call both
            // answered empty (arriveSections settles them), and the count
            // line shows the answer — the box is live, not a dead shell.
            expect(
                normalize(box?.querySelector("a.aurelius-card-section-reset")?.textContent),
                page.entity.typeName,
            ).toBe("0 result(s)");
            httpMock.verify();
        });
    }

    it("the rule page draws no box and asks for none (DET-48, DV-199)", () => {
        // The tenth layout is the only one the legacy left without the box.
        const { fixture, compiled, httpMock } = setup("dq-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({
                guid: "dq-1",
                typeName: "m4i_data_quality",
                displayText: "rule_entity",
                sections: sectionsOf({ fields: [end("f1", "chromosome_pos")] }),
            }),
            doorAnswer([doorCard("f1", "m4i_field", "chromosome_pos")]),
        );

        expect(compiled.querySelector("#gov-quality")).toBeNull();
        httpMock.expectNone("/api/atlas/v2/search/basic");
        httpMock.expectNone("/validate-entity/");
        expect(
            [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) => link.textContent),
        ).not.toContain("Governance Quality Rules");
        httpMock.verify();
    });
});

/** The view family's verdicts door (VDR-15, 7.25b): the rule page's one read. */
const VERDICTS_URL = "/api/aurelius/v1/rule/verdicts";

/**
 * The governance rule's body (DET-50): no sections — its two boxes seed from
 * the verdicts, not an end. `ruleExpression` is the one attribute the
 * properties table shows (every other attribute is the header's, the
 * description's, or on the legacy blacklist, DET-11).
 */
function m4iGovRule(overrides: Partial<EntityView> = {}): EntityView {
    return {
        guid: "gv-1",
        typeName: "m4i_gov_data_quality",
        displayText: "Name filled",
        name: "Name filled",
        qualifiedName: "Name filled@cluster",
        status: "ACTIVE",
        stale: false,
        attributes: {
            name: "Name filled",
            qualifiedName: "Name filled@cluster",
            description: "Every dataset carries a name.",
            ruleExpression: "is_filled('name')",
        },
        ...overrides,
    };
}

/** One door row: the judged entity, its verdict, the legacy's extras. */
function verdictRow(entity: string, compliant: boolean | null): Record<string, unknown> {
    return { entity, compliant, name: entity, message: "The dataset carries no name" };
}

/** The door answer for the two verdict boxes' seeded entities (DET-53): the
 * two datasets, each carrying the chain ends the box's facet groups count. */
function verdictCardsAnswer(): Record<string, unknown> {
    return doorAnswer([
        doorCard("e-1", "m4i_dataset", "raw_logs", {
            relations: [
                {
                    attribute: "m4i_data_domain",
                    entities: [{ guid: "d-1", name: "genomics", typeName: "m4i_data_domain" }],
                },
                {
                    attribute: "m4i_data_entity",
                    entities: [{ guid: "en-1", name: "variants", typeName: "m4i_data_entity" }],
                },
            ],
        }),
        doorCard("e-2", "m4i_dataset", "hourly_index", {
            relations: [
                {
                    attribute: "m4i_data_domain",
                    entities: [{ guid: "d-1", name: "genomics", typeName: "m4i_data_domain" }],
                },
                {
                    attribute: "m4i_data_entity",
                    entities: [{ guid: "en-1", name: "variants", typeName: "m4i_data_entity" }],
                },
            ],
        }),
    ]);
}

/**
 * Bring the rule page up: the entity, the verdict read, and both boxes'
 * card chunk all settle. `verdicts` rides the door's rows and `cards` the
 * search door's answer; `failVerdicts` stands in for a read that failed
 * (DET-55).
 */
function arriveRule(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    body: EntityView = m4iGovRule(),
    verdicts: Record<string, unknown>[] = [verdictRow("e-1", false), verdictRow("e-2", true)],
    cards: Record<string, unknown> = verdictCardsAnswer(),
    failVerdicts = false,
): void {
    arrive(fixture, httpMock, body);
    const door = httpMock.expectOne(VERDICTS_URL);
    if (failVerdicts) {
        door.flush({ error: "boom" }, { status: 500, statusText: "Server Error" });
    } else {
        door.flush({ verdicts });
    }
    fixture.detectChanges(); // the rows land, the seed re-runs, the chunks fire
    for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
        request.flush(cards);
    }
    fixture.detectChanges();
}

/** The Compliance Chart box's pie, as the screen drew it (DET-54). */
function pieOf(fixture: {
    debugElement: { query: (predicate: ReturnType<typeof By.css>) => { componentInstance: unknown } | null };
}) {
    const pie = fixture.debugElement.query(By.css("aurelius-atlas-ui-data-quality-pie"));
    return pie?.componentInstance as { value: () => number; size: () => number } | undefined;
}

describe("Details governance rule page (DET-50..DET-55, DD-848..DD-850)", () => {
    it("draws the legacy page in the legacy order and nav (DET-50)", () => {
        const { fixture, compiled, httpMock } = setup("gv-1");
        arriveRule(fixture, httpMock);

        // The landmarks top to bottom: the description, the stats bar, the
        // chart, the two verdict boxes, the properties — the legacy template.
        const landmarks = [...compiled.querySelectorAll<HTMLElement>("[id]")]
            .map((node) => node.id)
            .filter((id) =>
                ["description-details", "related-non-compliants", "related-compliants", "properties-details"].includes(
                    id,
                ),
            );
        expect(landmarks).toEqual([
            "description-details",
            "related-non-compliants",
            "related-compliants",
            "properties-details",
        ]);
        // The chart sits between the stats bar and the Non-compliant box.
        const boxes = [...compiled.querySelectorAll<HTMLElement>(".box")];
        const chart = compiled.querySelector<HTMLElement>(".aurelius-details-compliance-chart")!;
        expect(chart.classList.contains("box"), "the chart is a box").toBe(true);
        const stats = compiled.querySelector<HTMLElement>(".aurelius-details-stats")!;
        const nonCompliant = compiled.querySelector<HTMLElement>("#related-non-compliants")!;
        expect(boxes.indexOf(stats) < boxes.indexOf(chart), "chart after the stats").toBe(true);
        expect(boxes.indexOf(chart) < boxes.indexOf(nonCompliant), "chart before the box").toBe(true);
        // The layout's own titles (the bridge's `search.details.govQuality.*`).
        expect(normalize(compiled.querySelector("#description-details h2")?.textContent)).toBe("Description");
        expect(normalize(compiled.querySelector(".aurelius-details-compliance-chart h2")?.textContent)).toBe(
            "Compliance Chart",
        );
        // The box titles the legacy cards components carried (the chrome's
        // h2, UIC-27).
        const sectionTitle = (anchor: string) =>
            normalize(compiled.querySelector<HTMLElement>(`#${anchor} .aurelius-card-section-level h2`)?.textContent);
        expect(sectionTitle("related-non-compliants")).toBe("Non-compliant");
        expect(sectionTitle("related-compliants")).toBe("Compliant");
        // The People box is not on this page (DET-50), and the page carries
        // no Governance Quality Rules box — its content is that box (DV-199).
        expect(compiled.querySelector("#people-details")).toBeNull();
        expect(compiled.querySelector("#gov-quality")).toBeNull();
        // DET-50: the nav's three entries, in the legacy order — neither the
        // description nor the chart is one.
        const nav = [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) => [
            normalize(link.textContent),
            link.getAttribute("href"),
        ]);
        expect(nav).toEqual([
            ["Non-compliant", "/#related-non-compliants"],
            ["Compliant", "/#related-compliants"],
            ["Properties", "/#properties-details"],
        ]);
        // DET-51: the page's one read is the verdicts door — never the App
        // Search wire the legacy rode (ADR 071 R5), and no rule box either.
        httpMock.expectNone("/api/atlas/v2/search/basic");
        httpMock.expectNone("/validate-entity/");
        httpMock.expectNone(VERDICTS_URL);
        httpMock.verify();
    });

    it("counts the two verdict sets and the properties in the stats bar (DET-52)", () => {
        const { fixture, compiled, httpMock } = setup("gv-1");
        arriveRule(fixture, httpMock, m4iGovRule(), [
            verdictRow("e-1", false),
            verdictRow("e-2", true),
            verdictRow("e-3", null),
        ]);

        const stats = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item")].map((item) => {
            const heading = item.querySelector("p.heading a")!;
            return [
                normalize(heading.textContent) ?? "",
                heading.getAttribute("href") ?? "",
                normalize(item.querySelector("p.title")?.textContent) ?? "",
            ];
        });
        expect(stats).toEqual([
            ["Non-compliant", "#related-non-compliants", "1"],
            ["Compliant", "#related-compliants", "1"],
            // The one property the table shows (DET-24's Properties rule).
            ["Properties", "#properties-details", "1"],
        ]);
    });

    it("shows the two boxes' cards in door order (DET-53)", () => {
        const { fixture, compiled, httpMock } = setup("gv-1");
        arriveRule(fixture, httpMock, m4iGovRule(), [
            verdictRow("e-1", false),
            verdictRow("e-2", true),
            verdictRow("e-3", false),
        ]);

        const titles = (anchor: string) =>
            [...compiled.querySelectorAll<HTMLElement>(`#${anchor} aurelius-atlas-ui-entity-card .title.is-4 a`)].map(
                (link) => normalize(link.textContent),
            );
        // The non-compliant box carries both refused entities in door order;
        // the third's card never answered here, so only its seed shows.
        expect(titles("related-non-compliants")).toEqual(["raw_logs"]);
        expect(titles("related-compliants")).toEqual(["hourly_index"]);
        // The count line carries the seed, ahead of the answered cards (DET-17).
        expect(
            normalize(compiled.querySelector("#related-non-compliants a.aurelius-card-section-reset")?.textContent),
        ).toBe("2 result(s)");
        // DET-53: the box's funnel asks the four groups of the row (DV-201):
        // every one with a value among the cards shows, in the configured
        // order — a group with no row leaves the popover (VCF-12).
        compiled.querySelector<HTMLButtonElement>("#related-non-compliants .aurelius-card-section-funnel")!.click();
        fixture.detectChanges();
        const groups = [
            ...compiled.querySelectorAll<HTMLElement>("#related-non-compliants .dropdown-menu .menu-label"),
        ].map((label) => normalize(label.textContent));
        expect(groups).toEqual(["Type Name", "Data Domain", "Data Entity", "Name"]);
    });

    it("draws the pie at the score and the legend in the legacy order (DET-54, DET-51)", () => {
        const { fixture, compiled, httpMock } = setup("gv-1");
        arriveRule(fixture, httpMock, m4iGovRule(), [
            verdictRow("e-1", false),
            verdictRow("e-2", true),
            verdictRow("e-3", true),
        ]);

        // 2 of 3 judged pass: the legacy's formula, and size 8 (DET-54).
        const pie = pieOf(fixture)!;
        expect(pie.value()).toBeCloseTo(200 / 3);
        expect(pie.size()).toBe(8);
        // The legend: non-compliant first with its red swatch, compliant second
        // (DET-54's order; the swatches' colours are the sheet's, the legacy's
        // hsl pair — the pie's own layers carry the same two).
        const rows = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-legend-row")];
        expect(rows.map((row) => normalize(row.textContent))).toEqual(["Non-compliant", "Compliant"]);
        expect(rows.map((row) => row.querySelector(".aurelius-details-legend-swatch")!.className)).toEqual([
            "aurelius-details-legend-swatch aurelius-details-legend-non-compliant",
            "aurelius-details-legend-swatch aurelius-details-legend-compliant",
        ]);
    });

    it("keeps the page quiet and empty when the verdict read fails (DET-55)", () => {
        const { fixture, compiled, httpMock } = setup("gv-1");
        arriveRule(fixture, httpMock, m4iGovRule(), [], {}, true);

        // DET-49's posture: both boxes stand at zero, no alert, no retry.
        expect(
            normalize(compiled.querySelector("#related-non-compliants a.aurelius-card-section-reset")?.textContent),
        ).toBe("0 result(s)");
        expect(
            normalize(compiled.querySelector("#related-compliants a.aurelius-card-section-reset")?.textContent),
        ).toBe("0 result(s)");
        expect(compiled.querySelectorAll("#related-non-compliants aurelius-atlas-ui-entity-card")).toHaveLength(0);
        expect(compiled.querySelectorAll("#related-compliants aurelius-atlas-ui-entity-card")).toHaveLength(0);
        expect(pieOf(fixture)!.value()).toBe(0);
        const counts = [...compiled.querySelectorAll<HTMLElement>(".aurelius-details-stats .level-item p.title")].map(
            (title) => normalize(title.textContent),
        );
        expect(counts).toEqual(["0", "0", "1"]);
        httpMock.expectNone("/api/aurelius/v1/search");
        httpMock.verify();
    });

    it("scores a rule judging nothing at 0, the legacy's NaN painted no arc (DET-51)", () => {
        const { fixture, compiled, httpMock } = setup("gv-1");
        arriveRule(fixture, httpMock, m4iGovRule(), []);

        expect(pieOf(fixture)!.value()).toBe(0);
        expect(compiled.querySelectorAll("#related-non-compliants aurelius-atlas-ui-entity-card")).toHaveLength(0);
        expect(compiled.querySelectorAll("#related-compliants aurelius-atlas-ui-entity-card")).toHaveLength(0);
        httpMock.expectNone("/api/aurelius/v1/search");
        httpMock.verify();
    });

    it("the save re-read re-asks the door and re-seeds the boxes (DET-51, DD-327)", () => {
        const { fixture, compiled, httpMock } = setup("gv-1");
        arriveRule(fixture, httpMock);

        // The editor's save tick: the screen re-reads the entity (the door's
        // view, cached-evicted — DD-605), and the rule page asks the verdicts
        // door again — the sections store's rule for every arrival.
        TestBed.inject(EntityWritten).notify("gv-1", "saved");
        fixture.detectChanges();
        httpMock
            .expectOne((request) => request.url.startsWith(VIEW_URL))
            .flush(
                m4iGovRule({
                    displayText: "Name filled",
                    attributes: { ...m4iGovRule().attributes, name: "Name filled" },
                }) as unknown as Record<string, unknown>,
            );
        fixture.detectChanges();
        settleTypeDefs(httpMock);

        httpMock.expectOne(VERDICTS_URL).flush({ verdicts: [verdictRow("e-9", true)] });
        fixture.detectChanges(); // the new rows re-seed, the new chunk fires
        for (const request of httpMock.match((r) => r.url === "/api/aurelius/v1/search")) {
            request.flush(doorAnswer([doorCard("e-9", "m4i_dataset", "renamed")]));
        }
        fixture.detectChanges();

        expect(pieOf(fixture)!.value()).toBe(100);
        expect(
            [
                ...compiled.querySelectorAll<HTMLElement>(
                    "#related-compliants aurelius-atlas-ui-entity-card .title.is-4 a",
                ),
            ].map((link) => normalize(link.textContent)),
        ).toEqual(["renamed"]);
        httpMock.verify();
    });

    it("no other page asks the verdicts door (DET-51's gate)", () => {
        const { fixture, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        httpMock.expectNone(VERDICTS_URL);
        httpMock.verify();
    });
});

/**
 * Deliver the guid change's read: the first request already arrived via
 * {@link arrive}; this flushes the second one.
 */
function arriveSecond(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    body: Record<string, unknown>,
) {
    httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(body);
    fixture.detectChanges();
}
