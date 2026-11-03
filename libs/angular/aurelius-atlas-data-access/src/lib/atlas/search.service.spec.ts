import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import type { AtlasUserSavedSearch } from "./atlas-profile";
import {
    AtlasQuickSearchResult,
    AtlasSearchResult,
    AtlasSuggestionsResult,
    QuickSearchParameters,
    SearchParameters,
} from "./atlas-search";
import { SearchService } from "./search.service";

describe("SearchService", () => {
    let service: SearchService;
    let httpMock: HttpTestingController;

    const searchResult: AtlasSearchResult = {
        queryType: "BASIC",
        entities: [{ guid: "g-1", typeName: "hive_table", displayText: "t" }],
        approximateCount: 1,
    };
    const quickResult: AtlasQuickSearchResult = {
        searchResults: { queryType: "BASIC", entities: [], approximateCount: 2 },
        aggregationMetrics: { __typeName: [{ name: "hive_table", count: 2 }] },
    };
    const suggestions: AtlasSuggestionsResult = { prefixString: "pi", suggestions: ["PII"] };
    const savedSearch: AtlasUserSavedSearch = {
        guid: "g-9",
        ownerName: "aurelius-writer",
        name: "my_tables",
        searchType: "BASIC",
        searchParameters: { query: "table" },
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        service = TestBed.inject(SearchService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("searchWithParameters posts the parameters as body (APC-11, SRC-02)", () =>
        new Promise<void>((done, fail) => {
            const parameters: SearchParameters = { typeName: "Asset", limit: 5, excludeDeletedEntities: true };

            service.searchWithParameters(parameters).subscribe({
                next: (result) => {
                    expect(result).toEqual(searchResult);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/search/basic");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(parameters);
            req.flush(searchResult);
        }));

    it("searchUsingBasic sends the given parameters and drops the Java defaults (APC-11, SRC-11)", () => {
        service
            .searchUsingBasic({
                query: "table",
                typeName: "Asset",
                excludeDeletedEntities: true,
                limit: 20,
                sortOrder: "DESCENDING",
            })
            .subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/basic" &&
                r.params.get("query") === "table" &&
                r.params.get("typeName") === "Asset" &&
                r.params.get("excludeDeletedEntities") === "true" &&
                r.params.get("limit") === "20" &&
                r.params.get("sortOrder") === "DESCENDING" &&
                r.params.keys().length === 5,
        );
        expect(req.request.method).toBe("GET");
        req.flush(searchResult);
    });

    it("searchUsingBasic with no parameters sends none (APC-11)", () => {
        service.searchUsingBasic().subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/search/basic");
        expect(req.request.params.keys()).toEqual([]);
        req.flush(searchResult);
    });

    it("searchUsingAttribute sends the prefix criteria (APC-11, SRC-11)", () => {
        service
            .searchUsingAttribute({
                typeName: "hive_table",
                attrName: "qualifiedName",
                attrValuePrefix: "staging.",
                limit: 5,
            })
            .subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/attribute" &&
                r.params.get("typeName") === "hive_table" &&
                r.params.get("attrName") === "qualifiedName" &&
                r.params.get("attrValuePrefix") === "staging." &&
                r.params.get("limit") === "5",
        );
        expect(req.request.method).toBe("GET");
        req.flush(searchResult);
    });

    it("searchUsingFullText sends the query and page, answered with scores (APC-11, FTX-05)", () => {
        const fullText: AtlasSearchResult = {
            queryType: "FULL_TEXT",
            fullTextResult: [{ entity: { guid: "g" }, score: 9.5 }],
        };

        service.searchUsingFullText({ query: "sales", excludeDeletedEntities: true, limit: 7 }).subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/fulltext" &&
                r.params.get("query") === "sales" &&
                r.params.get("excludeDeletedEntities") === "true" &&
                r.params.get("limit") === "7",
        );
        expect(req.request.method).toBe("GET");
        req.flush(fullText);
    });

    it("quickSearch posts the parameters and answers with the facets (APC-11, QSR-01, QSR-03)", () =>
        new Promise<void>((done, fail) => {
            const parameters: QuickSearchParameters = { query: "tab", typeName: "Asset" };

            service.quickSearch(parameters).subscribe({
                next: (result) => {
                    expect(result.searchResults?.approximateCount).toBe(2);
                    expect(result.aggregationMetrics?.["__typeName"]).toEqual([{ name: "hive_table", count: 2 }]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/search/quick");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(parameters);
            req.flush(quickResult);
        }));

    it("quickSearchUsingQuery sends the query parameters (APC-11, QSR-01)", () => {
        service.quickSearchUsingQuery({ query: "tab", typeName: "Asset", offset: 10 }).subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/quick" &&
                r.params.get("query") === "tab" &&
                r.params.get("typeName") === "Asset" &&
                r.params.get("offset") === "10" &&
                r.params.keys().length === 3,
        );
        expect(req.request.method).toBe("GET");
        req.flush(quickResult);
    });

    it("getSuggestions sends the prefix and the optional field (APC-11, SUG-01, SUG-02)", () => {
        service.getSuggestions("pi", "__typeName").subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/suggestions" &&
                r.params.get("prefixString") === "pi" &&
                r.params.get("fieldName") === "__typeName",
        );
        expect(req.request.method).toBe("GET");
        req.flush(suggestions);
    });

    it("getSuggestions without a field sends only the prefix (APC-11, SUG-02)", () => {
        service.getSuggestions("pi").subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/suggestions" &&
                r.params.get("prefixString") === "pi" &&
                r.params.keys().length === 1,
        );
        req.flush(suggestions);
    });

    it("searchUsingDsl sends the given parameters and drops the Java defaults (ACS-01, DSE-01)", () => {
        service.searchUsingDsl({ query: "from t", typeName: "Asset", classification: "PII", limit: 5 }).subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/dsl" &&
                r.params.get("query") === "from t" &&
                r.params.get("typeName") === "Asset" &&
                r.params.get("classification") === "PII" &&
                r.params.get("limit") === "5" &&
                r.params.keys().length === 4,
        );
        expect(req.request.method).toBe("GET");
        req.flush({ ...searchResult, queryType: "DSL" });
    });

    it("searchUsingDsl with no parameters sends none; the server's length error surfaces typed (ACS-01, APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.searchUsingDsl().subscribe({
                error: (error) => {
                    expect(error.status).toBe(400);
                    expect(error.error.errorCode).toBe("ATLAS-400-00-008");
                    done();
                },
                next: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/search/dsl");
            expect(req.request.params.keys()).toEqual([]);
            req.flush(
                { errorCode: "ATLAS-400-00-008", errorMessage: "The query length is more than 4096." },
                { status: 400, statusText: "Bad Request" },
            );
        }));

    it("addSavedSearch posts the saved search as body (ACS-02, SVS-02)", () =>
        new Promise<void>((done, fail) => {
            service.addSavedSearch(savedSearch).subscribe({
                next: (saved) => {
                    expect(saved).toEqual(savedSearch);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/search/saved");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(savedSearch);
            req.flush(savedSearch);
        }));

    it("updateSavedSearch puts the saved search as body (ACS-02, SVS-03)", () => {
        service.updateSavedSearch(savedSearch).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/search/saved");
        expect(req.request.method).toBe("PUT");
        expect(req.request.body).toEqual(savedSearch);
        req.flush(savedSearch);
    });

    it("getSavedSearches answers the list with no parameters (ACS-03, SVS-04)", () =>
        new Promise<void>((done, fail) => {
            service.getSavedSearches().subscribe({
                next: (saved) => {
                    expect(saved).toEqual([savedSearch]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/search/saved");
            expect(req.request.method).toBe("GET");
            expect(req.request.params.keys()).toEqual([]);
            req.flush([savedSearch]);
        }));

    it("getSavedSearches sends the user parameter (ACS-03, SVS-04)", () => {
        service.getSavedSearches("aurelius-reader").subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/saved" &&
                r.params.get("user") === "aurelius-reader" &&
                r.params.keys().length === 1,
        );
        req.flush([]);
    });

    it("getSavedSearches keeps the 204 of no profile as null, not [] (ACS-03, DD-314)", () =>
        new Promise<void>((done, fail) => {
            service.getSavedSearches().subscribe({
                next: (saved) => {
                    expect(saved).toBeNull();
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/search/saved");
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it("getSavedSearch reads by encoded name with the optional user (ACS-04, SVS-04)", () => {
        service.getSavedSearch("my tables", "aurelius-reader").subscribe();

        const req = httpMock.expectOne(
            (r) => r.url === "/api/atlas/v2/search/saved/my%20tables" && r.params.get("user") === "aurelius-reader",
        );
        expect(req.request.method).toBe("GET");
        req.flush(savedSearch);
    });

    it("deleteSavedSearch DELETEs by guid and answers 204 (ACS-04, SVS-05)", () =>
        new Promise<void>((done, fail) => {
            service.deleteSavedSearch("g-9").subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/search/saved/g-9");
            expect(req.request.method).toBe("DELETE");
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it("executeSavedSearchByName runs the named search, user optional (ACS-05, SVS-06)", () => {
        service.executeSavedSearchByName("my_tables", "aurelius-reader").subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/search/saved/execute/my_tables" && r.params.get("user") === "aurelius-reader",
        );
        expect(req.request.method).toBe("GET");
        req.flush(searchResult);
    });

    it("executeSavedSearchByGuid runs the search of the guid, without a user (ACS-05, SVS-06)", () => {
        service.executeSavedSearchByGuid("g-9").subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/search/saved/execute/guid/g-9");
        expect(req.request.method).toBe("GET");
        expect(req.request.params.keys()).toEqual([]);
        req.flush(searchResult);
    });

    it("a failed call carries the typed Atlas error body (APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.searchWithParameters({}).subscribe({
                error: (error) => {
                    expect(error.status).toBe(400);
                    expect(error.error.errorCode).toBe("ATLAS-400-00-047");
                    done();
                },
                next: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/search/basic");
            req.flush(
                { errorCode: "ATLAS-400-00-047", errorMessage: "No search parameter was found." },
                { status: 400, statusText: "Bad Request" },
            );
        }));
});
