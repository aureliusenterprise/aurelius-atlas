/**
 * The error-handler chain (ALR-04): the app's handler records the alert
 * and delegates to the trace handler — telemetry untouched. The chain
 * composition is the rule under test, so the delegate is a spy.
 */
import { TestBed } from "@angular/core/testing";

import { AlertsErrorHandler } from "./alerts-error-handler";
import { AlertsService } from "./alerts.service";

describe("AlertsErrorHandler (ALR-04)", () => {
    let alerts: AlertsService;
    let delegate: { handleError(error: unknown): void };
    let handler: AlertsErrorHandler;

    beforeEach(() => {
        TestBed.configureTestingModule({ providers: [AlertsService] });
        alerts = TestBed.inject(AlertsService);
        delegate = { handleError: vi.fn() };
        handler = new AlertsErrorHandler(alerts, delegate);
    });

    it("records an error alert (ALR-04)", () => {
        handler.handleError(new Error("boom"));

        // The public feed carries the row's fields; the grouping source
        // (`app`) is the store's internal key, not part of the row.
        expect(alerts.alerts()).toHaveLength(1);
        expect(alerts.alerts()[0]).toMatchObject({ severity: "error", message: "boom" });
    });

    it("spells a thrown non-Error (ALR-04)", () => {
        handler.handleError("kaput");

        expect(alerts.alerts()[0].message).toBe("kaput");
    });

    it("delegates to the trace handler, always (ALR-04)", () => {
        handler.handleError(new Error("boom"));

        expect(delegate.handleError).toHaveBeenCalledWith(expect.any(Error));
    });

    it("delegates even when recording fails (ALR-04)", () => {
        // A store that throws must not swallow the error path (telemetry,
        // then Angular's default, keep running).
        vi.spyOn(alerts, "add").mockImplementation(() => {
            throw new Error("store down");
        });

        expect(() => handler.handleError(new Error("boom"))).not.toThrow();
        expect(delegate.handleError).toHaveBeenCalled();
    });
});
