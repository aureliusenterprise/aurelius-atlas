# 2026-11-05: Server silent, the first rehearsal

A rehearsal of the incident path (ADR 041 R3) on the dev stack, walking [Server silent](<https://aureliusenterprise.github.io/phase6-6.4f-resilience/architecture/platform/resilience/incident-management/#aurelius-atlas-server-silent>). The server was stopped on purpose; no data was at risk.

## Summary

A dev server was started, then stopped, and the walk followed the alert's section from the first signal to the all-clear. The path worked: the alert fired, the section's first checks named the server as the failed part, and a restart cleared it within two minutes. The alert fired late, though: 11 minutes after the server stopped. The rehearsal found why, the fix landed with it, and a second walk measured the fix: 7 minutes 42 seconds.

## Timeline

In UTC. The first walk, on the collector as it was:

| Time | Event |
| --- | --- |
| 00:49:07 | The server stops: the incident begins |
| 00:59:10 | "Server silent" turns pending |
| 01:00:10 | It fires, 11 minutes 3 seconds after the stop |
| 01:00:10 | Triage: the server's liveness does not answer; the collector is up; the store is green |
| 01:00:10 | Mitigation: the server is restarted |
| 01:02:11 | The rule is normal again: the all-clear, 2 minutes 1 second after the restart |

The second walk, with the collector's `metric_expiration` at 2 minutes:

| Time | Event |
| --- | --- |
| 01:13:31 | The server stops, after two minutes of exporting |
| 01:20:13 | "Server silent" turns pending |
| 01:21:13 | It fires, 7 minutes 42 seconds after the stop |
| 01:21:13 | Triage as before; mitigation: the server is restarted |
| 01:23:14 | The all-clear, 2 minutes 1 second after the restart |

A walk in between was discarded: the collector had been restarted during it, which dropped every series at once.

## Actions

1. The rule's runbook link, loaded in Grafana with the rule, names its section on Incident Management.
2. Check first, step 1: the server's liveness (`/api/atlas/admin/liveness`) gave no answer, so the server was down, not only its export.
3. To rule out the other parts, the collector's scrape (`up`) and the store's health were read: both fine.
4. Mitigate: the server was started again. The rule returned to normal at its next evaluations.
5. The delay was traced to the collector, fixed, and the walk repeated.

## Cause

The rehearsal's cause was the planned stop. Its finding was the late alert. The collector's Prometheus exporter keeps serving a series for 5 minutes after its producer's last point, by default. So the rule's 5-minute window began to empty only 5 minutes after the server stopped, and the rule fired after 5 + 5 + 1 minutes. "Part silent" reads the same series, so it waited the extra 5 minutes too.

## Follow-ups

- The collector drops a stopped producer's series after 2 minutes, in dev and in the chart (INC-04, increment 6.4f): done, measured by the second walk.
- "Server silent" says when it fires, about eight minutes after a stop, on Incident Management: done.
- The next rehearsal walks "Store red or silent" or "Snapshot overdue", the two alerts whose mitigation can lose data: scheduled for the yearly game-day.
