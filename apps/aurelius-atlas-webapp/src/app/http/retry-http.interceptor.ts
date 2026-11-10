import { HttpErrorResponse, HttpInterceptorFn } from "@angular/common/http";
import { retry, throwError, timer } from "rxjs";

/**
 * The methods one resubscribe cannot duplicate (APC-12): the reads, and the
 * writes HTTP defines as idempotent, where a repeat lands on the same state.
 * POST stays out. A POST whose response died can already be applied, and a
 * blind second POST writes twice.
 */
const RETRYABLE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "PUT", "DELETE"]);

/** The gateway statuses: a proxy that could not reach its upstream (APC-12). */
const GATEWAY_STATUSES = new Set([502, 503, 504]);

/** The wait before the single retry, in ms: long enough to clear a closing socket. */
const RETRY_AFTER_MS = 150;

/**
 * Whether a failure means a dead wire rather than a refusal (APC-12).
 * Status 0 is the browser's "no response": uvicorn's 5 s keep-alive close
 * landing on the dev proxy's pooled socket, a proxy restart, a laptop
 * sleep. The gateway statuses are a proxy's own upstream-down answer.
 * A 4xx or a 500 is an answer the server chose, so it returns untouched.
 * @param error the failed call's error
 * @returns whether the transport died
 */
function isDeadConnection(error: unknown): error is HttpErrorResponse {
    return error instanceof HttpErrorResponse && (error.status === 0 || GATEWAY_STATUSES.has(error.status));
}

/**
 * The one-retry interceptor (APC-12, DD-449): an idempotent call that fails
 * on a dead connection is resent once, quietly, 150 ms later. It sits
 * innermost in the chain (APC-13), so the alerts reporter (ALR-05, DD-173)
 * and the OTel interceptor (SHL-14) see only the outcome after the retry. A
 * call the second attempt saves never reaches the drawer.
 *
 * The race it retires: uvicorn closes an idle keep-alive connection after 5
 * s (its default), the dev proxy's pooled agent can write a request into the
 * socket that is closing, and the browser reads the truncated answer as
 * `ERR_CONTENT_LENGTH_MISMATCH`, which arrives as a status-0 error. The
 * editor's typedefs call lands there when a drawer opens a few seconds
 * after the page load, and the form renders without its fields. Reproduced
 * against :21000 on 2026-11-10: a reused connection failed every time
 * between 5.0 s and 8.0 s of idle, and back-to-back requests never failed.
 */
export const retryHttpInterceptor: HttpInterceptorFn = (req, next) => {
    if (!RETRYABLE_METHODS.has(req.method.toUpperCase())) {
        return next(req);
    }

    return next(req).pipe(
        retry({
            count: 1,
            // `delay` decides per failure: a dead wire waits and resubscribes.
            // Any other error throws here, so the outer stream ends with it,
            // unchanged for the caller.
            delay: (error) => (isDeadConnection(error) ? timer(RETRY_AFTER_MS) : throwError(() => error)),
        }),
    );
};
