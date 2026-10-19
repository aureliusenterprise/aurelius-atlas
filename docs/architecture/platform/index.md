# Platform

How the Aurelius Atlas system is connected, delivered, observed, kept alive, and secured. Content
arrives with the increments listed per page; see the tree convention on the [Architecture](../index.md)
page.

| Page                                                    | Scope                                                                                          | Written by        |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------- |
| [Components & Interfaces](components-and-interfaces.md) | The running parts by role: service, dashboards, store, identity, signals, with one anchor line | written (0.2–0.6) |
| [Data Pipelines](data-pipelines.md)                     | The catalogue's flows: request → store, model load at start-up; no streaming plane (ADR 050)   | 2.4               |

| Tree                                    | Subject                                              | Written by                   |
| --------------------------------------- | ---------------------------------------------------- | ---------------------------- |
| [Connectivity](connectivity/index.md)   | REST contract, TLS, service-to-service links         | 0.5 → 6.1                    |
| [Delivery](delivery/index.md)           | Configuration, change, testing, release, deployment  | 0.3 → 6.4                    |
| [Observability](observability/index.md) | Metrics, logs, traces, alerts                        | 6.4 (dev stack exists today) |
| [Resilience](resilience/index.md)       | Availability posture, incidents, snapshots, recovery | 6.4                          |
| [Security](security/index.md)           | Identity, access, secrets, encryption                | 0.1 → 6.2                    |
