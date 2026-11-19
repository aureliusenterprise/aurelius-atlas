import { HttpErrorResponse, HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { catchError, throwError } from "rxjs";

import { SessionExpiry } from "../shell/session-expiry";
import { AlertsService } from "./alerts.service";

/**
 * The same shape the bearer interceptor keys on (APC-06): the Atlas API and
 * the lineage-model aux API. The aux chain belongs in the drawer too — a
 * failed lineage fetch stays invisible on the box by design (LDG-10,
 * DD-392), so the drawer is where its 5xx reads.
 */
const REPORTED_URL = /\/api\/|\/lineage-model\//;

/**
 * The URLs that carry a bearer token — `bearerTokenConfig` (APC-06, app.config).
 * A `401` on one of these is an expired session, not a client error, so the
 * set here mirrors that config exactly: the validate-entity call signs its
 * request too, and a dead session fails it the same way (ALR-13, DD-706).
 */
const BEARER_URL = /\/api\/|\/lineage-model\/|\/validate-entity\//;

/**
 * The HTTP error reporter (ALR-05, DD-173; the aux chain joined by DD-392):
 * a failed `/api` or `/lineage-model` call becomes an error alert — the
 * `5xx` responses and the network failures (status 0, a request that never
 * got a response). `4xx` stays silent: a client
 * error is the calling feature's own business (its form validation, its
 * not-found handling), and reporting it here would train users to
 * ignore the drawer. The one exception is a `401` on a signed URL: the silent
 * refresh already failed (APC-07), so that call opens the sign-in again door
 * (ALR-13). The interceptor reports and re-throws; it changes
 * nothing about the response the caller sees.
 *
 * The message names the method, the path, and the status (or "no
 * response"); the store's window grouping (ALR-03) folds a flapping
 * endpoint's repeated 500s into one burst, so the drawer stays readable.
 */
export const alertsHttpInterceptor: HttpInterceptorFn = (req, next) => {
    const alerts = inject(AlertsService);
    const expiry = inject(SessionExpiry);

    return next(req).pipe(
        catchError((error: unknown) => {
            if (REPORTED_URL.test(req.url) && isReportable(error)) {
                alerts.add({ severity: "error", message: describe(req.method, req.url, error), source: "http" });
            } else if (isExpiredSession(error) && BEARER_URL.test(req.url)) {
                // A 401 on a signed call: the session is gone and the silent
                // refresh failed (APC-07), so sign in again (ALR-13, DD-706).
                // The call is not retried here — the caller's own error path
                // still runs, and the redirect leaves the page anyway.
                expiry.expired();
            }
            return throwError(() => error);
        }),
    );
};

/**
 * Whether a failed call earns an alert (ALR-05): a server `5xx` or a
 * network failure (`HttpErrorResponse` with status 0). A thrown
 * non-response (a bug in the caller) is not an HTTP failure and stays
 * out — the runtime `ErrorHandler` (ALR-04) is its door.
 * @param error the failed call's error
 * @returns whether to report it
 */
function isReportable(error: unknown): error is HttpErrorResponse {
    return error instanceof HttpErrorResponse && (error.status === 0 || error.status >= 500);
}

/**
 * Whether a failed call is an expired session (ALR-13): exactly `401`, and a
 * response rather than a thrown non-response. `403` is not — the session is
 * alive and the user simply lacks the right, which is the calling feature's
 * own business (ALR-05's rule for `4xx`).
 * @param error the failed call's error
 * @returns whether to start a sign-in again
 */
function isExpiredSession(error: unknown): error is HttpErrorResponse {
    return error instanceof HttpErrorResponse && error.status === 401;
}

/**
 * The alert's message: method, path, status (ALR-05). The server's
 * message rides when it sent a plain one.
 * @param method the request method
 * @param url the request URL (the path the user can read)
 * @param error the reportable response
 * @returns the message
 */
function describe(method: string, url: string, error: HttpErrorResponse): string {
    const status = error.status === 0 ? "no response" : String(error.status);
    const server = typeof error.error?.error === "string" ? `: ${error.error.error}` : "";

    return `Request failed: ${method} ${url} ${status}${server}`;
}
