# Observability

How Aurelius Atlas raises its hand when it is broken (ADR 040): metrics, logs, traces, and alerts.
The system's own signals arrive with increment 6.4. A signal collection stack runs in the
development arrangement today (`dev/observability`); which products, and their ports, are in
[Dev Topology](../../../contributor-guide/development-environment.md#dev-topology).

!!! INFO "Planned"

    To be written by increment 6.4 (hardening); see [Architecture](../../index.md).

| Page                        | Scope                                            | Written by |
| --------------------------- | ------------------------------------------------ | ---------- |
| [Monitoring](monitoring.md) | Metrics endpoints, scraped signals, dashboards   | 6.4        |
| [Logging](logging.md)       | Structured logs, correlation, retention          | 6.4        |
| [Alerting](alerting.md)     | Alert rules on liveness, readiness, store health | 6.4        |
