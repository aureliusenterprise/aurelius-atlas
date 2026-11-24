# 7.25b The governance rule's own page: counts, chart, and the two verdict lists

- **Status:** in progress
- **Pull request:** –
- **Records:** DET-50..DET-55, VDR-15 new; DV-201 new; DD-848 to DD-850; relies
  on 16.5i (ASG-09, AVS-12, VDR-14, DD-845..847, part-0), 14.6 (ASG-03/ASG-06),
  16.5i's ADR 071, 7.21a (DET-17..DET-24's section chrome and stats bar,
  UIC-27/UIC-24), 7.24 (UIC-36, the pie), 16.5d (VCF-05, the shared card),
  7.27 (DET-38, the rule-adjacent layout row), 7.25a (DET-42's box, the rule
  types' read), 7.29 (DET-49's failure posture)

This page is the `aurelius-atlas-webapp` part of increment 16.5i; its rule table
is the increment's shared set. The other part is with
[`aurelius-atlas-core`][part-0], which answers the door.

The legacy details screen dispatched ten layouts by type, and the tenth was not
a catalogue page but a verdict page: an `m4i_gov_data_quality` rule opened the
`gov-quality` layout (`.scratch/aurelius`,
`apps/atlas/src/app/search/details/details.component.ts` — the tenth entry of
`componentsByType`). Its content was the rule's whole verdict story: a
description box, a three-heading stats bar (Non-compliant, Compliant,
Properties), a Compliance Chart — a legend and the score pie of the compliant
share — and two card lists, one per verdict, each the shared card chrome over
the entities the rule judged. Aurelius has every part of that screen except the
screen: the worker keeps the verdicts current (ASG-06), the cards and the chrome
and the pie shipped (VCF-05, UIC-27, UIC-36), and 16.5i's part-0 answers the
door the lists read. The rule's page is the last box of roadmap 7.25 that has a
data source today — the score halves stay with the `dqscore_*` hold-out (DD-369).

The page opens where the shipped ones already lead: a row of 7.25a's
Governance Quality Rules box, the rule cards of the results screen, a search
for the rule by name.

## Scope

- the rule's layout row: description box, stats bar, chart box, the two verdict
  boxes, properties, and the three-entry navigation, in the legacy order
  (DET-50);
- the verdict read and its join: one door call split into the two lists, the
  counts, and the chart's score (DET-51, DET-52);
- the two card boxes over the shared chrome, the shared card, and the door's
  card resolve (DET-53);
- the compliance chart: legend, pie, score (DET-54);
- the unchanged neighbours: every other layout, 7.25a's box, the rule's Fields
  page (the `m4i_data_quality` row of DET-38), the card's governance mark
  (VCF-19).

Not in scope:

| Not delivered                                                                                                              | Lands with |
| -------------------------------------------------------------------------------------------------------------------------- | ---------- |
| The door and the store read (ASG-09, AVS-12, VDR-14)                                                                       | [part-0]   |
| The `dqscore_*` score boxes, pies and badges on the catalogue pages (roadmap 7.25's score half, DD-369's hold-out)         | 7.25c      |
| The `m4i_data_quality` page gaining any of this: the legacy dispatched it to the default layout, and it keeps DET-38 alone | –          |
| A verdict read of the rule's own view or the aux validate call: the page reads stored verdicts only (ADR 071 R2)           | –          |

## Semantics

The ids continue DET; the increment's store ids (ASG-09, AVS-12, VDR-14) live
with [part-0](../../../../libs/python/aurelius-atlas-core/specs/16-5i-rule-verdicts-door/spec.md).
"The rule page" below is what the details screen draws for an
`m4i_gov_data_quality` entity — the new layout row; every other layout keeps
its 7.21a–7.29 content unchanged.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VDR-15 | The `aurelius-atlas-data-access` view family grows the door's Angular twin: `RuleVerdictsService.verdicts(rule)` posts `{ rule }` to `/api/aurelius/v1/rule/verdicts` behind the same `API_BASE_URL` and bearer token as the other doors (APC-01), and answers `{ verdicts }` in the AVS-12 row shape (`atlas-view.ts` twin, AVS-07). It is the only caller of the route.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| DET-50 | The `m4i_gov_data_quality` type enters the layout dispatch (DET-15's direct hit) with the legacy page's content in the legacy order: the description box (no People box), the stats bar, the chart box, the Non-compliant box, the Compliant box, and the properties accordion. The side navigation carries three entries in that order — `search.details.govQuality.nonCompliant`, `search.details.govQuality.compliant`, `search.details.govQuality.properties` — anchored to `#related-non-compliants`, `#related-compliants`, and `#properties-details`; like the legacy, the nav names neither the description nor the chart (DET-25's anchor rules apply unchanged). The description box's title is `search.details.govQuality.description` and the properties accordion's `search.details.govQuality.properties`.                                                                                                                                                                                             |
| DET-51 | On every rule arrival the page asks part-0's door once for the opened rule's GUID and splits the rows by the row's `compliant`: `false` rows seed the Non-compliant box, `true` rows the Compliant box, a `null` verdict seeds neither (the legacy's asks filtered `compliant` to one value each). The score the chart shows is `compliant / (compliant + nonCompliant) × 100`, the legacy's own formula, and `0` when the rule judges nothing (the legacy answered `NaN` there, which painted no green arc — the same pixels, no `NaN`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| DET-52 | The stats bar's three headings are the layout's, in legacy order: Non-compliant showing the non-compliant rows' count, Compliant showing the compliant rows' count, Properties showing the rendered property rows as every other layout does (DET-24). The counts update with the read; while it is in flight they show `0`, the legacy's `startWith(0)`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| DET-53 | Each verdict box is a card section of the shared chrome (UIC-27) with the legacy titles `search.details.govQuality.nonCompliantCards.title` and `search.details.govQuality.compliantCards.title`, seeded from its rows' entity GUIDs in door order (ASG-09's id order). Its cards resolve through the search door's `guid` filter in chunks of 25 exactly as every DET-17 box does — the same chunked resolve, loading rows, failed-chunk alert and deleted-guid rule (DET-18, VCF-02), and the same nine-at-a-time scroll (DET-22). The keyword, the relevance-then-name sort, and the funnel behave as the sections store's do (DET-20, DET-21, VCF-08..VCF-12), over the card's fields, with the box's facet groups the person box's four — `typeName`, `m4i_data_domain`, `m4i_data_entity`, and `name` (the legacy asked the eight `ENTITY_SEARCH_FACETS` groups; DV-201 maps them to the four the search door counts). A row's card is the shared rich card (VCF-05); clicking one opens that entity (DET-06). |
| DET-54 | The chart box sits between the stats bar and the Non-compliant box (the legacy place): its title is `search.details.govQuality.complianceChart`, it holds the UIC-36 pie at size 8 with DET-51's score, and beside it the two-row legend — Non-compliant first with its red swatch, Compliant second with its green — the legacy's colours (`hsl(348 100% 61%)`, `hsl(141 53% 53%)`) and order.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| DET-55 | The read's failure posture is DET-49's: a failed door call keeps the page and renders both boxes empty at count `0` and a score of `0`, quietly — no alert, no retry loop. A card chunk that fails follows the sections store's rule, not this one: one alert, cards dropped, count kept (DET-18).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## Aurelius origin

- `search/details/gov-quality/gov-quality-details.component.{html,ts}` (legacy):
  the whole page. The stats bar's three headings read the two card services'
  `meta.page.total_results` with `startWith(0)`; the chart's score is
  `compliantCount / (compliantCount + nonCompliantCount) * 100` over a
  `models4insight-data-quality-pie` of `size 8`; the legend swatches are
  `.legend-non-compliant` before `.legend-compliant` with the two `hsl` colours
  the component's stylesheet pins.
- `search/details/gov-quality/{non-compliant,compliant}-cards/`: the two boxes.
  Each asks the `atlas-dev-gov-quality` engine with `filters.all`
  `[{ compliant: ['0' | '1'] }, { guid: [ruleGuid] }]`, reads `entity_guid`,
  loads every verdict page, then draws `details-cards-list` over an
  `atlas-dev` ask `filters.all [{ guid: [entityGuids] }]`, page 9, with
  `sortingOptions: ['name']` and the descendants control off. DET-51/DET-53
  replace the two engine asks with part-0's door call; the card ask becomes the
  shared chunked door resolve (DET-53).
- `search/details/details.component.ts` (legacy): the dispatch's tenth entry —
  `m4i_gov_data_quality` opens this page; `m4i_data_quality` is not in the
  table and keeps the default layout (DET-38 keeps it here).

## Deviations

Against Apache Atlas: none — the page and the door have no Atlas twin. Against
the demo, [DV-201](../../../../docs/architecture/conversion/deviations.md):
the page's two paged engine asks (verdict pages of up to 1,000, then entity
pages) become one door call answering every verdict of the rule, with the card
resolve as every other box's. The two counts come from the rows the browser
already holds instead of the engine's page metadata (DD-847), and a rule judging
nothing shows score `0` where the legacy computed `NaN` (DET-51's sentence).

## Acceptance

Unit (offline, `nx test aurelius-atlas-webapp -c ci`):

- `src/app/search/details/sections/rule-verdicts.state.spec.ts`: DET-51's split
  (false rows left, true rows right, null rows neither) and the score with its
  empty case; DET-52's counts; DET-55's quiet empty on a failed read and the
  clear on a null entity (DD-850).
- `src/app/search/details/sections/related-sections.state.spec.ts`: DET-53 over
  the seed entry DD-848 adds — the verdict GUIDs seed the two anchors, the
  chunked resolve of 25, the failed-chunk alert and the missing-guid rule, the
  keyword, sort, facet counts and page-of-9, and `countFor` for the stats bar.
- `src/app/search/details/sections/section-config.spec.ts`: DET-50 for the new
  row — section order (non-compliants before compliants), the three nav entries
  and anchors, the three stat sources; every other layout row unchanged.
- `src/app/search/details/details.component.spec.ts`: DET-50's drawn order,
  DET-52's live counts, DET-54's pie value and legend order on a stubbed store.
- `libs/angular/aurelius-atlas-data-access/src/lib/aurelius/rule-verdicts.service.spec.ts`:
  VDR-15's URL, body and answer.
- `src/app/i18n-completeness.spec.ts`: green, unchanged — every key the page
  shows already rides both catalogues: the seven `search.details.govQuality.*`.

E2E (Level 2, `nx e2e aurelius-atlas-webapp`):

- `e2e/test__aurelius_atlas_webapp_rule_page.py`: seed a dataset with a name but
  no description, seed two ACTIVE readable rules over `m4i_dataset` (a
  name-present rule it passes, a description-filled rule it refuses), wait for
  the worker's round through the door itself (ASG-06), open the refused rule's
  page, and assert DET-50..DET-54: the stats `1 / 0 / properties`, the pie at
  score 0, the Non-compliant box holding the dataset's card and the Compliant
  box empty, the nav entry scrolling to `#related-compliants`; then the passing
  rule's page at `0 / 1` and score 100. The rules and dataset ride the run's
  names and self-clean; no shared service restarts (DD-223).
