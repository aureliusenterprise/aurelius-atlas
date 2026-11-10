# 7.26 HTTP retry: the editor race and its class

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-449 (the retry interceptor, its set, and its place in the
  chain); DV-145 (the retry is Aurelius behaviour, not Atlas's). Relies on
  DD-173 (the alerts reporter, unchanged), APC-04 (the failure contract),
  APC-06 (the bearer interceptor, unchanged), APC-08 (the dev proxy path).

## Scope

The browser's HTTP client resends a failed call once when the failure means
the connection died rather than a refusal. One interceptor covers every
`HttpClient` call (APC-12), and its place in the chain is fixed (APC-13).

The report that opened it: the entity editor drawer sometimes opens without
its attribute fields. The cause is a connection race, not the drawer. The
server (uvicorn) closes an idle keep-alive connection after 5 s (its
default). The dev proxy's pooled agent can write the next request into the
socket that is closing, and the browser reads the truncated answer as
`ERR_CONTENT_LENGTH_MISMATCH`, which arrives as a status-0 error. The
typedefs call lands there when a drawer opens a few seconds after the page
load, so `loadTypeDefs` fails, its signal stays null, and the form resolves
zero fields. Reproduced against the dev server on 2026-11-10: a reused
connection failed every retry between 5.0 s and 8.0 s of idle, and
back-to-back requests never failed.

This increment does not change the server. Raising uvicorn's
`timeout_keep_alive` above the proxy's reuse window is the other half, and
the server increment that owns `__main__.py` takes it; the interceptor is
the half that also covers proxy restarts and every other dead wire.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| APC-12 | An `HttpClient` call whose method is idempotent (GET, HEAD, OPTIONS, PUT, DELETE) and whose failure is a dead connection (status 0, or a 502/503/504) is resent once, after a 150 ms wait. A POST is never resent: a POST whose response died can already be applied, and a second POST writes twice. A 4xx or a 500 is an answer the server chose and passes through untouched. After the one resend, the second failure reaches the caller unchanged. |
| APC-13 | The retry interceptor is innermost in the chain. The alerts reporter (ALR-05) and the OTel interceptor (SHL-14) observe only the outcome after the retry: a call the resend saves produces no alert and no failed span, and a call that fails twice still produces its one alert.                                                                                                                                                                       |

## Java origin

Nothing in Apache Atlas retries here. The legacy stack talks to a Jersey
container through no proxy hop, and its Angular client does not retry. The
race is a property of this deployment (dev proxy → TLS uvicorn) rather than
a ported behaviour.

## Deviations

DV-145: the browser resends an idempotent failed call once. Atlas 2.4.0's
client never resends.

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/http/retry-http.interceptor.spec.ts` —
  the APC-12 matrix: the saved GET, the saved 502, the give-up after one
  resend, the untouched POST, the untouched 404/500, the resent DELETE.
- `apps/aurelius-atlas-webapp/src/app/app.config.spec.ts` — the APC-13 pins
  through the real chain: a status-0 failure the retry saves reaches the
  caller with no alert, and a twice-failed call still alerts once.
- Run: `npx nx test aurelius-atlas-webapp -c ci`.
