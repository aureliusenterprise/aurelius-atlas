# High Availability

What keeps running when a part fails, and what does not. The system promises no uptime of its own ([ADR 037](<https://aureliusenterprise.github.io/feat-rest-requests-as-models/architecture/adr/037-the-system-itself-promises-nothing-about-staying-up/index.md>)): availability is what a deployment builds around it. This page states what the charts give a deployment to build with, and where the limits are.

## The shape the charts install

| Part | Instances by default | More than one |
| --- | --- | --- |
| Elasticsearch, the store | 1 | refused: the chart fails to render with `replicas` above 1 |
| The server | 1 | possible, with the limits below |
| The webapp | 2 | yes: it holds no state |
| Keycloak and its database | 1 | not offered |
| The observability stack | 1 each | not offered |
| The auxiliary APIs | 1 each | yes: each answers from its request alone |

Each part with more than one instance has a pod disruption budget, so a node drain leaves one running.

## What fails together

**The store is the critical dependency.** It is the system of record ([ADR 047](<https://aureliusenterprise.github.io/feat-rest-requests-as-models/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)), and it runs as a single node: every index has its primary and no replica (DD-323). While it is down, every request that reads or writes the catalogue fails with a server error, the server's readiness check fails (ADM-04), and the webapp shows the error. When it comes back on its volume, nothing is lost. When its volume is lost, the catalogue comes back from the newest snapshot, at most an hour old ([Backup &amp; Restore](<https://aureliusenterprise.github.io/feat-rest-requests-as-models/architecture/platform/resilience/backup-and-restore/index.md>)).

**Keycloak is the second.** While it is down, no one can sign in, and a token that expires is not renewed: the server verifies tokens against Keycloak's keys, which it caches for an hour, so requests with a valid token go on until the token or the cache expires. The parts that export signals mint their tokens at Keycloak too, so their signals stop with it, and "Part silent" fires.

**The observability stack fails alone.** The catalogue keeps working without it; only its signals and alerts are lost while it is down ([Incident Management](<https://aureliusenterprise.github.io/feat-rest-requests-as-models/architecture/platform/resilience/incident-management/#aurelius-atlas-collector-down>)).

## More than one server

The server is built for several processes on one store: tasks are claimed with a lease, so each runs once (DV-38), and a type change in one process reaches the others within `typedef_refresh_seconds`. Two limits remain:

- **Browser sessions stay in the process that made them.** The dashboards sign in with a session cookie, and each server keeps its sessions in memory (AUT-06). A browser routed to another server is sent to sign in again. More than one server needs session affinity at the gateway for the dashboards. Requests with a bearer token, the webapp's and the auxiliary APIs', are not affected.
- **Each server runs the schedules.** The hourly metrics save, the audit aging and the snapshot watcher run in every process. The second server to save an hour's metrics finds the first one's and logs that the save failed; the aging deletes what another already deleted. Both are harmless, but the log shows them.

## Not offered

A store of several nodes, with replicas that survive a node's loss, is a later increment: it needs a certificate per node for the transport layer (CHT-10). Keycloak in a cluster of its own, and a standby system in a second site ([ADR 026](<https://aureliusenterprise.github.io/feat-rest-requests-as-models/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>)'s fourth alternative), are decisions for a deployment, not offered by the charts.
