import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { VALIDATE_ENTITY_BASE_URL } from "./aux-config";
import { EntityValidationResponse, ValidateEntityService } from "./validate-entity.service";

describe("ValidateEntityService", () => {
    let service: ValidateEntityService;
    let httpMock: HttpTestingController;

    // The verdict document of 12.7 (VEV-02/VEV-03): the flat array and the
    // unread rules, as the app's engine answers them over the corpus rules.
    const response: EntityValidationResponse = {
        verdicts: [
            {
                ruleGuid: "rule-dataset-name",
                ruleName: "Dataset name required",
                attribute: "name",
                dimension: "COMPLETENESS",
                compliant: true,
                message: "This dataset has a name",
            },
            {
                ruleGuid: "rule-dataset-fields",
                ruleName: "Dataset fields required",
                attribute: "schematicFields",
                dimension: "COMPLETENESS",
                compliant: false,
                message: "This dataset should have at least one field",
            },
        ],
        unreadRules: [
            {
                ruleGuid: "rule-expression",
                ruleName: "A stored expression",
                error: "a stored expression rule needs re-authoring (DV-146)",
            },
        ],
    };

    const draft = { typeName: "m4i_dataset", attributes: { name: "tb1" } };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        service = TestBed.inject(ValidateEntityService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("defaults the base URL to /validate-entity (EDT-22, DD-445)", () => {
        expect(TestBed.inject(VALIDATE_ENTITY_BASE_URL)).toBe("/validate-entity");
    });

    it("validateEntity posts the draft to the root with no query string (EDT-21, VEV-01)", () =>
        new Promise<void>((done, fail) => {
            service.validateEntity(draft).subscribe({
                next: (answer) => {
                    expect(answer).toEqual(response);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/validate-entity/");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(draft);
            req.flush(response);
        }));

    it("validateEntity reads the 200 as the typed verdicts (EDT-21, VEV-02/VEV-03)", () =>
        new Promise<void>((done, fail) => {
            service.validateEntity(draft).subscribe({
                next: (answer) => {
                    expect(answer.verdicts).toHaveLength(2);
                    const [name, fields] = answer.verdicts;
                    expect(name.ruleGuid).toBe("rule-dataset-name");
                    expect(name.compliant).toBe(true);
                    expect(name.message).toBe("This dataset has a name");
                    expect(fields.attribute).toBe("schematicFields");
                    expect(fields.compliant).toBe(false);
                    expect(answer.unreadRules).toHaveLength(1);
                    expect(answer.unreadRules[0].ruleGuid).toBe("rule-expression");
                    expect(answer.unreadRules[0].error).toContain("DV-146");
                    done();
                },
                error: fail,
            });

            httpMock.expectOne("/validate-entity/").flush(response);
        }));

    it("validateEntity leaves a 401 on the error channel with its Atlas body (EDT-21, VE-03)", () =>
        new Promise<void>((done, fail) => {
            service.validateEntity(draft).subscribe({
                next: () => fail(new Error("the error must not reach next")),
                error: (error) => {
                    expect(error.status).toBe(401);
                    expect(error.error).toEqual({ errorCode: "ATLAS-401-00-001", errorMessage: "boom" });
                    done();
                },
            });

            const req = httpMock.expectOne("/validate-entity/");
            req.flush({ errorCode: "ATLAS-401-00-001", errorMessage: "boom" }, { status: 401, statusText: "Error" });
        }));
});
