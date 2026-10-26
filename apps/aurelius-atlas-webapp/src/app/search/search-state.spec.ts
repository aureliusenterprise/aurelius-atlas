import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { AtlasEntityHeader, AtlasSearchResult } from "aurelius-atlas-data-access";
import { vi } from "vitest";

import { AlertsService } from "../alerts/alerts.service";
import { SearchState } from "./search-state";

/** The endpoint the store posts to (SRH-03, APC-11). */
const BASIC_SEARCH = "/api/atlas/v2/search/basic";

/**
 * Build a page of hits, named `entity-<offset>…` so accumulation is visible.
 */
function page(offset: number, count: number, approximateCount: number): AtlasSearchResult {
    return {
        entities: Array.from({ length: count }, (_, i) => ({
            guid: `g${offset + i}`,
            typeName: "DataSet",
            displayText: `entity-${offset + i}`,
        })) as AtlasEntityHeader[],
        approximateCount,
        queryType: "BASIC",
    };
}

function setup() {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), SearchState] });
    return { store: TestBed.inject(SearchState), httpMock: TestBed.inject(HttpTestingController) };
}

describe("SearchState (SRH-02..06)", () => {
    it("run posts the basic search with the legacy page shape (SRH-03, SRH-04)", () => {
        const { store, httpMock } = setup();

        store.run("genomic");

        const request = httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({
            query: "genomic",
            limit: 10,
            offset: 0,
            excludeDeletedEntities: true,
        });
        request.flush(page(0, 3, 3));
        expect(store.entries()).toHaveLength(3);
        expect(store.approximateCount()).toBe(3);
        expect(store.queryText()).toBe("genomic");
    });

    it("pages accumulate at the offset and stop at the count (SRH-04)", () => {
        const { store, httpMock } = setup();

        store.run("gene");
        httpMock.expectOne(BASIC_SEARCH).flush(page(0, 10, 25));
        expect(store.entries()).toHaveLength(10);
        expect(store.allLoaded()).toBe(false);

        store.nextPage();
        const second = httpMock.expectOne(BASIC_SEARCH);
        expect(second.request.body).toMatchObject({ offset: 10, limit: 10 });
        second.flush(page(10, 10, 25));

        store.nextPage();
        httpMock.expectOne(BASIC_SEARCH).flush(page(20, 5, 25));
        expect(store.entries()).toHaveLength(25);
        expect(store.allLoaded()).toBe(true);

        // The end of the list: no further request (SRH-04's stop rule).
        store.nextPage();
        httpMock.expectNone(BASIC_SEARCH);
    });

    it("a query change resets the list to page one (SRH-04)", () => {
        const { store, httpMock } = setup();

        store.run("one");
        httpMock.expectOne(BASIC_SEARCH).flush(page(0, 10, 25));

        store.run("two");
        const request = httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.body).toMatchObject({ query: "two", offset: 0 });
        request.flush(page(0, 1, 1));
        expect(store.entries()).toHaveLength(1);
    });

    it("applyUrl follows the URL, re-runs nothing on the same text, and keeps the session filter (SRH-02)", () => {
        const { store, httpMock } = setup();

        store.explore("AtlasGlossary");
        httpMock.expectOne(BASIC_SEARCH).flush(page(0, 1, 1));

        // The results screen's effect fires on arrival with the URL's
        // (absent) query — the store's "" matches, so the explore survives.
        store.applyUrl(null);
        store.applyUrl("");
        httpMock.expectNone(BASIC_SEARCH);
        expect(store.typeFilter()).toBe("AtlasGlossary");

        // A hero submit of "term" (run) followed by the URL effect (applyUrl
        // of the same text): one request, not two (DD-219's no-op guard).
        store.run("term");
        httpMock.expectOne(BASIC_SEARCH).flush(page(0, 1, 1));
        store.applyUrl("term");
        httpMock.expectNone(BASIC_SEARCH);

        // A different text (back/forward, a pasted link): the store follows.
        store.applyUrl("other");
        const request = httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.body).toMatchObject({ query: "other", offset: 0 });
        request.flush(page(0, 1, 1));
        expect(store.queryText()).toBe("other");
    });

    it("explore searches the empty query with the card's type filter (SRH-08, DV-84)", () => {
        const { store, httpMock } = setup();

        store.explore("Infrastructure");

        const request = httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.body).toEqual({
            query: "",
            typeName: "Infrastructure",
            limit: 10,
            offset: 0,
            excludeDeletedEntities: true,
        });
        request.flush(page(0, 2, 2));
        expect(store.entries()).toHaveLength(2);
    });

    it("a run clears the session type filter (SRH-02, the legacy filter reset)", () => {
        const { store, httpMock } = setup();

        store.explore("AtlasGlossary");
        httpMock.expectOne(BASIC_SEARCH).flush(page(0, 1, 1));

        store.run("word");
        const request = httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.body).not.toHaveProperty("typeName");
        request.flush(page(0, 1, 1));
    });

    it("the empty query with no filter lists every entity (SRH-02, SRH-03, DD-221)", () => {
        const { store, httpMock } = setup();

        store.run(null);

        // The server rejects an empty query without a type (SRC-02); the
        // every-entity marker is the answer shape (SRC-03) — the demo
        // resolver's documented default, "we can still see results".
        const request = httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.body).toEqual({
            typeName: "_ALL_ENTITY_TYPES",
            query: "",
            limit: 10,
            offset: 0,
            excludeDeletedEntities: true,
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

        const request = httpMock.expectOne(BASIC_SEARCH);
        expect(request.request.body).toMatchObject({ typeName: "_ALL_ENTITY_TYPES", query: "" });
        request.flush(page(0, 2, 2));
        expect(store.entries()).toHaveLength(2);
    });

    it("a zero answer renders as no results (SRH-06)", () => {
        const { store, httpMock } = setup();

        store.run("nothing");
        httpMock.expectOne(BASIC_SEARCH).flush(page(0, 0, 0));

        expect(store.noResults()).toBe(true);
        expect(store.hasResults()).toBe(false);
    });

    it("a failing page lands in the alerts store and ends the load (SRH-03, DD-214)", () => {
        const { store, httpMock } = setup();
        const alerts = TestBed.inject(AlertsService);
        const add = vi.spyOn(alerts, "add");

        store.run("boom");
        httpMock
            .expectOne(BASIC_SEARCH)
            .flush({ errorCode: "ATLAS-400-00-047", errorMessage: "nope" }, { status: 400, statusText: "Bad Request" });

        expect(store.loading()).toBe(false);
        expect(add).toHaveBeenCalledWith(expect.objectContaining({ severity: "error", source: "search" }));
    });
});
