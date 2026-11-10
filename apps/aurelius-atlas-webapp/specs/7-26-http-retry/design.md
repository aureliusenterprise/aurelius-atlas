# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-449. The browser resends a dead-connection failure once, innermost

- **Status:** Proposed
- **Increment:** 7.26
- **Date:** 2026-11-10

**Decision.** One `HttpInterceptorFn` (`src/app/http/retry-http.interceptor.ts`)
resends a failed call once, after 150 ms, when both guards pass. The method
must be idempotent (GET, HEAD, OPTIONS, PUT, DELETE). The failure must mean
a dead wire: status 0, or a 502/503/504. It sits innermost in the
`withInterceptors` chain, past the OTel, bearer, and alerts interceptors
(APC-12, APC-13).

**Reason.** The editor drawer opened without its attribute fields while the
tour ran (2026-11-10): the browser logged
`ERR_CONTENT_LENGTH_MISMATCH` on `GET /api/atlas/v2/types/typedefs`,
`loadTypeDefs` took its error path, and the form resolved zero fields. The
race is between uvicorn's 5 s keep-alive close and the pooled socket of the
dev proxy's HTTP agent: a request written into a closing socket comes back
truncated, which the browser reports as a status-0 error. A raw client
against the dev server failed every reuse at 5.0 s to 8.0 s of idle and
never failed back-to-back. The fix at the server (a longer
`timeout_keep_alive`) closes this one race; the class is wider — proxy
restarts, a laptop waking, a gateway's flapping upstream. Every one of them
reads as the same status-0 or gateway error, and every Atlas read the
webapp makes is idempotent, so a single resend is safe and turns a visible
failure (an alert, an empty form) into nothing. POST stays out for the one
case a retry cannot judge: a POST whose response died may already be
applied, and Atlas entity writes have no idempotency key. The chain place
carries the rest of the contract: inside the alerts reporter, a call the
resend saves never reaches the drawer (ALR-05's alert stays a true failure),
and inside the OTel interceptor the span records the outcome the user saw.
RxJS `retry` with a `delay` predicate is the one operator that both decides
per failure and resubscribes, so the interceptor holds no state.

**Alternatives.** Raise uvicorn's `timeout_keep_alive` and ship nothing in
the browser. It fixes the measured race and leaves every other dead wire at
the alert drawer; it also belongs to a server increment, and the webapp
should not wait on one. Retry POST too. Refused: the save button is the one
path where a duplicate write is worse than the alert. Retry at the data
access services instead of the interceptor. Refused: it repeats the policy
per service and misses the calls that go through `HttpClient` directly
(`app.config.ts` reads `/config.json` itself). The `@angular/common/http`
retry-per-request option does not exist; an interceptor is the seam.

**Consequences.** A flapping endpoint produces no alert for a failure the
resend saves, and one alert for a failure that survives — the drawer stays
honest. The OTel span for a saved call is one span with a late 200, which
is what the user experienced. A twice-failed call costs two requests, then
behaves exactly as before (APC-04, ALR-05). The server-side knob stays
worth turning where a server increment next touches `__main__.py`; the two
fixes are independent. The 150 ms wait is one frame rounded up — long
enough for the proxy to notice its dead socket, short enough that no
loading bar changes.
