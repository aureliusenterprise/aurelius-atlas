# 16.5a The results page on the search door

- **Status:** in progress
- **Pull request:** #361
- **Records:** ADR 064, ADR 059; DD-599 to DD-603 (here); relies on 16.2 (AVR-01..13), 16.4
  (ASV-01..10), 16.1 (AVS-01..09), 4.2b (QSR-03/QSR-04's facets, DD-093), 7.4a/7.4b (SRH, SDX),
  11.5/11.5b (SBW, SBX)

The first screen switched to the view family (ADR 064). The results page today assembles its cards
from quick search's or the search by meaning's answer, and its sidebar from that answer's
`aggregationMetrics`. After this increment it reads one door: `POST /api/aurelius/v1/search`, in
16.1's card shape, with the four sidebar facets answered by the door itself. What the page shows
stays what 7.4a/7.4b built; what it reads changes.

## Scope

- in `aurelius-atlas-core`: the search door's two facet names beside the card fields, `owner` and
  `serviceType`, answered as DD-093's aggregator answers them (ADR 064's facet clause);
- in `aurelius-atlas-data-access`: the view family's Angular models (`atlas-view.ts`) and
  `ViewSearchService`, the door's client;
- in `aurelius-atlas-webapp`: the results store and the results component read the door (VSR-03 to
  VSR-09), and the four sidebar facets come from it.

Not in scope, with the increment that will:

| Not delivered                                                                     | Lands with |
| --------------------------------------------------------------------------------- | ---------- |
| The details screen on the read door, the GUID cache, the breadcrumb seam          | 16.5b      |
| The editor on the mutation door, the tag diff, the picker and conflict UX         | 16.5c      |
| A mode control on the results page (the settings panel owns the mode, SBX-01..03) | –          |
| A stale badge on the cards (the card carries the mark, AVS-06; nothing shows it)  | –          |
| The App Search wire retired                                                       | 16.6       |

## Semantics

The door's own rules (AVR, ASV) answer every request; the rules below cover the door's two new
facet names and the screen that reads it.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VSR-01 | The door accepts two facet names beside the card fields. `owner` counts `Asset`'s owner attribute. `serviceType` sums the entity types' counts by their service type, most first, ties by name, and leaves out a service type that counts none. Both names are always accepted, and answer empty where the registry holds nothing for them, as DD-093 does |
| VSR-02 | Every other answer of the door is unchanged (AVR-08, ASV-10): the new names join the accepted facet list, and no card, no keyword answer and no Apache Atlas answer changes                                                                                                                                                                                |
| VSR-03 | The results store asks the door with a body of `query`, `mode` (`keyword` for Words, `semantic`, `hybrid`), `filters`, `facets`, `limit` 10 and `offset`; the stored search mode names the `mode` (SBX-02). The door answers `{cards, facets, total}`                                                                                                      |
| VSR-04 | A type selection filters entities of the selected types and of their sub types: the door's `filters` hold an `any` of the selected names under `typeName` and under `superTypeNames`. An empty query with no selection answers every entity; quick search's every-entity marker is gone (AVR-11)                                                           |
| VSR-05 | The header's count and the list's end follow the mode (SBW-04 kept): `keyword` counts the door's exact `total` and loads until shown; a meaning mode counts what is shown and ends at a short page or at 1,000 (DD-479), and never asks past the door's window (ASV-08)                                                                                    |
| VSR-06 | The sidebar asks the type facet at 100 values (DD-093's facet size) and the other three as answered. `typeName` is the selectable facet and keeps the seen-value rule (DD-426: narrowed answers keep every seen value with its last count); `status`, `owner` and `serviceType` display only, in answer order, empty facets left out (SDX-03/05)           |
| VSR-07 | A card renders as 7.4a left it: the display text, the type's dictionary name and icon, no per-card fetch, and no new visible field. `status` and `stale` ride the card but are not shown                                                                                                                                                                   |
| VSR-08 | The door's embedding-off answer (ASV-09, `AURELIUS-404-00-001`) on a meaning search is the known one (SBW-06): a warning and the mode stored back to Words, which searches again. Any other failure lands in the alerts drawer with the loading message, as before                                                                                         |
| VSR-09 | A mode chosen in the settings restarts the shown query at its first page with the type selection kept (SBX-02); without a query it searches nothing                                                                                                                                                                                                        |
| VSR-10 | No other screen's calls change, and no Apache Atlas answer or the 11.4 endpoint's answer changes (R3, R4): the old services keep their methods for their own callers                                                                                                                                                                                       |

## Aurelius origin

- ADR 064: the door for the results screen, and the clause that moves the facet machinery to it
  without the wire's wrappers.
- 7.4a/7.4b (SRH-01..08, SDX-01..08, SRC): the query, paging, the type facet as filter, and the
  seen-value rule. The interactions stay; the wire under them changes.
- 4.2b (QSR-03/QSR-04, DD-093): the four facets and their counts, `Asset.owner` and `ServiceType`
  included. Their answers move from `SearchAggregator` into the door (VSR-01).
- 11.5/11.5b (SBW-03..06, SBX-01..03): the stored mode, its restart rule, and the fallback (VSR-08,
  VSR-09).
- 16.2 (AVR) and 16.4 (ASV): the door this screen reads.

## Deviations

None against Apache Atlas (VSR-02). Against the wire this page leaves (intentional, its retirement
road): the quick-search answer's `searchResults`/`aggregationMetrics` wrapping and `__`-prefixed
facet keys become the door's `{cards, facets, total}` with the card's field names; the comma-joined
`typeName` with `includeSubTypes` becomes the `filters` composition of VSR-04; the every-entity
marker of SRC-03 is gone because the door answers an empty query with everything (AVR-11);
`approximateCount` becomes the door's exact `total` in the keyword mode.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__view_search.py`: the two new facet names, their
  counts, their refusals, and the unchanged answers (VSR-01, VSR-02).
- `libs/angular/aurelius-atlas-data-access/src/lib/aurelius/view-search.service.spec.ts`: the
  door's URL, body and answer (VSR-03).
- `apps/aurelius-atlas-webapp/src/app/search/search-state.spec.ts`: the door request for words,
  meaning and both, the subtype filter, the marker's absence, paging and the counts, the facet
  merge, the fallback and the mode restart (VSR-03 to VSR-09).
- `apps/aurelius-atlas-webapp/src/app/search/results/results.component.spec.ts`: the cards and the
  four facets as the door answers them, nothing new shown (VSR-06, VSR-07).
- `apps/aurelius-atlas-webapp/src/app/search/browse/**` specs: the explore buttons' door bodies
  (VSR-04).
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts`: green with no key added or
  removed (the facet titles keep their labels on the door's names).
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp.py`: the hero search, the type facet
  filter and the no-results pair ride the door; one new critical scenario runs words, then a
  meaning mode chosen in the settings against a server without embedding, and lands on the warning
  and the words answer (VSR-03, VSR-04, VSR-08).
