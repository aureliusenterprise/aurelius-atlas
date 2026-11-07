import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter } from "@angular/router";
import { By } from "@angular/platform-browser";
import Keycloak from "keycloak-js";
import { Subject } from "rxjs";
import { faPenToSquare } from "@fortawesome/free-solid-svg-icons";

import type { AtlasEntity, AtlasEntityWithExtInfo } from "aurelius-atlas-data-access";
import { Breadcrumbs, PropertiesItem } from "aurelius-atlas-ui";

import { AlertsService } from "../../alerts/alerts.service";
import { APP_CONFIG } from "../../tokens";
import { EntitySaved } from "../editor/entity-saved";

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

/** The layout dispatch's typedef read (DET-15): `/v2/types/typedef/name/{name}`. */
const TYPEDEF_URL = "/api/atlas/v2/types/typedef/name/";

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
 * `detectChanges` lets the URL effect fire the read. The fake Keycloak
 * answers `canWrite` for the editor pencil (EDT-09): granted unless a
 * test passes `atlasWrite: false`.
 */
function setup(guid = "7a1b", { atlasWrite = true }: { atlasWrite?: boolean } = {}) {
    const paramMap = new Subject<ParamMap>();
    TestBed.configureTestingModule({
        imports: [Details],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            provideRouter([]),
            { provide: ActivatedRoute, useValue: { paramMap } },
            { provide: APP_CONFIG, useValue: { atlasClientId: "aurelius-atlas-server" } },
            {
                provide: Keycloak,
                useValue: { hasResourceRole: (role: string) => atlasWrite && role === "atlas-write" },
            },
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
    settleTypeDefs(httpMock);
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
        settleTypeDefs(httpMock);
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("second");
    });

    it("issues exactly one read per guid: no second client (DET-08)", () => {
        const { fixture, compiled, httpMock } = setup();

        const requests = httpMock.match((request) => request.url.startsWith(ENTITY_URL));
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

        TestBed.inject(EntitySaved).notify("saved-guid");
        fixture.detectChanges();

        // The still-mounted screen re-reads the saved entity (the drawer
        // save never changed this URL, so the router reused the component).
        const second = httpMock.expectOne("/api/atlas/v2/entity/guid/saved-guid");
        expect(second.request.method).toBe("GET");
        second.flush({ ...ANSWER, entity: { ...ANSWER.entity, attributes: { name: "renamed_after_save" } } });
        fixture.detectChanges();
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("renamed_after_save");
    });

    it("a save tick for another guid reads nothing (DD-327)", () => {
        const { fixture, compiled, httpMock } = setup("saved-guid");
        arrive(fixture, httpMock);

        TestBed.inject(EntitySaved).notify("some-other-guid");
        fixture.detectChanges();

        httpMock.expectNone("/api/atlas/v2/entity/guid/saved-guid");
        // The screen's own read is already flushed above; nothing else fires
        // and the rendered entity stays as it arrived.
        httpMock.verify();
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("genomic_variants");
    });
});

/** A related-entity end of the seeded `relationshipAttributes`. */
function end(guid: string, displayText: string): Record<string, unknown> {
    return { guid, displayText, typeName: "m4i_data_attribute", name: displayText };
}

/** A person end of the seeded `relationshipAttributes`. */
function person(guid: string, displayText: string): Record<string, unknown> {
    return { guid, displayText, typeName: "person" };
}

/** The m4i entity body, overridable per spec. */
function m4iEntity(overrides: Partial<AtlasEntity> = {}): AtlasEntityWithExtInfo {
    return {
        entity: {
            guid: "m4i-1",
            typeName: "m4i_data_entity",
            attributes: {
                name: "variants_entity",
                qualifiedName: "variants@cluster",
                description: "A governed entity.",
            },
            relationshipAttributes: {
                attributes: [end("a1", "gene_symbol"), end("a2", "chromosome")],
                businessOwner: [person("p1", "Ada")],
                steward: [person("p2", "Lin"), person("p2", "Lin again")],
                domainLead: [person("p3", "Ada Lead")],
            },
            ...overrides,
        },
        referredEntities: {},
    };
}

/** The bulk answer for the two seeded attributes; extra overrides per guid. */
function attributesAnswer(overrides: Record<string, Record<string, unknown>> = {}): Record<string, unknown> {
    return {
        entities: [
            {
                guid: "a1",
                typeName: "m4i_data_attribute",
                attributes: { name: "gene_symbol", qualifiedName: "gene_symbol@cluster", description: "HGNC symbol." },
                relationshipAttributes: { steward: [person("p2", "Lin")] },
                ...overrides["a1"],
            },
            {
                guid: "a2",
                typeName: "m4i_data_attribute",
                attributes: { name: "chromosome", qualifiedName: "chromosome@cluster", description: "The pair." },
                ...overrides["a2"],
            },
        ],
        referredEntities: {},
    };
}

/** Deliver an m4i entity's read and its sections' first chunk. */
function arriveSections(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    body: AtlasEntityWithExtInfo = m4iEntity(),
    answer: Record<string, unknown> = attributesAnswer(),
) {
    arrive(fixture, httpMock, body);
    for (const request of httpMock.match((r) => r.url === "/api/atlas/v2/entity/bulk")) {
        request.flush(answer);
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
        expect(normalize(compiled.querySelector("#people-details h3")?.textContent)).toBe("People");
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

        for (const request of httpMock.match((r) => r.url === "/api/atlas/v2/entity/bulk")) {
            request.flush(attributesAnswer());
        }
        fixture.detectChanges();

        const titles = [...(box?.querySelectorAll("aurelius-atlas-ui-entity-card .title.is-4 a") ?? [])].map((link) =>
            normalize(link.textContent),
        );
        expect(titles).toEqual(["gene_symbol", "chromosome"]);
        httpMock.verify();
    });

    it("a card body shows chips, the description, and the card entity's people (DET-19)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(
            fixture,
            httpMock,
            m4iEntity({ relationshipAttributes: { attributes: [end("a1", "gene_symbol")] } }),
            {
                entities: [
                    {
                        guid: "a1",
                        typeName: "m4i_data_attribute",
                        attributes: { name: "gene_symbol", description: "HGNC **symbol**." },
                        classifications: [{ typeName: "PII" }],
                        relationshipAttributes: { steward: [person("p2", "Lin")] },
                    },
                ],
                referredEntities: {},
            },
        );

        const card = compiled.querySelector("#related-attributes aurelius-atlas-ui-entity-card")!;
        expect(normalize(card.querySelector(".field.is-grouped .control")?.textContent)).toBe("PII");
        expect(card.querySelector(".aurelius-card-description strong")?.textContent).toBe("symbol"); // markdown (DET-10 sibling)
        expect(normalize(card.querySelector(".aurelius-people-row")?.textContent)).toBe("Data Steward(s) : Lin");
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
            m4iEntity({ relationshipAttributes: { attributes: [end("a1", "gene_symbol"), end("a2", "chromosome")] } }),
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
        arriveSections(fixture, httpMock, m4iEntity({ relationshipAttributes: { attributes: many } }), {
            entities: many.map((row) => ({
                guid: row["guid"],
                typeName: "m4i_data_attribute",
                attributes: { name: row["displayText"] },
            })),
            referredEntities: {},
        });

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

        for (const request of httpMock.match((r) => r.url === "/api/atlas/v2/entity/bulk")) {
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
        httpMock.expectNone("/api/atlas/v2/entity/bulk"); // no retry loop
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
            ["Properties", "#properties-details", "0"],
        ]);
        // No Data Quality stat at all (DD-369: not a zero, nothing).
        expect(stats.some(([label]) => label.includes("Quality"))).toBe(false);
    });

    it("the side navigation lists the layout's boxes (DET-25)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        const items = [...compiled.querySelectorAll(".aurelius-details-nav .menu-list a")].map((link) => [
            normalize(link.textContent),
            link.getAttribute("href"),
        ]);
        expect(items).toEqual([
            ["Description", "#description-details"],
            ["People", "#people-details"],
            ["Data Attributes", "#related-attributes"],
            ["Child Entities", "#related-entities"],
            ["Properties", "#properties-details"],
        ]);
    });

    it("the header badge shows the alias with the base type, the cards the alias alone (DET-26)", () => {
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
            attributesAnswer({ a1: { attributes: { name: "gene_symbol", typeAlias: "Data Attribute" } } }),
        );

        // The header badge: the alias with the base type beside it.
        expect(normalize(compiled.querySelector(".aurelius-details-type")?.textContent)).toBe(
            "Data Entity (m4i_data_entity)",
        );
        // The card badges: only the resolved card carrying an alias shows
        // one, and it shows the alias alone (DD-374, demo-measured — the
        // legacy card never passes showBaseTypeName).
        const badges = [
            ...compiled.querySelectorAll("#related-attributes aurelius-atlas-ui-entity-card .media-right"),
        ].map((badge) => normalize(badge.textContent));
        expect(badges).toEqual(["Data Attribute", "m4i_data_attribute"]);
    });

    it("an m4i attribute shows its People box and its Fields section (DET-16, DET-23)", () => {
        const { fixture, compiled, httpMock } = setup("attr-1");
        arriveSections(
            fixture,
            httpMock,
            {
                entity: {
                    guid: "attr-1",
                    typeName: "m4i_data_attribute",
                    attributes: { name: "gene_symbol" },
                    relationshipAttributes: { fields: [end("f1", "chromosome_pos")] },
                },
                referredEntities: {},
            },
            {
                entities: [{ guid: "f1", typeName: "m4i_field", attributes: { name: "chromosome_pos" } }],
                referredEntities: {},
            },
        );

        // The attribute page carries a People box (the spec table and the
        // legacy page both); with no people ends it shows the empty line.
        expect(compiled.querySelector("#people-details")).toBeTruthy();
        expect(normalize(compiled.querySelector(".aurelius-people-empty")?.textContent)).toBe("No people assigned.");
        expect(normalize(compiled.querySelector("#related-fields h3")?.textContent)).toBe("Fields");
        expect(compiled.querySelectorAll("#related-fields aurelius-atlas-ui-entity-card")).toHaveLength(1);
    });

    it("the save re-read re-seeds the sections (DET-17, DD-327)", () => {
        const { fixture, compiled, httpMock } = setup("m4i-1");
        arriveSections(fixture, httpMock);

        TestBed.inject(EntitySaved).notify("m4i-1");
        fixture.detectChanges();
        httpMock.expectOne("/api/atlas/v2/entity/guid/m4i-1").flush(m4iEntity({ relationshipAttributes: {} }));
        fixture.detectChanges();

        // The new entity has no ends: every section re-seeds to zero.
        expect(normalize(compiled.querySelector("#related-attributes h6")?.textContent)).toBe("0 result(s)");
        httpMock.verify();
    });

    it("a DataSet keeps the DET-14 default shape while its walk runs (DET-15)", async () => {
        const { fixture, compiled, httpMock } = setup("ds-1");
        // Delivered without settling the walk: this spec rides it to the end.
        httpMock.expectOne((request) => request.url.startsWith(ENTITY_URL)).flush(ANSWER);
        fixture.detectChanges();

        // The default layout's boxes — no section boxes, no People box.
        expect(compiled.querySelector("#related-fields")).toBeNull();
        expect(compiled.querySelector("#people-details")).toBeNull();
        expect(compiled.querySelector("table.aurelius-details-properties")).toBeTruthy();
        expect(normalize(compiled.querySelector(".aurelius-details-property-count")?.textContent)).toBe("2");

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
