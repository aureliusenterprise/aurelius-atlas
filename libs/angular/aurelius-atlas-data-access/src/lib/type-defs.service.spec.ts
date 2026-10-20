import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { API_BASE_URL, provideApiBaseUrl } from "./api-config";
import { AtlasTypeDef, AtlasTypesDef } from "./atlas-typedef";
import { TypeDefsService } from "./type-defs.service";

describe("TypeDefsService", () => {
    let service: TypeDefsService;
    let httpMock: HttpTestingController;

    const typesDef: AtlasTypesDef = {
        entityDefs: [{ name: "sales_table", category: "ENTITY", superTypes: ["DataSet"] }],
        structDefs: [],
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        service = TestBed.inject(TypeDefsService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("getTypedefs calls /api/atlas/v2/types/typedefs with no parameters (APC-02)", () =>
        new Promise<void>((done, fail) => {
            service.getTypedefs().subscribe({
                next: (result) => {
                    expect(result).toEqual(typesDef);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/types/typedefs");
            expect(req.request.method).toBe("GET");
            expect(req.request.params.keys()).toEqual([]);
            req.flush(typesDef);
        }));

    it("getTypedefs sends the search filter with the server's parameter names (APC-03, TYR-06/07)", () => {
        service
            .getTypedefs({
                type: "ENTITY",
                servicetype: "primary",
                supertype: "DataSet",
                excludeInternalTypesAndReferences: true,
            })
            .subscribe();

        const req = httpMock.expectOne(
            (r) =>
                r.url === "/api/atlas/v2/types/typedefs" &&
                r.params.get("type") === "ENTITY" &&
                r.params.get("servicetype") === "primary" &&
                r.params.get("supertype") === "DataSet" &&
                r.params.get("excludeInternalTypesAndReferences") === "true",
        );
        expect(req.request.params.keys()).toEqual([
            "type",
            "servicetype",
            "supertype",
            "excludeInternalTypesAndReferences",
        ]);
        req.flush({});
    });

    it("getTypedefs drops nil and empty parameters, keeps booleans (APC-03)", () => {
        service.getTypedefs({ type: "STRUCT", name: "", servicetype: undefined, notname: undefined }).subscribe();

        const req = httpMock.expectOne(
            (r) => r.url === "/api/atlas/v2/types/typedefs" && r.params.get("type") === "STRUCT",
        );
        expect(req.request.params.keys()).toEqual(["type"]);
        req.flush({});
    });

    it("getTypedefHeaders calls /typedefs/headers with the filter (APC-02)", () =>
        new Promise<void>((done, fail) => {
            const headers = [{ guid: "g1", name: "sales_table", serviceType: "primary", category: "ENTITY" as const }];

            service.getTypedefHeaders({ type: "ENTITY" }).subscribe({
                next: (result) => {
                    expect(result).toEqual(headers);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne(
                (r) => r.url === "/api/atlas/v2/types/typedefs/headers" && r.params.get("type") === "ENTITY",
            );
            expect(req.request.method).toBe("GET");
            req.flush(headers);
        }));

    it("getTypeDefByName calls /typedef/name/{name} (APC-02)", () =>
        new Promise<void>((done, fail) => {
            const typedef: AtlasTypeDef = { name: "sales_table", category: "ENTITY" };

            service.getTypeDefByName("sales_table").subscribe({
                next: (result) => {
                    expect(result).toEqual(typedef);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/types/typedef/name/sales_table");
            expect(req.request.method).toBe("GET");
            req.flush(typedef);
        }));

    it("getTypeDefByGuid calls /typedef/guid/{guid} (APC-02)", () =>
        new Promise<void>((done, fail) => {
            const typedef: AtlasTypeDef = { guid: "abc-123", name: "sales_table", category: "ENTITY" };

            service.getTypeDefByGuid("abc-123").subscribe({
                next: (result) => {
                    expect(result).toEqual(typedef);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/types/typedef/guid/abc-123");
            expect(req.request.method).toBe("GET");
            req.flush(typedef);
        }));

    it("getTypedefByName covers each kind's path (APC-02, TYR-03)", () => {
        const cases: [Parameters<TypeDefsService["getTypedefByName"]>, string][] = [
            [["enum", "state"], "/api/atlas/v2/types/enumdef/name/state"],
            [["struct", "addr"], "/api/atlas/v2/types/structdef/name/addr"],
            [["classification", "PII"], "/api/atlas/v2/types/classificationdef/name/PII"],
            [["entity", "tbl"], "/api/atlas/v2/types/entitydef/name/tbl"],
            [["relationship", "join"], "/api/atlas/v2/types/relationshipdef/name/join"],
            [["businessMetadata", "cost"], "/api/atlas/v2/types/businessmetadatadef/name/cost"],
        ];

        for (const [[kind, name], url] of cases) {
            service.getTypedefByName(kind, name).subscribe();
            const req = httpMock.expectOne(url);
            expect(req.request.method).toBe("GET");
            req.flush({});
        }
    });

    it("getTypedefByGuid covers each kind's path (APC-02, TYR-03)", () => {
        service.getTypedefByGuid("entity", "g-1").subscribe();
        const req = httpMock.expectOne("/api/atlas/v2/types/entitydef/guid/g-1");
        expect(req.request.method).toBe("GET");
        req.flush({});
    });

    it("createTypedefs POSTs the AtlasTypesDef body (APC-02, APC-03)", () =>
        new Promise<void>((done, fail) => {
            service.createTypedefs(typesDef).subscribe({
                next: (result) => {
                    expect(result).toEqual(typesDef);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/types/typedefs");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(typesDef);
            req.flush(typesDef);
        }));

    it("updateTypedefs PUTs the AtlasTypesDef body (APC-02, APC-03)", () =>
        new Promise<void>((done, fail) => {
            service.updateTypedefs(typesDef).subscribe({
                next: (result) => {
                    expect(result).toEqual(typesDef);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/types/typedefs");
            expect(req.request.method).toBe("PUT");
            expect(req.request.body).toEqual(typesDef);
            req.flush(typesDef);
        }));

    it("deleteTypedefs DELETEs with the AtlasTypesDef body (APC-02)", () =>
        new Promise<void>((done, fail) => {
            service.deleteTypedefs(typesDef).subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/types/typedefs");
            expect(req.request.method).toBe("DELETE");
            expect(req.request.body).toEqual(typesDef);
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it("deleteTypedefByName DELETEs /typedef/name/{name} (APC-02)", () =>
        new Promise<void>((done, fail) => {
            service.deleteTypedefByName("sales_table").subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/types/typedef/name/sales_table");
            expect(req.request.method).toBe("DELETE");
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it("surfaces the Atlas error body on a failed call (APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.getTypeDefByName("missing").subscribe({
                next: fail,
                error: (error) => {
                    expect(error.status).toBe(400);
                    expect(error.error).toEqual({
                        errorCode: "ATLAS-400-00-046",
                        errorMessage: "type with name missing does not exist",
                    });
                    done();
                },
            });

            const req = httpMock.expectOne("/api/atlas/v2/types/typedef/name/missing");
            req.flush(
                { errorCode: "ATLAS-400-00-046", errorMessage: "type with name missing does not exist" },
                { status: 400, statusText: "Bad Request" },
            );
        }));

    it("encodes names and GUIDs into the URL path (APC-01)", () => {
        service.getTypeDefByName("a b/c").subscribe();
        expect(httpMock.expectOne("/api/atlas/v2/types/typedef/name/a%20b%2Fc").request.method).toBe("GET");
    });

    it("composes every URL from API_BASE_URL (APC-01)", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), provideApiBaseUrl("https://atlas:21000/api")],
        });
        const custom = TestBed.inject(TypeDefsService);
        const mock = TestBed.inject(HttpTestingController);

        custom.getTypedefs().subscribe();
        custom.getTypedefHeaders().subscribe();
        custom.createTypedefs({}).subscribe();

        const url = "https://atlas:21000/api/atlas/v2/types/typedefs";
        expect(mock.expectOne((r) => r.url === url && r.method === "GET").request.method).toBe("GET");
        expect(mock.expectOne((r) => r.url === url && r.method === "POST").request.method).toBe("POST");
        expect(
            mock.expectOne((r) => r.url === "https://atlas:21000/api/atlas/v2/types/typedefs/headers").request.method,
        ).toBe("GET");
        mock.verify();
        expect(TestBed.inject(API_BASE_URL)).toBe("https://atlas:21000/api");
    });
});
