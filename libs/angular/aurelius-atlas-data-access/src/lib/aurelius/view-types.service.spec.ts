/**
 * The form-slice door's client (VDE-02, DD-611): the for-type wire and the
 * cache by type name DD-593 scheduled for 16.5. The door's rules (AVW-11) are
 * specced at the server; here: one request per type, answered from memory the
 * second time.
 */
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { firstValueFrom } from "rxjs";

import type { AtlasEntityDef } from "../atlas/atlas-typedef";
import { API_BASE_URL } from "../api-config";
import { ViewForTypeAnswer } from "../atlas/atlas-view";

import { ViewTypeService } from "./view-types.service";

describe("ViewTypeService", () => {
    let service: ViewTypeService;
    let httpMock: HttpTestingController;

    const entityDef = (name: string): AtlasEntityDef => ({
        category: "ENTITY",
        name,
        serviceType: "atlas_core",
    });

    const chain = (name: string): ViewForTypeAnswer => ({
        type: entityDef(name),
        superTypes: [entityDef("Referenceable"), entityDef("Asset")],
    });

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: "/api" }],
        });
        service = TestBed.inject(ViewTypeService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("VDE-02 asks the form-slice door for one type's chain", async () => {
        const answered = firstValueFrom(service.forType("DataSet"));

        const request = httpMock.expectOne("/api/aurelius/v1/types/for-type/DataSet");
        expect(request.request.method).toBe("GET");
        request.flush(chain("DataSet"));
        const answer = await answered;
        expect((answer.type as AtlasEntityDef).name).toBe("DataSet");
        expect(answer.superTypes).toHaveLength(2);
    });

    it("VDE-02 answers a type asked again in the session from memory (DD-611)", async () => {
        const first = firstValueFrom(service.forType("DataSet"));
        httpMock.expectOne("/api/aurelius/v1/types/for-type/DataSet").flush(chain("DataSet"));
        await first;

        const again = await firstValueFrom(service.forType("DataSet"));

        httpMock.expectNone("/api/aurelius/v1/types/for-type/DataSet"); // no second request
        expect((again.type as AtlasEntityDef).name).toBe("DataSet");
    });

    it("VDE-02 caches each type apart, and lets a failure through uncached", async () => {
        const failed = firstValueFrom(service.forType("Gone"));
        httpMock.expectOne("/api/aurelius/v1/types/for-type/Gone").flush("{}", { status: 404, statusText: "gone" });
        await expect(failed).rejects.toBeTruthy();

        const other = firstValueFrom(service.forType("Process"));
        httpMock.expectOne("/api/aurelius/v1/types/for-type/Process").flush(chain("Process"));
        expect((await other).superTypes).toHaveLength(2);

        const retried = firstValueFrom(service.forType("Gone")); // the failed name asks again
        httpMock.expectOne("/api/aurelius/v1/types/for-type/Gone").flush(chain("Gone"));
        expect((await retried).superTypes).toHaveLength(2);
    });

    it("VDE-02 encodes a name the URL cannot carry", async () => {
        const answered = firstValueFrom(service.forType("a/b c"));
        httpMock.expectOne("/api/aurelius/v1/types/for-type/a%2Fb%20c").flush(chain("a/b c"));
        expect((await answered).superTypes).toHaveLength(2);
    });
});
