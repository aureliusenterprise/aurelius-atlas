# 7.4a Search results

- **Status:** done
- **Pull request:** –
- **Records:** DD-218 (the 7.4 split; the search bar lands in the search hero, not the navbar; infinite scroll, not pagination), DD-219 (the results URL contract: `?query=` only), DD-220 (the demo pass: legacy count/box/no-results/row-gap typography, the field's icon plate), DD-221 (the empty query lists every entity through `_ALL_ENTITY_TYPES`), DV-83 (result cards render from the search hit), DV-84 (the explore buttons map the m4i governance types to Atlas base types); relies on ADR 053, DD-140, DD-142, DD-143, DD-145, DD-186, DD-188, DD-217 (the search client, consumed as-is), UIC rules (7.2), WBP rules (7.0)

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/feat-otel-edge-tracing/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The first slice with real data: port the Aurelius **search entry points and results screen** — the screen the DD-143 gate held until server 4.1/2.3 and the search client (DD-217) landed. This is the first half of the old 7.4 row, split per DD-218:

- the search subtree chrome (the legacy `SearchComponent`): the hero band wrapping the routed screens, with the ui-lib `search-field` in its title row (DD-218: the hero, not the navbar — the legacy navbar never carried the search bar)
- the results route `search/results` and screen: a basic search (POST `/v2/search/basic`) driven by the `?query=` parameter, an **infinite scroll** list of result cards, the "N results" header, the no-results state, and the filter sidebar **shell**
- the results → details entry: a card click routes to the 7.6 skeleton (`search/details/:guid`) — the entry point the 7.6 deferral table assigns to this slice
- the browse cards' re-added affordances (DD-143, superseding the BRW-06 ban): each context card's search field and explore button, and the governance card's `directToUser` (search the signed-in user's e-mail)
- the sticky navigation loading bar under the pinned navbar (DD-145's remaining half: the navbar and its body padding shipped with 7.11; the bar tracks router navigation, the legacy `models4insight-loading`)
- the ui-lib `infinite-scroll-container` (UIC-21..23): a dumb sentinel + "Load next page..." fallback, the legacy component ported

Explicitly not delivered here, with the increment that will:

| Deferred | Lands with | Why |
| --- | --- | --- |
| Facet sidebar (type/classification counts, toggles, show-more) | 7.4b Search discovery (DD-218) | Facets ride quick-search `aggregationMetrics` (QSR-03), a second call and a new ui-lib component; the shell ships here |
| Typeahead suggestions (`GET /search/suggestions`) | 7.4b Search discovery | The legacy Atlas app has no typeahead at all (the endpoint is unused there) — net-new UX, nothing to port |
| Advanced filters (attribute criteria, tag filters) | 7.4b Search discovery | The DTOs exist (APC-11); the UI is new work beyond the results screen |
| Saved searches | 4.5 (server) + a later 7.x slice | No REST surface exists (`UserProfileService` is planned, spec not written) — local-storage saves are DV-prone |
| DSL / advanced query search | 4.3/4.4 (server) | No parser, no endpoint family (planned) |
| Sort control on results | 7.4b (if kept) | The legacy results screen has none — ordering is relevance, the server default (DD-218 parity) |
| A navbar search bar (DD-145's wording) | Nothing — superseded by DD-218 | The legacy search bar lives in the search hero; the navbar's start slot renders zero buttons in Atlas |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name (TS/e2e tests name the id in the test title, the 7.3/7.5/7.6 pattern).

| Id | Rule |
| --- | --- |
| SRH-01 | The `/search` subtree renders inside a layout component (the legacy `SearchComponent`): the ui-lib `hero` above the routed content, its title the legacy literal "Atlas" (DD-220), and the ui-lib `search-field` in the hero's title row — placeholder `@@search.browse.searchPlaceholder` ("Type your search"). Submitting (`querySubmitted`, Enter/submit/clear) navigates to `search/results` with `queryParams.query` (the legacy `onQuerySubmitted`; clearing submits `null`, read as the empty query). The navbar keeps no search affordance (DD-218; DD-145's bar is the hero's). |
| SRH-02 | `search/results` reads `?query=` as its **only** URL state (DD-219): on arrival and on query-parameter change (the legacy `paramsOrQueryParamsChange` resolver contract, read as a signal), it runs the query — an absent/empty parameter searches `""` **with the `_ALL_ENTITY_TYPES` marker** (DD-221: the server rejects an empty query without a type, SRC-02; the marker is every-entity, SRC-03 — the legacy default that made the explore buttons' landings and the bare URL answer). Pages, filters and scroll state are session state in the layout-scoped store, never in the URL. Leaving the subtree destroys the store (it is provided by the layout component), so a fresh visit to browse resets the search (the legacy `NavigationEnd` reset, by construction). |
| SRH-03 | The query runs as `SearchService.searchWithParameters` — POST `{API_BASE_URL}/atlas/v2/search/basic` (APC-11, DD-188) with `SearchParameters` `{query, limit: 10, offset, excludeDeletedEntities: true}` plus the explore card's `typeName` (SRH-08) — or, for an empty query with no session filter, `typeName: "_ALL_ENTITY_TYPES"` (DD-221). No sort control (SRH-05's relevance parity), no App Search shape (DD-140): the screen reads the `AtlasSearchResult` the server answers. |
| SRH-04 | Results accumulate by page (the legacy infinite scroll): the first page replaces the list; a page request appends `entities` at `offset = pages · 10`; the `infinite-scroll-container`'s sentinel entering the viewport, or a click of its "Load next page..." button (`@@search.components.infiniteScrollContainer.loadNextPage`), requests the next page; `allResultsLoaded` (the list has `approximateCount` entries, the legacy equality rule) stops it; a query change resets to page 1. The list scrolls in its own box (the legacy `max-height: 80vh` result box). |
| SRH-05 | The header reads the count and `@@search.results.results` ("42 results"); each row is one ui-lib `entity-card` (single column) rendered **straight from the `AtlasEntityHeader` hit** (DV-83): `name` = `displayText` (the entity `name` attribute as fallback), `typeName`; no per-card entity fetch — the legacy card's intersection-triggered GET-by-guid served the App Search shape the header contract replaces. A card click routes to `search/details/:guid` (the 7.6 skeleton — the entry its deferral table assigns here); the guid is the `entityClicked` payload. |
| SRH-06 | A search that answers zero entities renders the legacy no-results pair — `@@search.results.noResults` ("No results found") and `@@search.results.anotherQuery` ("Please, try to make another query.") — and no cards, no count header. |
| SRH-07 | The results layout is the legacy two-column Bulma shape: a one-third filter column and the results box. The filter column ships as the **shell**: the legacy empty state `@@search.components.filter.notAvailable` ("No filters available.") with no facet controls (facets are 7.4b; the shell is the layout the 7.4b sidebar fills). |
| SRH-08 | The browse cards re-add their affordances (DD-143 supersedes BRW-06 for these controls): each card's `search-field` + explore button, placeholders and labels from the bridge (`@@search.browse.<context>.searchPlaceholder`, `.exploreButton`). Submit navigates `search/results?query=<text>`; the explore button navigates with the empty query and the card's session type filter (the legacy `directTo*`). The mapping is a model type the server knows, not the m4i dictionary (DV-84): business explores `typeName=AtlasGlossary`, technical explores `typeName=Infrastructure`, governance's explore is `directToUser` — `?query=<the signed-in user's e-mail>` from the Keycloak token (the legacy `directToUser` contract; Atlas has no Person type). The type filters ride the session store (the legacy in-memory filters, SRH-02), not the URL. BRW-06's "no route to results" ban is replaced by "the affordances are the search slice's, delivered here". |
| SRH-09 | The sticky navigation loading bar returns (DD-145): a Bulma `progress.is-link` fixed under the pinned navbar (the legacy `.sticky` at the navbar's foot, `z-index: 10`), visible from `NavigationStart` to `NavigationEnd`/`NavigationError` — router navigation only (the legacy `isNavigating`), not HTTP. It is the last deferred half of the 7.11 chrome. |
| SRH-10 | Every string on the new surfaces is a bridge key that **already exists** in both catalogues (WBP-05, DD-144 — `search.results.*`, `search.components.infiniteScrollContainer.loadNextPage`, `search.components.filter.notAvailable`, `search.browse.*`); the completeness gate (SHL-08) proves both locales. No new keys: the vendored dictionary covers the slice. |
| SRH-11 | Zoneless Angular idiom (WBP-02..04, purity gate): standalone, OnPush, signals, `inject()`; the results state is a signal store under `search/`, the layout's search store layout-scoped (SRH-02); the `infinite-scroll-container` is a dumb ui-lib component — content projection, `input()`/`output()` only, no services, no HTTP — with a Storybook story (UIC rules); the app owns routing and HTTP, the lib owns rendering. |

The ui-lib carries its UIC ids on (7.13's UIC-11..15, 7.16's UIC-16..20):

| Id | Rule |
| --- | --- |
| UIC-21 | `infinite-scroll-container` projects its content, and below it a sentinel + fallback row shown while `!allLoaded()`: a `button.is-fullwidth.is-loading`-capable button labelled `loadLabel()` (caller-supplied, the DD-136 rule; the legacy default "Load next page..."), which emits `nextPage()` on click and while `loading()` shows the Bulma spinner. |
| UIC-22 | The sentinel (the legacy `IntersectionObserver` directive, inlined: the DOM behaviour belongs to the component that owns the sentinel) emits `nextPage()` when it enters the viewport, `loading()` or `allLoaded()` suppressing re-triggers. No `IntersectionObserver` in the environment (jsdom) → the button remains the working path (the legacy keyboard/no-API fallback, by construction). |
| UIC-23 | Story with a `play()` interaction: scrolling the sentinel into view and clicking the button each emit `nextPage()`; `allLoaded()` removes the row (the UIC-10/20 pattern); purity gate green. |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit pinned by 7-0):

- `apps/atlas/src/app/search/search.component.{ts,html}` + `search-routing.module.ts` — the subtree chrome: hero (`title="Atlas"`) with the `simple-search-input` (`onQuerySubmitted` → `/search/results?query=`), the `NavigationEnd` store reset — SRH-01/02/08's shape
- `search/results/results.component.{ts,html,scss}` + `query.resolver.ts` + `results-filter.service.ts` — the results screen: the filter column + results box, "N results", the no-results pair, the `80vh` scroll box. Its data services (`AppSearchResultsService`, `EntitySearchResultsService`, the `elastic` POST) are the DD-140 stack this slice does **not** port — SRH-03 replaces them with `/v2/search/basic`
- `search/components/infinite-scroll-container/` (+ `libs/directives` `intersection-observer`, `libs/services` observer provider) — UIC-21..22
- `search/components/cards/details-card.component.{ts,html}` — the per-card lazy fetch DV-83 replaces; its shell is the 7.13 `entity-card` (UIC-12)
- `search/browse/business-context/`, `technical-context/`, `governance-responsibilities/` — the `simple-search-input` + `directTo*`/`directToUser` methods deferred by DD-143; their filters (`sourcetype`, `supertypenames`, `typename: m4i_person`) map per DV-84
- `libs/shell/src/lib/shell.component.html` + `loading/` — the sticky block: `position: fixed; top: 4.25rem; z-index: 10`, the `progress.is-link` bar on `isNavigating` — SRH-09

## Deviations

Against Apache Atlas: none — this slice is an Aurelius product screen; Atlas's own search UI is its dashboard (ADR 046, the parity reference stays untouched).

Against the Aurelius product, in the [design log](<https://aureliusenterprise.github.io/feat-otel-edge-tracing/architecture/conversion/design-log/index.md>) and [deviations](<https://aureliusenterprise.github.io/feat-otel-edge-tracing/architecture/conversion/deviations/index.md>):

- **DV-83** — result cards render straight from the search hit (`AtlasEntityHeader`: `displayText`, `typeName`). The legacy card fetched each entity lazily on viewport intersection because the App Search response carried only identity; the Atlas search contract (SRC-09) answers headers with display text, so the fetch is dead weight.
- **DV-84** — the explore buttons filter on model types the server knows (`AtlasGlossary`, `Infrastructure` — a plain `Glossary` answers `UNKNOWN_TYPENAME`, SRC-03) and `directToUser` searches the plain e-mail: the legacy `m4i_data_domain` / `m4i_system` / `m4i_person` filters name Aurelius's own type model, which Aurelius Atlas does not ship (ADR 046 keeps Atlas's).
- **DD-218** — the split itself (the 7.4 surface exceeds the one-PR budget, AGENTS.md); the search bar lands in the search hero (the legacy fact; amends DD-145's "navbar search bar" wording, superseding it); infinite scroll is kept, not replaced by the ui-lib `pagination` (the legacy UX is the product UX; `Pagination` stays unused here).
- **DD-219** — the results URL is `?query=` only (the legacy resolver, which read nothing else), so deep links carry the query and the store carries the rest. This deliberately forgoes shareable filter/sort URLs: with no facets (7.4b) there is nothing to share beyond the query, and inventing a parameter grammar the legacy app lacks is the speculative design DD-140 refuses.

## Acceptance

- Vitest (unit, `nx test aurelius-atlas-webapp -c ci`):

  - `search/search-layout.component.spec.ts` — hero + search field render, submit navigates `search/results?query=` (SRH-01, SRH-08's navigation half), clearing submits the empty query; store resets on destroy (SRH-02)
  - `search/results/results.component.spec.ts` (HttpTestingController) — the POST `/atlas/v2/search/basic` body `{query, limit: 10, offset: 0, excludeDeletedEntities: true}` (SRH-02/03); count header (SRH-05); sentinel/ `nextPage` appends page 2 at `offset: 10` and stops at `approximateCount` (SRH-04); a query change re-POSTs at `offset: 0` (SRH-04); card rows from the hit, no second request per card (SRH-05, DV-83's proof: zero outstanding requests after the search answers); card click routes to details (SRH-05); zero-count renders the no-results pair (SRH-06); filter column renders "No filters available." only (SRH-07)
  - `search/search-state.spec.ts` — pages accumulate, query change resets, reset on destroy, type filter rides session state (SRH-02/04/08)
  - `search/browse/*` card specs — field + explore button render (SRH-08), submit navigates with the query, explore navigates with the empty query + the card's type filter, governance explore uses the Keycloak e-mail (SRH-08); info-modal tests (BRW-03) and `#browse-placeholder` (BRW-01) stay green; the BRW-06 "no search affordance" spec is replaced per SRH-08's note
  - `shell/nav-loading-bar.component.spec.ts` — visible on `NavigationStart`, hidden on `NavigationEnd`/`NavigationError` (SRH-09)
  - `routes.spec.ts` — `search/results` lazy-loads the screen inside the layout (SRH-02); `i18n-completeness.spec.ts` — every id used exists in both catalogues (SRH-10)
- Vitest (ui-lib, `nx test aurelius-atlas-ui -c ci`):

  - `infinite-scroll-container.component.spec.ts` — sentinel enter + button click emit `nextPage` (UIC-21/22), `loading` suppresses and decorates, `allLoaded` removes the row (UIC-21)
- Storybook: `infinite-scroll-container.stories.ts` with the `play()` interaction (UIC-23)
- e2e (`nx e2e aurelius-atlas-webapp`, real server behind the proxy — DD-142, DD-217):

  - the search flow: seed entities through the proxy (`POST /api/atlas/v2/entity/bulk` — the server is open pre-6.1), sign in, type the seeded names in the hero field, submit → results show the seeded names + the count (SRH-01..05); click a card → the details skeleton at its guid (SRH-05); nl-NL renders "resultaten" (SRH-10). The seeds are single-word names carrying a run-unique token: Atlas matches free text word-exactly (FTX-01) and the shared dev stack keeps every run's seeds, so multi-word names would match earlier runs too. The flow submits on the button: the native `search`-on-Enter the legacy input relies on is Chromium-only.
  - the explore flow: the business card's explore lands on results rendering the seeded glossary, no query in the URL (SRH-08, DV-84)
  - a query that matches nothing renders the localized no-results pair (SRH-06)
- Purity gate green (SRH-11); umbrella checks: `nx build aurelius-atlas-webapp`, `nx lint`, both projects; example app untouched.

### Definition of done, in order

1. `nx test aurelius-atlas-webapp -c ci` and `nx test aurelius-atlas-ui -c ci` green.
2. `nx build aurelius-atlas-webapp`, `nx lint` both projects, purity gate green.
3. `nx e2e aurelius-atlas-webapp` — the search and explore flows green.
4. Spec status → `done`, roadmap rows 7.4a flipped, DD-218/219 accepted, DV-83/84 recorded, the 7.5/7.6 deferral rows marked delivered.
