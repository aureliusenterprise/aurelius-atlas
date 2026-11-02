# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-234. TLS material is a required setting; the server never serves plaintext

- **Status:** Accepted
- **Increment:** 9.2
- **Date:** 2026-10-27

**Decision.** `TLS_CERT_FILE` and `TLS_KEY_FILE` become required settings with no
default, joining the store endpoints/password/CA in the SRV-01/SRV-02 idiom: a
missing one stops start-up with a pydantic error naming the field. The
both-or-neither pair check is deleted — the "neither" arm no longer exists — and
`ServerSettings.tls` always returns the pair. `uvicorn_options` always carries
`ssl_certfile`/`ssl_keyfile`. The image bakes `ENV` defaults pointing at
`/certs/server.pem` / `/certs/server-key.pem` (DD-216's stack-owned mount), and
its healthcheck speaks HTTPS with CA verification. SRV-06 supersedes the second
sentence of SRV-03.

**Reason.** ADR 039 states TLS is the only serving mode, and every deployment
arrangement (dev, e2e, CI, the compose stacks) already supplies the pair —
plaintext is reachable only by misconfiguration, and a pentest (H3) counts a
plaintext listener as the finding it is. Making the setting required turns the
deployment's silent failure mode (an HTTP listener answering where HTTPS was
expected) into a start-up error that names itself, which is how every other
required setting already behaves.

**Alternatives.** (a) Keep the pair rule and fail when both are unset — refused:
"unset is valid" is the whole hole; it also keeps a dead code path (plaintext
uvicorn options) in `__main__`. (b) Terminate TLS at the proxy and serve
plaintext on loopback — refused: ADR 039's store-side pinning applies equally
server-side, the e2e/dashboards ride the server's own HTTPS, and a loopback-only
assumption is unenforceable inside a shared pod network. (c) Self-signed
material generated at start-up when unset — refused: silently untrusted
material is the failure mode users report as "the browser blocks the site",
and start-up crypto is the anti-pattern DD-216 removed for the stacks.

**Consequences.** Unit tests supply a stub pair (the `tls_pair` fixture;
`FilePath` validates existence, uvicorn never starts under test). A bare
`docker run` of the image without a mounted pair fails at start-up naming
`AURELIUS_ATLAS_SERVER_TLS_CERT_FILE` — the design working, documented as such.
The healthcheck no longer has a plaintext branch. Next free DD: 235.

### DD-235. A 5xx answer is opaque and carries the trace id as `requestId`

- **Status:** Accepted
- **Increment:** 9.2
- **Date:** 2026-10-27

**Decision.** `atlas_error_handler` stops echoing `errorCause` for a 5xx: the
body keeps `errorCode`/`errorMessage`, the cause's text goes only to the log (as
`exc_info`, as before), and the answer gains the current OTel trace id — 32-hex
`requestId` in the body, `X-Request-Id` in the headers — so a user's screenshot
correlates to the logged stack trace and the trace. 4xx answers keep SRV-04's
cause echo; Atlas's own validation messages are client-facing and the parity
scenarios pin them. DV-85 records the deviation from `AtlasBaseExceptionMapper`.

**Reason.** Pentest M5: the 5xx echo leaks internals (store URLs, index names,
exception classes from the ES client) to any caller who can trigger a server
fault — readiness against a downed store leaks the store URI. Atlas echoes
because its own logs were the only consumer of its UI's error dialogs; Aurelius
ships the whole OTel pipeline, so a trace id is the correlation key the support
flow needs, and the body stays Atlas's shape for every field the scenarios pin.

**Alternatives.** (a) Env flag for verbose errors — refused: an always-on
leak-by-default with a mitigation nobody enables; DD-016's fail-loud philosophy
is loud in the log, not on the wire. (b) Random per-request uuid as the id —
refused: the logs carry the trace id already (structlog/OTel), a random id
correlates to nothing. (c) Suppress 4xx causes too — refused: they are
parity-pinned client-facing messages (`UNKNOWN_TYPENAME`, validation detail).

**Consequences.** The client model's `errorCause` stays optional (4xx fills it).
In-process tests have recording spans (instrumented app + SDK provider), so
`requestId` is assertable; when telemetry is off the field is simply absent.
The header is additive, so parity scenarios (expected-response headers only) are
unaffected. Next free DD: 236.

### DD-236. Security response headers are a pure-ASGI middleware split on `/api` path

- **Status:** Accepted
- **Increment:** 9.2
- **Date:** 2026-10-27

**Decision.** One pure-ASGI `SecurityHeadersMiddleware`, added first in
`create_app` so it wraps routers, mounts, and the exception handler. `/api/**`
answers (by path prefix, so error and 404 answers are covered) get
`nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a
`Permissions-Policy`, `Cache-Control: no-store`, and a CSP that serves no
documents (`default-src 'none'; base-uri 'none'; frame-ancestors 'none'`). The
dashboard documents get a same-origin CSP with `'unsafe-inline'` +
`'unsafe-eval'` scripts and `'unsafe-inline'` styles (DV-86: the vendored
`index.html.tpl` inlines the build-varying bust value, and the
require-handlebars-plugin compiles templates at runtime with `new Function` —
the e2e dashboard boot is the regression guard; what CSP does enforce there is
`object-src`/`base-uri`/`frame-ancestors` closed and same-origin sources) and
`SAMEORIGIN` framing; assets fetched with the legacy `?bust=` get
`public, max-age=31536000, immutable` (the bust param is the legacy's own
content-versioning; HTML is excluded so a stale page cannot pin itself). HSTS
(max-age 1y, includeSubDomains) rides every answer when `hsts_enabled` —
default true, false in the dev `.env` (ADR 039's named dev relaxations: the
mkcert CA is not browser-trusted, and localhost must not pin). SRV-08.

**Reason.** Pentest L1: clickjacking on the dashboard, MIME sniffing on API
answers, cacheable API JSON, and a missing HSTS policy. A pure-ASGI stamp on
`http.response.start` reaches every response path — including the exception
handler's `JSONResponse` and static-file answers — where `BaseHTTPMiddleware`
wraps streaming awkwardly and StaticFiles bypasses route-level answers.

**Alternatives.** (a) nginx-terminated headers — refused: the server answers
directly in e2e and any deployment without the webapp proxy; headers belong to
the origin. (b) Strict CSP with hashes/nonces for the dashboards — refused for
now: the vendored `index.html.tpl` inline bootstrap inlines the build-varying
`<%- bust %>` value, so hashes churn per build (DV-86); the dashboard
retirement (6.3) removes the surface. (c) starlette `CORSMiddleware`/`GZip`
stacking — refused: none of them set these headers; this is one small
middleware, not a framework feature.

**Consequences.** Header tests cover API, 404, dashboard, bust-asset and
HSTS-off answers. The parity runner compares expected response headers only, so
additive headers keep every scenario green. The dev compose stacks carry
`HSTS_ENABLED=false` explicitly (e2e images do not read `.env`). Next free DD: 237.
