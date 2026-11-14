import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { firstValueFrom } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { ViewSearchAnswer } from "../atlas/atlas-view";
import { ViewSearchService } from "./view-search.service";

describe("ViewSearchService", () => {
    let service: ViewSearchService;
    let httpMock: HttpTestingController;

    const answer: ViewSearchAnswer = {
        cards: [
            {
                guid: "g-1",
                typeName: "m4i_data_entity",
                displayText: "Customer",
                status: "ACTIVE",
                stale: false,
            },
        ],
        facets: { typeName: [{ value: "m4i_data_entity", count: 1 }] },
        total: 1,
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: "/api" }],
        });
        service = TestBed.inject(ViewSearchService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("search posts the door's body to the search door (VSR-03)", async () => {
        const answered = firstValueFrom(
            service.search({
                query: "customer",
                mode: "keyword",
                filters: { any: [{ typeName: "Asset" }, { superTypeNames: "Asset" }] },
                facets: ["typeName", "status", "owner", "serviceType"],
                limit: 10,
                offset: 0,
            }),
        );

        const request = httpMock.expectOne("/api/aurelius/v1/search");
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({
            query: "customer",
            mode: "keyword",
            filters: { any: [{ typeName: "Asset" }, { superTypeNames: "Asset" }] },
            facets: ["typeName", "status", "owner", "serviceType"],
            limit: 10,
            offset: 0,
        });
        request.flush(answer);
        expect(await answered).toEqual(answer);
    });

    it("search answers the door's cards, facets and total (VSR-03)", async () => {
        const answered = firstValueFrom(service.search({ mode: "semantic", query: "orders" }));

        const request = httpMock.expectOne("/api/aurelius/v1/search");
        request.flush(answer);

        const held = await answered;
        expect(held.total).toBe(1);
        expect(held.cards[0].displayText).toBe("Customer");
        expect(held.facets["typeName"]).toEqual([{ value: "m4i_data_entity", count: 1 }]);
    });
});
