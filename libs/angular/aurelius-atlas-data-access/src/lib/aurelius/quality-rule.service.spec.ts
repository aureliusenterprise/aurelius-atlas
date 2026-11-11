import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { firstValueFrom } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { QualityKinds, QualityRuleService } from "./quality-rule.service";

describe("QualityRuleService", () => {
    let service: QualityRuleService;
    let httpMock: HttpTestingController;

    const vocabulary: QualityKinds = {
        kinds: [
            {
                name: "COLUMN_NOT_NULL_RATIO",
                dimension: "COMPLETENESS",
                required: ["column"],
                optional: [],
                reason: "the value is missing",
            },
        ],
        castableTypes: ["date", "int"],
        thresholdMin: 0,
        thresholdMax: 1,
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: "/api" }],
        });
        service = TestBed.inject(QualityRuleService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("kinds gets the kinds resource through the Aurelius base (EDT-30)", async () => {
        const answered = firstValueFrom(service.kinds());

        const request = httpMock.expectOne("/api/aurelius/v1/quality/kinds");
        expect(request.request.method).toBe("GET");
        request.flush(vocabulary);
        expect(await answered).toEqual(vocabulary);
    });

    it("kinds answers a later caller from the cache without a second request (EDT-25, EDT-30)", async () => {
        const first = firstValueFrom(service.kinds());
        httpMock.expectOne("/api/aurelius/v1/quality/kinds").flush(vocabulary);
        expect(await first).toEqual(vocabulary);

        expect(await firstValueFrom(service.kinds())).toEqual(vocabulary);
        httpMock.expectNone("/api/aurelius/v1/quality/kinds");
    });

    it("kinds retries after a failed load instead of caching the failure (EDT-30)", async () => {
        const failed = firstValueFrom(service.kinds());
        httpMock.expectOne("/api/aurelius/v1/quality/kinds").flush({}, { status: 500, statusText: "error" });
        let rejected = false;
        try {
            await failed;
        } catch {
            rejected = true;
        }
        expect(rejected).toBe(true);

        const retried = firstValueFrom(service.kinds());
        httpMock.expectOne("/api/aurelius/v1/quality/kinds").flush(vocabulary);
        expect(await retried).toEqual(vocabulary);
    });

    it("validateRule posts the stored-rule attributes to the validate endpoint (EDT-28, EDT-30)", async () => {
        const answered = firstValueFrom(
            service.validateRule({ name: "total filled", dqcheckkind: "COLUMN_NOT_NULL_RATIO", dqcolumn: "total" }),
        );

        const request = httpMock.expectOne("/api/aurelius/v1/quality/rules/validate");
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({
            name: "total filled",
            dqcheckkind: "COLUMN_NOT_NULL_RATIO",
            dqcolumn: "total",
        });
        request.flush({ valid: true, kind: "COLUMN_NOT_NULL_RATIO", dimension: "COMPLETENESS" });
        expect(await answered).toEqual({ valid: true, kind: "COLUMN_NOT_NULL_RATIO", dimension: "COMPLETENESS" });
    });

    it("validateRule carries a rejected rule's reason as a plain answer (QRE-02)", async () => {
        const answered = firstValueFrom(service.validateRule({ name: "broken" }));

        httpMock
            .expectOne("/api/aurelius/v1/quality/rules/validate")
            .flush({ valid: false, reason: "a rule names no check kind" });
        expect(await answered).toEqual({ valid: false, reason: "a rule names no check kind" });
    });
});
