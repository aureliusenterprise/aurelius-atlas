# 0.5 Server skeleton

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-015, DD-016; DV-03, DV-04, DV-05; relies on ADR 052, DD-001, DD-002

## Scope

The Aurelius Atlas server exists and answers the admin endpoints that tell a client, a load balancer or the dashboard whether Atlas is there and how it is configured.

- **`apps/aurelius-atlas-server`** (`aurelius_atlas_server`), a FastAPI application:

  - settings read once at start-up, the Elasticsearch store opened for the server's lifetime;
  - the Atlas error body and JSON media type, shared by every later endpoint;
  - `GET /api/atlas/admin/version`, `/status`, `/session`, `/liveness` and `/readiness`;
  - a container image, `nx serve` against the dev store, and `nx e2e` running the scenarios against the image over HTTPS.
- **Parity scenarios** for the five endpoints in `apps/aurelius-atlas-server/scenarios/admin/`, run in-process by the unit tests and over HTTPS by the end-to-end tests.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| The dashboards at `/` and `/n/` | 0.6 |
| Removing the template's example projects | 0.7 |
| Authentication; the session's user, groups and permissions | 6.1, 6.2 |
| Metrics (`/admin/metrics`) and the other admin endpoints | 6.4 and the increments that own them |
| High availability states (`PASSIVE`, `BECOMING_ACTIVE`, …) | not planned |

## Semantics

### The server

| Id | Rule |
| --- | --- |
| SRV-01 | Settings are read once at start-up from environment variables prefixed `AURELIUS_ATLAS_SERVER_`; a missing or invalid setting stops the start-up and names the setting |
| SRV-02 | The server opens the Elasticsearch store before it accepts requests and does not start when the store cannot be opened; it closes the store when it stops |
| SRV-03 | The server listens on port 21000 unless configured otherwise, and serves HTTPS when both a certificate and a key are configured; configuring only one is an error |
| SRV-04 | An Atlas error is answered with its HTTP status and the body `{"errorCode": ..., "errorMessage": ...}`, plus `errorCause` when the error has a cause |
| SRV-05 | JSON responses of the Atlas API carry the media type `application/json; charset=UTF-8` |

### The admin endpoints

| Id | Rule |
| --- | --- |
| ADM-01 | `GET /api/atlas/admin/version` answers 200 with `Version`, `Revision`, `Name` and `Description`; Aurelius Atlas names itself and its own release and revision (DV-03) |
| ADM-02 | `GET /api/atlas/admin/status` answers 200 with `{"Status": "ACTIVE"}` while the server runs |
| ADM-03 | `GET /api/atlas/admin/liveness` answers 200 with the text `Service is live` while the server runs |
| ADM-04 | `GET /api/atlas/admin/readiness` answers 200 with the text `Service is ready to accept requests` when the store is healthy, and otherwise 500 with error `ATLAS-500-00-001` and message `Internal server error Service not ready to accept client requests` |
| ADM-05 | `GET /api/atlas/admin/session` answers 200 with the user interface settings of Atlas 2.4.0 at their defaults, `userName` null, `groups` empty and both entity permissions false (DV-04), the time zone ids (DV-05) and a `_csrfToken` of 20 letters and digits |

Rules ADM-01 to ADM-05 are those of `AdminResource`; their parity scenarios cite it method by method. SRV-02 makes a server that cannot reach its only store fail at start-up rather than answer every request with an error ([DD-016](<https://aureliusenterprise.github.io/main/architecture/conversion/design-log/#dd-016-the-server-does-not-start-without-its-store>)); the application layout is [DD-015](<https://aureliusenterprise.github.io/main/architecture/conversion/design-log/#dd-015-the-server-is-a-fastapi-application-with-one-router-per-atlas-resource>).

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/resources/AdminResource.java`: `getVersion`, `getStatus`, `getUserProfile`, `serviceLiveliness`, `serviceReadiness`, the session defaults in the constructor
- `webapp/.../web/errors/AtlasBaseExceptionMapper.java`: the error body
- `intg/.../AtlasErrorCode.java`: `INTERNAL_ERROR`
- `webapp/.../web/util/Servlets.java`: `JSON_MEDIA_TYPE`
- `webapp/.../web/filters/AtlasCSRFPreventionFilter.java`: the CSRF defaults the session reports
- `intg/.../AtlasConfiguration.java`: the defaults of the session's feature switches

## Deviations

- [DV-03](<https://aureliusenterprise.github.io/main/architecture/conversion/deviations/index.md>): `version` reports Aurelius Atlas, not Apache Atlas.
- [DV-04](<https://aureliusenterprise.github.io/main/architecture/conversion/deviations/index.md>): no authentication until 6.1; the session has no user.
- [DV-05](<https://aureliusenterprise.github.io/main/architecture/conversion/deviations/index.md>): the session's time zone ids come from the IANA database.

## Acceptance

- `apps/aurelius-atlas-server/scenarios/admin/` — one scenario per endpoint, citing `AdminResource`.
- `apps/aurelius-atlas-server/tests/` — the scenarios in-process (ADM-01 to ADM-05), settings and start-up (SRV-01 to SRV-03), errors and media type (SRV-04, SRV-05), readiness with a store that is down (ADM-04).
- `apps/aurelius-atlas-server/e2e/` — the same scenarios over HTTPS against the container image connected to the dev store (`nx e2e aurelius-atlas-server`).
