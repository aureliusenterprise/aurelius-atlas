# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-319. Alerts are Grafana rules, sent to one webhook named per install

- **Status:** Proposed
- **Increment:** 6.4c
- **Date:** 2026-11-04

**Decision.** The alert rules are Grafana-managed rules, provisioned from a file that the chart copies byte for
byte. They read the Prometheus datasource the dashboards read. Their destination is one contact point,
`maintainers`: a webhook whose URL comes from a Secret the install names, so it can be Slack, Teams or an
incident tool. Without that Secret, as in dev, no contact point is provisioned, and the rules fire in Grafana's
alert list only.

**Reason.** Grafana already runs in both the dev stack and the chart, behind the realm login. Its rules see
every datasource, and its file provisioning has the shape the dashboards use. A webhook is the one receiver
every chat and incident tool accepts. A Secret keeps its URL, often a credential itself, out of the ConfigMap.

**Alternatives.** Prometheus rules with an Alertmanager: the canonical pair, but one more service to run,
secure and keep in step with the chart, and no view of Loki or Tempo. A Grafana email contact point: needs SMTP
settings on every install, and email is the destination people read last.

**Consequences.** A rule change is one file and its chart copy, kept equal by the chart suite. The
maintainers' webhook is the one destination; routing by severity is a later policy change. Dev shows firing
rules without notifying anyone.

### DD-320. The server's logs ride its ingest leg and still reach its output

- **Status:** Proposed
- **Increment:** 6.4c
- **Date:** 2026-11-04

**Decision.** The OTel library builds a log processor for the per-service leg, as it builds the trace processor
and metric reader. The server bridges its own logger, its libraries' loggers and `uvicorn.error` into it, and
keeps them propagating.

**Reason.** The server's env leg is off (DD-196), so its logs had no way to the collector. The collector's logs
pipeline already serves the per-service leg. Propagating keeps the stdout a container's runtime collects,
which is the record when the collector itself is down.

**Alternatives.** A third element in `IngestPipeline`: one session for all three exporters, but it changes the
pair the auxiliary APIs unpack and gives them a log exporter they do not use. Bridging without propagation, as
`bridge_logging` did: no duplicate lines, but no output when the collector is down.

**Consequences.** Every record of those loggers goes out twice: to the collector, and to the process's output.
The auxiliary APIs keep their pipeline unchanged.

### DD-321. The load test is a small driver run with the e2e suite

- **Status:** Proposed
- **Increment:** 6.4c
- **Date:** 2026-11-04

**Decision.** The load test is an asyncio driver of about a hundred lines beside the server's e2e tests. Its
users are tasks on one `httpx` client, and its report gives each operation's percentiles. It runs with the e2e
suite for 20 seconds by default, and three environment variables make the run longer or harder.

**Reason.** It reuses the suite's server, tokens and CA, so a load run proves the same deployment the e2e tests
prove. Run in CI, it catches what only concurrency shows, such as a write conflict or a lost update, on every
change. Its budget is loose enough for shared runners.

**Alternatives.** Locust or k6: richer reports and ramp-up profiles, but a new dependency (gevent, or a
JavaScript runtime and an image from outside `dhi.io`), its own credentials and its own target.

**Consequences.** CI pays about 30 seconds more for the server's e2e. The default budget guards errors and
gross regressions; a performance target is a longer run with a tighter budget, set by its variables.
