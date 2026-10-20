# Integration Methods

How clients integrate with Aurelius Atlas: request/response over the Atlas REST API, served to browsers and machines alike. The catalogue has **no streaming plane** — the event-streaming slice of the template was removed ([ADR 050](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)), so every integration is a call, and the catalogue's change events are its own store records (audit events arrive with increment 3.5), not a feed.

> [!NOTE]
>
> **Atlas published change events to Kafka — where are they?**
>
> Nowhere, by decision: the event-streaming slice was removed with [ADR 050](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>) and the Kafka hooks are recorded as [DV-01](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/conversion/deviations/index.md>). Integrations that watched the feed poll the REST API instead; the catalogue's own audit records (increment 3.5) are the durable event history.

## Surfaces

Three surfaces, one origin: the **REST API** for machines, the **dashboards** for people (the Atlas UI, served by the catalogue service from the API's origin — DD-018), and the **admin** endpoints for liveness, readiness, and status. Which endpoints answer today, and what each returns, is the server's own documentation: [aurelius-atlas-server](<https://aureliusenterprise.github.io/feat-webapp-port-plan/api-reference/apps/aurelius-atlas-server/index.md>) and its project `README.md`. Every one is byte-for-byte Atlas's in body and status, proven by parity scenarios ([ADR 052](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)); where Aurelius Atlas must answer differently, the difference is a recorded deviation, never a silent one.

## By phase

The [roadmap](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/conversion/index.md>) adds the Atlas resource families in order: types (1.6), entity read/write and delete (2.3–2.5), relationships and classifications (3.x), search and the Atlas DSL (4.x), lineage and glossary (5.x), authentication and authorization (6.1–6.2), import and export of Atlas migration archives (6.3). Each arrives with parity scenarios and, where behaviour differs, a recorded [deviation](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/conversion/deviations/index.md>) — clients integrate against the contract described in [API Management](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/platform/connectivity/api-management/index.md>), not against this page.
