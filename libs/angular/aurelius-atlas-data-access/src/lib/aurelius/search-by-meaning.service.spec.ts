import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { firstValueFrom } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { AtlasQuickSearchResult } from "../atlas/atlas-search";
import { SearchByMeaningService } from "./search-by-meaning.service";

describe("SearchByMeaningService", () => {
    let service: SearchByMeaningService;
    let httpMock: HttpTestingController;

    const answer: AtlasQuickSearchResult = {
        searchResults: {
            queryType: "BASIC",
            entities: [{ guid: "g-1", typeName: "m4i_data_entity" }],
            approximateCount: 1,
        },
        aggregationMetrics: { __typeName: [{ name: "m4i_data_entity", count: 1 }] },
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: "/api" }],
        });
        service = TestBed.inject(SearchByMeaningService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("search posts quick search's parameters and the mode to the Aurelius endpoint (SBW-01)", async () => {
        const answered = firstValueFrom(
            service.search({ query: "customer address", typeName: "m4i_data_entity", limit: 10, mode: "hybrid" }),
        );

        const request = httpMock.expectOne("/api/aurelius/v1/search/semantic");
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({
            query: "customer address",
            typeName: "m4i_data_entity",
            limit: 10,
            mode: "hybrid",
        });
        request.flush(answer);
        expect(await answered).toEqual(answer);
    });

    it("similar gets one entity's neighbours with the page as query parameters (SBW-01)", async () => {
        const answered = firstValueFrom(
            service.similar("g/1", { limit: 6, excludeDeletedEntities: true, typeName: null }),
        );

        const request = httpMock.expectOne(
            (candidate) => candidate.url === "/api/aurelius/v1/entity/guid/g%2F1/similar",
        );
        expect(request.request.method).toBe("GET");
        expect(request.request.params.get("limit")).toBe("6");
        expect(request.request.params.get("excludeDeletedEntities")).toBe("true");
        expect(request.request.params.has("typeName")).toBe(false);
        request.flush(answer);
        expect(await answered).toEqual(answer);
    });

    it("similar without a query sends no parameters (SBW-01)", async () => {
        const answered = firstValueFrom(service.similar("g-1"));

        const request = httpMock.expectOne("/api/aurelius/v1/entity/guid/g-1/similar");
        expect(request.request.params.keys()).toEqual([]);
        request.flush(answer);
        expect(await answered).toEqual(answer);
    });
});
