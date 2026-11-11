# aurelius-atlas-quality-scanner

The batch quality scanner of increment 12.2. This file covers wiring specific to this app;
workspace-wide rules, including the conversion workflow, live in the root `AGENTS.md`.

## Layout

The job is a CLI, not a service: one process per scan, no HTTP router, no port (DQS-01).

- `aurelius_atlas_quality_scanner/settings.py` — `ScannerSettings`
  (`AURELIUS_ATLAS_QUALITY_SCANNER_` prefix, frozen; `client_secret` required, the rest
  defaulted)
- `aurelius_atlas_quality_scanner/sources.py` — the reader seam, the `FileReader` of the first
  cut, and the `SourceRouter` that picks a dataset's reader by its source's `kind` (DQS-04,
  DQS-05, DQS-18). The `sources` map is the only source of paths: a dataset's qualified name is
  never used as a path (DD-459). An unknown `kind` is a skip, not a failure (DQS-18).
- `aurelius_atlas_quality_scanner/catalogue.py` — the catalogue door: paged basic search of
  `m4i_data_quality` (DQS-02), binding through the rule's `fields` end (DQS-03), one bulk
  score write (DQS-06). Every call rides `aurelius-atlas-server-client`.
- `aurelius_atlas_quality_scanner/records.py` — an engine document or an ERROR finding to the
  `m4i_dq_score` entity, keyed by `scoreKey` (DQS-06, DQS-07, DQS-08)
- `aurelius_atlas_quality_scanner/scan.py` — `run_scan`: the five steps, the per-rule
  outcomes, the dry-run and dataset filter (DQS-01, DQS-08, DQS-09). Testable with a fake
  client and reader; no Keycloak, no store.
- `aurelius_atlas_quality_scanner/__main__.py` — the CLI: settings, the client-credentials
  token (DD-458), optional telemetry, one scan, the exit code. `build_client` is the seam the
  e2e suite drives in-process.
- `specs/12-2-quality-scanner/` — the semantics spec and this increment's `design.md`
  (DD-455..461)
- `specs/12-4-source-readers/` — the planned umbrella: the contract every future source reader
  obeys (DQS-11..16); the database choice stays open
- `specs/12-4a-source-envelope/` — the shipped first step: `SOURCES` is a list of sources, each
  naming its dataset (qualified name or guid), its `kind`, and its `config`, and the router reads
  by kind with guid-first matching (DQS-17..20, DD-462..464)
- `tests/` — unit tests on a fake catalogue (`tests/fake_catalogue.py` answers the door's
  three calls over the wire)
- `e2e/` — the scanner in-process against a real server image on the dev stack (DQS-10)

## Rules the app keeps

The DQS rules live in `specs/12-2-quality-scanner/spec.md`; tests cite them with
`@pytest.mark.covers(..., rules=["DQS-NN"])` (ADR 056). The engine contract is 12.1's
(DQ-01..08, `libs/python/aurelius-atlas-quality`): cite that spec in any scoring change —
this app moves data, it never recomputes a score.

## Wiring Checklist

- `project.json` — the explicit `e2e` target replaces the inferred one: it skips this app's
  own `docker-build` (the suite drives the CLI in-process, DQS-10) and depends on the
  server's image plus the three dev stacks. It re-declares the `ci` configuration (the webapp
  override lesson: an explicit target loses the inferred `configurations`). No `serve`: the
  job has no process to serve; `scan` is the run target.
- Realm (DD-458): the `aurelius-atlas-quality-scanner` confidential client in
  `dev/keycloak/import/master.json`, with its service-account user holding `atlas-read` and
  `atlas-write` on the `aurelius-atlas-server` client. The server's store authorizer (AUZ-02)
  reads roles only from that client's `resource_access`, so a role-less service account gets
  scrubbed searches and refused writes. The client carries `fullScopeAllowed: true`: Keycloak
  mints a role-less token for a restricted client whose roles live on another client. The
  client's `defaultClientScopes` include `profile` so the token carries `preferred_username`
  and the audits name the account. A realm that was imported before this client needs a
  re-import (`down -v && up -d` on the dev compose).
- Audiences: the server accepts the scanner's token because
  `AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES` names the client (the server's `.env` for `serve`,
  the e2e compose for the suite). Adding a service client means editing that list too. The
  prod-side join lands with 12.3's chart work.
- `.env` / `.env.enc` — dev defaults; re-run `nx encrypt aurelius-atlas-quality-scanner`
  after changing `.env` (CI regenerates the plaintext from the `.env.enc`). The e2e vars the
  server image reads carry the server's own prefix (Nx injects this `.env` into the task).
- `tls.json` — the server's certificate SANs only: the job is a client and verifies the
  server and the issuer with `CA_FILE`.
- `Dockerfile` — the wheel `nx build` makes, nonroot, no EXPOSE and no HEALTHCHECK: the
  batch image ships for 12.3's CronJob.
- `e2e/docker-compose.yaml` — one service: the server image on the dev networks. The scanner
  itself has no service; the suite calls `run_scan` in-process (a batch CLI has nothing to
  compose). Tests seed `zz<run>`-namespaced entities and hard-delete them (DD-223: the shared
  dev store is never restarted), and every scan passes the `dataset_filter` (DQS-09): the
  sample corpus rides the same store, and an unscoped scan reads its rules. The seeded rule
  sets `active: true` itself — the write stamps an omitted primitive to its type's default
  (EWR-09), which for a rule is inactive, and the scan skips inactive rules (DQS-02, DD-461).

## Removal

The app is one increment's deliverable: remove `apps/aurelius-atlas-quality-scanner`, its
root `pyproject.toml` entries (member, dev group, uv source), the scanner client and
service-account user in `dev/keycloak/import/master.json` (and the helm copy), the scanner
entry in `AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES`, the mkdocs nav entry, and the 12.2 roadmap
rows. The `m4i_dq_score` model and its patches live in `aurelius-atlas-core` and stay —
7.25 reads them. The engine lib (12.1) stays.
