# 7.21a Details sections: the seven m4i pages

- **Status:** done
- **Pull request:** —
- **Records:** DD-365..DD-371, DD-374..DD-379 (the parity pass and its
  follow-ups); relies on DET-01..14 (7.6, 7.20), UIC-11..20
  (7.13, 7.16), DD-317/318 (the trail seam, the read's states), DD-140 (the
  App Search index is not ported), DD-341 (its chip lead; its `iconsByType`
  refusal ended at DD-378), DD-335/336
  (the chip anatomy), ADR 058/DD-362 (1.5b: the m4i types are in the
  catalogue), AEN-04 (`getEntitiesByGuids`, 8.17), APC-01 (one API base)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The demo details page is not one screen: it is a header plus a per-type set of
**sections** — a People box, a stats bar of counts, and rich card lists with
local keyword search, sorting, and paged loading. 7.6/7.20 shipped the header,
the description box, and the properties accordion (the _default_ layout), and
the 7.20 deferral table named this slice: "the nine `m4i_*` type-specific
layouts and the type dispatch". The types now exist: 1.5b loads the m4i data
dictionary types into every catalogue by default (ADR 058, DD-362), and
`data/atlas-sample/` ships sample data in them.

This slice renders, for the seven catalogue types — `m4i_data_domain`,
`m4i_data_entity`, `m4i_data_attribute`, `m4i_field`, `m4i_dataset`,
`m4i_collection`, `m4i_system` — the legacy layouts' sections that the ported
API can answer today (DET-15..26). Every other type keeps the DET-01..14
default layout untouched.

The data path (DD-365): the legacy sections queried Elastic App Search on
Flink-derived fields (`parentguid`, `derived*guid`, `dqscore_*`) that Aurelius
Atlas does not have. The same _forward_ sets come out of the reads already
live: the details read's `relationshipAttributes` seed every section (3.1b —
each entry carries `displayText`, `typeName`, `entityStatus`,
`relationshipStatus`), and `GET /v2/entity/bulk` (2.3, ERD-01) resolves those
guids into the full entities the cards render — description, classifications,
and the entity's own people ends. Search, sort, and paging run client-side
over the resolved set (DD-368). No server change is in scope.

Delivered here:

- the dispatch: an entity whose type is one of the seven, or names one of
  them among its super types, renders that type's layout; everything else
  keeps the default layout (DET-15)
- the seven layouts as one data-driven section table — anchors, titles, seed
  keys — no component copy-paste (DET-16, DD-366)
- the card section: seed from the resolved entity, ACTIVE edges only, chunked
  bulk resolve, uniform card body, keyword filter, sort with direction, 9 per
  page (DET-17..22)
- the People box: Domain Lead / Data Owner / Data Steward rows, deduped,
  routing on click, on the three layouts that carry one (DET-23)
- the stats bar and the side navigation of each layout, with counts live and
  sourceless entries left out (DET-24, DET-25)
- the type badge's alias: `attributes.typeAlias` as a string shows as the
  badge's display name, with the base type beside it on the header only
  (DET-26, DD-371, DD-374)
- two dumb components in the ui library: `DetailsCardSection` (UIC-27) and
  `PeopleBox` (UIC-28), each with a story

Explicitly not delivered here, with the increment that will:

| Deferred                                                                                                    | Lands with                                                          | Why                                                                                                                        |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| The entity page's Datasets section (the attributes → fields → datasets walk)                                | [7.21b](../7-21b-datasets-walk/spec.md)                             | It is a multi-round walk, not a seed; the legacy read the Flink-derived crossed field (DD-365)                             |
| The Data Quality section, the score stats, the DQ sorts, the card DQ badges, the field's Data Quality Rules | 7.8 (governance quality)                                            | No rule-evaluation engine exists: the legacy read `dqscore_*` documents its Flink job computed (DD-369)                    |
| The Governance Quality Rules section (all layouts)                                                          | 7.8                                                                 | Same engine: the legacy queried a Flink-evaluated per-entity rule index by `entity_guid`                                   |
| The dataset page's Data Entities, Producers, Consumers, and lineage sections                                | The lineage chain (ADR 055) and an inverse-edge read                | They are reverse lookups across other entities' edges; the browser holds only the opened entity's own ends                 |
| The "show all descendants" toggle and the facet filter dropdown                                             | The search work (7.4b's SDX facets, or a relationship-search slice) | Both read Flink-derived `derived*guid` fields and App Search facets (DD-370)                                               |
| The person and process layouts                                                                              | A later 7.x slice                                                   | Out of the user-set seven; both keep the default layout (their sections are governance/lineage sets the API cannot answer) |
| The breadcrumb trail inside the card bodies and the header                                                  | The trail endpoint (DD-317)                                         | The trail seam stays empty, unchanged from 7.20                                                                            |
| Delete flow, audit and business-metadata cards                                                              | 7.9                                                                 | 7.9 owns them (unchanged)                                                                                                  |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
(TS tests name the id in the test title, the 7.3/7.6 pattern;
`@pytest.mark.covers` applies to no file here). DET-01..14 stay in force for
the default layout; a layout matched by DET-15 replaces only the boxes below
the header — the header, the fetch, the stale-answer guard, the loading line,
the failure alert, and the empty state stay the DET-01..14 shapes.

The section table (the whole of the seven layouts; DD-366):

| Type                 | People box | Card sections (anchor · title key · seed key of `relationshipAttributes`)                                                                                                                                                                                                                           | Stats bar (counts, legacy order)                          |
| -------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `m4i_data_domain`    | yes        | Data Entities · `#related-entities` · `search.details.domain.entityCards.title` · `dataEntity`                                                                                                                                                                                                      | Data Entities, Properties (Data Quality deferred, DD-369) |
| `m4i_data_entity`    | yes        | Data Attributes · `#related-attributes` · `search.details.entity.attributesCards.title` · `attributes`; Child Entities · `#related-entities` · `search.details.entity.entitiesCards.title` · `childEntity` (Datasets: 7.21b)                                                                        | Data Attributes, Child Entities, Properties               |
| `m4i_data_attribute` | yes        | Fields · `#related-fields` · `search.details.attribute.fieldsCards.title` · `fields`                                                                                                                                                                                                                | Fields, Properties                                        |
| `m4i_field`          | no         | Data Attributes · `#related-attributes` · `search.details.field.attributesCards.title` · `attributes`; Child Fields · `#related-fields` · `search.details.field.fieldsCards.title` · `childField`                                                                                                   | Data Attributes, Child Fields, Properties                 |
| `m4i_dataset`        | no         | Fields · `#related-fields` · `search.details.dataset.fieldsCards.title` · `fields`; Child Datasets · `#related-datasets` · `search.details.dataset.datasetsCards.title` · `childDataset`                                                                                                            | Fields, Child Datasets, Properties                        |
| `m4i_collection`     | no         | Datasets · `#related-datasets` · `search.details.collection.datasetsCards.title` · `datasets`                                                                                                                                                                                                       | Datasets, Properties                                      |
| `m4i_system`         | no         | Collections · `#related-collections` · `search.details.system.collectionsCards.title` · `collections`; Sub-Systems · `#related-systems` · `search.details.system.systemsCards.title` · `childSystem`; Processes · `#related-processes` · `search.details.system.processesCards.title` · `processes` | Collections, Properties                                   |

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-15 | The layout is chosen from the entity's type: one of the seven names, or one of them among the type's super types, selects that layout; every other type (and every no-entity state) keeps the DET-01 default layout with all its rules. The type's super types are read from the typedef cache of `TypeDefsService` (7.3) — no second typedef call, no second URL (APC-01). While the entity is unresolved the screen renders the default layout's empty chrome (DET-02), so dispatch never flashes a half-layout.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| DET-16 | The seven layouts are one config table in `details/sections/section-config.ts`: per type, the ordered sections (anchor id, localized title key, seed keys), the stats entries, the navigation entries, and whether the layout has a People box. The table above is the config, key for key; the strings ride the bridge (DET-04's rule): every key named here is a catalogue key the XLIFF carries in both locales (checked, no fixture change; `i18n-completeness.spec.ts` stays green untouched). The anchors are the legacy ids so the navigation's `#href`s land.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| DET-17 | A section's seed is the resolved entity's `relationshipAttributes` for its seed keys, in order, keeping only entries whose `relationshipStatus` is `ACTIVE` (the EDT-15 rule, shared with the editor's seed) and that carry a `guid`. The section count — the count line and the stats bar — is the seed length; it is shown at once, before any card resolves (the legacy counted the query's total, not the loaded page). The seed follows the entity: the editor's save re-read (DD-327) re-seeds every section.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| DET-18 | The seed's guids resolve through `AtlasEntitiesService.getEntitiesByGuids` (AEN-04) in chunks of at most 25 (DD-368), so one URL stays browser- and edge-sized. Until a chunk answers, the section shows loading cards — the `entity-card`'s loading row with `search.details.loading` ("Loading {{name}}...") at the card's display text. A chunk that fails adds one alert (`severity: "error"`, source `search`, the 7.19/DET-13 idiom) and the section keeps the cards it has; no retry loop. A guid missing from the answer renders no card and keeps its count (a deleted related entity, not an error).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| DET-19 | The card body is uniform for every type (DD-367): the classification chips (the 7.16 `classification-chip`, one per entry of the entity's `classifications`, each labelled by its dictionary display name — DD-379), the description text — `definition` when it is a string, else `description` (the DET-10/DD-320 order), rendered by the ui `Markdown` component, omitted when neither is a string — and the people rows of the card entity's own `relationshipAttributes` by the DET-23 grouping (Domain Lead omitted there: it is a domain's end). The card uses the 7.13 `entity-card` with `showQuality` off (the DQ column has no source, DD-369) and the badge icon on, resolved from the app's `iconsByType` port (amended by DD-378: the badges lead with their type's icon). A title click routes the details screen to the card's guid (the DET-06 sibling); the `href` stays the keyboard path.                                                                                                                                                                                                                                |
| DET-20 | The section's keyword search filters the resolved cards client-side: a card matches when the term, case-insensitively, occurs in its display text, its `name` or `qualifiedName` attribute, or its description text (DD-368 — the legacy App Search matched its analysed document fields, a wider net, recorded as a deviation). The input is the ui `search-field` with the placeholder `search.details.components.detailsCardsList.placeholder` ("Search for keywords"); the filter follows the typing on every keystroke, and a clear empties it (DD-375 — a deviation: the legacy section filtered only on submit, and ignored the keystroke event its own input emitted). The count line is always the underlined reset link (DD-374, demo-measured): it shows the filtered count while a search is applied, the section count otherwise, and clicking it resets the query and the sort to their defaults — an unfiltered reset is a no-op (the legacy's unconditional `reset-search`; `search.details.components.detailsCardsList.results`, "result(s)").                                                                              |
| DET-21 | Sorting is client-side over the resolved cards. The select holds Relevance (`search.components.sorting.relevance`, the seed order) and Name (a `localeCompare` of the display texts); the direction button reverses. The DQ sorts the legacy offered are out with the DQ data (DD-369). Below Bulma 1's level breakpoint the header stacks and every group uses the box's width — the title and count flush left, the sort row stretched like the search box under it (DD-376: the demo centers them stacked, the parity rule's broken half).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| DET-22 | The grid pages at 9 cards (the legacy page size): the ui `infinite-scroll-container` with the caller's label `search.components.infiniteScrollContainer.loadNextPage` ("Load next page..."). `allLoaded` is the filtered set exhausted; the sentinel's intersection and the button both extend the page (UIC-22's behaviour, the 7.4a results screen's wiring idiom). Each card rides a caller column sized with Bulma's helpers: at most three across on a desktop, two on a tablet, one full-width on a phone (`is-one-third-desktop is-half-tablet`, DD-377). A bare column shares the row with every sibling, which squeezed six cards side by side. The section grid holds no sizing rule of its own: it projects the caller's cards (WBP-04) and a component rule never reaches projected content, so the legacy's `.column { min-width: 333px }` (which matched its own column divs) is not ported. A card title that does not fit its column shows one line with an ellipsis (the `entity-card` clips it and carries the whole name in the anchor's `title`, DD-377). It never breaks a long hyphenated name down one word per line. |
| DET-23 | The People box (the layouts flagged for one in DET-16's table: domain, entity, attribute — the legacy pages that show a People box; `m4i_field` carries a steward end but its legacy page has no box, so its table row has none) renders the resolved entity's people rows in this order: Domain Lead(s) (`domainLead`, key `search.components.people.domainLead`), Data Owner(s) (`businessOwner`, key `search.components.people.dataOwner`), Data Steward(s) (`steward`, key `search.components.people.dataSteward`). Each row dedupes by guid keeping the first (the legacy `deduplicate`), shows each person's `displayText` as a link that routes to that guid (the legacy `directToDetailsPage`), and renders only when non-empty. With every row empty the box shows the italic centered `search.components.people.empty` ("No people assigned.").                                                                                                                                                                                                                                                                                    |
| DET-24 | The stats bar is the 7.16 `section-stats` with the layout's stats in legacy order, minus every stat with no source in this slice (DD-369): a section's count is its DET-17 seed count, Properties is the DET-11 rendered row count. The Data Quality stat renders nothing at all — not a zero — the way the legacy template's `noDataQuality` branch dropped the value.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| DET-25 | The side navigation lists the layout's entries in legacy order, dropping every deferred section's link (DD-369): the rendered box set only. Each entry is the existing `#href`-anchor path (the default layout's shape) with the layout's own title keys.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| DET-26 | The type badge shows `attributes.typeAlias` as its alias — the `type-name`/`entity-card` alias input — when that attribute is a non-empty string. The header badge carries the base type name beside the alias (`showBaseTypeName`); the card badges show the alias alone — the legacy's card never passes the base name, and the suffix is what collapses the card title on narrow screens (DD-374). With no string alias the badge shows the type name alone, as today — by its dictionary display name, raw where the dictionary has no key (amended by DD-379, which extends the header badge's suffix the same way). Every badge leads with its type's icon, resolved from `search/meta/type-icons.ts` (the legacy `iconsByType` port) and passed as the ui component's icon inputs (amended by DD-378, superseding the refusal of DD-371/DD-341): a type outside the map renders no icon, as the legacy's `*ngIf` did.                                                                                                                                                                                                                 |
| DET-27 | e2e (authenticated, every browser): a seeded m4i mini-graph — a domain, an entity with two attributes, fields, datasets, and persons in the legacy roles — opened at the entity's details URL shows: the People box with the owner and steward links, the Data Attributes section with the seeded count and two cards whose bodies show the description text, the keyword filter narrowing the cards, the reset count line restoring them, and the Child Entities section rendering at its zero count (the empty box with the count line, no cards). Opening a seeded attribute shows its Fields section; its People box renders its empty line (the DET-16 table gives the attribute page a box — the DET-23 list — and the seeded attribute holds no people ends). A `DataSet` entity (not m4i) still renders the DET-14 shape. The seed rides the 7.4a `_seed_entities` idiom extended to the m4i types, namespaced by a unique token and self-cleaned by the existing purge helper (DD-223: no shared-service restarts).                                                                                                                 |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
`apps/atlas/src/app/search/`:

- `details/details.component.{ts,html}` — the `ngComponentOutlet` type
  dispatch DET-15 replaces with the config lookup; `details/components/
details-navigation` (the 7.16 UIC-18 shell this reuses)
- `details/domain/domain-details.component.html`,
  `details/entity/entity-details.component.html`,
  `details/attribute/attribute-details.component.html`,
  `details/field/field-details.component.html`,
  `details/dataset/dataset-details.component.html`,
  `details/collection/collection-details.component.html`,
  `details/system/system-details.component.html` — the seven layouts DET-16
  encodes; their `nav.level` stats bars are DET-24, their
  `details-navigation` lists are DET-25, their `id` anchors DET-16 keeps
- `details/components/details-cards-list/` — the card section DET-17..22
  ports: the title + `N result(s)` reset link, the search input
  (`simple-search-input` → the 7.4a `search-field`), the
  `sorting` component's select + direction button (its DQ sort options drop,
  DD-369), and the infinite-scroll container (already UIC-21/22); the
  `show-descendants-control` and the facet `filter` dropdown are out (DD-370)
- `details/*/[attributes|entities|datasets|fields|collections|systems|processes]-cards/`
  — each section's App Search query: `supertypenames: [type]` +
  `parentguid`/`derived*guid` filters over the Flink index. DET-17/DATA path
  replaces each with the forward `relationshipAttributes` seed or names the
  reverse lookup deferred (DD-365); `entity/datasets-cards` (the
  `deriveddatasetguid` walk) is 7.21b's
- `components/people/people.component.ts` — the DET-23 box verbatim: the
  three ends, `deduplicate` by guid, `displayText` links, the `empty` line
- `components/cards/*/[type]-details-card.component.html` — the card bodies;
  their unique columns are `dqscore_*` badges and the breadcrumb trail, both
  without a source (DD-367); `search/meta/icons-by-type.ts`'s `iconsByType`
  is the DET-26 map, ported as `search/meta/type-icons.ts` (DD-378)
- `services/entity-details/entity-details.service.ts` — the entity store the
  seeds read (7.20's `DetailsState` is its twin); the per-type `typeAlias`
  badge DET-26 reads is `attributes.typeAlias`, as the legacy's
  `typeAlias` input received it

## Deviations

None against Apache Atlas: this slice is an Aurelius product screen and adds
no server surface; the reads it rides (ERD-01, ERD-03..06) are already
contracted. Against the Aurelius product, the intended differences are the
design records beside this spec: the section data path (DD-365), the single
layout table (DD-366), the uniform card body (DD-367), the client-side
search/sort/page with its narrower match fields (DD-368), the hidden sourceless
sections (DD-369), the dropped descendants toggle and facet dropdown (DD-370),
and the icon-less alias badge (DD-371).

## Acceptance

- Vitest (unit):
    - `src/app/search/details/details.component.spec.ts` — amended: a seeded
      m4i entity renders its layout's boxes, anchors, stats and nav (DET-15,
      DET-24, DET-25), a `DataSet` and the no-entity states keep every
      DET-01..14 assertion green (DET-15's negative), the badge alias (DET-26).
    - `src/app/search/details/sections/section-config.spec.ts` — the table is
      the config, key for key, with both-locale keys resolvable (DET-16).
    - `src/app/search/details/sections/related-section.spec.ts` — the store:
      seed order, ACTIVE filter, count-before-resolve, chunking at 25 (two
      requests for 26 guids), the failure alert once, the missing-guid card
      drop (DET-17, DET-18), the search filter and reset (DET-20), the sort
      and direction (DET-21), the paging (DET-22).
    - `src/app/search/details/sections/card-content.spec.ts` — the uniform
      body: chips, the definition/description order, the people rows, the
      quality column off, the badge icon, the routing emit (DET-19, DET-23,
      DET-26).
    - `src/app/search/details/details.component.spec.ts` (People box cases) —
      the three rows, the dedupe, the empty line, the click routing (DET-23).
    - `libs/angular/aurelius-atlas-ui` — `details-card-section.component.spec.ts`
      and `people-box.component.spec.ts`: the dumb inputs, emits, and the
      projected shapes (UIC-27, UIC-28).
    - `i18n-completeness.spec.ts` unchanged (DET-16): every string used is a
      key the bridge already carries in both locales; this slice adds no
      catalogue keys.
- e2e (`nx e2e aurelius-atlas-webapp`): the DET-27 scenarios in the
  chromium/firefox/webkit matrix; DET-07/DET-14's scenarios keep their
  assertions (a `DataSet` is not m4i); the 7.4a card-to-details scenario
  (SRH-05) keeps passing.
- Storybook: `DetailsCardSection` and `PeopleBox` carry stories (the empty,
  loading, and filled shapes; UIC-15's rule for each new dumb part).
- Purity gate green (WBP-02: signals, standalone, no state-owning
  `BehaviorSubject`), umbrella checks for the app (`nx test
aurelius-atlas-webapp -c ci`, `nx lint`, `nx build`), `uv run
aurelius-atlas-trace check` reports the DET-15..27 gaps as expected
  (local-only by ADR 056/DD-215).

### Definition of done, in order

1. `nx test aurelius-atlas-webapp -c ci` and `nx build aurelius-atlas-webapp`
   green, `nx lint aurelius-atlas-webapp` and
   `nx run aurelius-atlas-webapp:check-purity` clean, the ui library's
   `nx test aurelius-atlas-ui -c ci` green.
2. `nx e2e aurelius-atlas-webapp` — the DET-27 scenarios green in the
   chromium/firefox/webkit matrix, DET-07/DET-14 unchanged. (Rides 1.5b being
   merged: the m4i types must load at start-up for the seed to exist.)
3. Spec status → `done`, roadmap row flipped, DD-365..371 accepted with a
   person's approval (never self-accepted).
