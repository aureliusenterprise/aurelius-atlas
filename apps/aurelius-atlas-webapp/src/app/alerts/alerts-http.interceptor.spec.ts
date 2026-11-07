/**
 * The HTTP error reporter (ALR-05): the interceptor's rules are the
 * reportable set (5xx and network failures on /api and the /lineage-model
 * aux API, never 4xx), the message's shape (method, path, status), and the
 * untouched re-throw. The store's grouping of the resulting alerts is
 * specced at the store.
 */
import { HttpClient, provideHttpClient, withInterceptors } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";

import { AlertsService } from "./alerts.service";
import { alertsHttpInterceptor } from "./alerts-http.interceptor";

function setup() {
    TestBed.configureTestingModule({
        providers: [provideHttpClient(withInterceptors([alertsHttpInterceptor])), provideHttpClientTesting()],
    });

    return {
        http: TestBed.inject(HttpClient),
        controller: TestBed.inject(HttpTestingController),
        alerts: TestBed.inject(AlertsService),
    };
}

describe("alertsHttpInterceptor (ALR-05)", () => {
    it("reports a 5xx on /api (ALR-05)", () => {
        const { http, controller, alerts } = setup();

        // The interceptor re-throws (ALR-05), so every expecting-failure
        // subscribe carries a no-op error handler — an unhandled
        // HttpErrorResponse fails the Vitest run (the re-throw itself is
        // the last test's subject).
        http.get("/api/atlas/v2/entity/guid/7").subscribe({ error: () => undefined });
        controller.match("/api/atlas/v2/entity/guid/7")[0].flush({}, { status: 500, statusText: "Server Error" });

        expect(alerts.alerts()).toHaveLength(1);
        expect(alerts.alerts()[0]).toMatchObject({ severity: "error" });
        expect(alerts.alerts()[0].message).toBe("Request failed: GET /api/atlas/v2/entity/guid/7 500");
    });

    it("reports a network failure (status 0) on /api (ALR-05)", () => {
        const { http, controller, alerts } = setup();

        http.get("/api/atlas/admin/status").subscribe({ error: () => undefined });
        controller.match("/api/atlas/admin/status")[0].flush(null, { status: 0, statusText: "Unknown Error" });

        expect(alerts.alerts()[0].message).toBe("Request failed: GET /api/atlas/admin/status no response");
    });

    it("names the server's message when it sends one (ALR-05)", () => {
        const { http, controller, alerts } = setup();

        http.post("/api/atlas/v2/entity", {}).subscribe({ error: () => undefined });
        controller.match("/api/atlas/v2/entity")[0].flush({ error: "no such type" }, { status: 500, statusText: "" });

        expect(alerts.alerts()[0].message).toBe("Request failed: POST /api/atlas/v2/entity 500: no such type");
    });

    it("keeps 4xx silent (ALR-05)", () => {
        const { http, controller, alerts } = setup();

        http.get("/api/atlas/v2/entity/guid/nope").subscribe({ error: () => undefined });
        controller.match("/api/atlas/v2/entity/guid/nope")[0].flush({}, { status: 404, statusText: "Not Found" });

        expect(alerts.alerts()).toHaveLength(0);
    });

    it("leaves non-/api calls alone (ALR-05)", () => {
        const { http, controller, alerts } = setup();

        http.get("/config.json").subscribe({ error: () => undefined });
        controller.match("/config.json")[0].flush({}, { status: 502, statusText: "Bad Gateway" });

        expect(alerts.alerts()).toHaveLength(0);
    });

    it("reports a 5xx on the lineage-model aux API (DD-392)", () => {
        const { http, controller, alerts } = setup();

        // The aux chain joined the reported set with 7.22b: the lineage box
        // stays silent by design (LDG-10, DD-392), so the drawer is where a
        // failed model call reads.
        http.get("/lineage-model/").subscribe({ error: () => undefined });
        controller.match("/lineage-model/")[0].flush({}, { status: 502, statusText: "Bad Gateway" });

        expect(alerts.alerts()).toHaveLength(1);
        expect(alerts.alerts()[0].message).toBe("Request failed: GET /lineage-model/ 502");
    });

    it("keeps a 4xx on the aux API silent too (ALR-05, DD-392)", () => {
        const { http, controller, alerts } = setup();

        http.get("/lineage-model/").subscribe({ error: () => undefined });
        controller.match("/lineage-model/")[0].flush({}, { status: 400, statusText: "Bad Request" });

        expect(alerts.alerts()).toHaveLength(0);
    });

    it("re-throws the failure untouched (ALR-05)", () => {
        const { http, controller } = setup();
        const errors: unknown[] = [];

        http.get("/api/x").subscribe({ error: (e) => errors.push(e) });
        controller.match("/api/x")[0].flush({}, { status: 503, statusText: "Unavailable" });

        expect(errors).toHaveLength(1);
        expect((errors[0] as { status: number }).status).toBe(503);
    });
});
