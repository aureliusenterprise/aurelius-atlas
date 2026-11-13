import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { AdminService, AtlasSession, AtlasStatus, AtlasVersion } from "./admin.service";
import { API_BASE_URL, provideApiBaseUrl } from "../api-config";
import type { AtlasAuditEntry, AuditSearchParameters } from "./atlas-audit";
import type { AtlasImportResult, AtlasServer, ExportImportAuditEntry } from "./atlas-impexp";
import type { AtlasMetrics, AtlasMetricsCharts, AtlasMetricsStat } from "./atlas-metrics";
import type { AtlasPatch } from "./atlas-patches";
import type { AtlasEntityHeader } from "./atlas-search";
import type { AtlasTask } from "./atlas-tasks";
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

    it("liveness answers the plain-text OK (AAC-01)", () =>
        new Promise<void>((done, fail) => {
            service.liveness().subscribe({
                next: (text) => {
                    expect(text).toBe("OK");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/liveness");
            expect(req.request.method).toBe("GET");
            req.flush("OK");
        }));

    it("readiness surfaces the Atlas error when the server is not ready (AAC-01, APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.readiness().subscribe({
                next: fail,
                error: (error) => {
                    expect(error.status).toBe(503);
                    // The call asked for text, so the Atlas JSON body arrives as text (APC-04).
                    expect(JSON.parse(error.error as string).errorCode).toBe("ATLAS-500-00-002");
                    done();
                },
            });

            const req = httpMock.expectOne("/api/atlas/admin/readiness");
            expect(req.request.method).toBe("GET");
            req.flush(
                JSON.stringify({ errorCode: "ATLAS-500-00-002", errorMessage: "elasticsearch cluster is unavailable" }),
                { status: 503, statusText: "Service Unavailable" },
            );
        }));

    it("patches unwraps the patches envelope (AAC-02)", () =>
        new Promise<void>((done, fail) => {
            const patch: AtlasPatch = {
                id: "patch-1",
                type: "TYPEDEF_PATCH",
                action: "ADD_ATTRIBUTE",
                status: "APPLIED",
                createdTime: 1730000000000,
                updatedTime: 1730000005000,
            };

            service.patches().subscribe({
                next: (patches) => {
                    expect(patches).toEqual([patch]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/patches");
            expect(req.request.method).toBe("GET");
            req.flush({ patches: [patch] });
        }));

    it("purge sends the bare guid array and answers the mutation response (AAC-03)", () =>
        new Promise<void>((done, fail) => {
            const answer = {
                mutatedEntities: { PURGE: [{ guid: "g-1", typeName: "table" }] },
                partialUpdatedEntities: null,
            };

            service.purge(["g-1"]).subscribe({
                next: (result) => {
                    expect(result.mutatedEntities?.PURGE).toEqual([{ guid: "g-1", typeName: "table" }]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/purge");
            expect(req.request.method).toBe("PUT");
            expect(req.request.body).toEqual(["g-1"]);
            req.flush(answer);
        }));

    it("purge of an empty list still sends [] (AAC-03, DV-10)", () =>
        new Promise<void>((done, fail) => {
            service.purge([]).subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/purge");
            expect(req.request.method).toBe("PUT");
            expect(req.request.body).toEqual([]);
            req.flush({});
        }));

    it("export answers the bytes and the content type (AAC-04, DD-315)", () =>
        new Promise<void>((done, fail) => {
            const zip = new ArrayBuffer(4);
            new Uint8Array(zip).set([0x50, 0x4b, 0x03, 0x04]);

            service
                .export({ itemsToExport: [{ guid: "g-1", typeName: "table", uniqueAttributes: null }], options: {} })
                .subscribe({
                    next: (answer) => {
                        expect(answer.body).toEqual(zip);
                        expect(answer.contentType).toBe("application/zip");
                        done();
                    },
                    error: fail,
                });

            const req = httpMock.expectOne("/api/atlas/admin/export");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual({
                itemsToExport: [{ guid: "g-1", typeName: "table", uniqueAttributes: null }],
                options: {},
            });
            req.flush(zip, { headers: { "content-type": "application/zip" } });
        }));

    it("export with no request sends no body (AAC-04, DV-120)", () =>
        new Promise<void>((done, fail) => {
            const zip = new ArrayBuffer(2);
            new Uint8Array(zip).set([0x50, 0x4b]);

            service.export().subscribe({
                next: (answer) => {
                    expect(answer.body).toEqual(zip);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/export");
            expect(req.request.body).toBeNull();
            req.flush(zip);
        }));

    it("export answers null bytes for the 204 that omits its ZIP (AAC-04, EXP-05)", () =>
        new Promise<void>((done, fail) => {
            service.export({ itemsToExport: [], options: { omitZipResponseForEmptyExport: true } }).subscribe({
                next: (answer) => {
                    expect(answer.body).toBeNull();
                    expect(answer.contentType).toBe("");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/export");
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it("importData sends the data file part and the plain-text request part (AAC-05, DD-313)", () =>
        new Promise<void>((done, fail) => {
            const answer: AtlasImportResult = {
                timeStamp: 1730000000000,
                processedEntities: ["g-1"],
                operationStatus: "SUCCESS",
            };

            service.importData(new Blob(["PK"]), { options: { updateTypeDefinition: "true" } }).subscribe({
                next: (result) => {
                    expect(result.operationStatus).toBe("SUCCESS");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/import");
            expect(req.request.method).toBe("POST");
            const form = req.request.body as FormData;
            expect(form).toBeInstanceOf(FormData);
            const data = form.get("data");
            expect(data).toBeInstanceOf(Blob);
            expect((data as File).name).toBe("export.zip");
            const request = form.get("request");
            expect(typeof request).toBe("string");
            expect(JSON.parse(request as string)).toEqual({ options: { updateTypeDefinition: "true" } });
            req.flush(answer);
        }));

    it("importData with no request sends only the data part (AAC-05)", () =>
        new Promise<void>((done, fail) => {
            service.importData(new Blob(["PK"])).subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/import");
            const form = req.request.body as FormData;
            expect([...form.keys()]).toEqual(["data"]);
            req.flush({});
        }));

    it("importFile sends the request as the bare JSON body (AAC-05, IMS-06)", () =>
        new Promise<void>((done, fail) => {
            const request = { options: { fileName: "/tmp/export.zip" } };

            service.importFile(request).subscribe({
                next: (result) => {
                    expect(result.operationStatus).toBe("SUCCESS");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/importfile");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(request);
            req.flush({ operationStatus: "SUCCESS" });
        }));

    it("tasks sends the repeated guids parameter and answers the task list (AAC-06)", () =>
        new Promise<void>((done, fail) => {
            const task: AtlasTask = {
                type: "CLASSIFICATION_PROPAGATION",
                guid: "g-1",
                attemptCount: 0,
                status: "COMPLETE",
            };

            service.tasks(["g-1", "g-2"]).subscribe({
                next: (tasks) => {
                    expect(tasks).toEqual([task]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne(
                (request) =>
                    request.url === "/api/atlas/admin/tasks" &&
                    JSON.stringify(request.params.getAll("guids")) === JSON.stringify(["g-1", "g-2"]),
            );
            expect(req.request.method).toBe("GET");
            req.flush([task]);
        }));

    it("tasks with no guids sends no parameter — every task (AAC-06)", () =>
        new Promise<void>((done, fail) => {
            service.tasks().subscribe({
                next: (tasks) => {
                    expect(tasks).toEqual([]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/tasks");
            expect(req.request.params.keys()).toEqual([]);
            req.flush([]);
        }));

    it("deleteTasks sends the repeated guids parameter and answers void on 204 (AAC-06)", () =>
        new Promise<void>((done, fail) => {
            service.deleteTasks(["g-1"]).subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/tasks?guids=g-1");
            expect(req.request.method).toBe("DELETE");
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it("metrics answers the server's counts (MET-01, AAC-08)", () =>
        new Promise<void>((done, fail) => {
            const metrics = { data: { general: { "entity.total": 3 } } } satisfies AtlasMetrics;

            service.metrics().subscribe({
                next: (result) => {
                    expect(result).toEqual(metrics);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/metrics");
            expect(req.request.method).toBe("GET");
            req.flush(metrics);
        }));

    it("metricsStats always sends mininfo: true by default, false when asked (MHS-02, AAC-08, DD-561)", () =>
        new Promise<void>((done, fail) => {
            const stat = {
                guid: "s-1",
                metricsId: "m-1",
                collectionTime: 1_700_000_000_000,
            } satisfies AtlasMetricsStat;

            service.metricsStats(false).subscribe({
                next: (result) => {
                    expect(result).toEqual([stat]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/metricsstats?mininfo=false");
            expect(req.request.method).toBe("GET");
            req.flush([stat]);
        }));

    it("metricsStats sends mininfo=true by default (MHS-02, AAC-08, DD-561)", () =>
        new Promise<void>((done, fail) => {
            service.metricsStats().subscribe({
                next: (result) => {
                    expect(result).toEqual([]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/metricsstats?mininfo=true");
            req.flush([]);
        }));

    it("metricsStat reads the metric stored at that collection time (MHS-02, AAC-09)", () =>
        new Promise<void>((done, fail) => {
            const stat = {
                guid: "s-1",
                metricsId: "m-1",
                collectionTime: 1_700_000_000_000,
            } satisfies AtlasMetricsStat;

            service.metricsStat(1_700_000_000_000).subscribe({
                next: (result) => {
                    expect(result).toEqual(stat);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/metricsstat/1700000000000");
            expect(req.request.method).toBe("GET");
            req.flush(stat);
        }));

    it("metricsInRange sends the times and the repeated typeName (MHS-03, AAC-09)", () =>
        new Promise<void>((done, fail) => {
            service.metricsInRange(1000, 2000, ["Table", "Dataset"]).subscribe({
                next: (result) => {
                    expect(result).toEqual([]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne(
                (request) =>
                    request.url === "/api/atlas/admin/metricsstats/range" &&
                    request.params.get("startTime") === "1000" &&
                    request.params.get("endTime") === "2000" &&
                    JSON.stringify(request.params.getAll("typeName")) === JSON.stringify(["Table", "Dataset"]),
            );
            expect(req.request.method).toBe("GET");
            req.flush([]);
        }));

    it("metricsCharts answers the chart series keyed by type name (MHS-04, AAC-09)", () =>
        new Promise<void>((done, fail) => {
            const charts = {
                Table: [{ key: "ACTIVE", values: [[1000, 2]] }],
            } satisfies AtlasMetricsCharts;

            service.metricsCharts(1000, 2000, ["Table"]).subscribe({
                next: (result) => {
                    expect(result).toEqual(charts);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne(
                "/api/atlas/admin/metricsstats/charts?startTime=1000&endTime=2000&typeName=Table",
            );
            expect(req.request.method).toBe("GET");
            req.flush(charts);
        }));

    it("auditDetails sends only a non-default limit or offset (ADA-05, AAC-09)", () =>
        new Promise<void>((done, fail) => {
            const header = { guid: "e-1", typeName: "Table", status: "DELETE_PENDING" } satisfies AtlasEntityHeader;

            service.auditDetails("a-1", 0, 20).subscribe({
                next: (result) => {
                    expect(result).toEqual([header]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/audit/a-1/details?offset=20");
            expect(req.request.method).toBe("GET");
            req.flush([header]);
        }));

    it("auditDetails with the defaults sends limit=10 only (ADA-05, AAC-09)", () =>
        new Promise<void>((done, fail) => {
            service.auditDetails("a-1").subscribe({
                next: (result) => {
                    expect(result).toEqual([]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/audit/a-1/details?limit=10");
            req.flush([]);
        }));

    it("server reads the catalogue of the full name (REP-01, AAC-10)", () =>
        new Promise<void>((done, fail) => {
            const server = {
                name: "srv-1",
                fullName: "cluster1:srv-1",
                urls: ["http://s:21000"],
            } satisfies AtlasServer;

            service.server("cluster1:srv-1").subscribe({
                next: (result) => {
                    expect(result).toEqual(server);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/server/cluster1%3Asrv-1");
            expect(req.request.method).toBe("GET");
            req.flush(server);
        }));

    it("exportImportAudit sends the values given and skips the rest (REP-05, AAC-10)", () =>
        new Promise<void>((done, fail) => {
            service.exportImportAudit({ serverName: "s", userName: "u", operation: "EXPORT" }).subscribe({
                next: (result) => {
                    expect(result).toEqual([]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/expimp/audit?serverName=s&userName=u&operation=EXPORT");
            expect(req.request.method).toBe("GET");
            req.flush([]);
        }));

    it("exportImportAudit with no query sends no parameter (REP-05, AAC-10)", () =>
        new Promise<void>((done, fail) => {
            const entry = {
                guid: "x-1",
                userName: "u",
                operation: "EXPORT",
                startTime: 1000,
            } satisfies ExportImportAuditEntry;

            service.exportImportAudit().subscribe({
                next: (result) => {
                    expect(result).toEqual([entry]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/expimp/audit");
            expect(req.request.params.keys()).toEqual([]);
            req.flush([entry]);
        }));

    it("audits posts the search parameters (ADA-04, AAC-11)", () =>
        new Promise<void>((done, fail) => {
            const parameters = { limit: 5, offset: 0 } satisfies AuditSearchParameters;
            const entry = { guid: "a-1", userName: "u", operation: "PURGE" } satisfies AtlasAuditEntry;

            service.audits(parameters).subscribe({
                next: (result) => {
                    expect(result).toEqual([entry]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/audits");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(parameters);
            req.flush([entry]);
        }));

    it("audits with no parameters asks for every entry with no body (ADA-04, AAC-11)", () =>
        new Promise<void>((done, fail) => {
            service.audits().subscribe({
                next: (result) => {
                    expect(result).toEqual([]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/audits");
            expect(req.request.body).toBeNull();
            req.flush([]);
        }));

    it("ageoutAudits answers the queued tasks and sends useAuditConfig only when set (AGE-01, AAC-11)", () =>
        new Promise<void>((done, fail) => {
            const task = { type: "ENTITY_AGEOUT", guid: "t-1", status: "PENDING" } satisfies AtlasTask;

            service.ageoutAudits({ auditAgingEnabled: true }, true).subscribe({
                next: (result) => {
                    expect(result).toEqual([task]);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/audits/ageout?useAuditConfig=true");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual({ auditAgingEnabled: true });
            req.flush([task]);
        }));

    it("ageoutAudits keeps the 204 of an aging that queued nothing as null, not [] (AGE-03, AAC-11, DD-561)", () =>
        new Promise<void>((done, fail) => {
            service.ageoutAudits().subscribe({
                next: (result) => {
                    expect(result).toBeNull();
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/admin/audits/ageout");
            expect(req.request.body).toBeNull();
            expect(req.request.params.keys()).toEqual([]);
            req.flush(null, { status: 204, statusText: "No Content" });
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
