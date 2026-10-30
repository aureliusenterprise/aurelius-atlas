# Observability

How Aurelius Atlas raises its hand when it is broken (ADR 040): metrics, logs, traces, and alerts. The system's own signals arrive with increment 6.4. A signal collection stack runs in the development arrangement today (`dev/observability`); which products, and their ports, are in [Dev Topology](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/contributor-guide/development-environment/#dev-topology>).

> [!NOTE]
>
> **Planned**
>
> To be written by increment 6.4 (hardening); see [Architecture](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/index.md>).

| Page | Scope | Written by |
| --- | --- | --- |
| [Monitoring](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/platform/observability/monitoring/index.md>) | Metrics endpoints, scraped signals, dashboards | 6.4 |
| [Logging](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/platform/observability/logging/index.md>) | Structured logs, correlation, retention | 6.4 |
| [Alerting](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/platform/observability/alerting/index.md>) | Alert rules on liveness, readiness, store health | 6.4 |
