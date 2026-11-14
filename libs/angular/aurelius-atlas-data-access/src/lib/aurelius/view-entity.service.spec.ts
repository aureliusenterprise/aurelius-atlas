import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { firstValueFrom } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { EntityView } from "../atlas/atlas-view";
import { ViewEntityService } from "./view-entity.service";

describe("ViewEntityService", () => {
    let service: ViewEntityService;
    let httpMock: HttpTestingController;

    const view = (guid: string): EntityView => ({
        guid,
        typeName: "m4i_data_entity",
        displayText: `Entity ${guid}`,
        status: "ACTIVE",
        stale: false,
        sections: [{ attribute: "dataDomain", entities: [{ guid: "d-1", name: "Domain" }] }],
    });

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: "/api" }],
        });
        service = TestBed.inject(ViewEntityService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("views one guid through the read door (VDR-01)", async () => {
        const answered = firstValueFrom(service.view("e-1"));

        const request = httpMock.expectOne("/api/aurelius/v1/entity/guid/e-1");
        expect(request.request.method).toBe("GET");
        request.flush(view("e-1"));
        expect(await answered).toEqual(view("e-1"));
    });

    it("answers a guid read again in the session from memory (VDR-07, DD-605)", async () => {
        const first = firstValueFrom(service.view("e-1"));
        httpMock.expectOne("/api/aurelius/v1/entity/guid/e-1").flush(view("e-1"));
        await first;

        const again = await firstValueFrom(service.view("e-1"));

        httpMock.expectNone("/api/aurelius/v1/entity/guid/e-1"); // no second request (VDR-07)
        expect(again).toEqual(view("e-1"));
    });

    it("asks the door again after the save tick evicts the guid (VDR-07, DD-327)", async () => {
        const first = firstValueFrom(service.view("e-1"));
        httpMock.expectOne("/api/aurelius/v1/entity/guid/e-1").flush(view("e-1"));
        await first;

        service.evict("e-1");
        const reread = firstValueFrom(service.view("e-1"));
        httpMock.expectOne("/api/aurelius/v1/entity/guid/e-1").flush(view("e-1"));

        expect(await reread).toEqual(view("e-1"));
    });

    it("keeps its last fifty views, the oldest making room (VDR-07, DD-605)", async () => {
        const reads = Array.from({ length: 51 }, (_, index) => firstValueFrom(service.view(`g-${index}`)));
        for (let index = 0; index < 51; index += 1) {
            httpMock.expectOne(`/api/aurelius/v1/entity/guid/g-${index}`).flush(view(`g-${index}`));
        }
        await Promise.all(reads);

        const remembered = await firstValueFrom(service.view("g-50")); // the last read stays
        httpMock.expectNone("/api/aurelius/v1/entity/guid/g-50");
        expect(remembered).toEqual(view("g-50"));

        const dropped = firstValueFrom(service.view("g-0")); // the first fell out of the fifty
        httpMock.expectOne("/api/aurelius/v1/entity/guid/g-0").flush(view("g-0"));
        expect(await dropped).toEqual(view("g-0"));
    });

    it("lets a failed read through without remembering it (VDR-08)", async () => {
        const failed = firstValueFrom(service.view("e-1"));
        httpMock.expectOne("/api/aurelius/v1/entity/guid/e-1").flush("{}", { status: 500, statusText: "error" });
        await expect(failed).rejects.toBeTruthy();

        const retried = firstValueFrom(service.view("e-1")); // the next read goes out again
        httpMock.expectOne("/api/aurelius/v1/entity/guid/e-1").flush(view("e-1"));
        expect(await retried).toEqual(view("e-1"));
    });
});
