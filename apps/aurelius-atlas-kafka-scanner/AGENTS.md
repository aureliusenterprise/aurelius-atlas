# aurelius-atlas-kafka-scanner

The batch Kafka cluster scanner of increment 13.1. This file covers wiring
specific to this app; workspace-wide rules, including the conversion workflow,
live in the root `AGENTS.md`.

## Layout

The job is a CLI, not a service: one process per scan, no HTTP router, no port
(KSC-01).

- `aurelius_atlas_kafka_scanner/settings.py` — `ScannerSettings`, the CLI
  itself (DD-472): a `CliSettingsSource` first, so every key has a flag and
  the flag beats the environment; `--help` prints; secrets are
  `CliSuppress`ed, which hides their flag from help but does not reject it —
  deployments keep secrets in the environment (DD-465..472 records the gap).
  (`AURELIUS_ATLAS_KAFKA_SCANNER_` prefix, frozen; `client_secret` required,
  the rest defaulted; the OTLP trio stands or falls together; the broker
  auth ladder — `security_protocol` × `sasl_mechanism` × its credentials —
  is validated as a whole, KSC-10.) The CLI parses only when `__main__.py`
  passes `_cli_parse_args=`, so pytest's own argv never reaches it; a
  malformed flag raises `SettingsError` (`cli_exit_on_error=False`), which
  `run` maps to exit 1 like any configuration error.
- `aurelius_atlas_kafka_scanner/cluster.py` — the broker door
  (`KafkaCluster`): the external topic list, the cluster id, the newest record
  of one topic (KSC-02, KSC-05, KSC-10). A broker that answers no metadata
  raises `BrokerUnreachableError` naming the bootstrap list — the run fails,
  it never hangs (KSC-01). `broker_config` builds the kafka-python client
  config for one of the four security protocols; `OAUTHBEARER` rides an
  `OAuthTokenProvider` wrapping the minted token, and a refused mint raises
  `BrokerAuthError` (DD-471). A wrong SASL secret surfaces from the admin
  client's constructor as a `KafkaTimeoutError`, which is a `KafkaError` —
  the same `BrokerUnreachableError` path covers it.
- `aurelius_atlas_kafka_scanner/registry.py` — the Schema Registry door
  (`SchemaRegistry`): a subject's latest schema and a schema by id (KSC-04,
  KSC-05). It takes a `transport` seam the tests inject.
- `aurelius_atlas_kafka_scanner/fields.py` — schema text and payload shapes to
  a `FieldSpec` tree: `parse_avro`, `parse_json_schema`, `parse_payload`
  (magic byte → id, or JSON inference), and `schema_id_of` (KSC-04..06).
- `aurelius_atlas_kafka_scanner/graph.py` — the tree: qualified names under
  the legacy rule, the System/Collection/Dataset/Field entities, the
  request-local temp guids and `relationshipAttributes` (KSC-03, KSC-06,
  KSC-07). Pure: no I/O, tested directly.
- `aurelius_atlas_kafka_scanner/scan.py` — `run_scan`: list, read, build, one
  bulk write (KSC-01, KSC-07..09). The `ScanDoor` protocol is the seam the
  e2e suite wraps to record what a run wrote. Testable with fakes; no
  Keycloak, no broker, no store.
- `aurelius_atlas_kafka_scanner/__main__.py` — the CLI: the settings model
  _is_ the parser (no argparse, DD-472), the client-credentials token
  (KSC-09), the OAUTHBEARER broker token when the ladder names it (KSC-10),
  optional telemetry, one scan, the exit code. `build_client` is the seam the
  e2e suite drives in-process.
- `specs/13-1-kafka-cluster-scanner/` — the semantics spec and this
  increment's `design.md` (DD-465..472)
- `tests/` — unit tests on fake doors (a fake broker, a fake Registry
  transport, a recording client): the qualified-name rule, the parsers, the
  wire id, the notices, the dry-run, the temp-guid bulk shape.
- `e2e/` — the scanner in-process against a real server image on the dev
  stack, driving a real broker and Schema Registry (KSC-07, KSC-09, KSC-10).

## Rules the app keeps

The KSC rules live in `specs/13-1-kafka-cluster-scanner/spec.md`; tests cite
them with `@pytest.mark.covers(..., rules=["KSC-NN"])` (ADR 056). The
qualified-name rule and the tree shape are the legacy scanner's, ported (the
spec's "Ported from" section names the source); any change to either is a
deviation and needs a `deviations.md` row, not a silent edit.

## Wiring Checklist

- `project.json` — the explicit `e2e` target replaces the inferred one: it
  skips this app's own `docker-build` (the suite drives the CLI in-process)
  and depends on the server's image plus the four dev stacks (keycloak,
  observability, elasticsearch, kafka). It re-declares the `ci` configuration
  (the webapp override lesson: an explicit target loses the inferred
  `configurations`) and sets `parallelism: false` — one server container on
  one port. No `serve`: the job has no process to serve; `scan` is the run
  target.
- Realm (DD-469's sibling of DD-458): the
  `aurelius-atlas-kafka-scanner` confidential client in
  `dev/keycloak/import/master.json` (and the byte-identical helm copy), with
  its service-account user holding `atlas-read` and `atlas-write` on the
  `aurelius-atlas-server` client. The server's store authorizer (AUZ-02)
  reads roles only from that client's `resource_access`. The client carries
  `fullScopeAllowed: true` and the `profile` scope, as the quality scanner's
  does. A realm imported before this client needs a re-import
  (`down -v && up` on the dev keycloak compose) — the e2e mint probe says so
  when it bites.
- Audiences: the server accepts the scanner's token because
  `AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES` names the client (the server's `.env`
  for `serve`, the e2e compose's `AUTH_AUDIENCES` for the suite). Adding a
  service client means editing that list too. The prod-side join lands with
  13.2's chart work.
- `dev/kafka` — the broker and Registry the scan reads in dev and in e2e:
  loopback-pinned ports 29092 (PLAINTEXT, no credentials, DD-469), 29095
  (SASL_PLAINTEXT with SCRAM-SHA-512, DD-471) and 28081 (Registry). The
  SCRAM pair in `dev/kafka/.env` is mirrored in this app's `.env` (as
  `AURELIUS_ATLAS_KAFKA_SCANNER_SASL_USERNAME`/`_PASSWORD`) so the e2e suite
  authenticates against it: keep the two pairs equal when either changes,
  and re-encrypt both `.env.enc` files. Its `README.md` carries the removal
  checklist.
- `.env` / `.env.enc` — dev defaults; re-run
  `nx encrypt aurelius-atlas-kafka-scanner` after changing `.env` (CI
  regenerates the plaintext from the `.env.enc`). The e2e vars the server
  image and the keycloak compose read carry their own names
  (`AURELIUS_ATLAS_SERVER_*`, bare `KAFKA_SCANNER_CLIENT_SECRET`
  passthrough) because Nx injects this `.env` into the task. The dev SASL
  credentials mirror `dev/kafka/.env` — see the `dev/kafka` bullet above.
- `tls.json` — the server's certificate SANs only: the job is a client and
  verifies the server and the issuer with `CA_FILE`. The broker and Registry
  are PLAINTEXT and need no certificate material (DD-469).
- `Dockerfile` — the wheel `nx build` makes, nonroot, no EXPOSE and no
  HEALTHCHECK: the batch image ships for 13.2's CronJob.
- `e2e/docker-compose.yaml` — one service: the server image on the dev
  networks, port 21006 (21005 was 12.2's). The scanner itself has no service;
  the suite calls `run_scan` in-process. Tests seed `zz<run>`-namespaced
  topics, subjects, and entities and delete them in teardown, fields before
  datasets (DD-223: the shared dev store and broker are never restarted).
  The door wrapper records the bulk write's guid assignments so teardown
  deletes by guid, not by name.

## Removal

The app is one increment's deliverable: remove
`apps/aurelius-atlas-kafka-scanner`, its root `pyproject.toml` entries
(member, dev group, uv source), `dev/kafka` (its own README has the full
unwire), the scanner client and service-account user in
`dev/keycloak/import/master.json` (and the helm copy), the
`KAFKA_SCANNER_CLIENT_SECRET` passthrough in `dev/keycloak/docker-compose.yaml`,
the scanner entry in `AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES`, the `kafka`
entry in `tests/test__dev_stack.py`'s `DEV_COMPOSES`, the mkdocs nav entry,
and the 13.1 roadmap rows. Drop the mirrored SASL pair from this app's
`.env`/`.env.enc` with the stack (`dev/kafka`'s own README unwires its side).
The `m4i_dataset`/`m4i_field` models stay — the webapp reads them.
