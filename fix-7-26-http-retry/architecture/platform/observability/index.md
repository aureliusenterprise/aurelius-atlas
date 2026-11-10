# Observability

How Aurelius Atlas raises its hand when it is broken (ADR 040): metrics, logs, traces, and alerts. Every part sends its signals to one collection point, the OpenTelemetry collector, which passes them to Prometheus, Loki and Tempo; Grafana shows them and evaluates the alert rules. The development arrangement runs that stack in `dev/observability`; which products, and their ports, are in [Dev Topology](<https://aureliusenterprise.github.io/fix-7-26-http-retry/contributor-guide/development-environment/#dev-topology>). The observability chart runs the same stack on a cluster.

| Page | Scope | Written by |
| --- | --- | --- |
| [Monitoring](<https://aureliusenterprise.github.io/fix-7-26-http-retry/architecture/platform/observability/monitoring/index.md>) | The signals each part sends, the dashboards | 6.4c |
| [Logging](<https://aureliusenterprise.github.io/fix-7-26-http-retry/architecture/platform/observability/logging/index.md>) | The server's log records, their correlation to traces | 6.4c |
| [Alerting](<https://aureliusenterprise.github.io/fix-7-26-http-retry/architecture/platform/observability/alerting/index.md>) | The alert rules, their destination, how to see one fire | 6.4c |

Metrics are kept 15 days, logs 30 days, traces 7 days and the alerts' history 30 days; the [lifetimes](<https://aureliusenterprise.github.io/fix-7-26-http-retry/architecture/data-lifecycle-management/data-archiving/index.md>) page says why and where each is set (ADR 025).
