# Incident Management

What to do when an alert fires, who decides, and what is written down afterwards ([ADR 041](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/architecture/adr/041-a-failure-of-the-running-system-has-an-owner-and-a-rehearsed-path/index.md>)). The owner is the maintainers team, and the path from first signal to all-clear is in [Operations Ownership](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/contributor-guide/operations-ownership/#incident-response>). This page holds the steps for each alert, the record an incident leaves, and the rehearsals. The rules are those of increment 6.4f (INC-01 to INC-03).

## From an alert to this page

Every alert rule ([Alerting](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/architecture/platform/observability/alerting/index.md>)) links its section below as its runbook URL. Grafana shows the link on the rule and sends it with each notification. A section says what the alert means, what to check first, what may be done to mitigate without asking, and when to escalate.

The commands are for a cluster release named `atlas` in the namespace `atlas`. In dev the same parts run as compose services: `docker compose -f dev/<stack>/docker-compose.yaml ps` and `logs` stand in for `kubectl`.

## The alerts

### Server silent

**Means.** The server has sent no process metrics for five minutes: it is down, cannot reach the collector, or has lost its ingest credential. Clients see errors or nothing, unless only the export is broken. The rule fires about eight minutes after the server stops: the collector keeps a stopped producer's series for two minutes, the rule waits for five minutes without metrics, then one more (INC-04).

**Check first.**

1. Liveness: `kubectl -n atlas get pods -l app.kubernetes.io/name=atlas-server`, then `kubectl -n atlas logs deploy/atlas-server --tail=100`. A crash at start names its cause: a store it cannot open, a setting it cannot read.
2. If the server answers (`/api/atlas/admin/liveness` returns 200), the export is broken: the server's log names the failed token mint or export. Check "Collector down" and Keycloak.

**Mitigate.** Restart the server: `kubectl -n atlas rollout restart deploy/atlas-server`. A server that fails at start against an unhealthy store waits for the store; see "Store red or silent".

**Escalate.** When the server stays down for 15 minutes, or its start fails on the store's data.

### Part silent

**Means.** A part (`exported_job`) sent signals in the last six hours and none in the last ten minutes: one of the auxiliary APIs, a metrics puller, the webapp's edge. The label `exported_job` names it.

**Check first.** The part's pod and log, as for the server. A puller that cannot mint its token restarts until Keycloak answers, so check Keycloak too.

**Mitigate.** Restart the part. A part removed on purpose clears the alert within six hours.

**Escalate.** When the part is the store's puller: the store's own alert is then blind.

### Server errors

**Means.** More than 5% of the server's answers over five minutes were 5xx. Each 5xx carries a `requestId`, the trace id of the failed request (SRV-07).

**Check first.** The dashboard "Aurelius Atlas Server": the routes with 5xx answers, and their traces. Then the store: most 5xx answers are a store that is red, full or unreachable.

**Mitigate.** A store problem is mitigated at the store. A fault in one route is not: roll back to the previous release ([Deployment](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/architecture/platform/delivery/deployment/index.md>)).

**Escalate.** At once when a write route fails: writes may be lost. Pull in the dataset's owner ([Operations Ownership](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/contributor-guide/operations-ownership/#dataset-ownership>)).

### Server slow

**Means.** The 95th percentile of the server's requests over five minutes is over two seconds, for ten minutes.

**Check first.** The busiest routes on the server's dashboard, then the store's CPU and heap on the "Elasticsearch" dashboard. A large search or import shows as one busy route, and as long spans in its traces.

**Mitigate.** None is needed for a burst that passes. A store short of heap or CPU needs more, set in the store chart's `resources` and `heap` together.

**Escalate.** When it lasts an hour, or the server's errors rise with it.

### Store red or silent

**Means.** Elasticsearch reports red, a primary shard unassigned, or its metrics have stopped. Requests that read or write an index on a red shard fail with a server error, and the server's readiness check fails.

**Check first.**

1. `kubectl -n atlas logs statefulset/atlas-elasticsearch --tail=200`, and the pod's events.
2. A full data volume shows as watermark errors in the log; a pod that does not start, as its events.
3. Silent but healthy: the store's puller, `deploy/atlas-elasticsearch-metrics-puller`.

**Mitigate.** Restart the store's pod only when it is stuck at start. A full volume needs a larger claim. A shard that stays red after the node is up needs a restore of its index: [Backup &amp; Restore](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/architecture/platform/resilience/backup-and-restore/#restoring>), after taking a snapshot of what is left.

**Escalate.** Before any restore: it loses the writes since the snapshot. The decider and a second maintainer agree on it, and the dataset's owner is told.

### Collector down

**Means.** Prometheus cannot scrape the OpenTelemetry collector. Every signal passes it, so every other rule is blind while it is down.

**Check first.** `kubectl -n atlas logs deploy/atlas-observability --tail=100`: a config it cannot load, or Keycloak's keys it cannot fetch.

**Mitigate.** Restart it: `kubectl -n atlas rollout restart deploy/atlas-observability`.

**Escalate.** When it stays down for 15 minutes: the system is then unobserved.

### Collector export failures

**Means.** The collector failed to deliver spans, metric points or log records in the last ten minutes. A backend, Tempo, Prometheus or Loki, is down or full.

**Check first.** The "Observability Stack" dashboard's exporter panels name the backend; its pod and log say why.

**Mitigate.** Restart the backend. A full volume needs a larger claim or a shorter lifetime ([Data Archiving](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/architecture/data-lifecycle-management/data-archiving/index.md>)).

**Escalate.** When it lasts an hour: the signals lost are the evidence of anything else that happens.

### Snapshot overdue

**Means.** The store's last successful snapshot is more than two hours old: two hourly runs have failed or not run, and the maximum data loss is no longer bounded at an hour.

**Check first.** The server's log names the last failure ("The last snapshot failed"). The usual causes are a full snapshots claim, the store red, or the policy deleted. List the snapshots: `kubectl -n atlas exec deploy/atlas-server -- python -m aurelius_atlas_server.snapshots list`.

**Mitigate.** Take a snapshot now, once the cause is gone: `kubectl -n atlas exec deploy/atlas-server -- python -m aurelius_atlas_server.snapshots take`. A deleted policy comes back with a server restart.

**Escalate.** When no snapshot succeeds for a day: the store is then unprotected.

## The record

Every incident leaves a record, and so does every rehearsal, in [Incidents](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/architecture/platform/resilience/incidents/index.md>). The decider writes it at the all-clear, as one page named `<date>-<slug>.md`, with these sections:

- **Summary**: what was seen, for how long, and what it cost.
- **Timeline**: in UTC, from the first signal to the all-clear.
- **Actions**: what was tried, in order, and by whom.
- **Cause**: what broke, and why.
- **Follow-ups**: each a change, an alert rule or a record, with its pull request or issue. A lesson that should become a rule becomes one (ADR 041 R6).

## Rehearsals

The incident path is rehearsed on the dev stack once a year, and after a change to an alert rule or to this page's steps. A rehearsal picks one alert, causes its condition, and walks the section, from the alert to its all-clear. It leaves a record, and fixes what the walk found wrong on this page. The first rehearsal walked "Server silent" ([2026-11-05](<https://aureliusenterprise.github.io/feat-15-2-tenant-scoped-stores/architecture/platform/resilience/incidents/2026-11-05-rehearsal-server-silent/index.md>)).
