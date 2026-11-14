import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, convertToParamMap } from "@angular/router";
import { Subject } from "rxjs";
import { vi } from "vitest";

import { SearchState } from "../search-state";
import { Results } from "./results.component";

const DOOR = "/api/aurelius/v1/search";

/**
 * A page of cards, named so the rows are identifiable, in the search door's
 * answer shape (AVR-08) — no facets unless a test asks (VSR-03).
 */
function page(count: number, total: number, offset = 0) {
    return {
        cards: Array.from({ length: count }, (_, i) => ({
            guid: `g${offset + i}`,
            typeName: "DataSet",
            displayText: `entity-${offset + i}`,
            status: "ACTIVE",
            stale: false,
        })),
        facets: {},
        total,
    };
}

/** A page carrying the m4i-shaped facets (SDX-02: results and facets, one answer). */
function facetPage() {
    return {
        ...page(3, 3),
        facets: {
            typeName: [
                { value: "m4i_data_attribute", count: 75 },
                { value: "m4i_data_domain", count: 9 },
            ],
            status: [{ value: "ACTIVE", count: 84 }],
            owner: [],
        },
    };
}

/**
 * The screen with a controllable URL: the subject stands in for the router's
 * query-parameter stream (the legacy `paramsOrQueryParamsChange`). The
 * screen's URL effect fires on arrival — the stream starts empty, so the
 * arrival is the query-less URL: the list-everything search (DD-221),
 * consumable as `arrival`.
 */
function setup() {
    const navigate = vi.fn().mockResolvedValue(true);
    const queryParamMap = new Subject<ParamMap>();
    TestBed.configureTestingModule({
        imports: [Results],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            SearchState,
            { provide: Router, useValue: { navigate } },
            { provide: ActivatedRoute, useValue: { queryParamMap } },
        ],
    });
    const fixture = TestBed.createComponent(Results);
    fixture.detectChanges();
    return {
        fixture,
        navigate,
        queryParamMap,
        store: TestBed.inject(SearchState),
        httpMock: TestBed.inject(HttpTestingController),
        compiled: fixture.nativeElement as HTMLElement,
        /** The arrival's list-everything request (the empty stream). */
        arrival: () => TestBed.inject(HttpTestingController).expectOne(DOOR),
    };
}

/**
 * Arrive on `?query=…`: the screen runs it, the answer flushes, the rows
 * render. Returns the harness with the first request consumed.
 */
function arrive(query: string, answer = page(3, 3)) {
    const harness = setup();
    harness.arrival().flush(page(0, 0)); // the query-less arrival (DD-221)
    harness.queryParamMap.next(convertToParamMap({ query }));
    harness.fixture.detectChanges(); // the URL effect runs, the request fires
    harness.httpMock.expectOne(DOOR).flush(answer);
    harness.fixture.detectChanges();
    return harness;
}

const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

describe("Results screen (SRH-02, SRH-04..07)", () => {
    it("arrives on the URL's query and runs it (SRH-02, SRH-03)", () => {
        const harness = setup();
        harness.arrival().flush(page(0, 0));

        harness.queryParamMap.next(convertToParamMap({ query: "genomic" }));
        harness.fixture.detectChanges(); // the URL effect runs the search

        const request = harness.httpMock.expectOne(DOOR);
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toMatchObject({ query: "genomic", mode: "keyword", limit: 10, offset: 0 });
        request.flush(page(1, 1));
    });

    it("a query-parameter change re-runs the search (SRH-02)", () => {
        const harness = arrive("one", page(1, 1));

        harness.queryParamMap.next(convertToParamMap({ query: "two" }));
        harness.fixture.detectChanges();

        const request = harness.httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({ query: "two", offset: 0 });
        request.flush(page(1, 1));
    });

    it("an absent query lists every entity (SRH-02, SRH-03, DD-221)", () => {
        const harness = setup();

        // The arrival IS the query-less URL: the resolver twin's '' default,
        // which the door answers with every entity — no filter, no marker
        // (VSR-04, AVR-11, DD-600).
        const request = harness.arrival();
        expect(request.request.body).toMatchObject({ query: "", offset: 0 });
        expect(request.request.body).not.toHaveProperty("filters");
        request.flush(page(2, 2));
        harness.fixture.detectChanges();
        expect(harness.compiled.querySelectorAll("aurelius-atlas-ui-entity-card")).toHaveLength(2);
    });

    it("renders the count header and one card per hit, from the hit (SRH-05, DV-83)", () => {
        const { compiled, httpMock } = arrive("genomic", page(3, 3));

        expect(normalize(compiled.querySelector(".results-count")?.textContent)).toBe("3 results");
        // The header is the legacy h6.title.is-6 INSIDE the results box.
        expect(compiled.querySelector(".results-box .title.is-6.results-count")).toBeTruthy();

        const cards = compiled.querySelectorAll("aurelius-atlas-ui-entity-card");
        expect(cards).toHaveLength(3);
        // The title is the hit's displayText, rendered straight from the
        // search answer: the screen issued exactly one request (DV-83).
        expect(normalize(cards[0].querySelector(".title.is-4 a")?.textContent)).toBe("entity-0");
        expect(normalize(cards[2].querySelector(".title.is-4 a")?.textContent)).toBe("entity-2");
        httpMock.verify();
    });

    it("a card click routes to the entity's details (SRH-05)", () => {
        const { compiled, navigate } = arrive("genomic");

        compiled.querySelector<HTMLElement>("aurelius-atlas-ui-entity-card .title.is-4 a")!.click();
        expect(navigate).toHaveBeenCalledWith(["/search/details", "g0"]);
    });

    it("a card whose type is in the icon map leads its badge with the icon (DET-26, DD-378)", () => {
        const cardPage = {
            ...page(1, 1),
            cards: [{ guid: "g0", typeName: "m4i_dataset", displayText: "topic-x", status: "ACTIVE", stale: false }],
        };
        const { compiled } = arrive("topic", cardPage);

        const icon = compiled.querySelector("aurelius-atlas-ui-entity-card .media-right .icon");
        expect(icon).toBeTruthy();
        expect(icon!.classList.contains("technical")).toBe(true);
        expect(icon!.querySelector("fa-icon svg")).toBeTruthy();
        // The badge shows the dictionary display name (SRH-05, DD-379).
        expect(normalize(compiled.querySelector("aurelius-atlas-ui-entity-card .media-right")?.textContent)).toBe(
            "Dataset",
        );
        // The fixture page's DataSet hits are outside the map: the legacy
        // *ngIf rendered no icon for them — checked by the map spec; here
        // the m4i card is the only one on screen.
    });

    it("the filter column is the legacy shell: the keyed line, no controls (SRH-07)", () => {
        const { compiled } = arrive("genomic");

        const column = compiled.querySelector(".column.is-one-third");
        expect(column).toBeTruthy();
        expect(normalize(column?.querySelector(".no-filters")?.textContent)).toBe("No filters available.");
        expect(column?.querySelector("input, button")).toBeFalsy();
    });

    it("the facet sidebar renders one menu per non-empty facet (SDX-02, SDX-03, SDX-05)", () => {
        const { compiled } = arrive("data", facetPage());

        const menus = compiled.querySelectorAll(".column.is-one-third aurelius-atlas-ui-facet-list");
        expect(menus).toHaveLength(2); // Asset.owner (empty) dropped (SDX-03)
        const labels = [...menus].map((menu) => normalize(menu.querySelector(".menu-label")?.textContent));
        expect(labels).toEqual(["Type", "State"]);
        // The count rides the row in parentheses (UIC-33); the label is the
        // type's dictionary display name (SDX-08).
        const typeRows = menus[0].querySelectorAll(".menu-list li .label-text");
        expect(normalize(typeRows[0].textContent)).toBe("Data Attribute (75)");
    });

    it("the type facet is checkboxes and the others are plain text (SDX-04, SDX-05)", () => {
        const { compiled } = arrive("data", facetPage());

        const menus = compiled.querySelectorAll(".column.is-one-third aurelius-atlas-ui-facet-list");
        // The type facet (first) carries real checkboxes; the state facet none.
        expect(menus[0].querySelectorAll("input[type=checkbox]")).toHaveLength(2);
        expect(menus[1].querySelector("input[type=checkbox]")).toBeFalsy();
    });

    it("ticking a type re-runs the search narrowed to it (SDX-04, UIC-34)", () => {
        const harness = arrive("data", facetPage());

        const box = harness.compiled.querySelector<HTMLInputElement>(".column.is-one-third input[type=checkbox]")!;
        box.click(); // tick "m4i_data_attribute" (the first type row)
        harness.fixture.detectChanges();

        const request = harness.httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({
            query: "data",
            filters: { any: [{ typeName: ["m4i_data_attribute"] }, { superTypeNames: ["m4i_data_attribute"] }] },
            offset: 0,
        });
        request.flush(page(1, 1));
    });

    it("a zero answer renders the no-results pair: no cards, no count (SRH-06)", () => {
        const { compiled } = arrive("nothing", page(0, 0));

        expect(compiled.querySelector(".results-count")).toBeFalsy();
        expect(compiled.querySelector("aurelius-atlas-ui-entity-card")).toBeFalsy();
        // The #noData twin is top-level: the columns — the filter shell
        // included — are gone with the data (the legacy ngIf/ngIf:else).
        expect(compiled.querySelector(".column.is-one-third")).toBeFalsy();
        expect(normalize(compiled.querySelector(".no-results")?.textContent)).toBe("No results found");
        expect(normalize(compiled.querySelector(".another-query")?.textContent)).toBe(
            "Please, try to make another query.",
        );
    });

    it("the container's button asks for the next page, appended (SRH-04)", () => {
        const harness = arrive("gene", page(10, 25));

        expect(harness.store.entries()).toHaveLength(10);
        const load = [...harness.compiled.querySelectorAll<HTMLButtonElement>("button.button")].find((button) =>
            button.textContent?.includes("Load next page"),
        )!;
        expect(load).toBeTruthy();

        load.click();

        const second = harness.httpMock.expectOne(DOOR);
        expect(second.request.body).toMatchObject({ query: "gene", offset: 10, limit: 10 });
        second.flush(page(10, 25));
        expect(harness.store.entries()).toHaveLength(20);
    });

    it("the loaded list stops asking: no button once every page is in (SRH-04)", () => {
        const harness = arrive("gene", page(3, 3));

        expect(harness.store.allLoaded()).toBe(true);
        const load = [...harness.compiled.querySelectorAll("button.button")].find((button) =>
            button.textContent?.includes("Load next page"),
        );
        expect(load).toBeFalsy();
    });
});
