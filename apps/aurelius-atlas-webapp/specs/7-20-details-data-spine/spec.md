# 7.20 Details data spine

- **Status:** done
- **Pull request:** –
- **Records:** DD-317 (the breadcrumb trail is app state with no source yet),
  DD-318 (the details read drives the loading, failure, and not-found states);
  relies on DD-186/DD-187 (7.6, the skeleton and the client method), DD-140
  (one client method per server surface), DD-188/ADR 054 (one API base),
  DD-214 (the frontend failure path, 7.19), UIC-11..20 (7.13, 7.16),
  WBP rules (7.0)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

This is the **2.3+7.6 wiring increment** the 7.6 deferral table names. The
server's entity read (`GET /api/atlas/v2/entity/guid/{guid}`, increment 2.3) is
live, the Angular client method (DET-03, `AtlasEntitiesService.getEntityByGuid`)
is built, and the details skeleton (DET-01..07) renders its empty state. 7.20
joins the three: the screen fetches the entity for the route's `:guid` and
binds the skeleton's existing slots to it.

Delivered here:

- the fetch: the screen calls `getEntityByGuid` for the route's guid, keyed by
  guid so a stale answer cannot paint a newer entity (the legacy
  `latestEntityId` guard)
- the header: the title (`attributes.name`, else `attributes.qualifiedName`,
  else the DET-02 fallback), the type-name line (the 7.16 `type-name`), and
  the classification chips (the 7.16 `classification-chip`, one per entity
  classification)
- the description box: `attributes.definition` when it is a string, else
  `attributes.description` (DD-320), rendered as markdown the way the legacy
  did (DD-321); with neither, the legacy placeholder line
- the properties accordion: the merged attribute/relationship-attribute
  property rows, minus the legacy blacklist and the empty values, rendered by
  the 7.13 `properties-item` (link arrays route on click), with the count
  above reading the row count
- the breadcrumb trail store (DD-317): app-side state the screen renders, with
  no source yet, ready for the API join later
- the ui library's `Markdown` component (DD-321): the legacy markdown block
  re-ported on `marked` with its Bulma renderer mappings, per-instance rather
  than the legacy's shared-service mutation
- the loading, failure, and not-found states (DD-318): a localized loading
  line, a failed read as an error alert (7.19's idiom), a 404 answered by the
  DET-02 empty state

Explicitly not delivered here, with the increment that will:

| Deferred                                                                                                   | Lands with                                       | Why                                                                                                       |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| The nine `m4i_*` type-specific layouts and the type dispatch                                               | A later 7.x slice, when such types exist         | The server ships the Apache Atlas model types, not the m4i governance types (the 7.6 deferral, unchanged) |
| The trail's data (a server endpoint that computes the parent chain)                                        | A server increment, then one store fill (DD-317) | Legacy derived the trail from its App Search index; Aurelius Atlas has no such index and no endpoint yet  |
| The glossary-terms chips (`meanings`), People cards, data-quality stats, related-cards lists, lineage view | 7.8/7.9 and the lineage backend                  | Aurelius backends this product does not have (DD-140); no term chip in the ui library yet                 |
| The edit affordance (`DATA_STEWARD`) and the delete flow                                                   | 7.7, 7.9                                         | The editor and delete slices own them                                                                     |
| Audit-events and business-metadata cards                                                                   | 7.9                                              | The client methods exist (8.17, 8.19); the cards are that slice's                                         |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
(TS tests name the id in the test title, the 7.3/7.6 pattern;
`@pytest.mark.covers` applies to no file here). 7.6's DET-01..07 stay in force;
this increment lifts DET-02's "(2.3 absent)" premise and DET-03's "no screen
calls it" clause, and keeps their shapes: the anatomy, the empty state, and the
deep-link contract are re-asserted against a screen that now fetches.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-08 | The screen fetches the entity through `AtlasEntitiesService.getEntityByGuid(guid)` (DET-03's method, the screen's first call site) whenever the route's `:guid` changes. The URL stays the screen's whole address (DET-07): navigating to another guid (a crumb click, DET-06) re-runs the fetch, and an answer for a superseded guid is dropped (the legacy stale-fetch guard, DD-318). No second entity client, no second URL (APC-01, DD-188).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| DET-09 | With an entity resolved, the header renders from it: the `h1.aurelius-details-title` shows `attributes.name`, else `attributes.qualifiedName`, else the DET-02 fallback; the `.aurelius-details-type` line is the 7.16 `type-name` with the entity's `typeName`; the classifications block renders one 7.16 `classification-chip` per entry of the entity's classifications, labelled by the classification's type name. The parts stay dumb inputs (DET-05).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| DET-10 | The description box shows `attributes.definition` when that value is a string. With no string `definition` it shows `attributes.description` when that is a string. The text renders as markdown through the ui library's `Markdown` component (DD-321). With no string in either attribute the box shows the legacy placeholder line — `search.components.description.notAvailable` ("No description available."), italic and centered, the legacy `DescriptionComponent`'s no-description template. (The legacy `DescriptionComponent` read `definition`; this server ships the Apache Atlas model types, which carry their text in `description` — DD-320.)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| DET-11 | The properties rows are the entity's own attributes merged with its relationship attributes (the relationship values win a key clash, the legacy spread order), then filtered: an entry with a nil value or a key on the legacy blacklist (`blacklist-properties.ts`, ported verbatim with its citation) earns no row. The rows sort by key. A string, number, or boolean renders through `properties-item`; an array whose entries each carry a `guid` renders as the `properties-item` link array (displayText, else name, else guid), and a clicked link navigates the details route to that guid (DET-06's sibling); every other shape renders no row. The key the description box shows earns no row (DD-320): the legacy table already drops `definition` by the blacklist's own rule, and the same drop covers `description` when the box shows it. The `.aurelius-details-property-count` reads the rendered row count. When no row renders, the accordion shows the legacy table's placeholder line instead of the table (headers included) — `components.sortableTableShell.noData` ("No data available"), the zero-data swap of the legacy `sortable-table-shell`. |
| DET-12 | The breadcrumb trail renders from an app-side store (DD-317): a signal holder the details route component provides, typed as the 7.13 `breadcrumbs` `Breadcrumb` list, with a reader and a clear/set. In this increment nothing fills it, so the trail renders under the empty guard (DET-02's shape) on every visit, and DET-06's crumb-click routing stays wired and tested at the component boundary. Nothing derives crumbs from the entity read.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| DET-13 | While a fetch is in flight and no entity has answered yet, the screen shows a loading line labelled `@@search.services.entityDetails.retrieve` ("Retrieving the entity details"). A failed read (404 excepted) adds an alert (`severity: "error"`, source `search`, the 7.19 failure idiom) with the same localized text; a 404 adds none — the empty state answers it (ALR-05's silence, DET-07's deep link). Either way the screen keeps the DET-02 empty shape (the fallback title, the description box holding no text — its placeholder line, DET-10, and zero rows). No mock or placeholder entity data appears in any state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| DET-14 | e2e (authenticated, every browser): a seeded entity carrying a `description` opened at `/search/details/<guid>` shows the live title (the seeded name), the type-name line, and the seeded `description` in the description box. The properties table holds zero rows and the count reads 0: `name` and `qualifiedName` ride the title (blacklisted per DET-11), and `description` rides the box (DET-10, DD-320). The no-entity deep link (DET-07's fixture, a guid nothing owns) still renders the empty chrome in both locales.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
`apps/atlas/src/app/search/`:

- `details/details.component.{ts,html}` — the resolved-entity header: the
  `name || qualifiedName` title, the type-name line, the classifications and
  terms blocks, the trail, the `ngComponentOutlet` type dispatch (the dispatch
  stays deferred)
- `details/details.resolver.ts` — the resolver passes the `:id` through (its
  body only clears the API cache); the fetch itself lives in
  `services/entity-details/entity-details.service.ts`, with the
  `latestEntityId` stale-answer guard DET-08 ports
- `services/filtered-properties/filtered-properties.service.ts` and
  `blacklist-properties.ts` — the property merge, the nil drop, and the
  blacklist set DET-11 ports
- `components/description/description.component.ts` — the
  `attributes.definition` read DET-10 ports (its `ruleDescription` branch
  serves the m4i governance types this product does not have; DET-10's
  `description` fallback stands in for the m4i text attribute — DD-320); its
  `noDescription` template (the italic centered placeholder line,
  `search.components.description.notAvailable`) is DET-10's empty-box shape,
  and it renders the text through the markdown component below
- `libs/components/src/lib/markdown/markdown.component.ts` — the
  `models4insight-markdown` block DET-10 now rides (DD-321): the four Bulma
  renderer mappings ported 1:1; its constructor-registered overrides on the
  shared `ngx-markdown` `MarkdownService` are the defect the port fixes by
  holding a per-component `marked` instance instead
- `components/properties/properties.component.ts` — the Key/Value table over
  the filtered map (the row item is the 7.13 `properties-item`)
- `components/bread-crumbs/bread-crumbs.service.ts` — the trail store this
  slice does **not** port: it read the `breadcrumbguid`/`breadcrumbname`/
  `breadcrumbtype` arrays of the legacy search document, which the legacy Flink
  job `libs/m4i-flink-tasks/.../entity_created.py` derived from the parent
  chain. The store DET-12 defines replaces that source with an empty seam
  (DD-317)

## Deviations

None against Apache Atlas: this slice is an Aurelius product screen; Atlas's
own details UI is its dashboard (ADR 046, the parity reference stays).

Against the Aurelius product, three intended differences are recorded in the
design records beside this spec. The breadcrumb trail renders empty until an
endpoint supplies it (DD-317). The read's loading/failure/not-found states ride
this app's loading line and alerts drawer instead of the legacy task strip
(DD-318). The description box falls back to the `description` attribute,
because this server ships the Apache Atlas model types and not the m4i types
the legacy read (DD-320). The deferral table carries the rest (the type
dispatch, the Aurelius-only cards).

## Acceptance

- Vitest (unit):
    - `src/app/search/details/details.component.spec.ts` — amended and
      extended: a fetch fires for the route guid and nothing else (DET-08), a
      superseded answer paints nothing (DET-08), the resolved header renders
      title/type-name/chips per DET-09, the description per DET-10, the rows
      and count per DET-11 (including a link-array click routing), the empty
      trail per DET-12, the loading line and the 404 fallback per DET-13, the
      failure alert per DET-13. 7.6's anatomy/strings/empty-state specs keep
      passing (DET-01..04) with the "issues no HTTP requests" spec replaced by
      the fetch specs (DET-08's premise change).
    - `src/app/search/details/details-breadcrumb-state.spec.ts` — the store
      reads empty, a set/list round-trips, clear empties (DET-12).
    - `src/app/search/details/property-filter.spec.ts` — merge order, nil
      drop, blacklist, sort, scalar/link/other classification (DET-11).
    - `i18n-completeness.spec.ts` unchanged: every string used is a key the
      bridge already carries in both locales (DET-04, SHL-08) — 7.20 adds no
      catalogue keys.
- e2e (`nx e2e aurelius-atlas-webapp`): the seeded-details scenario (DET-14)
  in the chromium/firefox/webkit matrix; the DET-07 no-entity scenario keeps
  its assertions on the empty chrome; the 7.4a card-to-details scenario
  (SRH-05) now lands on a live header — extend it with the title assertion.
  Shared `dev/*` services are never restarted (DD-223); the seeded entity
  rides the 7.4a `_seed_entities` helper (a unique single-token name) and
  self-cleans nothing the purge helper does not already cover.
- Storybook: the ui library's `Markdown` component carries its story (the
  full-document and plain-prose shapes, DD-321); the details screen gains no
  story (the dumb parts carry theirs, UIC-15/20).
- Purity gate green (WBP-02: signals, standalone, no state-owning
  `BehaviorSubject`), umbrella checks for the app
  (`nx test aurelius-atlas-webapp -c ci`, `nx lint`, `nx build`),
  `uv run aurelius-atlas-trace check` reports the DET-08..14 gaps as expected
  (local-only by ADR 056/DD-215).

### Definition of done, in order

1. `nx test aurelius-atlas-webapp -c ci` and `nx build aurelius-atlas-webapp`
   green, `nx lint aurelius-atlas-webapp` and
   `nx run aurelius-atlas-webapp:check-purity` clean.
2. `nx e2e aurelius-atlas-webapp` — the seeded-details scenario green in the
   chromium/firefox/webkit matrix, DET-07 unchanged.
3. Spec status → `done`, roadmap row flipped, DD-317/318 accepted with a
   person's approval (never self-accepted).
