import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { provideApiBaseUrl } from "./api-config";
import { AtlasEntitiesService } from "./atlas-entities.service";
import type { AtlasEntityWithExtInfo } from "./atlas-entity";

/**
 * The entity-by-GUID read, asserted on the wire (DET-03, DD-187): the
 * request (method, path, encoding, the APC-01 base url) and the DTO mapping.
 * The endpoint is server 2.3's surface — today it answers 404, so every
 * scenario here is an `expectOne` plus a synthetic `flush`: honest against
 * the wire format, not a claim that the server speaks it yet.
 */
describe("AtlasEntitiesService (DET-03)", () => {
    let service: AtlasEntitiesService;
    let httpMock: HttpTestingController;

    const read: AtlasEntityWithExtInfo = {
        entity: {
            guid: "7a1b",
            typeName: "sales_table",
            status: "ACTIVE",
            attributes: { name: "orders", qualifiedName: "s1.table.orders" },
            classificationNames: ["PII"],
            relationshipAttributes: { meanings: { termNames: ["G1"], meaning: [{ guid: "t1", displayText: "G1" }] } },
        },
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), provideApiBaseUrl("/api")],
        });
        service = TestBed.inject(AtlasEntitiesService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("getEntityByGuid calls GET /api/atlas/v2/entity/guid/{guid} (DET-03, APC-01)", () =>
        new Promise<void>((done, fail) => {
            service.getEntityByGuid("7a1b").subscribe({
                next: (result) => {
                    // The DTO maps through untouched — the client is the wire shape.
                    expect(result).toEqual(read);
                    expect(result.entity?.attributes?.["qualifiedName"]).toBe("s1.table.orders");
                    expect(result.entity?.relationshipAttributes?.meanings?.meaning?.[0]?.displayText).toBe("G1");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b");
            expect(req.request.method).toBe("GET");
            expect(req.request.params.keys()).toEqual([]);
            req.flush(read);
        }));

    it("URL-encodes the guid (DET-03, the typedefs lookups' idiom)", () => {
        service.getEntityByGuid("a b/c?d").subscribe();

        // Angular encodes the remaining reserved characters of the path.
        const req = httpMock.expectOne((r) => r.url.includes("entity/guid/"));
        expect(req.request.url).toBe("/api/atlas/v2/entity/guid/a%20b%2Fc%3Fd");
        req.flush({});
    });

    it("composes from the injected API_BASE_URL, not a hard-coded host (APC-01, DD-188)", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [
                provideHttpClient(),
                provideHttpClientTesting(),
                provideApiBaseUrl("https://catalogue.example/gw"),
            ],
        });
        TestBed.inject(AtlasEntitiesService).getEntityByGuid("g1").subscribe();

        TestBed.inject(HttpTestingController)
            .expectOne("https://catalogue.example/gw/atlas/v2/entity/guid/g1")
            .flush({});
    });

    it("surfaces the Atlas error body on a 404, honest against today's server (APC-04, DD-187)", () => {
        let status = 0;
        service.getEntityByGuid("missing").subscribe({
            error: (error) => {
                status = error.status;
            },
        });

        // Today's server (admin, types) has no entity endpoint: 404, and the
        // client keeps the status — it does not swallow it.
        httpMock
            .expectOne("/api/atlas/v2/entity/guid/missing")
            .flush(
                { errorCode: "ATLAS-404-00-002", errorMessage: "entity not found" },
                { status: 404, statusText: "Not Found" },
            );
        expect(status).toBe(404);
    });
});
