# 7.25c The data-quality scores: the box, the stat, the sorts, and the card

- **Status:** in review
- **Pull request:** –
- **Records:** DET-56..DET-63 new; DV-202..DV-205 new; DD-851..DD-856;
  relies on 7.24 (UIC-36/UIC-37/UIC-39, DET-35/DET-36, DD-444/DD-447), 7.21a
  (DET-17..DET-27's chrome, stats bar, and nav, UIC-24/UIC-27, DD-365..DD-371),
  7.25a (DET-42..DET-48's governance box, DD-841..DD-843), 7.25b (DET-50..DET-55,
  DD-848..DD-850, ADR 071), 14.5 (ASQ-01..ASQ-08, DD-528..DD-532), 16.1
  (AVS-01..AVS-09, ADR 064), 16.2 (AVR-01..AVR-13), 16.5d/16.5h (VCF-05,
  VCF-19/VCF-20, AVS-11, DD-620/DD-840), and closes DD-369

Seven of the ten details layouts carried a second quality concept besides the
governance rules: the _data quality_ score. The legacy read it off the opened
entity's App Search document — a box of five dimension rows, a stats-bar
heading showing the overall percent, and a navigation entry — and printed a
compact version of the same list on every card the page drew. Aurelius has the
data: 12.2's scanner scores a rule over a dataset, 14.5's roll-up adds those
scores to the fields, their data attributes, and every entity of their
breadcrumb (ASQ-04, ASQ-05), and 16.1 carries the result on every card of the
view family as `quality` (AVS-01). What never landed is the screen: 7.6 deferred
it (DD-369) as the hold-out of "no score source", and 7.21a, 7.24, and 7.25a
each left their row of the hold-out in place with a pointer here. The score
source exists, the dumb components exist (UIC-36, UIC-37, UIC-39), and the door
sorts and facets on `quality.<dimension>.<part>` (AVR-05, AVR-06). This
increment draws the box, the stat, the sorts, and the card's list, and retires
DD-369.

## Scope

- the `#data-quality` box of the seven catalogue layouts: its title, its five
  dimension rows, and its "not available" rest (DET-56, DET-57);
- the stats-bar heading and the side-navigation entry for it, in the legacy
  place on each of the seven layouts, with the legacy's `Unavailable` value
  word (DET-58);
- the legacy's per-box sort options over the score fields, and the tie-breaks
  they need (DET-59);
- the score list on the card of a details section, off on a results row
  (DET-60, DET-61);
- the unchanged neighbours: 7.25a's Governance Quality Rules box, 7.25b's rule
  page, 7.24's field-page rules box, the People box, the lineage box, the
  governance mark on the card (VCF-19/VCF-20).

Not in scope:

| Not delivered                                                                                                                                                 | Lands with |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| The rule's own page: the legacy dispatched `m4i_gov_data_quality` to its verdict page and `m4i_data_quality` to the default layout; neither gains a score box | –          |
| A score box or score sort on the lineage quickview panel and the Model Browser tab — the legacy draws no quality there (DV-203)                               | –          |
| A score list on the results screen's cards — the legacy turns it off there with its own token (DV-202)                                                        | –          |
| The legacy's per-card App Search asks: the card's score list reads `card.quality`, the door's own rows (DV-204)                                               | –          |
| The `dqscore_*` documents and the `/data_quality` engine, kept as they are (ASQ-01..ASQ-08)                                                                   | –          |
| The rule card's single pie and dimension word (the legacy's `data-quality-card`): the door carries no rule score on a rule card (AVS-01)                      | –          |

## Semantics

The ids continue DET. "The score rows" below is `EntityCard.quality` (AVS-01):
at most six entries, one per dimension plus `overall`, each with `score`
(0..1), `count`, and `total`, and only the dimensions the entity holds. "The
seven score layouts" are `m4i_dataset`, `m4i_collection`, `m4i_system`,
`m4i_field`, `m4i_data_attribute`, `m4i_data_entity`, and `m4i_data_domain` —
exactly the legacy pages that drew the box (checked against all ten templates);
the process, person, and the two rule layouts never did and gain nothing here.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| DET-56 | A score layout draws a `#data-quality` box in the legacy place of its box list (DET-57). Its title is the layout's own `search.details.<layout>.dataQuality`. Its rows are the score rows minus `overall`, in the fixed legacy order `accuracy`, `completeness`, `timeliness`, `uniqueness`, `validity`: each row the UIC-37 `QualityDimensionList` shape (the pie at its own default size, the score as a percent to one decimal at most, the dimension word, the count in parentheses). The dimension words are the Aurelius catalogue keys `dqscore_<dimension>` (both catalogues carry all five). A box whose rows are absent shows the placeholder `search.components.dataqualitylist.notAvailable`, and nothing else — the legacy's `notAvailable` branch (DET-63).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| DET-57 | The box enters each score layout's box list in the legacy's order. On six layouts it enters directly before the `gov-quality` box (DET-48); on the field layout it enters directly before DET-35's Data Quality Rules box, which the legacy places after it (the template's own order: `#data-quality`, then `#related-rules`). Per layout it follows: dataset — Consumers; collection — Datasets; system — Processes; field — Child Fields; data attribute — Fields; data entity — Child Entities; data domain — Data Entities. Its anchor enters the layout's box list, so `sectionViews` draws it in the config's order like every other box (DET-48's precedent), and it is no card section: it carries no keyword, sort, facet, page, or count line (the legacy's box has none).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| DET-58 | The stats bar of a score layout gains a heading in the legacy place: dataset — after Consumers; collection — after Datasets; system — after Collections; field — after Child Fields, before the Data Quality Rules heading DET-36 added; data attribute — after Fields; data entity — after Child Entities; data domain — after Data Entities; always before Properties. Its label is the layout's own `search.details.<layout>.dataQuality`; it links to `#data-quality` as every other heading does (DET-25's anchor rules). Its value follows the legacy's two-state rule: when the opened view has an `overall` score row whose `count` is greater than 0, that row's `score` as a percent to one decimal at most; otherwise the layout's own `search.details.<layout>.unavailable` word (`search.details.collection.dataQualityUnavailable` for the collection layout, whose legacy template names that key). It shows no count and no zero — the legacy gates on the count, and DD-369's posture stands for the state with no source. The side navigation gains the matching entry in the legacy place: after the box entries that precede it and before `governanceQualityRules` on dataset, collection, system, entity, attribute, and domain; on field after Child Fields, before `governanceQualityRules` and before `dataQualityRules` (the legacy's own nav order for that page).                                                                                                                                                                                                                                                                                              |
| DET-59 | Ten card sections offer seven sort options in the legacy order — Relevance, Name, then Accuracy, Completeness, Timeliness, Uniqueness, Validity: the dataset's Fields and Child Datasets boxes, the collection's Datasets box, the system's Collections and Subsystems boxes, the field's Child Fields box, the data attribute's Fields box, the data entity's Data Attributes and Child Entities boxes, and the data domain's Data Entities box — the sections whose legacy `*-cards` component asked `['name', 'dqscore_accuracy', …, 'dqscore_validity']`. Every other box keeps its own list: the legacy's plain-`name` boxes keep the DET-21 pair (a dataset's Producers and Consumers, a system's Processes, the rule page's two verdict boxes, every box of the process layout), the governance box keeps DET-45's five, the field's rules box keeps DET-21's pair (DV-205 for its legacy pair), and the person page's responsibilities box keeps the pair — the legacy asks score sorts there too, but 14.5 puts score totals only on fields, data attributes and their breadcrumbs (ASQ-04, ASQ-05), so a person card never holds a row to sort on. Every sort runs in the browser exactly as DET-21's pair does (DV-204): Relevance is the seed order, the other six order the section's cards by that dimension's score row, cards without that row last, ties by display text with the locale's collation and the raw name as tie-break (the webapp's label-sort convention, DD-493's rule), reversed for a descending ask. The dimension labels are the `dqscore_<dimension>` keys; Name keeps the raw titlecased literal DET-21's pair carries. The default stays Relevance. |
| DET-60 | The card of a details section prints the score list in the legacy place — as its own block after the trail and the classification chips, above the card's description and people rows. It is the same list DET-56 draws: the five dimension rows in the fixed order, the dimension words from the `dqscore_<dimension>` keys, `overall` left out. A card with no score rows prints no block at all (the legacy's `showPlaceholder` is off on a card, so a sourceless card prints no placeholder — DET-63's card half). A card with a partial set prints only the dimensions it holds, like the opened entity's box.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| DET-61 | The score list shows on the cards of a details screen only. A results-screen card never prints it, whatever its scores — the legacy's own switch (`SHOW_DATA_QUALITY = false` on the results page, DV-202). The screen the card is mounted by decides; the card itself reads no server setting. The governance mark (VCF-19/VCF-20, UIC-38) keeps its own rule and its own column, and a card that carries both prints both: the mark in the quality column, the score list in the content blocks.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| DET-62 | Every score the increment renders reads the card's or the opened view's own `quality` rows (AVS-01, AVS-08): no extra call, no poll, no client-side roll-up. The opened entity's box and stat read the view the details screen already holds (DET-08's read); a card's list and a box's sorts read the cards the resolve already answered (DET-17's chunked resolve). A card whose scores changed while the page stayed open refreshes the next time its read runs — the box, stat, and sorts follow their own read, exactly as DET-20's keyword and DET-22's page do.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| DET-63 | "Sourceless" means the same thing in all four surfaces: no `overall` row, or one with `count` 0. The box then shows its placeholder and the stat its word (DET-56, DET-58), a card prints nothing (DET-60), and a sort takes the missing row as the last place (DET-59). A dimension row with `count` 0 prints exactly as one with a count (the legacy prints the dimension whenever its count is present, and a 0-count dimension is a held row of the roll-up). A score of `null` or a negative score in a row never renders: the row is skipped, the box keeps its other rows, and no call is retried or reported — same quiet posture as DET-49.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

## Aurelius origin

- `search/details/{dataset,collection,system,field,attribute,entity,domain}/*-details.component.{html,ts}`
  (legacy): the seven score pages. Each stats bar carries the
  `search.details.<page>.dataQuality` heading over
  `dataQualityScore$ | async | percent: '1.0-1'` with
  `<ng-template #noDataQuality>` printing the page's own `unavailable` key
  (the collection page's is `search.details.collection.dataQualityUnavailable`);
  each draws `<div id="data-quality" class="box">` with the page's own title
  key over `models4insight-data-quality-list`, and its
  `details-navigation` carries the matching entry in the place DET-58 states.
  The observable pair in each component is
  `searchResultService.document$.pipe(map((d) => d.dqscorecnt_overall?.raw ?? 0))`
  and the same for `dqscore_overall`.
- `search/components/data-quality-list/data-quality-list.component.{html,ts}`
  (legacy): the box and card body. Five dimension templates in the fixed order,
  each gated on `searchResult['dqscorecnt_' + dimension]?.raw`, the pie at
  `dqscore_<dimension>.raw * 100`, the text
  `<percent> <dimension> (<count>)`, and the `#notAvailable` branch behind
  `showPlaceholder` (off on a card).
- `search/components/cards/<type>/<type>-details-card.component.html` (legacy):
  the card block — `<div *ngIf="showDataQuality">` over
  `models4insight-data-quality-list` with `showPlaceholder` off, after the
  breadcrumb and classifications. `search/components/cards/config/show-data-quality.ts`
  and `search/results/results.component.ts` are DET-62's switch.
- `search/details/<page>/*-cards/*-cards.component.ts` (legacy): the sort lists
  DET-59 names. `attribute/fields-cards`, `collection/datasets-cards`,
  `dataset/{datasets,fields}-cards`, `domain/entity-cards`,
  `entity/{attributes,datasets,entities}-cards`, `field/fields-cards`, and
  `system/{collections,systems}-cards` ask
  `['name', 'dqscore_accuracy', …, 'dqscore_validity']`;
  `dataset/{producers,consumers}-cards`, `process/{inputs,outputs,systems}-cards`,
  `system/processes-cards`, and the two verdict boxes ask `['name']`.
  `field/data-quality-cards` asks `['name', 'dataqualityruledimension', 'dqscore']`,
  and DV-205 leaves that pair out. `search/components/sorting/sorting.component.html` renders each
  option as `{{ option | translate | titlecase }}`, which is where DET-59's
  dimension labels come from.

## Deviations

Against Apache Atlas: none — Atlas 2.4.0 has no data-quality screen, and the
legacy score documents and engine stay as 14.5 answers them. Against the demo:

- [DV-202](../../../../docs/architecture/conversion/deviations.md): the card's
  switch is a mount-site input, not the legacy's injection token.
- [DV-203](../../../../docs/architecture/conversion/deviations.md): the quickview
  panel gains no quality addon — the legacy draws none there (the roadmap's
  "quickview addon" has no legacy source).
- [DV-204](../../../../docs/architecture/conversion/deviations.md): the score
  sorts and lists run over the card rows the screen already holds instead of the
  legacy's per-ask `result_fields` and per-card document asks.
- [DV-205](../../../../docs/architecture/conversion/deviations.md): the Data
  Quality Rules box keeps DET-21's pair where the legacy sorted on Dimension and
  Quality Score — a rule's dimension is an attribute no card carries, and the
  roll-up writes no totals on a rule entity (ASQ-04, ASQ-05).

## Acceptance

Unit (offline, `uv run pytest` for nothing here — the increment is webapp-only;
`npx nx test aurelius-atlas-webapp -c ci`, and `npx nx build aurelius-atlas-webapp`
as the type gate):

- `src/app/search/details/sections/section-config.spec.ts`: DET-56/DET-57/DET-58
  for the seven layouts — the box's anchor and place in the box list, the stat
  entry's place and its `score` source kind, the nav entry's place; and the
  negative half: no score box, stat, or nav entry on the process, person, and
  the two rule rows.
- `src/app/search/details/details.component.spec.ts`: DET-56's five rows in
  order with the pie, percent, dimension word, and count; DET-56/DET-63's
  placeholder when the view has no score rows; DET-58's percent value, its
  `Unavailable` word at count 0 and with no rows, and its place in the bar;
  DET-58's nav entry; DET-62's no-extra-call rule (`httpMock.expectNone` around
  a score render); the DET-24 stats-bar pin and the DET-19 card pin updated to
  the new order.
- `src/app/search/details/sections/related-sections.state.spec.ts`: DET-59's
  option list per box — the ten that gain the five dimension sorts, and the
  exceptions that keep the pair, the governance five, and the person box; the
  five score sorts over a seeded page (score order, cards without the dimension
  last, ties by localised display text, reversed on a descending ask).
- `src/app/search/shared/catalogue-card.component.spec.ts`: DET-60's block
  content and place, the no-rows case, the partial set, and DET-61's mount-site
  switch beside the governance mark.
- `src/app/i18n-completeness.spec.ts` stays green untouched: every string here
  is a key both catalogues carry already, and the increment adds no `@@` id of
  its own.

E2E (`npx nx e2e aurelius-atlas-webapp`): one scenario on the m4i mini-graph
with a seeded score source — the sample catalogue carries no scores (the e2e
store never imports it), so the scenario writes two completeness rules and the
scanner's `m4i_dq_score` entities itself and waits the worker's roll-up (ASQ-04,
ASQ-05, ASQ-07). It opens the scored dataset, reads the box's rows and the stats
bar's percent, sorts a Fields box by Completeness, and reads the score block on
one of its cards; and the negative — a dataset with no scores shows the
placeholder and `Unavailable`, and a results row prints no score block. The
scenario names its rules (DET-56, DET-58, DET-59, DET-60, DET-61).
