# 6.4f Resilience pages and the first incident rehearsal

- **Status:** done
- **Pull request:** #269
- **Records:** DD-359, DD-360; ADR 041 (R2, R3, R5)

The alerts of 6.4c and 6.4e fire, but nothing tells a responder what to do next, and the incident path of
ADR 041 has never been walked. This increment writes the steps for each alert and links them from the alert
itself. It defines the record an incident leaves, and walks the path once in dev: the first rehearsal. It also
writes the pages 6.4 still owed: High Availability, Incident Management and Deployment.

## Scope

No endpoint and no code change. The changes are:

| Project             | What changes                                                                             |
| ------------------- | ---------------------------------------------------------------------------------------- |
| `dev/observability` | every alert rule's `runbook_url`; the collector's `metric_expiration`; both in the chart |
| `docs`              | High Availability, Incident Management, Deployment, and the incident records             |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                    |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| INC-01 | The Incident Management page has a section for every alert rule, its heading anchored by the rule's uid (`{ #<uid> }`). Each section states what the alert means, what to check first, what may be done to mitigate, and when to escalate: the paragraphs **Means.**, **Check first.**, **Mitigate.** and **Escalate.** |
| INC-02 | Every alert rule carries the annotation `runbook_url`, the published Incident Management page followed by `#<uid>`. The chart's copy of the rules is byte-identical (OBS-03)                                                                                                                                            |
| INC-03 | Every incident and every rehearsal leaves a record in `docs/architecture/platform/resilience/incidents/`, named `<yyyy-mm-dd>-<slug>.md`, with the sections Summary, Timeline, Actions, Cause and Follow-ups. Each record is listed on the incidents index and in the docs' navigation                                  |
| INC-04 | The collector's Prometheus exporter drops a series 2 minutes after its producer's last point (`metric_expiration: 2m`), in dev and in the chart, so the silence rules see a stopped producer that much sooner                                                                                                           |

## Origin

No Java class is ported. ADR 041 names the owner and the path; [Operations
Ownership](../../../../docs/contributor-guide/operations-ownership.md#incident-response) holds the path, and
this increment adds the steps per alert and the record.

## Deviations

None from Atlas.

## Findings

The first rehearsal walked "Server silent" in dev; its record is
[2026-11-05](../../../../docs/architecture/platform/resilience/incidents/2026-11-05-rehearsal-server-silent.md).

## Acceptance

- `tests/test__incidents.py` — INC-01 to INC-04.
- `tests/test__charts_observability.py` — the chart's copy of the rules (OBS-03).
- In dev Grafana: the rules load with their runbook links, and the rehearsal's timeline.
- `uv run zensical build --strict`.
