# Spec Map

Where each increment's specification lives: `<home>/specs/<N-M-slug>/spec.md`, with its `DD-NNN` records in `design.md` beside it. The home is the project that owns the increment's rule namespace; when an increment's rules are split across two projects, both parts are named and they share the one rule table (the trace tool reads them as a single source, so a shared row repeated at different tree depths is the same rule). The columns after the home list the rule namespaces.

This table is the reference for a move: it fixes the home before files are touched. A move PR changes the Status column and nothing else here. Homes follow [ADR 002](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/002-modules-are-removable-slices/index.md>) : a rule belongs to the project whose code it constrains.

## Moved (0.x to 10.x)

| Increment | Spec | Home | Rules |
| --- | --- | --- | --- |
| 0.1 | Adopt the template | `specs/` (workspace root) | ADO |
| 0.2 | Elasticsearch infrastructure | `dev/elasticsearch` + `libs/python/aurelius-atlas-store-es` | ESD, STO |
| 0.3 | Test report and traceability | `libs/python/aurelius-atlas-trace` | TRC |
| 0.4 | Parity harness | `libs/python/aurelius-atlas-parity` + `libs/python/aurelius-atlas-trace` | SCN, TRC |
| 0.5 | Server skeleton | `apps/aurelius-atlas-server` | ADM, SRV |
| 0.6 | Dashboards served | `apps/aurelius-atlas-dashboard` + `apps/aurelius-atlas-server` | DSH |
| 1.1 | Typedef models | `libs/python/aurelius-atlas-model` | TDM |
| 1.2 | Type registry | `libs/python/aurelius-atlas-typesystem` | TRG |
| 1.3 | Type hierarchies | `libs/python/aurelius-atlas-typesystem` | THY |
| 1.4 | Typedef store | `libs/python/aurelius-atlas-core` | TDS |
| 1.5 | Built-in models and patches | `libs/python/aurelius-atlas-core` | MDL |
| 1.6 | Types REST | `apps/aurelius-atlas-server` | TYR |
| 2.1a | Entity models | `libs/python/aurelius-atlas-model` | ENT |
| 2.1b | Value types | `libs/python/aurelius-atlas-model` + `libs/python/aurelius-atlas-typesystem` | VAL |
| 2.1c | Entity validation | `libs/python/aurelius-atlas-typesystem` | EVL |
| 2.2 | Entity store | `libs/python/aurelius-atlas-core` | ENS |
| 2.3 | Entity read REST | `apps/aurelius-atlas-server` | ERD |
| 2.4 | Entity write REST | `apps/aurelius-atlas-server` | EWR |
| 2.5 | Delete semantics | `libs/python/aurelius-atlas-core` + `apps/aurelius-atlas-server` | EDL |
| 3.1a | Relationship instances | `libs/python/aurelius-atlas-core` | REL |
| 3.1b | Relationship attributes | `libs/python/aurelius-atlas-core` | REL |
| 3.2 | Ownership cascades | `libs/python/aurelius-atlas-core` | OWN |
| 3.3a | Direct classifications | `libs/python/aurelius-atlas-core` | CLS |
| 3.3b | Bulk classifications | `libs/python/aurelius-atlas-core` | CLA |
| 3.4a | Classification propagation | `libs/python/aurelius-atlas-core` | PRO |
| 3.4b | Propagation tasks | `libs/python/aurelius-atlas-core` | TSK |
| 3.5a | Entity audit | `libs/python/aurelius-atlas-core` | AUD |
| 3.5b | Classification audit | `libs/python/aurelius-atlas-core` | CAU |
| 4.1a | Entity search | `libs/python/aurelius-atlas-core` | SRC |
| 4.1b | Classification search | `libs/python/aurelius-atlas-core` | CSR |
| 4.2a | Free text | `libs/python/aurelius-atlas-core` | FTX |
| 4.2b | Quick search and suggestions | `libs/python/aurelius-atlas-core` | QSR, SUG |
| 4.3 | DSL parser | `libs/python/aurelius-atlas-dsl` | DSL |
| 4.4a | DSL search of entities | `libs/python/aurelius-atlas-core` | DSE |
| 4.4b | DSL projections and traversals | `libs/python/aurelius-atlas-core` | DSP |
| 4.5 | Saved searches and user profile | `libs/python/aurelius-atlas-core` | SVS |
| 5.1 | Lineage | `libs/python/aurelius-atlas-core` | LIN |
| 5.2a | Glossaries and categories | `libs/python/aurelius-atlas-core` | GLS, GCT |
| 5.2b | Glossary terms | `libs/python/aurelius-atlas-core` | GTM |
| 5.2c | Term assignment | `libs/python/aurelius-atlas-core` | GTA |
| 5.2d | Glossary import | `libs/python/aurelius-atlas-core` | GIM |
| 6.1a | Authentication | `apps/aurelius-atlas-server` | AUT |
| 6.1b | The acting user on writes | `apps/aurelius-atlas-server` | USR |
| 6.2a | Authorization: the authorizer, types and admin | `apps/aurelius-atlas-server` | AUZ |
| 6.2b | Authorization: entities and classifications | `apps/aurelius-atlas-server` | AUZ |
| 6.2c | Authorization: search, lineage and type listings | `apps/aurelius-atlas-server` | AUZ |
| 7.0 | Webapp foundation (umbrella) | `apps/aurelius-atlas-webapp` | WBP |
| 7.1 | Webapp shell and localisation | `apps/aurelius-atlas-webapp` | SHL |
| 7.2 | Design system | `libs/angular/aurelius-atlas-ui` | UIC |
| 7.3 | API client and auth wiring | `libs/angular/aurelius-atlas-data-access` + `apps/aurelius-atlas-webapp` | APC |
| 7.4a | Search results | `apps/aurelius-atlas-webapp` + `libs/angular/aurelius-atlas-ui` | SRH, UIC |
| 7.5 | Browse landing page | `apps/aurelius-atlas-webapp` | BRW |
| 7.6 | Entity details | `apps/aurelius-atlas-webapp` | DET |
| 7.7a | Entity editor drawer | `apps/aurelius-atlas-webapp` | EDT |
| 7.11 | Shell chrome | `apps/aurelius-atlas-webapp` | SHC |
| 7.12 | Theme, branding and layout | `apps/aurelius-atlas-webapp` | SHM |
| 7.13 | UI components: details set | `libs/angular/aurelius-atlas-ui` | UIC |
| 7.14 | Settings panel | `apps/aurelius-atlas-webapp` | SPL |
| 7.15 | Alerts drawer | `apps/aurelius-atlas-webapp` + `libs/angular/aurelius-atlas-ui` | ALR |
| 7.16 | UI components: details chrome set | `libs/angular/aurelius-atlas-ui` | UIC |
| 7.17 | Collector ingest auth | `libs/python/aurelius-atlas-otel` + `dev/observability` | CIA |
| 7.18 | Collector ingest identity | `libs/python/aurelius-atlas-otel` + `dev/keycloak` + `dev/observability` | CIA |
| 7.19 | Frontend failure UX | `apps/aurelius-atlas-webapp` | – (no new ids, DD-214) |
| 7.20 | Details data spine | `apps/aurelius-atlas-webapp` | DET |
| 7.21a | Details sections: the seven m4i pages | `apps/aurelius-atlas-webapp` + `libs/angular/aurelius-atlas-ui` | DET |
| 7.21b | Details sections: the entity datasets walk | `apps/aurelius-atlas-webapp` | DET |
| 7.21c | Details sections: producers, consumers, the process page | `apps/aurelius-atlas-webapp` | DET |
| 8.0 | Auxiliary API foundation | `libs/python/aurelius-atlas-auth` + `libs/python/aurelius-atlas-otel` | AUX |
| 8.1 | data2model API | `apps/aurelius-atlas-data2model` | DTM |
| 8.2 | lineage-model API | `apps/aurelius-atlas-lineage-model` | LM |
| 8.3 | validate-entity API | `apps/aurelius-atlas-validate-entity` | VE |
| 8.4 | API client libraries | `libs/python/aurelius-atlas-server-client` + `libs/python/aurelius-atlas-data2model-client` + `libs/python/aurelius-atlas-lineage-model-client` + `libs/python/aurelius-atlas-validate-entity-client` | CL |
| 8.5 | lineage-model circuit breakers | `apps/aurelius-atlas-lineage-model` | LM |
| 8.6 | Aux API failure hardening | `apps/aurelius-atlas-data2model` + `apps/aurelius-atlas-lineage-model` + `apps/aurelius-atlas-validate-entity` | – (cites DTM, LM) |
| 8.7 | Client failure contract | `libs/python/aurelius-atlas-server-client` + `libs/python/aurelius-atlas-data2model-client` + `libs/python/aurelius-atlas-lineage-model-client` + `libs/python/aurelius-atlas-validate-entity-client` | CL |
| 9.1 | Targeted resilience e2e | `apps/aurelius-atlas-webapp` | RSL |
| 9.2 | Server hardening | `apps/aurelius-atlas-server` | SRV (0.5, 9.2, 9.3 share it, by id band) |
| 9.3 | Search cost and client-IP trust | `libs/python/aurelius-atlas-core` + `apps/aurelius-atlas-server` | ENS, SRV |
| 9.4 | Edge tracing | `apps/aurelius-atlas-webapp` | ETR |
| 10.1 | Deployment chart foundation | `helm/` | CHT |
| 10.2 | Stateful platform charts | `helm/` | CHT |
| 10.3a | App and edge charts | `helm/` | CHT |
| 10.3b | Observability chart | `helm/` | CHT |
| 10.6 | Network segmentation | `helm/` | CHT |
| 10.7 | Production identity realm | `helm/` + `dev/keycloak` | CHT |
| 10.8 | Grafana login via the production realm | `helm/` + `dev/observability` | CHT |
| 10.9 | Per-producer ingest credentials | `helm/` + `dev/keycloak` | CHT |
| 10.10 | Digest-pinned images and signed charts | `helm/` | CHT |
| 10.11 | Low-findings hardening | `helm/` | CHT |
| 10.12 | Server authentication, chart wiring | `helm/` | CHT |
