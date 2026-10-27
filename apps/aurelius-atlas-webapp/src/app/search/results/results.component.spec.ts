import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, convertToParamMap } from "@angular/router";
import { Subject } from "rxjs";
import { vi } from "vitest";

import { SearchState } from "../search-state";
import { Results } from "./results.component";

const BASIC_SEARCH = "/api/atlas/v2/search/basic";

/** A page of hits, named so the rows are identifiable. */
function page(count: number, approximateCount: number) {
    return {
        entities: Array.from({ length: count }, (_, i) => ({
            guid: `g${i}`,
            typeName: "DataSet",
            displayText: `entity-${i}`,
            attributes: { name: `attr-${i}` },
        })),
        approximateCount,
        queryType: "BASIC",
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
        arrival: () => TestBed.inject(HttpTestingController).expectOne(BASIC_SEARCH),
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
    harness.httpMock.expectOne(BASIC_SEARCH).flush(answer);
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

        const request = harness.httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toMatchObject({ query: "genomic", limit: 10, offset: 0 });
        request.flush(page(1, 1));
    });

    it("a query-parameter change re-runs the search (SRH-02)", () => {
        const harness = arrive("one", page(1, 1));

        harness.queryParamMap.next(convertToParamMap({ query: "two" }));
        harness.fixture.detectChanges();

        const request = harness.httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.body).toMatchObject({ query: "two", offset: 0 });
        request.flush(page(1, 1));
    });

    it("an absent query lists every entity (SRH-02, SRH-03, DD-221)", () => {
        const harness = setup();

        // The arrival IS the query-less URL: the resolver twin's '' default,
        // answered with the every-entity marker (SRC-03) standing in for the
        // type the server requires with an empty query (SRC-02).
        const request = harness.arrival();
        expect(request.request.body).toMatchObject({ typeName: "_ALL_ENTITY_TYPES", query: "", offset: 0 });
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

    it("the filter column is the legacy shell: the keyed line, no controls (SRH-07)", () => {
        const { compiled } = arrive("genomic");

        const column = compiled.querySelector(".column.is-one-third");
        expect(column).toBeTruthy();
        expect(normalize(column?.querySelector(".no-filters")?.textContent)).toBe("No filters available.");
        expect(column?.querySelector("input, button")).toBeFalsy();
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

        const second = harness.httpMock.expectOne(BASIC_SEARCH);
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
