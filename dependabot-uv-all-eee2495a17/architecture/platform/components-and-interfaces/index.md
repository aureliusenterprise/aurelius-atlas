# Components &amp; Interfaces

The parts of the running system (increments 0.2–0.6 today) and the interfaces between them. The production shape is this same set — one service, one store, one identity provider, one signal path — with the deployment supplying certificates and endpoints. The development arrangement mirrors it; where a row describes development, that is labelled.

```
graph LR
    B[Browser] -->|HTTPS: REST| S[Catalogue service]
    S -->|TLS + credentials| E[(Search store)]
    S -->|TLS| O[Signal collector]
    B -->|OIDC| K[Identity provider]
    K -->|TLS| P[(Provider database)]
    O --> G[Signal backends]
```

The catalogue serves browsers and the store serves the catalogue; identity and observation sit beside the path, not on it.

**Current implementations.** The catalogue service is a FastAPI app (`aurelius-atlas-server`), serving on Atlas's own port; the dashboards are the vendored Atlas `dashboardv2`/`dashboardv3`, built from 2.4.0 source; the search store is Elasticsearch 9, reached through `aurelius-atlas-store-es`; the identity provider is Keycloak, on its own Postgres; the collector and the signal backends are an OpenTelemetry Collector with Prometheus, Tempo, Loki, and Grafana (`dev/observability`).

> [!NOTE]
>
> **Where is the event plane?**
>
> Atlas integrations hook a Kafka stream: hook messages in, change notifications out. The catalogue carries no streaming plane — the template's event slice was removed ([ADR 050](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>), [DV-01](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/conversion/deviations/index.md>)) — so every integration is a REST call, and the catalogue's change events are its own store records (audit events arrive with increment 3.5).

| Part | Role | Contract it offers |
| --- | --- | --- |
| Catalogue service | The catalogue's API — Atlas 2.4.0's REST contract; owns the store's lifetime at start-up | HTTPS; configured only through its environment ([ADR 018](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)) |
| Dashboards | The Atlas UI, served by the catalogue service from the API's origin | Static files; the API takes precedence (DD-018) |
| Search store | The only store: system of record and search index at once ([ADR 047](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)) | TLS with certificate verification and credentials |
| Identity provider | The shared sign-in for every authenticated surface ([ADR 007](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/adr/007-one-shared-identity-provider/index.md>)); the examples use it today, the API from 6.1 | OIDC over verified TLS |
| Provider database | The identity provider's own store, and the template examples' — not the catalogue's (ADR 047) | TLS with full verification |
| Signal collector | The single collection point for the system's signals ([ADR 034](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/adr/034-signals-meet-at-one-replaceable-collection-point/index.md>)) | Signals leave the system only through it; a deployment points the exporter at its own collector |

> [!NOTE]
>
> **No endpoint needs a login yet**
>
> The identity provider signs people in today for the template examples, but the API accepts anonymous calls and the session reports no user, groups, or permissions. Authentication arrives with increment 6.1; the difference is recorded as [DV-04](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/conversion/deviations/index.md>) until then.

## Interfaces

The REST contract is Atlas 2.4.0's, proven by parity scenarios ([ADR 046](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>), [ADR 052](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)). The service–store interface is the store library, https-only. Signals leave only through the collector ([ADR 034](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/adr/034-signals-meet-at-one-replaceable-collection-point/index.md>)). Every service-to-service path is TLS with CA verification ([data encryption](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/architecture/platform/security/data-encryption/index.md>)). The endpoint names, ports, and settings of each path belong to the parts themselves: the server's knobs are in [its design documentation](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/api-reference/apps/aurelius-atlas-server/index.md>), the store's in [its library's](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/api-reference/libs/python/aurelius-atlas-store-es/index.md>).

TLS material is per project — declared, issued, and cleaned per project, development material only ([TLS Certificates](<https://aureliusenterprise.github.io/dependabot-uv-all-eee2495a17/contributor-guide/tls-certificates/index.md>)). A deployment serves with its own certificates.
