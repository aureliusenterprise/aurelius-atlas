# 055\. The lineage chain is a named data surface: the auxiliary APIs join the server's surface set

- **Status:** Proposed
- **Date:** 2026-11-08
- **Deciders:** Aurelius Enterprise
- **Supersedes:** the lineage and validate rows of [DD-051](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/conversion/design-log/#dd-051-the-rest-client-ports-the-live-surface-the-search-client-is-redesigned-in-7-4>)

## Decision

**The Aurelius lineage chain is a data surface of Aurelius Atlas, named here.** The legacy application renders its lineage graph from two small backend services — `lineage_model` (flattens a dataset's upstream/downstream `m4i_*_process` relations into archimate rows) and `data2model` (turns those rows into an ar3 model string the diagram library draws) — and a validation mock, `validate_entity`. Aurelius Atlas ports all three as FastAPI services: `apps/aurelius-atlas-lineage-model`, `apps/aurelius-atlas-data2model`, and `apps/aurelius-atlas-validate-entity` (increments 8.1–8.3).

This is the ADR event [054](<https://aureliusenterprise.github.io/feat-aux-apis-data2model/architecture/adr/054-the-server-api-is-the-webapps-one-data-plane/index.md>) requires for a new **data** surface: the auxiliary APIs are the second data surface family of the product, each app deployed at its own origin, named at the deployment boundary (the CSP, increment 8.4) when the webapp starts calling them.

**What 054 keeps.** One token (the Keycloak bearer), one auth library (`aurelius-atlas-auth`, increment 8.0), Atlas's wire-contract discipline — extended to Aurelius-origin endpoints by citing the Aurelius source as the reference (052's rule, applied to a non-Atlas reference: the legacy services in `.scratch/aurelius`). The consolidation rule stands for everything it named: search stays the server's (047), the App Search surface stays unported, and the legacy catalogue APIs (entity, glossary, relationship) stay the server's Atlas paths (046).

**What 054 relaxes, and only here.** DD-051 excluded the lineage and validate clients because "the lineage/validate/dashboard backends are separate services with no Aurelius equivalent" — the exclusion was about a backend that would never exist. This increment builds the backend, so the exclusion retires for lineage and validate. It stands unchanged for the App Search trio (`/elastic`, `/gov_quality`, `/data_quality`) and the dashboard backend: those have no Aurelius Atlas system of record and are not ported.

**The data path is stubbed at first, the API ships real.** 8.1–8.3 read the lineage feed from a configurable Atlas base URL (`GET /v2/lineage/{guid}`) with fixtures; the server's real lineage work is increment 5.1, and the lineage-model app's wiring to it is 5.1's delivery. Shipping the API first keeps each increment one slice (051).

## Context

The webapp track (7.x) ports the screens; the lineage graph is the one screen family whose backend does not exist in this workspace. The legacy chain is small (three services, a few hundred lines each), its contracts are fully readable in source, and the ar3 JSON the diagram library consumes is specified by the legacy parsers — a portable surface with no third-party dependency once `m4i-analytics` is reimplemented natively (DV-15). Leaving it unported would leave the webapp's lineage slices (7.x) permanently unwired.

## Requirements

- **R1 — One identity story.** All three apps verify the same Keycloak tokens through `aurelius-atlas-auth` (8.0's rules AUX-04/05); no app invents an auth path.
- **R2 — One deployment shape.** FastAPI apps with the workspace's Docker, healthcheck, env-prefix, SOPS, and OTel conventions; per-service `otel-<service>` ingest identities (DD-108).
- **R3 — The browser contract is the legacy contract.** The JSON shapes the legacy services return (`{model, metadata}` for data2model, the flattened rows for lineage-model) are kept verbatim; the ar3 string is consumed by the webapp's existing archimate3 parser (7.x) without changes.
- **R4 — Parity cites Aurelius source.** Every rule of 8.1–8.3 names the legacy file it ports; there is no Atlas 2.4 counterpart (these endpoints exist in no Apache product), and no live Java/Aurelius system is run.
- **R5 — The data path lands with 5.1.** 8.x fixtures stand in for the real feed; the apps keep one configurable upstream and no hardcoded host.

## Alternatives

- **Fold the chain into the server.** One app, three route groups: fewer containers, but the server's ADR 046 parity surface gains non-Atlas paths, its image gains the layout engine, and 051's increment sizes break. Refused.
- **Keep m4i-analytics.** Port the legacy ar3 library (pandas, graphviz, bokeh, \~2k lines) as a workspace lib: a dependency of a retired product for a JSON string the webapp only needs to be ar3-shaped. Native reimplementation (DV-15) keeps the browser contract and drops the tree. Refused.
- **Server-side lineage feed first (5.1 before 8.x).** The real data path before the APIs: 5.1 grows lineage semantics without a consumer to specify them, and 8.x stays blocked. Refused — stub first (this ADR's data-path rule).
- **One app for all three services.** One container, `/lineage_model`, `/data2model`, `/validate_entity` route groups: fewer images, but each legacy service has its own scaling, health, and env story, and the user's deployment decision names one app per legacy service. Refused.

## Consequences

- The webapp gains a lineage screen family with a working backend path (8.4+): its CSP widens to the auxiliary origins, named at deployment.
- The deployment topology grows three stateless containers (plus their OTel/Keycloak plumbing, 8.0) — all stateless, no new store; the lineage data stays in the server's store (047), read through `/v2/lineage/{guid}`.
- `deviations.md` records the deliberate divergences: DV-14 (validate-entity ships as the legacy mock), DV-15 (native ar3 layout replaces m4i-analytics), DV-16 (lineage source stubbed until 5.1).
- DD-051's audit note stays as history; its lineage/validate exclusion is superseded **by this record**, its App Search exclusion stands.
