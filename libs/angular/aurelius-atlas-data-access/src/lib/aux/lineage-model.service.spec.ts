import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { LINEAGE_MODEL_BASE_URL } from "./aux-config";
import { LineageModelResponse, LineageModelService } from "./lineage-model.service";

describe("LineageModelService", () => {
    let service: LineageModelService;
    let httpMock: HttpTestingController;

    const response: LineageModelResponse = {
        model: JSON.stringify({ type: "ar3_model", nodes: [] }),
        metadata: [{ id: "m4i_dataset:g-1", data: { name: "tb1", typeName: "m4i_dataset" } }],
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        service = TestBed.inject(LineageModelService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("defaults the base URL to /lineage-model (LDG-07, DD-387)", () => {
        expect(TestBed.inject(LINEAGE_MODEL_BASE_URL)).toBe("/lineage-model");
    });

    it("getLineageModel always sends the guid, depth and direction defaults (LDG-01)", () =>
        new Promise<void>((done, fail) => {
            service.getLineageModel("g-1").subscribe({
                next: (model) => {
                    expect(model).toEqual(response);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/lineage-model/?guid=g-1&depth=3&direction=BOTH");
            expect(req.request.method).toBe("GET");
            req.flush(response);
        }));

    it("getLineageModel sends the caller's depth and direction (LDG-01)", () =>
        new Promise<void>((done, fail) => {
            service.getLineageModel("g-1", 2, "INPUT").subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/lineage-model/?guid=g-1&depth=2&direction=INPUT");
            req.flush(response);
        }));

    it("getLineageModel reads the 200 as the typed model and rows (LDG-02)", () =>
        new Promise<void>((done, fail) => {
            service.getLineageModel("g-1").subscribe({
                next: (model) => {
                    expect(typeof model?.model).toBe("string");
                    const ar3 = model && (JSON.parse(model.model) as { type?: string; nodes?: unknown[] });
                    expect(ar3).toEqual({ type: "ar3_model", nodes: [] });
                    expect(model?.metadata).toEqual(response.metadata);
                    done();
                },
                error: fail,
            });

            httpMock.expectOne("/lineage-model/?guid=g-1&depth=3&direction=BOTH").flush(response);
        }));

    it("getLineageModel keeps the 204 of no lineage as null, not an error (LDG-03, DD-386)", () =>
        new Promise<void>((done, fail) => {
            service.getLineageModel("g-1").subscribe({
                next: (model) => {
                    expect(model).toBeNull();
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/lineage-model/?guid=g-1&depth=3&direction=BOTH");
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it.each([
        [400, "ATLAS-400-00-027"],
        [401, "ATLAS-401-00-001"],
        [502, "ATLAS-500-00-002"],
    ])(
        "getLineageModel leaves a %d on the error channel with its Atlas body (LDG-04, LM-07)",
        (status, code) =>
            new Promise<void>((done, fail) => {
                service.getLineageModel("g-1").subscribe({
                    next: () => fail(new Error("the error must not reach next")),
                    error: (error) => {
                        expect(error.status).toBe(status);
                        expect(error.error).toEqual({ errorCode: code, errorMessage: "boom" });
                        done();
                    },
                });

                const req = httpMock.expectOne("/lineage-model/?guid=g-1&depth=3&direction=BOTH");
                req.flush({ errorCode: code, errorMessage: "boom" }, { status, statusText: "Error" });
            }),
    );
});
