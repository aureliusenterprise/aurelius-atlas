# 7.6 Entity details

- **Status:** in progress
- **Pull request:** [\#109](<https://github.com/aureliusenterprise/aurelius-atlas/pull/109>)
- **Records:** DD-186 (details skeleton: route contract, gated data), DD-187 (the entity client grows with server 2.3), DD-188 (one API base: the client's URLs all ride the `API_BASE_URL` token, ADR 054); relies on ADR 053, DD-140, DD-143, UIC-11..13 (7.13), WBP rules (7.0)

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

Port the Aurelius **entity details screen** (`search/details`) — the screen the router shows for one entity by GUID — as the **routed skeleton the data-free webapp can host today**, and wire its chrome to the dumb components 7.13 already ships:

- the route `search/details/:guid`, replacing the subtree route-by-route pattern 7.1 declared for it (`search.routes.ts`)
- the details header: the entity title (name, qualified name as its fallback), the type-name line, and the breadcrumbs trail (the 7.13 `breadcrumbs`, with `activeGuid` and the caller-routed `itemClicked`)
- the section shell: description box, properties accordion, and the side navigation — the shape of the legacy `default` details component, composed from Bulma and the 7.13 `properties-item`
- `AtlasEntitiesService` in `aurelius-atlas-data-access`: the client method set for `GET /api/atlas/v2/entity/guid/{guid}` (the Atlas `EntityREST` shape, increment 2.3), built test-first against the wire format read from the Atlas source — the method the screen wires to when 2.3 lands

This is 7.5's gated-slice shape (DD-143), applied to a screen whose content is entirely data: every Aurelius details section reads one resolved entity, and server 2.3 (entity read REST) is planned, not built. The slice that ships the **live** details screen is the 2.3+7.6 wiring increment, named in the deferral table; it lands the nine type-specific components, the lineage view, and the governance-quality cards.

Explicitly not delivered here, with the increment that will:

| Deferred | Lands with | Why |
| --- | --- | --- |
| Fetching the entity (resolver, loading, not-found, header data) | The 2.3+7.6 wiring increment | `GET /v2/entity/guid/{guid}` is increment 2.3 (planned); a fetch against a 404 is the speculative build DD-140 refuses |
| The nine type-specific components (domain/entity/attribute/field/dataset/collection/system/person/process) | The 2.3+7.6 wiring increment | They are m4i governance-type layouts (`m4i_data_domain`, …) — Aurelius's own type model, meaningless without entity data |
| Lineage view, governance-quality cards, data-quality lists/pies | The 2.3+7.6 wiring increment (+ lineage backend) | Lineage is server 5.1; the quality cards post to Aurelius backends Aurelius Atlas does not have (DD-140) |
| Classifications list, glossary terms (`meanings`), edit affordance (`DATA_STEWARD`), people, domains | Later 7.x slices (7.8, 7.9) + 3.3/3.4, 6.2 | Each is a feature whose server increment is planned, not built |
| Search entry into details (results page) | **Delivered in 7.4a** — a card deep-links this skeleton (SRH-05) | The gate lifted with the search client (DD-217); the entity fetch stays 2.3's (DET-02) |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name (TS/e2e tests name the id in the test title; `@pytest.mark.covers` applies to the client spec, in the lib's Python-free Vitest suite — the rule ids ride the test names, the 7.3 pattern).

| Id | Rule |
| --- | --- |
| DET-01 | `/search/details/:guid` renders the details skeleton: the header block (title slot, type-name line, breadcrumbs trail), the description box, the properties accordion, and the side navigation — the legacy default layout's shape (its `default-details` anatomy), in Aurelius's palette. The `:guid` is a route parameter the skeleton keeps in a signal; it is the screen's address. |
| DET-02 | The skeleton is empty-state, not fake-state (DD-186): with no entity (all states, 2.3 absent), the title falls back to the localized `search.details.typeSelect.label` ("Entity type" — the chrome's type label), the breadcrumbs trail renders nothing (the 7.13 `breadcrumbs` empty guard), the description box is empty, and the properties accordion holds zero rows (its count reads 0). No placeholder data, no mock entity, no loading state. |
| DET-03 | `AtlasEntitiesService.getEntityByGuid(guid)` is the one client method for `GET {API_BASE_URL}/atlas/v2/entity/guid/{guid}` — composed from the injected token, no second base URL anywhere (DD-140's one-method rule, APC-01, the consolidated-server rule of ADR 054/DD-188, the typedefs client's pattern): the wire DTOs (`AtlasEntity`, its `relationships`, `classificationNames`, `relationshipAttributes.meanings`) are typed from the Apache Atlas 2.4.0 source (`intg/.../model/instance/AtlasEntity.java`, `EntityREST.java`), cited at the type. Specs use `HttpTestingController` — the method is honest against the wire format, and answers 404 against today's server; no screen calls it (DET-02). |
| DET-04 | Every chrome string is a `@@search.details.*` id with entries in both fixture locales (WBP-05, the DD-144 bridge rule); the skeleton uses the keys the bridge already carries (`search.details.default.description`, `search.details.default.properties`, `search.details.components.properties.key`/`.value`, `search.details.components.navigation.details`, `search.details.typeSelect.label`). The completeness gate (SHL-08) proves both locales. |
| DET-05 | The screen is zoneless/Angular idiom (standalone, OnPush, signals, `inject()`) and the dumb parts stay dumb (WBP-02..04, purity gate): the header's crumbs arrive as the 7.13 `breadcrumbs` component's `items`/`activeGuid` inputs; the properties rows are `properties-item`s; the screen owns state, the lib owns rendering. |
| DET-06 | The breadcrumbs' `itemClicked(guid)` navigates the details route to that guid (the caller-routes contract, DD-154's sibling); the skeleton wires the router, the lib component never does. |
| DET-07 | The details route is deep-linkable (ALR-01's pattern, the drawer route's proof): a direct visit to `/search/details/<guid>` (authenticated) renders the skeleton — the URL is the whole state, as 2.3+7.6 will make it. e2e (authenticated): the skeleton renders at the deep link in every browser; the header shows the localized section titles. |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit pinned by 7-0), `apps/atlas/src/app/search/details/`:

- `details.component.{ts,html}` — the type-dispatch shell (`componentsByType`, nine `m4i_*` types + default), the header (title, type name, classifications, terms, breadcrumbs, the `DATA_STEWARD` edit icon) — its data services (`EntityDetailsService`, `ElementSearchService`, the App Search providers) are the DD-140 stack this slice does not port
- `details-routing.module.ts` / `details.resolver.ts` — the `:id` route and its resolver (the resolver's fetch is 2.3-gated)
- `default/default-details.component.{ts,html}` — the default section layout (description box, property-count level, properties accordion, side nav) — the shape DET-01/02 port
- `components/properties/`, `components/navigation/` — the properties table (its item is the 7.13 `properties-item`) and the section nav
- `apps/atlas/src/app/search/components/bread-crumbs/` — the trail, ported in 7.13 as the ui-lib `breadcrumbs`; `details.component.html` shows its call site

## Deviations

None against Apache Atlas: this slice is an Aurelius product screen; Atlas's own details UI is its dashboard (ADR 046, the parity reference stays).

Against the Aurelius product, one intended difference is recorded in [design-log](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/conversion/design-log/index.md>): the details screen is ported as a **routed skeleton** (DD-186) — its data spine (entity fetch, type dispatch, lineage, quality) arrives with the 2.3+7.6 wiring increment, because the server's entity read REST (2.3) is planned and every Aurelius details section reads one resolved entity. The client method (DET-03) is built test-first against the Atlas wire format so the wiring increment is composition, not design (DD-187).

## Acceptance

- Vitest (unit):

  - `libs/angular/aurelius-atlas-data-access/src/lib/atlas/atlas-entities.service.spec.ts` — `getEntityByGuid` hits `…/v2/entity/guid/<guid>` with the Atlas headers, maps the DTO, encodes the guid (APC-01's base-url rule, DET-03)
  - `search/details/details.component.spec.ts` — the skeleton renders at the route (DET-01), empty-state per DET-02 (title fallback, no crumbs, zero property rows), strings from the catalogue (DET-04), `itemClicked` navigates the route (DET-06), no outstanding `HttpTestingController` requests (the screen fetches nothing — DET-02's proof)
  - `routes.spec.ts` — `search/details/:guid` loads the component (DET-01)
  - `i18n-completeness.spec.ts` — every `@@search.details.*` id used by the skeleton exists in both catalogues (DET-04)
- e2e (`nx e2e aurelius-atlas-webapp`): the deep link renders the skeleton in every browser, localized titles visible (DET-07)
- Storybook: the 7.13 components already carry the stories (UIC-15); the screen is app-side, no new story
- Purity gate green (DET-05); umbrella checks (`nx build`, `nx test -c ci`, `nx lint`, `nx e2e`, both projects); example app untouched.

### Definition of done, in order

1. `nx test aurelius-atlas-webapp -c ci` and `nx test aurelius-atlas-ui -c ci` green.
2. `nx build aurelius-atlas-webapp`, `nx lint` both projects, purity gate green.
3. `nx e2e aurelius-atlas-webapp` — the deep-link scenario green in the chromium/firefox/webkit matrix.
4. Spec status → `done`, roadmap row flipped, design-log DD-186..187 accepted.
