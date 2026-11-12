# 12.3 The scanner chart and schedule

- **Status:** in review
- **Pull request:** #326
- **Records:** adds CHT-114 to CHT-120 and CHT-125 (the shared chart-track
  contract, stated
  whole here; each scanner chart proves its share in its own suite) and
  DD-508 to DD-513 (here); relies on 12.2 (DQS-01..10, DD-455..461),
  10.7/DD-277 (the prod realm and the per-client credential roster), and
  6.1a/DD-250 (the server's auth join)

## Scope

The quality scanner ships as a batch image with no deployment: 12.2's
Dockerfile names this increment as its scheduler. This increment delivers the
deployment half — `apps/aurelius-atlas-quality-scanner/helm`, a standalone Helm
chart that runs the scan as a Kubernetes `CronJob` — and the audience join the
server chart grants so a scanner's token is accepted (CHT-120). The client
registration and credential the job signs in with belong to the deployment
(CHT-118/119): the customer runs the scanners on their own systems, and this
repository ships no scanner client or secret.

Two sibling increments share this spec's rule set and land in the same pull
request, because one CronJob shape and one identity contract cover all three
batch scanners:

- 13.2 — `apps/aurelius-atlas-kafka-scanner/helm` (the Kafka scanner,
  CHT-121/122 and DD-514/515)
- 13.4 — `apps/aurelius-atlas-db-scanner/helm` (the database scanner,
  CHT-123/124 and DD-516/517)

This increment does not deliver: scanner dependencies in the `helm/` umbrella
(deliberate, DD-508), any scanner client registration or credential generation
(deliberate, DD-509), or incremental scans beyond the cron expression itself
(DD-460's boundary stays). Telemetry and trust are first-class and optional
(CHT-125, CHT-117): a customer deployment turns each on with its own values
and this repository ships no collector, CA, or credential for them.

## Rules

The rules are the chart-track contract for the batch scanner charts. Each
chart proves the shared rules in its own suite
(`tests/test__charts_<scanner>.py`); each rule names chart parts by role, so
one reading covers the three charts. The audience rule (CHT-120) and the
registration absence (CHT-118/119) are proven once, in
`tests/test__charts_server.py`, `tests/test__charts_keycloak.py`, and
`tests/test__charts_umbrella.py`, and name every scanner client including
13.2's and 13.4's.

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHT-114 | Each batch scanner chart is a standalone chart at `apps/<app>/helm/` that is **never** a dependency of the `helm/` umbrella (DD-508). It declares the full `global.*` contract with empty defaults, so it renders and installs on its own, and its `helm-publish` target pushes it to its own OCI repository like every other chart (DD-288's release wiring rides the owning project). A cluster that installs the umbrella runs no scanner workload until the operator installs a scanner chart too.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| CHT-115 | The workload is one `CronJob` (batch/v1), never a Deployment: no Service, no `Certificate`, no probes, and no ingress `NetworkPolicy` render, because the job listens on no port and no in-cluster caller dials it. `schedule` is a required value and `catalogue.serverUrl` is a required value (the CHT-02 guard fails the bare render, not the pod); `concurrencyPolicy` defaults to `Forbid`; `startingDeadlineSeconds`, the history limits, `suspend`, and `activeDeadlineSeconds` (default 3600) are values; `ttlSecondsAfterFinished` renders only when a value names it. The pod carries `restartPolicy: Never`, the hardened security context (uid/gid 65532, read-only root, drop-all, seccomp `RuntimeDefault`), and `automountServiceAccountToken: false`.                                                                                                                                                                                                                                                                                                      |
| CHT-116 | The job's identity is a join, never a literal (CHT-21's rule for a batch job): `<PREFIX>TOKEN_URL` derives from the issuer and realm exactly as the service charts derive it (`global.issuer.url`, fallback `https://keycloak.<domain>`, realm `global.realm`); `<PREFIX>SERVER_URL` arrives from the required `catalogue.serverUrl` value (a batch job has no co-deployed server to name by convention); `<PREFIX>CLIENT_ID` defaults to the app's own client id and is a value; `<PREFIX>CLIENT_SECRET` is a `secretKeyRef` into the Secret named by `auth.secretName` (default `<release>-scanner-clients`) under the key `auth.secretKey` (default the client id). The Secret is the deployment's own (CHT-118): the chart never generates a credential and never takes one as a value (DD-509).                                                                                                                                                                                                                                                                        |
| CHT-117 | Trust arrives through an optional mounted Secret: when `trust.caSecretName` (or `global.trust.caSecretName`) names a Secret, the job mounts it read-only at `/etc/aurelius-atlas/ca` and joins `<PREFIX>CA_FILE` to `<mount>/ca.crt`; with no name, no volume and no `CA_FILE` render and the image keeps its system trust store (the bootstrap path for a bring-your-own issuer). The `config`, `secretRefs`, and `extraEnv` blocks pass through verbatim like the service charts', which is how the file-source `SOURCES` map (DQS-17), the per-database DSN (13.4), and broker SASL credentials (13.2) arrive without bespoke values.                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| CHT-118 | A scanner's client registration is the deployment's own act, never a shipped one (DD-509): the customer runs the scanner against their own catalogue and often their own issuer, so the repository ships no registration for them. The hardened realm asset (`dev/keycloak/helm/files/aurelius-atlas.json`) carries **no** client whose id names a scanner, and no Keycloak import placeholder names one — the asset's minimal surface (CHT-75) and empty `users` list hold unchanged. A deployment that runs a scanner registers one confidential client per scanner in its own issuer, named by the chart's `auth.clientId` default, with a service account holding `atlas-read` and `atlas-write` on the `aurelius-atlas-server` client (AUZ-02 reads roles only there) — the shape the dev realm's scanner clients (12.2/13.1/13.3, master.json) already prove.                                                                                                                                                                                                         |
| CHT-119 | No credential for a scanner is generated by this repository's Helm trees: the umbrella's generated Secrets stay exactly the set it generates today (CHT-88's roster — elasticsearch, keycloak admin/database, otel clients, grafana, server client), and neither the umbrella nor a scanner chart renders a Secret keyed by a scanner client id. A scanner chart reads the Secret named by its `auth.secretName` (CHT-116) and that Secret's bytes come from the deployment — its vault, its Secret manager, or a hand-placed Secret under the default name. Dev keeps its own path (the `dev/keycloak` compose feeds the dev realm's scanner placeholders from its `.env`) — that is the repository's stack, not a customer contract.                                                                                                                                                                                                                                                                                                                                      |
| CHT-120 | The server chart's `auth.audiences` default lists the webapp client **and** the three scanner client ids (CHT-108's join): a deployed catalogue accepts a scanner's token out of the box, and the value stays an operator knob for deployments that install fewer scanners. `AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES` renders the list through `toJson`, unchanged in shape.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| CHT-125 | Telemetry is a first-class block, optional and off by default: `telemetry.enabled` false renders no `OTEL_*` env at all (the plain SDK setup the app builds on its own); true requires `telemetry.endpoint` — the CHT-02 guard fails the render without it (DD-508's reason: a batch job has no co-deployed collector to derive one from). `telemetry.auth.enabled` true (the default) joins the app-owned leg's trio, `<PREFIX>OTEL_ENDPOINT`, `_TOKEN_URL`, `_CLIENT_ID`, and `_CLIENT_SECRET` as a `secretKeyRef` (DD-196): the ingest client defaults to `auth.clientId` and its Secret defaults to the identity join's `auth.secretName` and key (DD-514's reuse rule), each a value naming a dedicated ingest client when the deployment registers one. False rides the SDK env leg unauthenticated — bare `OTEL_EXPORTER_OTLP_ENDPOINT`, plus `OTEL_EXPORTER_OTLP_CERTIFICATE` at the CA mount path when `trust.caSecretName` names a Secret (DD-210). The chart generates nothing here either: the ingest credential is the deployment's, CHT-119's rule unchanged. |

## Deviations

From the umbrella's install shape: the scanner charts sit outside it (DD-508).
A customer deployment installs and values them per deployment; the dev stack
composes what it needs with its compose files, as the scanners' own e2e
stacks already do.
From Java Atlas: none (platform slice, no REST behaviour changes).

## Acceptance

- `uv run pytest tests/test__charts_quality_scanner.py` — CronJob shape,
  identity joins, CA branch, telemetry branches and guard, guards
  (CHT-115/116/117/125).
- `uv run pytest tests/test__charts_keycloak.py`
  `tests/test__charts_umbrella.py` `tests/test__charts_server.py` — the
  audience default (CHT-120) and the registration absence: no scanner client
  in the realm asset, no scanner Secret among the umbrella's (CHT-118/119).
- `npx nx run-many -t helm-lint helm-template` — green with the three new
  charts in the gate (CHT-06); `npx nx run-many -t helm-config-scan` — zero
  findings (the CronJob charts are KSV-clean by construction, DD-510).
- Hand check (reported in the PR): `helm template` plus `kubectl apply` of one
  scanner chart with `suspend: true` on the dev cluster brings its CronJob and
  ServiceAccount up; a one-shot `cronjob create` job of the CronJob reaches
  `Complete` against an installed umbrella stack pointed at the dev realm.
