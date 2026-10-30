# 7.0 Webapp foundation (umbrella)

- **Status:** planned
- **Pull request:** –
- **Records:** ADR 053; DD-126 to DD-131

## Scope

This is an **umbrella**, not a buildable increment: it fixes the shape of the 7.x track and the rules every slice in it obeys. Each 7.x slice is specified and delivered in its own pull request ([ADR 051](<https://aureliusenterprise.github.io/feat-chart-prod-realm/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)).

The 7.x track rewrites the Aurelius Atlas web interface in this workspace as `apps/aurelius-atlas-webapp` ([ADR 053](<https://aureliusenterprise.github.io/feat-chart-prod-realm/architecture/adr/053-the-webapp-is-rewritten-in-angular-idiom-slice-by-slice/index.md>)). The starting material is `apps/atlas` plus the 20 `@models4insight/*` libraries of the `aureliusenterprise/aurelius` repository (Angular 17.3, 62 NgModules, a custom Redux wrapper).

**What every slice in this track must satisfy**, stated once here and referenced by each increment's Acceptance:

- **No `NgModule`** in new code: standalone components, `bootstrapApplication`, zoneless change detection. The workspace has no `@angular/platform-browser-dynamic` to fall back on.
- **State is signals**: `signal()` and `computed()`, following the signal-service pattern of `aurelius-atlas-frontend-example`. A slice that carries a `BehaviorSubject` store forward has not delivered its slice (ADR 053 R3).
- **Presentational components are dumb and shared**: `input()`/`output()` only, no side-effect services, living in `aurelius-atlas-ui`, with a story. Brand tokens from `@aurelius/atlas-brand`, never redefined colours (ADR 053 R7).
- **Tests come with the slice**: Vitest for logic, one Playwright scenario for the capability, the Aurelius Jest assertions re-expressed not dropped (ADR 053 R5). Coverage gates hold.
- **Localisation is built-in `@angular/localize`** with XLIFF, not `ngx-translate`.
- **No hard-coded endpoints**: runtime `AppConfig` from `/config.json`, base URL supplied by `aurelius-atlas-data-access`.

### The slices, in build order

Ordered so that a slice depends only on slices before it. Slices 7.1–7.2 need no catalogue API, which is what makes 7.1 the safe place to stand up the project.

| \# | Slice | Depends on |
| --- | --- | --- |
| 7.1 | [Shell and localisation](<https://aureliusenterprise.github.io/feat-chart-prod-realm/architecture/conversion/increments/7-1-webapp-shell/index.md>): project, bootstrap, router, i18n bridge, OTel telemetry | – |
| 7.2 | Design system: legacy shared components → `aurelius-atlas-ui` dumb components + stories | 7.1 |
| 7.3 | API client: `libs/atlas/api` (65 files) → `aurelius-atlas-data-access`, Keycloak auth wiring | 7.1 |
| 7.4 | Search: query and results, the first slice with real data | 7.2, 7.3 |
| 7.5 | Browse: domain browse, card grids | 7.4 |
| 7.6 | Entity details: header, attributes, relationships, lineage view | 7.4 |
| 7.7 | Create and edit entity: forms, validation | 7.4, 7.6 |
| 7.8 | Governance quality, classifications, domains | 7.6 |
| 7.9 | Delete, audit, and the remaining detail cards | 7.6 |
| 7.10 | Serving, and retirement of the example app | 7.1 – 7.9 |

### Not in scope

| Not delivered here | Delivered by |
| --- | --- |
| Any catalogue REST endpoint the server does not answer yet | increments 1.x – 6.x |
| Authentication and authorisation semantics | 6.1, 6.2 (wired here, not built) |
| Apache Atlas `dashboardv2` / `dashboardv3` changes | not planned (ADR 046, DD-001) |
| Migration of a live Aurelius deployment | not planned |

## Semantics

The umbrella's own rules; the slice rules (`SHL-NN`, and each later prefix) live in their increment.

| Id | Rule |
| --- | --- |
| WBP-01 | `aurelius-atlas-webapp` builds in this workspace on the workspace's Angular, Nx, and TypeScript, with no dependency on the Aurelius repository |
| WBP-02 | No `NgModule`-decorated class, and no `@models4insight/*` import, exists in `aurelius-atlas-webapp` or in the Angular libraries it consumes |
| WBP-03 | No `BehaviorSubject`/`Subject`-owned application state exists in the webapp: state is a `signal`, derived state a `computed` |
| WBP-04 | A presentational component in `aurelius-atlas-ui` declares only `input()`/`output()` (or `model()`), injects no service with side effects, and has a story |
| WBP-05 | Every user-visible string is a localisation unit: no literal prose reaches a template, and the `nl-NL` XLIFF catalogues the whole surface in scope |
| WBP-06 | The Aurelius app keeps building and serving in its own repository throughout; the port adds nothing to it |
| WBP-07 | The Apache Atlas dashboards keep being served and keep passing their parity checks; the 7.x track changes nothing in them |

## Java origin

None. The 7.x track ports an Angular front end written by Aurelius, not Apache Atlas code, so there is no `release-2.4.0` class to cite and ADR 052's scenario format does not apply. The origin is the Aurelius source, cited by path:

- `apps/atlas/src/app/` — the screens: `search/{browse,results,details,create-entity,edit-entity, meta,components,services,utils}`, `dashboards/{domains,mockups}`
- `libs/atlas/api/src/` — the Atlas REST client: `atlas`, `elastic`, `gov-quality`, `types`
- `libs/redux/src/` — the custom store replaced by signals
- `libs/core/src/lib/core.ts` — `Core.imports`, the module graph being dissolved
- `libs/{components,utils,shell,repository,directives,permissions,authentication,i18n}` — shared code

## Deviations

- **DV-64**: Aurelius Atlas serves a web interface of its own design once 7.10 lands, where Apache Atlas 2.4.0 serves its two dashboards. The REST contract is unaffected; the parity harness keeps reading the Atlas dashboards as the reference. Added to [Deviations](<https://aureliusenterprise.github.io/feat-chart-prod-realm/architecture/conversion/deviations/index.md>).

## Acceptance

The umbrella is accepted when 7.1 lands and demonstrates the shape, and each slice thereafter carries its own acceptance in its specification. Checks that every slice must pass:

```
nx build aurelius-atlas-webapp
nx test aurelius-atlas-webapp -c ci
nx test aurelius-atlas-ui -c ci
nx lint aurelius-atlas-webapp
nx e2e aurelius-atlas-webapp
```

WBP-02 and WBP-03 are checked by grep over the tree as well as by review, so a `NgModule`, a `@models4insight` import, or a state-owning `Subject` cannot arrive unnoticed.
