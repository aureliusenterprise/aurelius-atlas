import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { firstValueFrom } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { RuleVerdictsAnswer } from "../atlas/atlas-view";
import { RuleVerdictsService } from "./rule-verdicts.service";

describe("RuleVerdictsService", () => {
    let service: RuleVerdictsService;
    let httpMock: HttpTestingController;

    const answer: RuleVerdictsAnswer = {
        verdicts: [
            { entity: "e-1", compliant: true, name: "Name present", message: "The record carries no name" },
            { entity: "e-2", compliant: false, name: "Name present", message: "The record carries no name" },
        ],
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: "/api" }],
        });
        service = TestBed.inject(RuleVerdictsService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("verdicts posts the rule GUID to the verdicts door (VDR-15)", async () => {
        const answered = firstValueFrom(service.verdicts("r-1"));

        const request = httpMock.expectOne("/api/aurelius/v1/rule/verdicts");
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({ rule: "r-1" });
        request.flush(answer);
        expect(await answered).toEqual(answer);
    });

    it("verdicts answers the door's rows in store order (VDR-15, AVS-12)", async () => {
        const answered = firstValueFrom(service.verdicts("r-1"));

        const request = httpMock.expectOne("/api/aurelius/v1/rule/verdicts");
        request.flush(answer);

        const held = await answered;
        expect(held.verdicts.map((row) => [row.entity, row.compliant])).toEqual([
            ["e-1", true],
            ["e-2", false],
        ]);
    });

    it("verdicts answers none for a rule the store holds nothing of (VDR-15, VDR-14)", async () => {
        const answered = firstValueFrom(service.verdicts("r-404"));

        const request = httpMock.expectOne("/api/aurelius/v1/rule/verdicts");
        request.flush({ verdicts: [] });

        expect((await answered).verdicts).toEqual([]);
    });
});
