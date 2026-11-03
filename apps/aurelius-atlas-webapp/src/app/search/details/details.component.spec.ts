import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter } from "@angular/router";
import { By } from "@angular/platform-browser";
import { Subject } from "rxjs";

import type { AtlasEntityWithExtInfo } from "aurelius-atlas-data-access";
import { Breadcrumbs, PropertiesItem } from "aurelius-atlas-ui";

import { AlertsService } from "../../alerts/alerts.service";

import { Details } from "./details.component";

/**
 * The details screen on its data spine (DET-08..DET-13, 7.20): the route's
 * guid drives one `GET /api/atlas/v2/entity/guid/{guid}` (DET-08), the
 * header/description/properties bind to the entity that answers
 * (DET-09..DET-11), and every no-entity state keeps the 7.6 empty shape
 * (DET-02). The specs ride the results screen's idiom: a `paramMap`
 * Subject so a guid change is observable, `expectOne` + `flush` for the
 * arrival, `detectChanges` to let the effects and signals settle.
 */
const ENTITY_URL = "/api/atlas/v2/entity/guid/";

/** The wire body of the fixture entity: two renderable properties. */
const ANSWER: AtlasEntityWithExtInfo = {
    entity: {
        guid: "7a1b",
        typeName: "DataSet",
        attributes: {
            name: "genomic_variants",
            qualifiedName: "genomic_variants@cluster",
            definition: "Curated variant calls.",
            description: "A seeded description.",
            owner: "analyst-3",
        },
        relationshipAttributes: {},
        classifications: [{ typeName: "PII" }, { typeName: "CONFIDENTIAL" }],
    },
    referredEntities: {},
};

/** The entity minus its classifications — the chip-less variant. */
const NO_CHIPS = { ...ANSWER, entity: { ...ANSWER.entity, classifications: [] } };

/**
 * Bring the screen up at the given guid: the paramMap Subject carries the
 * address (a guid change is then observable), and the first
 * `detectChanges` lets the URL effect fire the read.
 */
function setup(guid = "7a1b") {
    const paramMap = new Subject<ParamMap>();
    TestBed.configureTestingModule({
        imports: [Details],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            provideRouter([]),
            { provide: ActivatedRoute, useValue: { paramMap } },
        ],
    });
    const fixture = TestBed.createComponent(Details);
    paramMap.next(convertToParamMap({ guid }));
    fixture.detectChanges(); // the URL effect runs, the request fires
    const compiled = fixture.nativeElement as HTMLElement;
    return { fixture, compiled, paramMap, httpMock: TestBed.inject(HttpTestingController) };
}

/** Deliver the entity body for the in-flight read and settle the screen. */
function arrive(fixture: { detectChanges: () => void }, httpMock: HttpTestingController, body = ANSWER) {
    httpMock.expectOne((request) => request.url.startsWith(ENTITY_URL)).flush(body);
    fixture.detectChanges();
}

const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

describe("Details data spine (DET-08..DET-13)", () => {
    it("fetches the entity by guid on arrival (DET-08)", () => {
        const { httpMock } = setup("g-42");

        const request = httpMock.expectOne("/api/atlas/v2/entity/guid/g-42");
        expect(request.request.method).toBe("GET");
        request.flush(ANSWER);
    });

    it("re-fetches on a guid change and ignores a stale answer (DET-08, DD-318)", () => {
        const { fixture, compiled, paramMap, httpMock } = setup("first");

        // Two reads in flight: the first guid's answer arrives after the
        // screen moved on, and must not paint (the legacy
        // EntityDetailsService.latestEntityId guard).
        const first = httpMock.expectOne("/api/atlas/v2/entity/guid/first");
        paramMap.next(convertToParamMap({ guid: "second" }));
        fixture.detectChanges();
        const second = httpMock.expectOne("/api/atlas/v2/entity/guid/second");

        first.flush(ANSWER); // stale: its entity names a different screen
        fixture.detectChanges();
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("Entity type");

        second.flush({ ...ANSWER, entity: { ...ANSWER.entity, guid: "second", attributes: { name: "second" } } });
        fixture.detectChanges();
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("second");
    });

    it("issues exactly one read per guid: no second client (DET-08)", () => {
        const { fixture, compiled, httpMock } = setup();

        const requests = httpMock.match((request) => request.url.startsWith(ENTITY_URL));
        expect(requests).toHaveLength(1);
        requests[0].flush(ANSWER);
        fixture.detectChanges();

        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("genomic_variants");
    });

    it("binds the header: title, type-name line, one chip per classification (DET-09)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("genomic_variants");
        const typeLine = compiled.querySelector(".aurelius-details-type");
        expect(typeLine?.querySelector("aurelius-atlas-ui-type-name")).toBeTruthy();
        expect(normalize(typeLine?.textContent)).toContain("DataSet");

        const chips = [...compiled.querySelectorAll(".aurelius-details-classifications .control")].map((control) =>
            normalize(control.textContent),
        );
        expect(chips).toEqual(["PII", "CONFIDENTIAL"]);
    });

    it("falls back: no name, qualifiedName titles; neither, the localized label (DET-09)", () => {
        const { fixture, compiled, paramMap, httpMock } = setup();
        arrive(fixture, httpMock, {
            ...ANSWER,
            entity: { ...ANSWER.entity, attributes: { qualifiedName: "qualified@only" } },
        });
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("qualified@only");

        // With neither attribute the fallback title returns (DET-02 shape
        // restored): the same localized chrome label the 7.6 skeleton rode.
        paramMap.next(convertToParamMap({ guid: "blank" }));
        fixture.detectChanges();
        arriveSecond(fixture, httpMock, {
            ...ANSWER,
            entity: { ...ANSWER.entity, guid: "blank", attributes: {} },
        });
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("Entity type");
    });

    it("renders no chips when the entity carries none (DET-09)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, NO_CHIPS);

        expect(compiled.querySelector(".aurelius-details-classifications")).toBeNull();
    });

    it("shows the description from the definition attribute (DET-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(normalize(compiled.querySelector(".aurelius-details-description")?.textContent)).toBe(
            "Curated variant calls.",
        );
    });

    it("shows the legacy placeholder when neither attribute exists (DET-10, DD-321)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, {
            ...ANSWER,
            entity: { ...ANSWER.entity, attributes: { name: "no-definition" } },
        });

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
            entity: {
                ...ANSWER.entity,
                attributes: { ...ANSWER.entity!.attributes, definition: "Curated **variant** calls." },
            },
        });

        const box = compiled.querySelector(".aurelius-details-description");
        // The asterisks are gone and the emphasis landed as markup.
        expect(normalize(box?.textContent)).toBe("Curated variant calls.");
        expect(box!.querySelector("strong")!.textContent).toBe("variant");
    });

    it("falls back to the description attribute, and keeps it out of the rows (DET-10, DET-11, DD-320)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, {
            ...ANSWER,
            entity: { ...ANSWER.entity, attributes: { name: "atlas-typed", description: "A seeded description." } },
        });

        // The Atlas model types carry their text in `description`: the box
        // shows it (DET-10) and the table drops it (DD-320 — the shown key
        // appears once on the screen, the blacklist's own mechanism).
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
        expect(compiled.querySelectorAll(".aurelius-details-properties tbody tr")).toHaveLength(2);
        expect(compiled.querySelector(".aurelius-details-properties-empty")).toBeNull();
    });

    it("renders the filtered, sorted property rows and the count (DET-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // name, qualifiedName and definition are blacklisted (the legacy
        // filter): description and owner are the renderable two, sorted.
        const rows = [...compiled.querySelectorAll(".aurelius-details-properties tbody tr")].map((row) =>
            normalize(row.querySelector("td")?.textContent),
        );
        expect(rows).toEqual(["description", "owner"]);
        expect(normalize(compiled.querySelector(".aurelius-details-property-count")?.textContent)).toBe("2");
    });

    it("routes the details screen when a property link is clicked (DET-11, DET-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, {
            ...ANSWER,
            entity: {
                ...ANSWER.entity,
                relationshipAttributes: { upstreamDatasets: [{ guid: "linked-1", displayText: "Upstream" }] },
            },
        });

        // Sorted rows: description, owner, upstreamDatasets — the link is
        // the third, and the only one whose value is a guid array (DET-11).
        const rows = [...compiled.querySelectorAll(".aurelius-details-properties tbody tr")];
        expect(rows.map((row) => normalize(row.querySelector("td")?.textContent))).toEqual([
            "description",
            "owner",
            "upstreamDatasets",
        ]);

        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const items = fixture.debugElement.queryAll(By.directive(PropertiesItem));
        (items[2].componentInstance as PropertiesItem).itemClicked.emit("linked-1");

        expect(navigate).toHaveBeenCalledWith(["/search/details", "linked-1"]);
    });

    it("renders the trail from the breadcrumb store, and routes a crumb click (DET-12, DET-06)", () => {
        const { fixture, compiled, httpMock } = setup("current");
        arrive(fixture, httpMock);

        // The seam (DD-317): the screen renders whatever the store holds
        // — empty until an API fills it — and the trail stays absent.
        expect(compiled.querySelector("nav.breadcrumb")).toBeNull();

        // The routing contract is proven at the component boundary: the
        // lib's emit reaches the screen's router call, the lib never routes.
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const crumbs = fixture.debugElement.query(By.directive(Breadcrumbs)).componentInstance as Breadcrumbs;
        crumbs.itemClicked.emit("g2");
        expect(navigate).toHaveBeenCalledWith(["/search/details", "g2"]);
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

        httpMock.expectOne(`${ENTITY_URL}7a1b`).flush({ error: "boom" }, { status: 500, statusText: "Server Error" });
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

        httpMock.expectOne(`${ENTITY_URL}missing`).flush({}, { status: 404, statusText: "Not Found" });
        fixture.detectChanges();

        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("Entity type");
        expect(compiled.querySelector(".aurelius-details-loading")).toBeNull();
        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(false);
    });

    it("keeps the guid from the route as the screen's address (DET-01, DET-07)", () => {
        const { fixture, httpMock } = setup("guid-from-route");
        httpMock.expectOne("/api/atlas/v2/entity/guid/guid-from-route").flush(ANSWER);

        const crumbs = fixture.debugElement.query(By.directive(Breadcrumbs)).componentInstance as Breadcrumbs;
        expect(crumbs.activeGuid()).toBe("guid-from-route");
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
    httpMock.expectOne((request) => request.url.startsWith(ENTITY_URL)).flush(body);
    fixture.detectChanges();
}
