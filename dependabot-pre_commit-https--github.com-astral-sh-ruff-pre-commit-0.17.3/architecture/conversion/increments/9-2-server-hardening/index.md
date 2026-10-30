# 9.2 Server hardening: TLS, error detail, security headers

- **Status:** in progress
- **Pull request:** [\#154](<https://github.com/aureliusenterprise/aurelius-atlas/pull/154>)
- **Records:** DD-234, DD-235, DD-236; DV-85, DV-86; supersedes parts of SRV-03 and SRV-04 (0.5)

## Scope

The server's own attack surface, closed at the edges a pentest named (H3, M5, L1):

- **TLS is a start-up requirement**: the certificate/key pair joins the settings that have no default, so the server can never serve plaintext (SRV-06, [DD-234](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-astral-sh-ruff-pre-commit-0.17.3/architecture/conversion/design-log/#dd-234--tls-material-is-a-required-setting-the-server-never-serves-plaintext>)); the image's healthcheck speaks HTTPS accordingly.
- **A 5xx answer is opaque**: no exception text on the wire, a trace-id request id on the body and a header for support correlation (SRV-07, [DD-235](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-astral-sh-ruff-pre-commit-0.17.3/architecture/conversion/design-log/#dd-235--a-5xx-answer-is-opaque-and-carries-the-trace-id-as-requestid>)).
- **Security response headers** on every answer, split API/dashboard, HSTS with a dev escape (SRV-08, [DD-236](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-astral-sh-ruff-pre-commit-0.17.3/architecture/conversion/design-log/#dd-236--security-response-headers-are-a-pure-asgi-middleware-split-on-api-path>)).

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| API authentication, per-change attribution | 6.1 (separate PR track) |
| CSRF enforcement (the session's `_csrfToken` stays a parity field) | the CSRF increment (ADM-06) |
| Rate limiting, client-IP trust (`forwarded_allow_ips`) | the search-cost increment |
| CSP nonces for the legacy dashboards (hashes churn — DV-86) | the dashboard retirement (6.3) |

## Semantics

| Id | Rule |
| --- | --- |
| SRV-06 | The server serves HTTPS, always: `TLS_CERT_FILE` and `TLS_KEY_FILE` are required settings (SRV-01 idiom) and a missing one stops start-up naming it — the both-or-neither rule of SRV-03 is superseded because the "neither" arm no longer exists |
| SRV-07 | An Atlas error of status 500+ answers with `{"errorCode": ..., "errorMessage": ...}` and never an `errorCause` (superseding SRV-04's cause echo for 5xx only); the cause is logged, and the answer carries the current trace id as `requestId` in the body and `X-Request-Id` in the headers. 4xx answers keep SRV-04 unchanged |
| SRV-08 | Every response carries security headers: `/api/**` gets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a `Permissions-Policy`, `Cache-Control: no-store` and a CSP that serves no documents; the dashboard documents get a same-origin CSP that allows the legacy app's inline bootstrap and runtime template compilation (DV-86) with `object-src`/`base-uri`/`frame-ancestors` closed, and `X-Frame-Options: SAMEORIGIN`; dashboard assets served with a `bust=` query get immutable cache headers; `Strict-Transport-Security` is sent when `HSTS_ENABLED` (default true, off in the dev arrangement, ADR 039) |

## Java origin

Apache Atlas 2.4.0 has no security-header filter to port — the headers are Aurelius hardening. The rule that changes Atlas behaviour is SRV-07: `AtlasBaseExceptionMapper` echoes `exception.getMessage()` into `errorCause` on every status, including 5xx (the echo Aurelius keeps for 4xx, DV-85).

## Deviations

- [DV-85](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-astral-sh-ruff-pre-commit-0.17.3/architecture/conversion/deviations/index.md>): 5xx answers drop the `errorCause` echo, adding `requestId`.
- [DV-86](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-astral-sh-ruff-pre-commit-0.17.3/architecture/conversion/deviations/index.md>): the dashboard CSP allows inline and eval'd scripts — the vendored bootstrap inlines a build-varying `bust` value (hashes are not stable) and the require-handlebars-plugin compiles templates at runtime with `new Function` (the e2e dashboard boot is the regression guard).

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_settings.py` — the missing-TLS test names the setting (SRV-06, mirroring the SRV-01 test); `test__aurelius_atlas_server___main__.py` — uvicorn always gets the ssl pair.
- `tests/test__aurelius_atlas_server_errors.py` — 5xx opaque + requestId, 4xx echo kept (SRV-07); `tests/test__aurelius_atlas_server_admin.py` — readiness 500 carries `requestId` + header.
- `tests/test__aurelius_atlas_server_security_headers.py` — API headers, 404 headers, dashboard CSP, bust-asset immutable cache, HSTS off (SRV-08).
- Existing parity scenarios stay green unchanged: the runner checks expected response headers only, so additive headers cannot fail them (ADR 052).
- `nx e2e aurelius-atlas-server` — the scenarios over HTTPS against the image; a bare `docker run` of the image without mounted material fails at start-up naming the setting.
