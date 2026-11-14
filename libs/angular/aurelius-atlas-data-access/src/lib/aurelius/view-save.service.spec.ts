/**
 * The mutation door's client (VDE-05, VDE-07): the POST wire, and the conflict
 * answer the editor re-edits from. The door's rules (AVW) are specced at the
 * server; here: the one request the save is, and the two 409 answers the
 * caller must tell apart.
 */
import { provideHttpClient } from "@angular/common/http";
import type { HttpErrorResponse } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { firstValueFrom } from "rxjs";

import { API_BASE_URL } from "../api-config";
import { EntityView, ViewSaveRequest } from "../atlas/atlas-view";
import { isAtlasErrorBody } from "../atlas/atlas-error";

import { viewConflictFrom, ViewSaveService } from "./view-save.service";

describe("ViewSaveService", () => {
    let service: ViewSaveService;
    let httpMock: HttpTestingController;

    const saved = (overrides: Partial<EntityView> = {}): EntityView => ({
        guid: "e-1",
        typeName: "DataSet",
        displayText: "genomic_variants",
        status: "ACTIVE",
        stale: false,
        updateTime: 1_700_000_000_000,
        classificationNames: ["PII"],
        sections: [{ attribute: "dataDomain", entities: [{ guid: "d-1", name: "Domain" }] }],
        ...overrides,
    });

    const body: ViewSaveRequest = {
        guid: "e-1",
        typeName: "DataSet",
        updateTime: 1_699_999_000_000,
        attributes: { qualifiedName: "genomic@cluster", name: "genomic_variants" },
        classifications: ["PII"],
        sections: [{ attribute: "dataDomain", entities: ["d-1"] }],
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: "/api" }],
        });
        service = TestBed.inject(ViewSaveService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("VDE-05 posts the whole desired state in one request and answers the live view", async () => {
        const answered = firstValueFrom(service.save(body));

        const request = httpMock.expectOne("/api/aurelius/v1/entity");
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual(body);
        request.flush(saved());
        const answer = await answered;
        expect(answer.guid).toBe("e-1");
        expect(answer.stale).toBe(false); // the door's write is the freshness (AVW-07)
    });

    it("VDE-05 sends a create without a guid and reads the server's from the answer", async () => {
        const created: ViewSaveRequest = { typeName: "DataSet", attributes: { qualifiedName: "new@cluster" } };
        const answered = firstValueFrom(service.save(created));

        const request = httpMock.expectOne("/api/aurelius/v1/entity");
        expect(request.request.body).toEqual(created);
        request.flush(saved({ guid: "server-1" })); // the server's GUID (AVW-06)
        expect((await answered).guid).toBe("server-1");
    });

    it("VDE-07 reads the stored view off a version conflict", async () => {
        const failed = firstValueFrom(service.save(body));
        httpMock
            .expectOne("/api/aurelius/v1/entity")
            .flush(
                { errorCode: "ENTITY_VERSION_CONFLICT", view: saved({ name: "other" }) },
                { status: 409, statusText: "conflict" },
            );
        const error = await failed.then(
            () => null,
            (caught: HttpErrorResponse) => caught,
        );

        const conflict = viewConflictFrom(error as HttpErrorResponse);
        expect(conflict?.view.name).toBe("other"); // the material to re-edit from (DD-591)
    });

    it("VDE-08 leaves a name-taken answer in the Atlas error shape", async () => {
        const failed = firstValueFrom(service.save(body));
        httpMock.expectOne("/api/aurelius/v1/entity").flush(
            {
                errorCode: "ENTITY_NAME_TAKEN",
                errorMessage: "The qualified name dup@cluster is held by entity other-1",
            },
            { status: 409, statusText: "conflict" },
        );
        const error = (await failed.then(
            () => null,
            (caught: HttpErrorResponse) => caught,
        )) as HttpErrorResponse;

        expect(isAtlasErrorBody(error.error)).toBe(true);
        expect(viewConflictFrom(error)).toBeNull(); // not the re-edit path
    });

    it("VDE-07 does not read a conflict out of any other failure", async () => {
        const failed = firstValueFrom(service.save(body));
        httpMock
            .expectOne("/api/aurelius/v1/entity")
            .flush({ errorCode: "ENTITY_VERSION_CONFLICT", view: saved() }, { status: 400, statusText: "bad" });
        const error = (await failed.then(
            () => null,
            (caught: HttpErrorResponse) => caught,
        )) as HttpErrorResponse;

        expect(viewConflictFrom(error)).toBeNull(); // a 400 is never the re-edit path
    });
});
