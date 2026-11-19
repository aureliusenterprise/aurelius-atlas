import { TestBed } from "@angular/core/testing";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";

import { AtlasVersion } from "aurelius-atlas-data-access";

import { VersionService } from "./version.service";

/**
 * The version read (VER-01/02/03, DD-725): one call to the server's admin
 * answer, the empty value before it lands, the value after it, and silence when
 * it never arrives. The answer itself is the server's contract (ADM-01, DV-03) —
 * this spec pins only what the webapp does with it.
 */

/** The shape `GET /api/atlas/admin/version` answers (ADM-01, DV-03). */
const ANSWER: AtlasVersion = {
    Version: "7.34.0#abc1234",
    Revision: "0123456789abcdef",
    Name: "aurelius-atlas",
    Description: "Apache Atlas 2.4.0 REST API on Elasticsearch",
};

function setup() {
    TestBed.configureTestingModule({
        providers: [provideHttpClient(), provideHttpClientTesting()],
    });

    return { service: TestBed.inject(VersionService), httpMock: TestBed.inject(HttpTestingController) };
}

describe("VersionService (VER-01/02/03, DD-725)", () => {
    it("VER-02: the version is empty until the answer arrives", () => {
        const { service } = setup();

        expect(service.version()).toBe("");
    });

    it("VER-01: the service reads the server's version answer (ADM-01)", () => {
        const { service, httpMock } = setup();

        const request = httpMock.expectOne("/api/atlas/admin/version");
        expect(request.request.method).toBe("GET");
        request.flush(ANSWER);

        expect(service.version()).toBe("7.34.0#abc1234");
    });

    it("VER-02: one instance reads once, however many readers it has", () => {
        const { service, httpMock } = setup();

        // A second and third reader (footer, About, the PNG writer) share the
        // root instance and must not add a call.
        expect(TestBed.inject(VersionService)).toBe(service);
        expect(TestBed.inject(VersionService)).toBe(service);
        httpMock.expectOne("/api/atlas/admin/version").flush(ANSWER);
        httpMock.verify();
    });

    it("VER-03: a failed answer stays empty and throws nowhere (the About section's posture, SPL-07)", () => {
        const { service, httpMock } = setup();

        // 7.26's retry interceptor is not provided here: one failure is what
        // reaches the service, which is the give-up state the rule covers.
        httpMock.expectOne("/api/atlas/admin/version").flush({}, { status: 503, statusText: "Unavailable" });

        expect(service.version()).toBe("");
    });
});
