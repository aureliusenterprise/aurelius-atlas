import { HttpErrorResponse, HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { catchError, throwError } from "rxjs";

import { AlertsService } from "./alerts.service";

/** The same shape the bearer interceptor keys on (APC-06): the Atlas API. */
const API_URL = /\/api\//;

/**
 * The HTTP error reporter (ALR-05, DD-085): a failed `/api` call becomes
 * an error alert — the `5xx` responses and the network failures (status
 * 0, a request that never got a response). `4xx` stays silent: a client
 * error is the calling feature's own business (its form validation, its
 * not-found handling), and reporting it here would train users to
 * ignore the drawer. The interceptor reports and re-throws; it changes
 * nothing about the response the caller sees.
 *
 * The message names the method, the path, and the status (or "no
 * response"); the store's window grouping (ALR-03) folds a flapping
 * endpoint's repeated 500s into one burst, so the drawer stays readable.
 */
export const alertsHttpInterceptor: HttpInterceptorFn = (req, next) => {
    const alerts = inject(AlertsService);

    return next(req).pipe(
        catchError((error: unknown) => {
            if (API_URL.test(req.url) && isReportable(error)) {
                alerts.add({ severity: "error", message: describe(req.method, req.url, error), source: "http" });
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
