import { ErrorHandler, inject } from "@angular/core";
import { AureliusTraceErrorHandler } from "aurelius-atlas-observability";

import { AlertsService } from "./alerts.service";

/**
 * The app's `ErrorHandler` (ALR-04, DD-172): an uncaught runtime error
 * becomes an alert, and the chain then hands the error to the
 * OpenTelemetry handler — SHL-14's telemetry is untouched, the alert is
 * appended, not substituted. Recording is guarded: alerting must never
 * break the app's error path (the same rule the trace handler keeps
 * against telemetry).
 *
 * It is wired in `app.config.ts` as the composed root handler
 * (`new AlertsErrorHandler(alerts, new AureliusTraceErrorHandler())`),
 * the same composition the trace handler itself keeps against
 * Angular's default.
 */
export class AlertsErrorHandler implements ErrorHandler {
    constructor(
        private readonly alerts: AlertsService,
        private readonly delegate: ErrorHandler,
    ) {}

    /**
     * Record the error as an alert (source `app`), then delegate.
     * @param error the uncaught value, of any shape
     */
    handleError(error: unknown): void {
        try {
            this.alerts.add({ severity: "error", message: describe(error), source: "app" });
        } catch {
            // Alerting is best-effort: the delegate must run regardless.
        }
        this.delegate.handleError(error);
    }
}

/**
 * The alert's message for a thrown value: the Error's message, else the
 * value spelled out (a thrown string is a real pattern; `[object
 * Object]` is not, so stringification is explicit).
 * @param error the thrown value
 * @returns a one-line message
 */
function describe(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

/**
 * The factory the app's provider uses: the alerts handler on top of the
 * trace handler (ALR-04). Kept as a function so the composition reads
 * as the chain it is.
 * @returns the composed root handler
 */
export function alertsErrorHandlerFactory(): ErrorHandler {
    return new AlertsErrorHandler(inject(AlertsService), new AureliusTraceErrorHandler());
}
