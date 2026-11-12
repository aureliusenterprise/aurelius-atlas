# aurelius-atlas-db-scanner

The batch relational database scanner of increment 13.3. This file covers
wiring specific to this app; workspace-wide rules, including the conversion
workflow, live in the root `AGENTS.md`.

## Layout

The job is a CLI, not a service: one process per scan, no HTTP router, no port
(DBS-02).

- `aurelius_atlas_db_scanner/settings.py` — `ScannerSettings`, the CLI itself
  (DD-472): a `CliSettingsSource` first, so every key has a flag and the flag
  beats the environment; `--help` prints; secrets (`DSN`, `CLIENT_SECRET`) are
  `CliSuppress`ed, which hides their flag from help but does not reject it —
  deployments keep the DSN and its password out of the shell history and the
  process list (DD-506). (`AURELIUS_ATLAS_DB_SCANNER_` prefix, frozen;
  `dsn`/`system_name`/`client_secret` required, the rest defaulted; the OTLP
  trio stands or falls together, DD-196.) The `schema` field (the `--schema`
  flag, DBS-11) shadows pydantic v1's deprecated `schema()` method — the
  module-level `warnings.filterwarnings` narrows that one warning to this one
  field; do not widen it. The CLI parses only when `__main__.py` passes
  `_cli_parse_args=`, so pytest's own argv never reaches it; a malformed flag
  raises `SettingsError` (`cli_exit_on_error=False`), which `run` maps to exit
  1 like any configuration error.
- `aurelius_atlas_db_scanner/database.py` — the database door
  (`SqlDatabase`): connect with the timeout, schema names, table names, one
  reflection per table (DBS-01..05). The reflection rides SQLAlchemy Core's
  inspector only — no `information_schema` SQL, no vendor tooling (DD-502).
  `SYSTEM_SCHEMAS` and the `pg_` prefix stand for the dialects' own metadata
  (DBS-04); `NAMELESS_DIALECTS` carries SQLite's nameless-default-schema case.
  A database that answers no connect raises `DatabaseUnreachableError` naming
  the URL rendered by `safe_url` (`hide_password=True`) — host and database,
  never the password (DBS-02, DD-506). `compile_patterns`/`matches_any` are
  the wildcard rule shared by `SCHEMAS` and `TABLES` (DBS-04/05).
- `aurelius_atlas_db_scanner/reflect.py` — one inspector table to the scan's
  `TableInfo`: rendered column types as `fieldType`, comment-or-`Primary key`
  mark as `definition`, the table comment, and each foreign key as ordered
  column pairs with the referred columns resolved positionally against the
  referred table's real primary key (DBS-06..08; the starting script's
  `ref_column or "id"` guess is fixed, DV-150). The `Inspector` Protocol is
  the seam the unit tests fake.
- `aurelius_atlas_db_scanner/graph.py` — the tree: qualified names under the
  legacy rule (KSC-03), the System/Collection/Dataset/Field entities, one
  Process per foreign-key column pair with the referring dataset on `inputs`
  and the referred one on `outputs` (DBS-08), and the request-local temp guids
  with the ends riding `relationshipAttributes` (KSC-07, DD-466). Pure: no
  I/O, tested directly. Note the store's unique-qualifiedName rule is per
  type, so a Field and a Process may share a qualifiedName — selectors must
  discriminate by type name.
- `aurelius_atlas_db_scanner/scan.py` — `run_scan`: the walk, the notices, one
  bulk write (DBS-02..05, DBS-09, DBS-11). The `ScanDoor` Protocol is the seam
  the tests fake; a `ScanReport` carries the counts the CLI prints.
- `aurelius_atlas_db_scanner/__main__.py` — the CLI: the settings model _is_
  the parser (no argparse, DD-472), the client-credentials token (DBS-10),
  optional telemetry, one scan, the exit code. `build_client` is the seam the
  e2e suite drives in-process.
- `specs/13-3-relational-database-scanner/` — the semantics spec and this
  increment's `design.md` (DD-502..507)
- `tests/` — unit tests on fake doors (SQLite in memory, a fake inspector, a
  recording catalogue): the qualified names, the reflection shapes, the FK
  pairing, the notices, the dry-run, the bulk shape, the CLI exit codes.
- `e2e/` — the scanner in-process against a real server image on the dev
  stack, driving a real Postgres the suite owns (DBS-01, DBS-03, DBS-08..10).

## Rules the app keeps

The DBS rules live in `specs/13-3-relational-database-scanner/spec.md`; tests
cite them with `@pytest.mark.covers(..., rules=["DBS-NN"])` (ADR 056). The
qualified-name rule and the tree shape are 13.1's contracts (KSC-03, KSC-06,
KSC-07), cited not restated; any change to either is a deviation and needs a
`deviations.md` row, not a silent edit.

## Wiring Checklist

- `project.json` — the explicit `e2e` target replaces the inferred one: it
  skips this app's own `docker-build` (the suite drives the CLI in-process) and
  depends on the server's image plus the three dev stacks (keycloak,
  observability, elasticsearch). It re-declares the `ci` configuration and sets
  `parallelism: false` — one server container on one port. No `serve`: the job
  has no process to serve; `scan` is the run target.
- Realm (DD-458's pattern, 13.1's sibling): the
  `aurelius-atlas-db-scanner` confidential client in
  `dev/keycloak/import/master.json` (and the byte-identical helm copy), with
  its service-account user holding `atlas-read` and `atlas-write` on the
  `aurelius-atlas-server` client. The client carries `fullScopeAllowed: true`
  and the `profile` scope, as the other scanners' do. A realm imported before
  this client needs a re-import (`down -v && up` on the dev keycloak compose) —
  the e2e mint probe says so when it bites.
- Audiences: the server accepts the scanner's token because
  `AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES` names the client (the server's `.env`
  for `serve`, the e2e compose's `AUTH_AUDIENCES` for the suite). Adding a
  service client means editing that list too. The prod-side join lands with
  13.4's chart work.
- `.env` / `.env.enc` — dev defaults; re-run
  `nx encrypt aurelius-atlas-db-scanner` after changing `.env` (CI regenerates
  the plaintext from the `.env.enc`). The e2e vars the server image and the
  compose read carry their own names
  (`AURELIUS_ATLAS_SERVER_*`, `OTEL_INGEST_CLIENT_SECRET`) because Nx injects
  this `.env` into the task. `AURELIUS_ATLAS_DB_SCANNER_POSTGRES_PASSWORD` is
  the suite Postgres's and its DSN's one password (the e2e compose's
  `${VAR:?}` guards fail loudly when a value is missing). The dev writer's
  `USERNAME`/`PASSWORD` mirror the dev realm's seeded user so the suite's
  seeding tokens mint; keep them equal to the realm import.
- `tls.json` — the server's certificate SANs only: the job is a client and
  verifies the server and the issuer with `CA_FILE`. The database needs no
  certificate material for the suite (the Postgres speaks plain TCP on
  loopback; a TLS database rides `CA_FILE` too if its DSN asks for it).
- `Dockerfile` — the wheel `nx build` makes, nonroot, no EXPOSE and no
  HEALTHCHECK: the batch image ships for 13.4's CronJob. `psycopg[binary]` is
  baked in because the e2e and most deployments scan Postgres; musllinux
  wheels keep the hardened image free of system libpq (DD-465's rule). Other
  dialects arrive as driver additions, never code (DBS-01).
- `e2e/docker-compose.yaml` — two services: the server image on the dev
  networks, port 21007 (21006 was 13.1's), and the suite's own
  `dhi.io/postgres` on 25432 (DD-507: the scan reads a database the suite
  starts, seeds, and discards — never a shared store, never a restarted one,
  DD-223). The hardened Postgres image refuses `POSTGRES_HOST_AUTH_METHOD`
  `trust`, so the service runs SCRAM with the suite's password — which also
  keeps DBS-02's scrubbing honest end to end. The scanner itself has no
  service; the suite calls `run` in-process. Tests seed `zz<run>`-namespaced
  schemas and drop them `CASCADE` in teardown; the catalogue teardown deletes
  by guid, recorded through the door wrapper.
- Root `pyproject.toml` — the pyright `executionEnvironments` entry carries
  `apps/aurelius-atlas-db-scanner/e2e` in `extraPaths` so the suite's
  `from conftest import ...` resolves for pyright as pytest resolves it.
  The unit tests deliberately do NOT import conftest symbols (the trace
  conftest-collision rule, #306): their shared literals are inline.

## Removal

Remove the app directory, its root `pyproject.toml` uv member and dev-group
entries and `uv.sources`, its `pyright.executionEnvironments` entry, its
realm client and service-account user in both `master.json` copies, and the
`aurelius-atlas-db-scanner` entry in every `AUTH_AUDIENCES` list (the server
`.env` and each e2e compose). Nothing else imports this app: it is a leaf.
The 13.4 chart work has not landed yet, so there is no helm or schedule
footprint to unwire.
