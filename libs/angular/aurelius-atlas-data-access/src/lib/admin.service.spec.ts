import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { AdminService, AtlasSession, AtlasStatus, AtlasVersion } from "./admin.service";
import { API_BASE_URL, provideApiBaseUrl } from "./api-config";
import { atlasErrorFrom } from "./atlas-error";

describe("AdminService", () => {
    let service: AdminService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        service = TestBed.inject(AdminService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("getVersion calls /api/atlas/admin/version (APC-02)", () =>
        new Promise<void>((done, fail) => {
            const response: AtlasVersion = {
                Version: "0.6.1",
                Revision: "abc1234",
                Name: "aurelius-atlas",
                Description: "Apache Atlas 2.4.0 REST API on Elasticsearch",
            };

            service.getVersion().subscribe({
                next: (result) => {
                    expect(result).toEqual(response);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/version");
            expect(req.request.method).toBe("GET");
            req.flush(response);
        }));

    it("getStatus calls /api/atlas/admin/status (APC-02)", () =>
        new Promise<void>((done, fail) => {
            const response: AtlasStatus = { Status: "ACTIVE" };

            service.getStatus().subscribe({
                next: (result) => {
                    expect(result).toEqual(response);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/status");
            expect(req.request.method).toBe("GET");
            req.flush(response);
        }));

    it("getSession calls /api/atlas/admin/session (APC-02)", () =>
        new Promise<void>((done, fail) => {
            const response = {
                "atlas.ui.default.version": "v2",
                "atlas.rest-csrf.enabled": true,
                userName: null,
                groups: [],
                timezones: ["UTC", "Europe/Amsterdam"],
                _csrfToken: "aToken20charsOfL3tt3r",
            } satisfies AtlasSession;

            service.getSession().subscribe({
                next: (result) => {
                    expect(result["atlas.ui.default.version"]).toBe("v2");
                    expect(result.userName).toBeNull();
                    expect(result.timezones).toContain("Europe/Amsterdam");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/session");
            expect(req.request.method).toBe("GET");
            req.flush(response);
        }));

    it("surfaces the Atlas error body on a 4xx (APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.getVersion().subscribe({
                next: fail,
                error: (error) => {
                    expect(error.status).toBe(404);
                    expect(atlasErrorFrom(error)).toEqual({
                        errorCode: "ATLAS-404-00-001",
                        errorMessage: "no such admin endpoint",
                    });
                    done();
                },
            });

            const req = httpMock.expectOne("/api/atlas/admin/version");
            req.flush(
                { errorCode: "ATLAS-404-00-001", errorMessage: "no such admin endpoint" },
                { status: 404, statusText: "Not Found" },
            );
        }));

    it("maps a 5xx response onto its Atlas body too (APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.getStatus().subscribe({
                next: fail,
                error: (error) => {
                    expect(error.status).toBe(503);
                    expect(atlasErrorFrom(error)).toEqual({
                        errorCode: "ATLAS-500-00-002",
                        errorMessage: "elasticsearch cluster is unavailable",
                    });
                    done();
                },
            });

            const req = httpMock.expectOne("/api/atlas/admin/status");
            req.flush(
                { errorCode: "ATLAS-500-00-002", errorMessage: "elasticsearch cluster is unavailable" },
                { status: 503, statusText: "Service Unavailable" },
            );
        }));

    it("yields no Atlas body for a network failure (APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.getSession().subscribe({
                next: fail,
                error: (error) => {
                    expect(error.status).toBe(0);
                    expect(atlasErrorFrom(error)).toBeNull();
                    done();
                },
            });

            const req = httpMock.expectOne("/api/atlas/admin/session");
            req.flush(null, { status: 0, statusText: "Unknown Error" });
        }));

    it("composes every URL from API_BASE_URL (APC-01)", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), provideApiBaseUrl("https://atlas:21000/api")],
        });
        const custom = TestBed.inject(AdminService);
        const mock = TestBed.inject(HttpTestingController);

        custom.getVersion().subscribe();
        custom.getStatus().subscribe();
        custom.getSession().subscribe();

        expect(mock.expectOne("https://atlas:21000/api/atlas/admin/version").request.method).toBe("GET");
        expect(mock.expectOne("https://atlas:21000/api/atlas/admin/status").request.method).toBe("GET");
        expect(mock.expectOne("https://atlas:21000/api/atlas/admin/session").request.method).toBe("GET");
        mock.verify();
        expect(TestBed.inject(API_BASE_URL)).toBe("https://atlas:21000/api");
    });
});
