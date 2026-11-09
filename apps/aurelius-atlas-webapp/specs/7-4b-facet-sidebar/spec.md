# 7.4b Search discovery: the facet sidebar

- **Status:** done
- **Pull request:** #297
- **Records:** DD-424 (quick search replaces the basic search, one call answers the
  page and the counts, `includeSubTypes` rides `true`), DD-425 (the facet selection
  stays session state, the record DD-219 reserved for 7.4b), DD-426 (only the type
  facet filters, narrowed counts keep seen values visible), DD-427 (the sidebar
  ships as one dumb ui-lib component with four new bridge keys). DV-143 (facet
  counts narrow, non-type facets display only). Relies on DD-093/QSR-01..04 (server
  4.2b, shipped), DD-217 (the search client, its `quickSearch` consumed as-is),
  DD-218/219/220/221 and SRH rules (7.4a, amended here as noted), DD-128 (the
  catalogue bridge), UIC rules (7.2), WBP rules (7.0)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01 to WBP-07 this
slice inherits. This is the first cut of the 7.4b roadmap row: the facet sidebar. The row's
other two parts move to a later slice, listed under Scope.

## Scope

Fill the filter column that 7.4a shipped as a shell (SRH-07): the **facet sidebar**
above the results list, fed by the quick-search endpoint the server has answered since
increment 4.2b (`POST`/`GET /api/atlas/v2/search/quick`, QSR-01..04). One call answers
the page of results and the facet counts together, so the results store switches from
the basic search to the quick search instead of adding a second request (DD-424, SDX-01).

Delivered here:

- the store's endpoint swap: quick search with the same page shape (SRH-03 amended,
  SDX-01/02), a facet signal fed by `aggregationMetrics`
- the ui-lib `facet-list` component (UIC-33..35): Bulma menu per facet, checkbox rows
  with counts, five values then "Show more" (the legacy `filter`/`facet`/`check-box`
  shape, `.scratch/aurelius`)
- the type facet's interaction: checkboxes filter, multi-select, session state
  (SDX-04..07, DD-426)
- `__state`, `Asset.owner`, and `ServiceType` rendered read-only (SDX-05)
- four new bridge keys for the facet titles, both locales (SDX-08):
  `search.components.filter.type` (Type / Type), `.state` (State / Status),
  `.owner` (Owner / Eigenaar), `.serviceType` (Service Type / Servicetype).
  SRH-10's "no new keys" fact ends here: the slice extends the vendored fixtures and
  regenerates the XLIFF (the DD-128 route, the `search.createEntity` precedent)

Explicitly not delivered here, with the increment that will:

| Deferred                                           | Lands with                         | Why                                                                                                      |
| -------------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Typeahead suggestions (`GET /search/suggestions`)  | 7.4c Search discovery: suggestions | Net-new UX with no legacy copy (the roadmap row's own wording), its own spec, small and independent      |
| Advanced filters (attribute criteria, tag filters) | 7.4c (or a later 7.x)              | The DTOs exist (APC-11) but quick search answers no facets for them; the UI is a design task of its own  |
| A sort control on results                          | Nothing — 7.4a's ruling stands     | The legacy results screen has none, ordering stays relevance (DD-218)                                    |
| Facets in the URL                                  | Nothing — DD-425                   | The legacy app kept filters in the in-memory store, and DD-219's URL rule stands (recorded, not changed) |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
(the 7.3/7.5/7.6 pattern: the TS test title names the id).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDX-01 | The results store runs the search as `SearchService.quickSearch` — POST `{API_BASE_URL}/atlas/v2/search/quick` (QSR-01) with the body `{query, limit: 10, offset, excludeDeletedEntities: true, includeSubTypes: true}` (DD-424: `includeSubTypes` must ride `true` because the quick-search model defaults it `false`, unlike the basic search's `true` (SRC-01) — without it the explore buttons' subtype listings (SRH-08) stop answering), plus `typeName` when a facet selection or an explore filter is set (the values joined by `,`, SRC-03) or the `_ALL_ENTITY_TYPES` marker when the query is empty with no selection (DD-221 unchanged). The entities and `approximateCount` are read from the answer's `searchResults` (SRC-09 nested one level). SRH-04's paging, SRH-05's cards, SRH-06's no-results pair, and SRH-08's explore buttons are unchanged except through this row (SRH-03, SRH-08's transport amended). |
| SDX-02 | One call answers both: `aggregationMetrics` arrives in the same answer as the page (QSR-02/QSR-03). The store keeps no second request for the counts, and the sidebar re-renders from every page's answer (the counts are unpaged, DD-093, so they are stable across pages).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| SDX-03 | The sidebar renders the facets in the order the server answers them (`__typeName`, `__state`, `Asset.owner`, then `ServiceType` when present, QSR-03/QSR-04), and skips a facet whose list is empty (the legacy `FilterService` dropped empty facets, so an owner-less sample renders three menus, not four). With every facet empty the column keeps rendering SRH-07's shell text (`@@search.components.filter.notAvailable`, unchanged). The column shows only with results, as 7.4a shipped it (SRH-07).                                                                                                                                                                                                                                                                                                                                                                                                                       |
| SDX-04 | The `__typeName` facet is interactive (DD-426): a Bulma menu of checkbox rows (UIC-33), each row the value's display label and its count in parentheses; ticking or unticking a value updates the session selection and restarts the search at page one (SRH-04's restart rule). The checked values are the `typeName` list of SDX-01.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| SDX-05 | `__state`, `Asset.owner`, and `ServiceType` render as read-only rows (the value and its count, no checkbox): the quick-search contract takes no parameter that a click could send (QSR-01's scope), and `excludeDeletedEntities` is fixed `true`, so `__state` answers `ACTIVE` alone (DV-143).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| SDX-06 | The selection is session state (DD-425): `search/results?query=` stays the whole URL contract (DD-219 unchanged). A hero submit clears the selection (the rule SRH-02 already had for the explore filter, now for the facet selection too); a URL query change keeps it (the resolver kept the legacy store's filters). Leaving the subtree destroys it with the store (SRH-02).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| SDX-07 | Counts narrow with the selection (QSR-03 counts what the query matches, types included). The sidebar keeps every value it has shown for the current query visible: a narrowed answer replaces the counts it carries, and a value it no longer carries keeps its last count (DD-426). The seen set resets when the query changes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| SDX-08 | Labels: each facet title rides a bridge key (`@@search.components.filter.type`, `.state`, `.owner`, `.serviceType` — new, extended into both fixture catalogues and regenerated, DD-128; the completeness gate SHL-08 proves both locales). Show-more, show-less, and the shell text ride the existing keys (`search.components.filter.facet.showMore`/`showLess`, `.notAvailable`). A type value renders through `nameDisplay` (DD-379, the same map the card badges use), `ACTIVE` and service-type values render raw — the legacy's missing-key answer. The wire value is what filters and what is sent, never the label (EDT-16's rule).                                                                                                                                                                                                                                                                                       |
| SDX-09 | Zoneless Angular idiom (WBP-02..04, purity gate): the facet state lives in the layout-scoped `SearchState` signal store; `facet-list` is a dumb ui-lib component (UIC rules): `input()`/`output()` only, no services, no HTTP, a Storybook story with a `play()` interaction; the app owns routing and HTTP, the lib owns rendering.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

The ui-lib carries its UIC ids on (7.4a's UIC-21..23, the series last used by 7.21a's UIC-28):

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| UIC-33 | `facet-list` renders a Bulma `menu` per facet (the legacy `facet.component.html` shape): `p.menu-label` with the caller's title, then a `ul.menu-list`. Each value row is the caller's label plus `&nbsp;(count)` when a count is present, the legacy `check-box.component.html` text minus its form control.                                                                                                                                                                              |
| UIC-34 | With `selectable`, a row is a `label.checkbox` over an `input[type=checkbox]` and emits `toggled(value, checked)` (the legacy checkbox's `updateFilterSelection` contract). Without it, the row is plain text (read-only facets, SDX-05). Past five values the list adds the legacy "Show more" / "Show less" link (`@@search.components.filter.facet.showMore`/`showLess`, caller-supplied labels per DD-136), and showing all is the component's own state (the legacy `showMore` flag). |
| UIC-35 | Story with a `play()` interaction: ticking a row emits `toggled`, "Show more" reveals the hidden rows (the UIC-10/20/23 pattern); purity gate green.                                                                                                                                                                                                                                                                                                                                       |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit pinned by 7-0):

- `apps/atlas/src/app/search/components/filter/filter.component.{ts,html}` — the
  sidebar: a facet menu per non-empty facet, the `#noFilters` twin this slice replaces
  with it (SRH-07's shell)
- `search/components/filter/facet/facet.component.{ts,html}` — the Bulma menu, the
  five-value slice and the show-more link (UIC-34)
- `search/components/filter/check-box/check-box.component.{ts,html}` +
  `check-box.service.ts` — the checkbox row and the toggle-in-the-selection store
  contract (UIC-33/34); its label/count markup without its form control (WBP-02:
  signals, no reactive forms)
- `search/services/filter/filter.service.ts` — empty facets dropped, keys kept in
  answer order (SDX-03)
- The legacy `SearchService`/App Search plumbing behind the toggles is **not** ported:
  the legacy selection rode the App Search query object, and DD-140 replaced that
  stack with the Atlas search contract. SDX-01/04 are the Atlas reading of the same
  interaction.

There is no Java origin: the endpoint's Apache Atlas origin is cited and ported in
server increment 4.2b (`libs/python/aurelius-atlas-core/specs/4-2-quick-search/`), and
Atlas's own dashboard shows no facet sidebar (ADR 046). This slice is the Aurelius
product screen over the shipped contract.

## Deviations

Against Apache Atlas: none — the contract is server 4.2b's, ported with its parity
scenarios. This slice consumes it.

Against the Aurelius product, in the [deviations](../../../../docs/architecture/conversion/deviations.md)
list (DV-143, entered with the implementation PR):

- **DV-143** — the facet sidebar narrows its counts with the selection, and only the
  type facet is interactive. The legacy App Search self-faceted (a facet's own field
  excluded from its counts, so every value kept its count) and every facet was a
  checkbox over the App Search query object. Atlas quick search counts the entities
  its query matches (QSR-03), and `__state`, `Asset.owner`, and `ServiceType` have no
  quick-search parameter, so a click there could send nothing.

Against 7.4a, recorded as amendments where the rule names them:

- **DD-424** — SRH-03's basic search becomes the quick search; SRH-08's session filter
  becomes the selection list the facet sidebar owns. The one-call answer supersedes
  the 7.4a deferral note's "a second call" wording (that row's only content-level error
  about the future).
- **DD-425** — records what DD-219 left for 7.4b to decide: the selection stays out of
  the URL, and DD-219 itself stands.

## Acceptance

- Vitest (unit, `nx test aurelius-atlas-webapp -c ci` and `nx test aurelius-atlas-ui -c ci`):
    - `search/search-state.spec.ts` (the BASIC_SEARCH constant and body pins become
      the quick endpoint) — the POST `/atlas/v2/search/quick` body carries
      `includeSubTypes: true` and the marker/explore rules of SDX-01; entities and
      count read from `searchResults` (SDX-01); `aggregationMetrics` feeds the facet
      signal with empty facets dropped and order kept (SDX-02/03); ticking a type
      re-POSTs at `offset: 0` with the comma-joined `typeName` (SDX-04); a hero submit
      clears the selection and the seen set while a URL query change keeps the
      selection (SDX-06/07); a narrowed answer updates carried counts and keeps seen
      values with their last count (SDX-07).
    - `search/results/results.component.spec.ts` — facet menus render in answer order
      with the title keys and `nameDisplay` labels (SDX-08); the shell text still
      renders when every facet is empty and never beside facets (SDX-03); clicking a
      type checkbox reaches the store (SDX-04); the read-only rows carry no checkbox
      (SDX-05).
    - `facet-list.component.spec.ts` — menu markup, count text, selectable rows emit
      `toggled`, read-only rows do not, five-value cap with show-more (UIC-33/34).
    - `i18n-completeness.spec.ts` — the four new ids exist in both catalogues (SDX-08,
      SHL-08).
- Storybook (`nx test-storybook aurelius-atlas-ui`): the UIC-35 `play()` interaction.
- e2e (`nx e2e aurelius-atlas-webapp`, real server behind the proxy — DD-142): seed
  entities of two types through the proxy with run-unique single-word names carrying
  the run token (the 7.4a seeding rule, plus quick search's prefix match, QSR-02),
  namespaced and self-cleaned (the DD-223 rule on the shared store). Sign in as the
  authenticated fixture, search the token → the sidebar shows the type facet with
  both types' counts (SDX-03/08); tick one type → the list shows only that type and
  the checked value stays visible (SDX-04/07); untick → the list broadens again
  (SDX-04); `__state` reads ACTIVE with no checkbox (SDX-05); the hero field's submit
  clears the tick (SDX-06). The facet titles render in Dutch on the nl-NL locale
  (SDX-08).
- Offline gates: `nx lint`, `nx typecheck`, `nx run aurelius-atlas-webapp:check-purity`,
  `nx test aurelius-atlas-webapp -c ci`, `nx test aurelius-atlas-ui -c ci`.
