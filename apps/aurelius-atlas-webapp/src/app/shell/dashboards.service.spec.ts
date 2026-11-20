import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";

import { TENANCY } from "../tenancy";
import { APP_CONFIG } from "../tokens";
import { DashboardsService } from "./dashboards.service";

/**
 * The tenant's dashboards link (TDL-08, TDL-09): one read of the server's
 * answer with tenancy on, the link on 200, nothing on any other answer, and no
 * read at all with tenancy off. Who may see the link is the server's rule
 * (TDL-06, TDL-07); this spec pins only what the webapp does with the answer.
 */

const PATH = "/api/aurelius/v1/tenancy/dashboards";
const URL = "https://atlas.example/grafana/d/tenant-catalogue?orgId=7";

function setup(enabled: boolean) {
    TestBed.configureTestingModule({
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            { provide: APP_CONFIG, useValue: { apiBaseUrl: "/api" } },
            { provide: TENANCY, useValue: { enabled, operatorOrganization: "operators", operatorRole: "op" } },
        ],
    });
    return { service: TestBed.inject(DashboardsService), httpMock: TestBed.inject(HttpTestingController) };
}

describe("DashboardsService (TDL-08, TDL-09)", () => {
    it("TDL-08: with tenancy on, reads the link once and keeps it", () => {
        const { service, httpMock } = setup(true);

        expect(service.url()).toBeUndefined();
        expect(TestBed.inject(DashboardsService)).toBe(service);
        const request = httpMock.expectOne(PATH);
        expect(request.request.method).toBe("GET");
        request.flush({ url: URL });

        expect(service.url()).toBe(URL);
        httpMock.verify();
    });

    it("TDL-09: a refusal or no dashboards leaves no link and throws nowhere", () => {
        const { service, httpMock } = setup(true);

        httpMock.expectOne(PATH).flush({ errorCode: "AURELIUS-403-00-006" }, { status: 403, statusText: "Forbidden" });

        expect(service.url()).toBeUndefined();
    });

    it("TDL-08: with tenancy off, asks nothing", () => {
        const { service, httpMock } = setup(false);

        httpMock.expectNone(PATH);
        expect(service.url()).toBeUndefined();
    });
});
