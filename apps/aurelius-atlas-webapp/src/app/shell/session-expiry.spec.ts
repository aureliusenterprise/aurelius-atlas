/**
 * The expired-session door (ALR-13): a `401` on a signed URL becomes one
 * `warning` alert and one interactive sign-in back to the page shown. A dead
 * session fails every in-flight call at once, so the sign-in must fire once.
 */
import { TestBed } from "@angular/core/testing";
import Keycloak from "keycloak-js";

import { AlertsService } from "../alerts/alerts.service";
import { SessionExpiry } from "./session-expiry";

function setup() {
    const login = vi.fn().mockResolvedValue(undefined);
    TestBed.configureTestingModule({
        providers: [{ provide: Keycloak, useValue: { login } }],
    });

    return {
        expiry: TestBed.inject(SessionExpiry),
        alerts: TestBed.inject(AlertsService),
        login,
    };
}

describe("SessionExpiry (ALR-13)", () => {
    it("warns and signs in to the page shown", () => {
        const { expiry, alerts, login } = setup();

        expiry.expired();

        expect(alerts.alerts()).toHaveLength(1);
        expect(alerts.alerts()[0]).toMatchObject({ severity: "warning" });
        expect(alerts.alerts()[0].message).toBe("Your session has expired. Signing you in again.");
        expect(login).toHaveBeenCalledTimes(1);
        expect(login).toHaveBeenCalledWith({ redirectUri: globalThis.location.href });
    });

    it("signs in only once, however many calls report the expiry", () => {
        const { expiry, alerts, login } = setup();

        // A dead session fails every in-flight call at once, so the door's own
        // flag must swallow the later reports (ALR-13).
        expiry.expired();
        expiry.expired();

        expect(login).toHaveBeenCalledTimes(1);
        expect(alerts.alerts()).toHaveLength(1);
    });
});
