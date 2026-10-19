# Platform

How the Aurelius Atlas system is connected, delivered, observed, kept alive, and secured. Content arrives with the increments listed per page; see the tree convention on the [Architecture](<https://aureliusenterprise.github.io/ci-chromatic-affected-gate/architecture/index.md>) page.

| Page | Scope | Written by |
| --- | --- | --- |
| [Components &amp; Interfaces](<https://aureliusenterprise.github.io/ci-chromatic-affected-gate/architecture/platform/components-and-interfaces/index.md>) | The running parts by role: service, dashboards, store, identity, signals, with one anchor line | written (0.2–0.6) |
| [Data Pipelines](<https://aureliusenterprise.github.io/ci-chromatic-affected-gate/architecture/platform/data-pipelines/index.md>) | The catalogue's flows: request → store, model load at start-up; no streaming plane (ADR 050) | 2.4 |

| Tree | Subject | Written by |
| --- | --- | --- |
| [Connectivity](<https://aureliusenterprise.github.io/ci-chromatic-affected-gate/architecture/platform/connectivity/index.md>) | REST contract, TLS, service-to-service links | 0.5 → 6.1 |
| [Delivery](<https://aureliusenterprise.github.io/ci-chromatic-affected-gate/architecture/platform/delivery/index.md>) | Configuration, change, testing, release, deployment | 0.3 → 6.4 |
| [Observability](<https://aureliusenterprise.github.io/ci-chromatic-affected-gate/architecture/platform/observability/index.md>) | Metrics, logs, traces, alerts | 6.4 (dev stack exists today) |
| [Resilience](<https://aureliusenterprise.github.io/ci-chromatic-affected-gate/architecture/platform/resilience/index.md>) | Availability posture, incidents, snapshots, recovery | 6.4 |
| [Security](<https://aureliusenterprise.github.io/ci-chromatic-affected-gate/architecture/platform/security/index.md>) | Identity, access, secrets, encryption | 0.1 → 6.2 |
