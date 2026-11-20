/**
 * The HTTP error reporter (ALR-05): the interceptor's rules are the
 * reportable set (5xx and network failures on /api and the /lineage-model
 * aux API, never 4xx), the message's shape (method, path, status), and the
 * untouched re-throw. The store's grouping of the resulting alerts is
 * specced at the store. A 401 on a signed URL is the expired-session door
 * (ALR-13): a warning plus one sign-in, so the Keycloak client is stubbed.
 */
import { HttpClient, provideHttpClient, withInterceptors } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import Keycloak from "keycloak-js";

import { AlertsService } from "./alerts.service";
import { alertsHttpInterceptor } from "./alerts-http.interceptor";

function setup() {
    const login = vi.fn().mockResolvedValue(undefined);
    TestBed.configureTestingModule({
        providers: [
            provideHttpClient(withInterceptors([alertsHttpInterceptor])),
            provideHttpClientTesting(),
            { provide: Keycloak, useValue: { login } },
        ],
    });

    return {
        http: TestBed.inject(HttpClient),
        controller: TestBed.inject(HttpTestingController),
        alerts: TestBed.inject(AlertsService),
        login,
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

    it("signs in again on a 401 from /api (ALR-13)", () => {
        const { http, controller, alerts, login } = setup();

        // The silent refresh runs before sending (APC-07), so a 401 is a dead
        // session: the drawer warns once and login() returns to this page.
        http.get("/api/atlas/v2/entity/guid/7").subscribe({ error: () => undefined });
        controller.match("/api/atlas/v2/entity/guid/7")[0].flush({}, { status: 401, statusText: "Unauthorized" });

        expect(alerts.alerts()).toHaveLength(1);
        expect(alerts.alerts()[0]).toMatchObject({ severity: "warning" });
        expect(alerts.alerts()[0].message).toBe("Your session has expired. Signing you in again.");
        expect(login).toHaveBeenCalledTimes(1);
        expect(login).toHaveBeenCalledWith({ redirectUri: globalThis.location.href });
    });

    it("signs in again only once for a burst of 401s (ALR-13)", () => {
        const { http, controller, alerts, login } = setup();

        // A dead session fails every in-flight call at once; one bounce, one alert.
        http.get("/api/a").subscribe({ error: () => undefined });
        http.get("/api/b").subscribe({ error: () => undefined });
        controller.match("/api/a")[0].flush({}, { status: 401, statusText: "Unauthorized" });
        controller.match("/api/b")[0].flush({}, { status: 401, statusText: "Unauthorized" });

        expect(login).toHaveBeenCalledTimes(1);
        expect(alerts.alerts()).toHaveLength(1);
    });

    it("signs in again for a 401 on the lineage-model aux API (ALR-13)", () => {
        const { http, controller, login } = setup();

        // The set mirrors bearerTokenConfig (APC-06).
        http.get("/lineage-model/").subscribe({ error: () => undefined });
        controller.match("/lineage-model/")[0].flush({}, { status: 401, statusText: "Unauthorized" });

        expect(login).toHaveBeenCalledTimes(1);
    });

    it("signs in again for a 401 on the validate-entity aux API (ALR-13)", () => {
        const { http, controller, login } = setup();

        // The third bearer URL, which REPORTED_URL left out of the 5xx set.
        http.post("/validate-entity/", {}).subscribe({ error: () => undefined });
        controller.match("/validate-entity/")[0].flush({}, { status: 401, statusText: "Unauthorized" });

        expect(login).toHaveBeenCalledTimes(1);
    });

    it("keeps a 401 on an unsigned URL silent (ALR-13)", () => {
        const { http, controller, alerts, login } = setup();

        // /config.json carries no token, so a 401 there is not a session loss.
        http.get("/config.json").subscribe({ error: () => undefined });
        controller.match("/config.json")[0].flush({}, { status: 401, statusText: "Unauthorized" });

        expect(alerts.alerts()).toHaveLength(0);
        expect(login).not.toHaveBeenCalled();
    });

    it("keeps a 403 silent (ALR-13)", () => {
        const { http, controller, alerts, login } = setup();

        // The session is alive; a missing right is the feature's business (ALR-05).
        http.get("/api/atlas/v2/entity").subscribe({ error: () => undefined });
        controller.match("/api/atlas/v2/entity")[0].flush({}, { status: 403, statusText: "Forbidden" });

        expect(alerts.alerts()).toHaveLength(0);
        expect(login).not.toHaveBeenCalled();
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

    it("keeps a 4xx other than 401 on the aux API silent too (ALR-05, DD-392)", () => {
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
