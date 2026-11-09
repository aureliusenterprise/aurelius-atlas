import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { AtlasAggregationEntry, AtlasEntityHeader, AtlasSearchResult } from "aurelius-atlas-data-access";
import { vi } from "vitest";

import { AlertsService } from "../alerts/alerts.service";
import { SearchState } from "./search-state";

/** The endpoint the store posts to (SDX-01, QSR-01, APC-11). */
const QUICK_SEARCH = "/api/atlas/v2/search/quick";

/**
 * Build a quick-search answer: a page of hits named `entity-<offset>…` so
 * accumulation is visible, nested under `searchResults` with the sidebar's
 * `aggregationMetrics` beside it (QSR-02, SDX-02).
 */
function page(
    offset: number,
    count: number,
    approximateCount: number,
    metrics: Record<string, AtlasAggregationEntry[]> = {},
) {
    const results: AtlasSearchResult = {
        entities: Array.from({ length: count }, (_, i) => ({
            guid: `g${offset + i}`,
            typeName: "DataSet",
            displayText: `entity-${offset + i}`,
        })) as AtlasEntityHeader[],
        approximateCount,
        queryType: "BASIC",
    };
    return { searchResults: results, aggregationMetrics: metrics };
}

/** The m4i-shaped facets the server answers (QSR-03's example, owner empty as in the sample). */
function typeMetrics(entries: [string, number][]): Record<string, AtlasAggregationEntry[]> {
    return {
        __typeName: entries.map(([name, count]) => ({ name, count })),
        __state: [{ name: "ACTIVE", count: entries.reduce((sum, [, count]) => sum + count, 0) }],
        "Asset.owner": [],
    };
}

function setup() {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), SearchState] });
    return { store: TestBed.inject(SearchState), httpMock: TestBed.inject(HttpTestingController) };
}

describe("SearchState (SRH-02..06, SDX-01..07)", () => {
    it("run posts the quick search with sub types and the legacy page shape (SDX-01, SRH-04)", () => {
        const { store, httpMock } = setup();

        store.run("data");

        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({
            query: "data",
            limit: 10,
            offset: 0,
            excludeDeletedEntities: true,
            includeSubTypes: true,
        });
        request.flush(page(0, 3, 3));
        expect(store.entries()).toHaveLength(3);
        expect(store.approximateCount()).toBe(3);
        expect(store.queryText()).toBe("data");
    });

    it("one answer feeds the list and the facet signal (SDX-02)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(QUICK_SEARCH).flush(
            page(
                0,
                3,
                116,
                typeMetrics([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );

        // Entities and count read from `searchResults` (SDX-01); no second request exists (SDX-02).
        expect(store.entries()).toHaveLength(3);
        expect(store.approximateCount()).toBe(116);

        const facets = store.facets();
        expect(facets.map((facet) => facet.key)).toEqual(["__typeName", "__state"]);
        // The empty Asset.owner facet is dropped (SDX-03, the legacy FilterService rule).
        expect(facets.find((facet) => facet.key === "Asset.owner")).toBeUndefined();

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

    it("pages accumulate at the offset and stop at the count (SRH-04)", () => {
        const { store, httpMock } = setup();

        store.run("gene");
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 10, 25));
        expect(store.entries()).toHaveLength(10);
        expect(store.allLoaded()).toBe(false);

        store.nextPage();
        const second = httpMock.expectOne(QUICK_SEARCH);
        expect(second.request.body).toMatchObject({ offset: 10, limit: 10 });
        second.flush(page(10, 10, 25));

        store.nextPage();
        httpMock.expectOne(QUICK_SEARCH).flush(page(20, 5, 25));
        expect(store.entries()).toHaveLength(25);
        expect(store.allLoaded()).toBe(true);

        // The end of the list: no further request (SRH-04's stop rule).
        store.nextPage();
        httpMock.expectNone(QUICK_SEARCH);
    });

    it("a query change resets the list to page one (SRH-04)", () => {
        const { store, httpMock } = setup();

        store.run("one");
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 10, 25));

        store.run("two");
        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.body).toMatchObject({ query: "two", offset: 0 });
        request.flush(page(0, 1, 1));
        expect(store.entries()).toHaveLength(1);
    });

    it("ticking a type re-runs the search with the selection and checks the row (SDX-04)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(QUICK_SEARCH).flush(
            page(
                0,
                3,
                116,
                typeMetrics([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );

        store.toggleType("m4i_data_domain", true);
        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.body).toMatchObject({
            query: "data",
            typeName: "m4i_data_domain",
            offset: 0,
            includeSubTypes: true,
        });
        expect(store.typeSelection()).toEqual(["m4i_data_domain"]);
        request.flush(page(0, 1, 9, typeMetrics([["m4i_data_domain", 9]])));
        expect(store.entries()).toHaveLength(1);

        const type = store.facets()[0];
        expect(type.items.find((item) => item.value === "m4i_data_domain")?.checked).toBe(true);
        expect(type.items.find((item) => item.value === "m4i_data_attribute")?.checked).toBe(false);
    });

    it("the seen type values stay visible with their last counts while the counts narrow (SDX-07, DD-426)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(QUICK_SEARCH).flush(
            page(
                0,
                3,
                116,
                typeMetrics([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );

        store.toggleType("m4i_data_domain", true);
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 1, 9, typeMetrics([["m4i_data_domain", 9]])));

        // The narrowed answer carries its one type first; the value it no
        // longer carries keeps its last count and stays listed, unchecked.
        const rows = store.facets()[0].items;
        expect(rows.map((row) => [row.value, row.count, row.checked ?? false])).toEqual([
            ["m4i_data_domain", 9, true],
            ["m4i_data_attribute", 75, false],
        ]);

        // Unticking restores the broad answer and its counts (DD-426).
        store.toggleType("m4i_data_domain", false);
        const broad = httpMock.expectOne(QUICK_SEARCH);
        expect(broad.request.body).not.toHaveProperty("typeName");
        broad.flush(
            page(
                0,
                3,
                116,
                typeMetrics([
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
        httpMock.expectOne(QUICK_SEARCH).flush(
            page(
                0,
                3,
                116,
                typeMetrics([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );
        store.toggleType("m4i_data_domain", true);
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 1, 9, typeMetrics([["m4i_data_domain", 9]])));

        store.run("other");
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 0, 0));
        // The seen rows are gone with the query; the next answer's facets stand alone.
        expect(store.facets()).toEqual([]);
    });

    it("a hero submit clears the selection and a URL change keeps it (SDX-06, DD-425)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(QUICK_SEARCH).flush(
            page(
                0,
                3,
                116,
                typeMetrics([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );
        store.toggleType("m4i_data_domain", true);
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 1, 9, typeMetrics([["m4i_data_domain", 9]])));

        // The resolver twin of the SAME text re-runs nothing and clears nothing.
        store.applyUrl("data");
        httpMock.expectNone(QUICK_SEARCH);
        expect(store.typeSelection()).toEqual(["m4i_data_domain"]);

        // A different URL text (back/forward, a pasted link): the store
        // follows, the selection survives — the legacy resolver set the
        // store's query and never touched its filters (SDX-06).
        store.applyUrl("other");
        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.body).toMatchObject({ query: "other", offset: 0 });
        expect(store.typeSelection()).toEqual(["m4i_data_domain"]);
        request.flush(page(0, 0, 0));

        // A hero submit clears it (the legacy onQuerySubmitted's reset).
        store.toggleType("m4i_field", true);
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 0, 0));
        expect(store.typeSelection()).toEqual(["m4i_data_domain", "m4i_field"]);
        store.run("fresh");
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 0, 0));
        expect(store.typeSelection()).toEqual([]);
    });

    it("a multi-select selection posts the comma-joined typeName (SDX-01, SRC-03)", () => {
        const { store, httpMock } = setup();

        store.run("data");
        httpMock.expectOne(QUICK_SEARCH).flush(
            page(
                0,
                3,
                116,
                typeMetrics([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );

        store.toggleType("m4i_data_domain", true);
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 1, 9, typeMetrics([["m4i_data_domain", 9]])));
        store.toggleType("m4i_data_attribute", true);
        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.body).toMatchObject({ typeName: "m4i_data_domain,m4i_data_attribute" });
        request.flush(
            page(
                0,
                2,
                84,
                typeMetrics([
                    ["m4i_data_attribute", 75],
                    ["m4i_data_domain", 9],
                ]),
            ),
        );
    });

    it("applyUrl follows the URL and re-runs nothing on the same text (SRH-02)", () => {
        const { store, httpMock } = setup();

        store.explore("AtlasGlossary");
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 1, 1));

        // The results screen's effect fires on arrival with the URL's
        // (absent) query — the store's "" matches, so the explore survives.
        store.applyUrl(null);
        store.applyUrl("");
        httpMock.expectNone(QUICK_SEARCH);
        expect(store.typeSelection()).toEqual(["AtlasGlossary"]);

        // A hero submit of "term" (run) followed by the URL effect (applyUrl
        // of the same text): one request, not two (DD-219's no-op guard).
        store.run("term");
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 1, 1));
        store.applyUrl("term");
        httpMock.expectNone(QUICK_SEARCH);

        // A different text (back/forward, a pasted link): the store follows.
        store.applyUrl("other");
        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.body).toMatchObject({ query: "other", offset: 0 });
        request.flush(page(0, 1, 1));
        expect(store.queryText()).toBe("other");
    });

    it("explore searches the empty query with the card's type in the selection (SRH-08, DV-84)", () => {
        const { store, httpMock } = setup();

        store.explore("Infrastructure");

        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.body).toEqual({
            query: "",
            typeName: "Infrastructure",
            limit: 10,
            offset: 0,
            excludeDeletedEntities: true,
            includeSubTypes: true,
        });
        request.flush(page(0, 2, 2));
        expect(store.entries()).toHaveLength(2);
    });

    it("the empty query with no selection lists every entity (SRH-02, SDX-01, DD-221)", () => {
        const { store, httpMock } = setup();

        store.run(null);

        // The server rejects an empty query without a type (QSR-01); the
        // every-entity marker is the answer shape (SRC-03) — the demo
        // resolver's documented default, "we can still see results".
        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.body).toEqual({
            typeName: "_ALL_ENTITY_TYPES",
            query: "",
            limit: 10,
            offset: 0,
            excludeDeletedEntities: true,
            includeSubTypes: true,
        });
        request.flush(page(0, 3, 42));
        expect(store.entries()).toHaveLength(3);
        expect(store.approximateCount()).toBe(42);
    });

    it("a first arrival at a query-less URL fires the list-everything search (SRH-02, DD-221)", () => {
        const { store, httpMock } = setup();

        // Arriving at /search/results directly (a bookmark, a reload): the
        // legacy resolver ran on every arrival, its query='' default
        // included — the store's "" is not yet "already run".
        store.applyUrl(null);

        const request = httpMock.expectOne(QUICK_SEARCH);
        expect(request.request.body).toMatchObject({ typeName: "_ALL_ENTITY_TYPES", query: "" });
        request.flush(page(0, 2, 2));
        expect(store.entries()).toHaveLength(2);
    });

    it("a zero answer renders as no results (SRH-06)", () => {
        const { store, httpMock } = setup();

        store.run("nothing");
        httpMock.expectOne(QUICK_SEARCH).flush(page(0, 0, 0));

        expect(store.noResults()).toBe(true);
        expect(store.hasResults()).toBe(false);
    });

    it("a failing page lands in the alerts store and ends the load (SDX-01, DD-214)", () => {
        const { store, httpMock } = setup();
        const alerts = TestBed.inject(AlertsService);
        const add = vi.spyOn(alerts, "add");

        store.run("boom");
        httpMock
            .expectOne(QUICK_SEARCH)
            .flush({ errorCode: "ATLAS-400-00-047", errorMessage: "nope" }, { status: 400, statusText: "Bad Request" });

        expect(store.loading()).toBe(false);
        expect(add).toHaveBeenCalledWith(expect.objectContaining({ severity: "error", source: "search" }));
    });
});
