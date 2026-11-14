import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { EntityCard, FacetEntry, ViewSearchAnswer } from "aurelius-atlas-data-access";
import { vi } from "vitest";

import { AlertsService } from "../alerts/alerts.service";
import { SearchMode, SearchModeService } from "../settings/search-mode.service";
import { SearchState } from "./search-state";

/** The search door's endpoint (VSR-03, AVR-01, APC-11). */
const DOOR = "/api/aurelius/v1/search";

/** Every request asks the sidebar's four facets, the type facet at DD-093's size (VSR-06). */
const FACETS = { typeName: { size: 100 }, status: {}, owner: {}, serviceType: {} };

/**
 * Build a door answer: a page of cards named `entity-<offset>…` so
 * accumulation is visible, with the sidebar's facet counts beside it (AVR-08).
 */
function page(
    offset: number,
    count: number,
    total: number,
    facets: Record<string, FacetEntry[]> = {},
): ViewSearchAnswer {
    return {
        cards: Array.from({ length: count }, (_, i): EntityCard => ({
            guid: `g${offset + i}`,
            typeName: "DataSet",
            displayText: `entity-${offset + i}`,
            status: "ACTIVE",
            stale: false,
        })),
        facets,
        total,
    };
}

/** The m4i-shaped facets the door answers (VSR-01's names, owner empty as in the sample). */
function typeFacet(entries: [string, number][]): Record<string, FacetEntry[]> {
    return {
        typeName: entries.map(([value, count]) => ({ value, count })),
        status: [{ value: "ACTIVE", count: entries.reduce((sum, [, count]) => sum + count, 0) }],
        owner: [],
    };
}

function setup() {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), SearchState] });
    return { store: TestBed.inject(SearchState), httpMock: TestBed.inject(HttpTestingController) };
}

describe("SearchState (SRH-02..06, SDX-01..07, VSR-03..09)", () => {
    it("run posts the door body with the mode, the facets and the page of ten (VSR-03, SRH-04)", () => {
        const { store, httpMock } = setup();

        store.run("data");

        const request = httpMock.expectOne(DOOR);
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({
            query: "data",
            mode: "keyword",
            facets: FACETS,
            limit: 10,
            offset: 0,
        });
        request.flush(page(0, 3, 3));
        expect(store.entries()).toHaveLength(3);
        expect(store.total()).toBe(3);
        expect(store.queryText()).toBe("data");
    });

    it("one answer feeds the list and the facet signal (SDX-02, VSR-06)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(DOOR).flush(
            page(
                0,
                3,
                116,
                typeFacet([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );

        // Cards and count read from the one answer (VSR-03); no second request exists (SDX-02).
        expect(store.entries()).toHaveLength(3);
        expect(store.total()).toBe(116);

        const facets = store.facets();
        expect(facets.map((facet) => facet.key)).toEqual(["typeName", "status"]);
        // The empty owner facet is dropped (SDX-03, the legacy FilterService rule).
        expect(facets.find((facet) => facet.key === "owner")).toBeUndefined();

        const type = facets[0];
        expect(type.selectable).toBe(true);
        expect(type.title).toBe("Type");
        expect(type.items.map((item) => [item.value, item.count])).toEqual([
            ["m4i_data_attribute", 75],
            ["m4i_data_domain", 9],
        ]);
        // The value's display name rides the dictionary (SDX-08); the state facet is read-only (SDX-05).
        expect(type.items[1].label).toBe("Data Domain");
        const state = facets[1];
        expect(state.selectable).toBe(false);
        expect(state.title).toBe("State");
        expect(state.items[0].value).toBe("ACTIVE");
    });

    it("pages accumulate at the offset and stop at the count (SRH-04, VSR-05)", () => {
        const { store, httpMock } = setup();

        store.run("gene");
        httpMock.expectOne(DOOR).flush(page(0, 10, 25));
        expect(store.entries()).toHaveLength(10);
        expect(store.allLoaded()).toBe(false);

        store.nextPage();
        const second = httpMock.expectOne(DOOR);
        expect(second.request.body).toMatchObject({ offset: 10, limit: 10 });
        second.flush(page(10, 10, 25));

        store.nextPage();
        httpMock.expectOne(DOOR).flush(page(20, 5, 25));
        expect(store.entries()).toHaveLength(25);
        expect(store.allLoaded()).toBe(true);

        // The end of the list: no further request (SRH-04's stop rule).
        store.nextPage();
        httpMock.expectNone(DOOR);
    });

    it("a query change resets the list to page one (SRH-04)", () => {
        const { store, httpMock } = setup();

        store.run("one");
        httpMock.expectOne(DOOR).flush(page(0, 10, 25));

        store.run("two");
        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({ query: "two", offset: 0 });
        request.flush(page(0, 1, 1));
        expect(store.entries()).toHaveLength(1);
    });

    it("ticking a type re-runs with the sub-type filter and checks the row (SDX-04, VSR-04)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(DOOR).flush(
            page(
                0,
                3,
                116,
                typeFacet([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );

        store.toggleType("m4i_data_domain", true);
        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({
            query: "data",
            filters: { any: [{ typeName: ["m4i_data_domain"] }, { superTypeNames: ["m4i_data_domain"] }] },
            offset: 0,
        });
        expect(store.typeSelection()).toEqual(["m4i_data_domain"]);
        request.flush(page(0, 1, 9, typeFacet([["m4i_data_domain", 9]])));
        expect(store.entries()).toHaveLength(1);

        const type = store.facets()[0];
        expect(type.items.find((item) => item.value === "m4i_data_domain")?.checked).toBe(true);
        expect(type.items.find((item) => item.value === "m4i_data_attribute")?.checked).toBe(false);
    });

    it("the seen type values stay visible with their last counts while the counts narrow (SDX-07, DD-426)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(DOOR).flush(
            page(
                0,
                3,
                116,
                typeFacet([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );

        store.toggleType("m4i_data_domain", true);
        httpMock.expectOne(DOOR).flush(page(0, 1, 9, typeFacet([["m4i_data_domain", 9]])));

        // The narrowed answer carries its one type first; the value it no
        // longer carries keeps its last count and stays listed, unchecked.
        const rows = store.facets()[0].items;
        expect(rows.map((row) => [row.value, row.count, row.checked ?? false])).toEqual([
            ["m4i_data_domain", 9, true],
            ["m4i_data_attribute", 75, false],
        ]);

        // Unticking restores the broad answer and its counts (DD-426).
        store.toggleType("m4i_data_domain", false);
        const broad = httpMock.expectOne(DOOR);
        expect(broad.request.body).not.toHaveProperty("filters");
        broad.flush(
            page(
                0,
                3,
                116,
                typeFacet([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );
        expect(store.facets()[0].items.map((row) => [row.value, row.count])).toEqual([
            ["m4i_data_attribute", 75],
            ["m4i_data_domain", 9],
        ]);
    });

    it("a query change resets the facet seen set (SDX-07)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(DOOR).flush(
            page(
                0,
                3,
                116,
                typeFacet([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );
        store.toggleType("m4i_data_domain", true);
        httpMock.expectOne(DOOR).flush(page(0, 1, 9, typeFacet([["m4i_data_domain", 9]])));

        store.run("other");
        httpMock.expectOne(DOOR).flush(page(0, 0, 0));
        // The seen rows are gone with the query; the next answer's facets stand alone.
        expect(store.facets()).toEqual([]);
    });

    it("a hero submit clears the selection and a URL change keeps it (SDX-06, DD-425)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(DOOR).flush(
            page(
                0,
                3,
                116,
                typeFacet([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );
        store.toggleType("m4i_data_domain", true);
        httpMock.expectOne(DOOR).flush(page(0, 1, 9, typeFacet([["m4i_data_domain", 9]])));

        // The resolver twin of the SAME text re-runs nothing and clears nothing.
        store.applyUrl("data");
        httpMock.expectNone(DOOR);
        expect(store.typeSelection()).toEqual(["m4i_data_domain"]);

        // A different URL text (back/forward, a pasted link): the store
        // follows, the selection survives — the legacy resolver set the
        // store's query and never touched its filters (SDX-06).
        store.applyUrl("other");
        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({ query: "other", offset: 0 });
        expect(store.typeSelection()).toEqual(["m4i_data_domain"]);
        request.flush(page(0, 0, 0));

        // A hero submit clears it (the legacy onQuerySubmitted's reset).
        store.toggleType("m4i_field", true);
        httpMock.expectOne(DOOR).flush(page(0, 0, 0));
        expect(store.typeSelection()).toEqual(["m4i_data_domain", "m4i_field"]);
        store.run("fresh");
        httpMock.expectOne(DOOR).flush(page(0, 0, 0));
        expect(store.typeSelection()).toEqual([]);
    });

    it("a multi-select selection asks both fields for every selected name (VSR-04)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(DOOR).flush(
            page(
                0,
                3,
                116,
                typeFacet([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );

        store.toggleType("m4i_data_domain", true);
        httpMock.expectOne(DOOR).flush(page(0, 1, 9, typeFacet([["m4i_data_domain", 9]])));
        store.toggleType("m4i_data_attribute", true);
        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({
            filters: {
                any: [
                    { typeName: ["m4i_data_domain", "m4i_data_attribute"] },
                    { superTypeNames: ["m4i_data_domain", "m4i_data_attribute"] },
                ],
            },
        });
        request.flush(
            page(
                0,
                2,
                84,
                typeFacet([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );
    });

    it("applyUrl follows the URL and re-runs nothing on the same text (SRH-02)", () => {
        const { store, httpMock } = setup();

        store.explore("AtlasGlossary");
        httpMock.expectOne(DOOR).flush(page(0, 1, 1));

        // The results screen's effect fires on arrival with the URL's
        // (absent) query — the store's "" matches, so the explore survives.
        store.applyUrl();
        store.applyUrl("");
        httpMock.expectNone(DOOR);
        expect(store.typeSelection()).toEqual(["AtlasGlossary"]);

        // A hero submit of "term" (run) followed by the URL effect (applyUrl
        // of the same text): one request, not two (DD-219's no-op guard).
        store.run("term");
        httpMock.expectOne(DOOR).flush(page(0, 1, 1));
        store.applyUrl("term");
        httpMock.expectNone(DOOR);

        // A different text (back/forward, a pasted link): the store follows.
        store.applyUrl("other");
        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({ query: "other", offset: 0 });
        request.flush(page(0, 1, 1));
        expect(store.queryText()).toBe("other");
    });

    it("explore searches the empty query with the card's type in the selection (SRH-08, DV-84)", () => {
        const { store, httpMock } = setup();

        store.explore("Infrastructure");

        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toEqual({
            query: "",
            mode: "keyword",
            filters: { any: [{ typeName: ["Infrastructure"] }, { superTypeNames: ["Infrastructure"] }] },
            facets: FACETS,
            limit: 10,
            offset: 0,
        });
        request.flush(page(0, 2, 2));
        expect(store.entries()).toHaveLength(2);
    });

    it("the empty query with no selection asks no filter and lists everything (VSR-04, DD-221)", () => {
        const { store, httpMock } = setup();

        store.run(null);

        // The door answers an empty query with everything (AVR-11): the
        // every-entity marker left with the quick-search wire (DD-600).
        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toEqual({
            query: "",
            mode: "keyword",
            facets: FACETS,
            limit: 10,
            offset: 0,
        });
        expect(request.request.body).not.toHaveProperty("filters");
        request.flush(page(0, 3, 42));
        expect(store.entries()).toHaveLength(3);
        expect(store.total()).toBe(42);
    });

    it("a first arrival at a query-less URL fires the list-everything search (SRH-02, DD-221)", () => {
        const { store, httpMock } = setup();

        // Arriving at /search/results directly (a bookmark, a reload): the
        // legacy resolver ran on every arrival, its query='' default
        // included — the store's "" is not yet "already run".
        store.applyUrl();

        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({ query: "" });
        expect(request.request.body).not.toHaveProperty("filters");
        request.flush(page(0, 2, 2));
        expect(store.entries()).toHaveLength(2);
    });

    it("a zero answer renders as no results (SRH-06)", () => {
        const { store, httpMock } = setup();

        store.run("nothing");
        httpMock.expectOne(DOOR).flush(page(0, 0, 0));

        expect(store.noResults()).toBe(true);
        expect(store.hasResults()).toBe(false);
    });

    it("a failing page lands in the alerts store and ends the load (SDX-01, DD-214, VSR-08)", () => {
        const { store, httpMock } = setup();
        const alerts = TestBed.inject(AlertsService);
        const add = vi.spyOn(alerts, "add");

        store.run("boom");
        httpMock
            .expectOne(DOOR)
            .flush(
                { errorCode: "AURELIUS-400-00-002", errorMessage: "nope" },
                { status: 400, statusText: "Bad Request" },
            );

        expect(store.loading()).toBe(false);
        expect(add).toHaveBeenCalledWith(expect.objectContaining({ severity: "error", source: "search" }));
    });
});

/** Store a mode as the settings panel does (SBX-01, SBX-02). */
function chooseMode(mode: SearchMode): void {
    TestBed.inject(SearchModeService).set(mode);
}

describe("SearchState by meaning (SBW-03..SBW-06, SBX-02, VSR-03/05/08/09)", () => {
    // The mode is a stored setting: every test starts, and leaves, with Words.
    beforeEach(() => localStorage.clear());
    afterEach(() => localStorage.clear());

    it("Meaning posts the door body with the semantic mode (VSR-03, ASV-01)", () => {
        const { store, httpMock } = setup();
        chooseMode("semantic");

        store.run("customer address");

        const request = httpMock.expectOne(DOOR);
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({
            query: "customer address",
            mode: "semantic",
            facets: FACETS,
            limit: 10,
            offset: 0,
        });
        request.flush(page(0, 3, 3, typeFacet([["m4i_data_entity", 3]])));
        expect(store.entries()).toHaveLength(3);
        expect(store.facets()[0].items.map((item) => item.value)).toEqual(["m4i_data_entity"]);
        httpMock.verify();
    });

    it("Both posts the door body with the hybrid mode and the type filter (VSR-03, VSR-04)", () => {
        const { store, httpMock } = setup();
        chooseMode("hybrid");
        store.run("employee");
        httpMock.expectOne(DOOR).flush(page(0, 1, 1, typeFacet([["DataSet", 1]])));

        store.toggleType("DataSet", true);

        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({
            query: "employee",
            mode: "hybrid",
            filters: { any: [{ typeName: ["DataSet"] }, { superTypeNames: ["DataSet"] }] },
        });
        httpMock.verify();
    });

    it("an empty query lists in words whatever the mode (SBW-03, ASV-06)", () => {
        const { store, httpMock } = setup();
        chooseMode("semantic");

        store.run(null);

        // The door refuses a meaning mode without words (ASV-06): the body
        // carries the keyword mode while none of the query's words are there.
        expect(httpMock.expectOne(DOOR).request.body).toMatchObject({ mode: "keyword" });
        expect(store.byMeaning()).toBe(false);
        httpMock.verify();
    });

    it("by meaning a full page asks for the next and the header counts what is shown (SBW-04, VSR-05)", () => {
        const { store, httpMock } = setup();
        chooseMode("semantic");
        store.run("orders");
        httpMock.expectOne(DOOR).flush(page(0, 10, 10));

        expect(store.allLoaded()).toBe(false);
        expect(store.shownCount()).toBe(10);
        store.nextPage();
        const next = httpMock.expectOne(DOOR);
        expect(next.request.body).toMatchObject({ offset: 10, limit: 10 });
        next.flush(page(10, 4, 14));

        expect(store.shownCount()).toBe(14);
        expect(store.allLoaded()).toBe(true);
        store.nextPage();
        httpMock.verify();
    });

    it("by meaning the list ends at 1,000 entities, never past the door's window (SBW-04, VSR-05, ASV-08)", () => {
        const { store, httpMock } = setup();
        chooseMode("semantic");
        store.run("orders");

        for (let offset = 0; offset < 1000; offset += 10) {
            httpMock.expectOne(DOOR).flush(page(offset, 10, offset + 10));
            store.nextPage();
        }

        expect(store.entries()).toHaveLength(1000);
        expect(store.allLoaded()).toBe(true);
        // The window's end: offset + limit stays at most 1,000 (ASV-08).
        httpMock.verify();
    });

    it("a mode stored in the settings restarts a search with a query at page one, the selection kept (SBX-02, VSR-09)", () => {
        const { store, httpMock } = setup();
        store.run("orders");
        httpMock.expectOne(DOOR).flush(page(0, 10, 30, typeFacet([["DataSet", 30]])));
        store.toggleType("DataSet", true);
        httpMock.expectOne(DOOR).flush(page(0, 10, 30));

        chooseMode("hybrid");

        const request = httpMock.expectOne(DOOR);
        expect(request.request.body).toMatchObject({
            offset: 0,
            mode: "hybrid",
            filters: { any: [{ typeName: ["DataSet"] }, { superTypeNames: ["DataSet"] }] },
        });
        expect(store.entries()).toEqual([]);
        chooseMode("hybrid");
        httpMock.verify();
    });

    it("a mode stored without a query searches nothing until a query comes (SBX-02, VSR-09)", () => {
        const { store, httpMock } = setup();

        chooseMode("semantic");

        httpMock.verify();
        expect(store.mode()).toBe("semantic");
    });

    it("a server without search by meaning says so and searches by words again (SBW-06, VSR-08)", () => {
        const { store, httpMock } = setup();
        const alerts = TestBed.inject(AlertsService);
        const add = vi.spyOn(alerts, "add");
        chooseMode("semantic");
        store.run("orders");

        httpMock
            .expectOne(DOOR)
            .flush({ errorCode: "AURELIUS-404-00-001", errorMessage: "off" }, { status: 404, statusText: "Not Found" });

        expect(add).toHaveBeenCalledWith(expect.objectContaining({ severity: "warning", source: "search" }));
        expect(store.mode()).toBe("words");
        const words = httpMock.expectOne(DOOR);
        expect(words.request.body).toMatchObject({ query: "orders", mode: "keyword" });
        httpMock.verify();
    });

    it("any other failure by meaning is the failed page's alert, the mode kept (SBW-06, VSR-08)", () => {
        const { store, httpMock } = setup();
        const alerts = TestBed.inject(AlertsService);
        const add = vi.spyOn(alerts, "add");
        chooseMode("semantic");
        store.run("orders");

        httpMock.expectOne(DOOR).flush({ errorCode: "AURELIUS-503-00-001" }, { status: 503, statusText: "Down" });

        expect(add).toHaveBeenCalledWith(expect.objectContaining({ severity: "error", source: "search" }));
        expect(store.mode()).toBe("semantic");
        expect(store.loading()).toBe(false);
        httpMock.verify();
    });
});
