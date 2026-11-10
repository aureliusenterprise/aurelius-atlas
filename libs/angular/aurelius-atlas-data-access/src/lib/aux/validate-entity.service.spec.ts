import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { VALIDATE_ENTITY_BASE_URL } from "./aux-config";
import { EntityValidationResponse, ValidateEntityService } from "./validate-entity.service";

describe("ValidateEntityService", () => {
    let service: ValidateEntityService;
    let httpMock: HttpTestingController;

    // The deployed 8.3 mock document (VE-02, DV-67): the four cards, verbatim
    // as aurelius_atlas_validate_entity.mock.MOCK_VALIDATION answers them.
    const response: EntityValidationResponse = {
        dataEntity: {
            items: [
                {
                    result: { raw: "This entity is missing a dataEntity" },
                    dataqualitytype: { raw: "attribute" },
                    usedattributes: { raw: ["dataEntity"] },
                    name: { raw: "Attribute - dataEntity" },
                    compliant: { raw: "0" },
                    _meta: { engine: "atlas-dev-gov-quality", score: 1, id: "doc-6290d9e0dd895e02b897451f" },
                    id: { raw: "doc-6290d9e0dd895e02b897451f" },
                },
            ],
            isNonCompliant: true,
        },
        definition: {
            items: [
                {
                    result: { raw: "This entity has a definition" },
                    dataqualitytype: { raw: "attribute" },
                    usedattributes: { raw: ["definition"] },
                    name: { raw: "Attribute - definition" },
                    compliant: { raw: "1" },
                    _meta: { engine: "atlas-dev-gov-quality", score: 1, id: "doc-6290d9dedd895e197b974510" },
                    id: { raw: "doc-6290d9dedd895e197b974510" },
                },
            ],
            isNonCompliant: false,
        },
        domainLead: {
            items: [
                {
                    result: { raw: "This entity is missing a domainLead" },
                    dataqualitytype: { raw: "attribute" },
                    usedattributes: { raw: ["domainLead"] },
                    name: { raw: "Attribute - domainLead" },
                    compliant: { raw: "0" },
                    _meta: { engine: "atlas-dev-gov-quality", score: 1, id: "doc-6290d9e0dd895e02b8974528" },
                    id: { raw: "doc-6290d9e0dd895e02b8974528" },
                },
            ],
            isNonCompliant: true,
        },
        name: {
            items: [
                {
                    result: { raw: "This entity has a name" },
                    dataqualitytype: { raw: "attribute" },
                    usedattributes: { raw: ["name"] },
                    name: { raw: "Attribute - name" },
                    compliant: { raw: "1" },
                    _meta: { engine: "atlas-dev-gov-quality", score: 1, id: "doc-6290d9dedd895e197b974507" },
                    id: { raw: "doc-6290d9dedd895e197b974507" },
                },
            ],
            isNonCompliant: false,
        },
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

    it("defaults the base URL to /validate-entity (EDT-22, DD-435)", () => {
        expect(TestBed.inject(VALIDATE_ENTITY_BASE_URL)).toBe("/validate-entity");
    });

    it("validateEntity posts the draft to the root with no query string (EDT-21, VE-01)", () =>
        new Promise<void>((done, fail) => {
            service.validateEntity(draft).subscribe({
                next: (cards) => {
                    expect(cards).toEqual(response);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/validate-entity/");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(draft);
            req.flush(response);
        }));

    it("validateEntity reads the 200 as the typed cards (EDT-21, VE-02)", () =>
        new Promise<void>((done, fail) => {
            service.validateEntity(draft).subscribe({
                next: (cards) => {
                    expect(Object.keys(cards).sort()).toEqual(["dataEntity", "definition", "domainLead", "name"]);
                    const dataEntity = cards["dataEntity"];
                    expect(dataEntity.isNonCompliant).toBe(true);
                    expect(dataEntity.items[0].compliant.raw).toBe("0");
                    expect(dataEntity.items[0].result.raw).toBe("This entity is missing a dataEntity");
                    expect(dataEntity.items[0]._meta.engine).toBe("atlas-dev-gov-quality");
                    expect(cards["name"].isNonCompliant).toBe(false);
                    expect(cards["name"].items[0].compliant.raw).toBe("1");
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
