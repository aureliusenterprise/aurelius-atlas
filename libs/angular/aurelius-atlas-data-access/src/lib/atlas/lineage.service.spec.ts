import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { API_BASE_URL, provideApiBaseUrl } from "../api-config";
import { atlasErrorFrom } from "./atlas-error";
import type { AtlasLineageInfo } from "./atlas-lineage";
import { LineageService } from "./lineage.service";

describe("LineageService", () => {
    let service: LineageService;
    let httpMock: HttpTestingController;

    const lineage: AtlasLineageInfo = {
        baseEntityGuid: "g-1",
        lineageDirection: "BOTH",
        lineageDepth: 3,
        guidEntityMap: { "g-1": { guid: "g-1", typeName: "table", displayText: "orders.tb1" } },
        relations: [{ fromEntityId: "g-1", toEntityId: "g-2", relationshipId: "10" }],
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        service = TestBed.inject(LineageService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("getLineage always sends the depth and direction defaults (ALN-01)", () =>
        new Promise<void>((done, fail) => {
            service.getLineage("g-1").subscribe({
                next: (info) => {
                    expect(info).toEqual(lineage);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/lineage/g-1?depth=3&direction=BOTH");
            expect(req.request.method).toBe("GET");
            req.flush(lineage);
        }));

    it("getLineage sends the caller's depth and direction (ALN-01)", () =>
        new Promise<void>((done, fail) => {
            service.getLineage("g-1", 2, "INPUT").subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/lineage/g-1?depth=2&direction=INPUT");
            req.flush(lineage);
        }));

    it("getLineage percent-encodes the guid path segment (ALN-01, APC-01)", () =>
        new Promise<void>((done, fail) => {
            service.getLineage("g 1/x").subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne(
                (r) =>
                    r.url === "/api/atlas/v2/lineage/g%201%2Fx" &&
                    r.params.get("depth") === "3" &&
                    r.params.get("direction") === "BOTH",
            );
            req.flush(lineage);
        }));

    it("getLineageOnDemand sends the constraints map as the body (ALN-02)", () =>
        new Promise<void>((done, fail) => {
            const constraints = {
                "g-2": { direction: "INPUT" as const, inputRelationsLimit: 10, outputRelationsLimit: 0, depth: 2 },
            };

            service.getLineageOnDemand("g-1", constraints).subscribe({
                next: (info) => {
                    expect(info.relations).toEqual(lineage.relations);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/lineage/g-1");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(constraints);
            req.flush(lineage);
        }));

    it("getLineageOnDemand with no or empty constraints sends no body (ALN-02)", () =>
        new Promise<void>((done, fail) => {
            service.getLineageOnDemand("g-1").subscribe({ next: () => done(), error: fail });
            const first = httpMock.expectOne("/api/atlas/v2/lineage/g-1");
            expect(first.request.body).toBeNull();
            first.flush(lineage);

            service.getLineageOnDemand("g-1", {}).subscribe({ next: () => done(), error: fail });
            const second = httpMock.expectOne("/api/atlas/v2/lineage/g-1");
            expect(second.request.body).toBeNull();
            second.flush(lineage);
        }));

    it("getLineageOnDemand surfaces the not-enabled error (ALN-02, APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.getLineageOnDemand("g-1").subscribe({
                next: fail,
                error: (error) => {
                    expect(error.status).toBe(400);
                    expect(atlasErrorFrom(error)?.errorCode).toBe("ATLAS-400-00-100");
                    done();
                },
            });

            const req = httpMock.expectOne("/api/atlas/v2/lineage/g-1");
            req.flush(
                { errorCode: "ATLAS-400-00-100", errorMessage: "Lineage on demand config: x is not enabled" },
                { status: 400, statusText: "Bad Request" },
            );
        }));

    it("getLineageByUniqueAttributes sends attr: parameters, depth, direction (ALN-03)", () =>
        new Promise<void>((done, fail) => {
            service.getLineageByUniqueAttributes("table", { qualifiedName: "orders.tb1", name: "tb1" }).subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne(
                (request) =>
                    request.url === "/api/atlas/v2/lineage/uniqueAttribute/type/table" &&
                    request.params.get("depth") === "3" &&
                    request.params.get("direction") === "BOTH" &&
                    request.params.get("attr:qualifiedName") === "orders.tb1" &&
                    request.params.get("attr:name") === "tb1",
            );
            expect(req.request.method).toBe("GET");
            req.flush(lineage);
        }));

    it("getLineageByUniqueAttributes percent-encodes the type name (ALN-03, APC-01)", () =>
        new Promise<void>((done, fail) => {
            service.getLineageByUniqueAttributes("sa fi", { qualifiedName: "x" }).subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne(
                (r) =>
                    r.url === "/api/atlas/v2/lineage/uniqueAttribute/type/sa%20fi" &&
                    r.params.get("attr:qualifiedName") === "x",
            );
            req.flush(lineage);
        }));

    it("a 404 of a guid with no lineage passes through as the Atlas error (ALN-04, LM-05)", () =>
        new Promise<void>((done, fail) => {
            service.getLineage("g-nope").subscribe({
                next: fail,
                error: (error) => {
                    expect(error.status).toBe(404);
                    expect(atlasErrorFrom(error)).toEqual({
                        errorCode: "ATLAS-404-00-001",
                        errorMessage: "no lineage for g-nope",
                    });
                    done();
                },
            });

            const req = httpMock.expectOne("/api/atlas/v2/lineage/g-nope?depth=3&direction=BOTH");
            req.flush(
                { errorCode: "ATLAS-404-00-001", errorMessage: "no lineage for g-nope" },
                { status: 404, statusText: "Not Found" },
            );
        }));

    it("composes every URL from API_BASE_URL (APC-01)", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), provideApiBaseUrl("https://atlas:21000/api")],
        });
        const custom = TestBed.inject(LineageService);
        const mock = TestBed.inject(HttpTestingController);

        custom.getLineage("g-1").subscribe();

        expect(
            mock.expectOne("https://atlas:21000/api/atlas/v2/lineage/g-1?depth=3&direction=BOTH").request.method,
        ).toBe("GET");
        mock.verify();
        expect(TestBed.inject(API_BASE_URL)).toBe("https://atlas:21000/api");
    });
});
