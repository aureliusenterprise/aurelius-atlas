# 7.25e The Data Quality Rules box shows each rule's score on this field

- **Status:** in review
- **Pull request:** #463
- **Records:** DET-65, DET-66 new; DV-207 new, DV-205 superseded by it; DD-865
  to DD-867 (here); relies on 16.5j (ASQ-09, AVS-13, VDR-16, DD-862..DD-864),
  7.24 (DET-35/DET-36, DD-444), 7.25c (DET-59..DET-63, DD-851..DD-857,
  DV-205), 7.25d (DET-60..DET-64, DD-860/DD-861), 16.1 (AVS-04), 16.5d (VCF-05,
  DD-616), and 12.9 (DD-858/DD-859, DV-206: the demo corpus ships 42 per-field
  scores).

## Scope

The field page's Data Quality Rules box (DET-35) shows nine rule cards and no
score. The legacy box showed a score on every card, because its cards were the
App Search `data_quality` **results** — the query filtered `fieldguid: [entityId]`
and read `dqscore` beside the rule's name and dimension
(`apps/atlas/src/app/search/details/field/data-quality-cards/`). Aurelius seeds
the box from the field's `dataQuality` end instead (DD-444) and dropped the score
column because the score had no source (DD-369, DD-444's own note that 7.25 would
bring it back).

The source exists now: 14.5's worker derives a `qualityResult` per score, over
the fields it scored (ASQ-02), and 16.5j joins the field's results into its view
(AVS-13, VDR-16). This increment draws them: a rule card in that box carries the
pie, the percent, and the dimension of the score that rule earned on this field,
and the box gains back the two sorts DD-444 dropped.

| Delivered                                         | Holds                                                                |
| ------------------------------------------------- | -------------------------------------------------------------------- |
| `atlas-view.ts`                                   | the `RuleScore` twin of AVS-13 (AVS-07)                              |
| `related-sections.state.ts`                       | the box's score join and its two new sorts (DET-65, DET-66)          |
| `section-config.ts`                               | the field box's config row: its sort set (DET-66)                    |
| `catalogue-card.component.ts`                     | the rule score row, in DET-60's place (DET-65)                       |
| `details.component.html` / `details.component.ts` | the screen's join, from the view the screen already holds (DET-62)   |
| `quality-dimension-list.component.ts` (ui)        | `showCount`, so one row prints the legacy rule card's shape (DET-65) |

Not in scope:

| Not delivered                                                                             | Lands with | Why                                                                                                                                                                                                                                         |
| ----------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The Data Quality Rules stat (DET-36) reading the score count instead of the section count | –          | DET-24's rule is uniform — a section's stat is its seed count — and the box counts what it lists. The legacy number was the field's score count; where the two differ (an associated rule with no score), the box and its stat stay in step |
| A score on the score box (DET-56), the stat (DET-58), or the other boxes' sorts           | –          | 7.25c ships those over the view's `quality` roll-up; nothing here changes them                                                                                                                                                              |
| A per-card request for the score                                                          | –          | DET-62: the screen already holds the view the rows ride (DV-198's posture)                                                                                                                                                                  |
| A facet group for the dimension on this box                                               | –          | DV-168 stands: the popover counts card fields, and a rule card carries no dimension of its own                                                                                                                                              |
| Result-shaped cards (the box listing the scores instead of the rules)                     | –          | DET-35's seed stays (DD-444's box, 16.5j's DD-863): an associated rule with no score keeps its card, unscored (DV-207)                                                                                                                      |
| Scores on the rule's own page, on a dataset's Governance box, or on search cards          | –          | AVS-13: a score is a rule/field pair; only a field's view answers them (DD-863)                                                                                                                                                             |

## Semantics

The ids continue DET. "The field's rule scores" are the opened field view's
`ruleScores` rows (AVS-13, 16.5j): each one rule GUID, rule name, dimension, and
score. "A rule card" is a card of the field layout's `#related-rules` box
(DET-35). "Its score" is the row of the same rule GUID — matched by GUID, never
by name.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-65 | A rule card of the field box prints its score in DET-60's place — the score block after the trail and the classification chips and above the description and people rows — as one row of the UIC-37 list: the UIC-36 pie, the percent, the dimension word. The percent is the score at `percent: '1.0-1'`, the dimension word is the row's dimension lowercased, and no count prints, exactly as the legacy's rule card rendered (`data-quality-card.component.html`: the pie at `dqscore.raw * 100`, the percent, the dimension `dataqualityruledimension.raw \| lowercase`). The row is the field's row for that rule (AVS-13), joined by GUID — the card's own `quality` is never the source, and a rule card with no row prints no block (DET-63's card half: no source, no placeholder). The join changes nothing else about the card: the same component with no row renders as DET-60 states, so a rule card anywhere else — a search result, another screen — prints nothing extra. The score row and DET-60's roll-up never both print on one card: a rule entity carries no score totals (ASQ-04 attaches totals to fields and above), so its roll-up is empty. A score the screen cannot use — absent, negative, not a number — prints no row (DET-63's posture), and neither does a row whose dimension word is empty: no line prints for a row the card cannot name |
| DET-66 | The field box's sort select holds four options in this order: Relevance, Name, Dimension, Quality Score. Their keys are DET-21's two plus the legacy box's own two asks — `['name', 'dataqualityruledimension', 'dqscore']` (`data-quality-cards.component.ts`) — so DD-444's dropped sorts return through their own entry as its consequences promised; Relevance leads because the legacy's sorting component puts `_score` first whatever the box asks. Relevance is DET-21's seed order and Name is DET-21's Name. Dimension orders by the joined row's dimension word, ascending; Quality Score orders by its score, ascending, both with DET-59's posture: a card the sorted field cannot place — no row at all, or a row DET-65 prints no line for — takes the last place of the ascending order, a tie falls back to DET-59's label tie-break, and a descending ask is DET-21's plain reversal. The labels are the catalogue's `dataqualityruledimension` and `dqscore` keys — "Dimension" and "Quality Score" — the two every locale already carries (DD-622's rule); Relevance and Name keep their 7.21a/7.25c shapes. DET-59's ten score boxes and DET-21's pair stay as they are. DET-19's uniformity is the legacy's own: its box held four options where the score pages' boxes held seven, so this box's set is the parity, not a per-box invention               |

## Aurelius origin

- `apps/atlas/src/app/search/details/field/data-quality-cards/data-quality-cards.component.ts`
  (legacy): the box's three sort options `['name', 'dataqualityruledimension',
'dqscore']` and its `result_fields` `guid, name,
dataqualityruledescription, dataqualityruledimension, dqscore` over
  `filters.all` `[{fieldguid: [entityId]}]`, page size 9. DET-66 ports the
  option list; AVS-13 carries the four fields the ask read.
- `apps/atlas/src/app/search/components/sorting/sorting.component.html` (legacy):
  the select every box shares — a hard-coded `_score` option translated by
  `search.components.sorting.relevance` first, then each asked option rendered
  `option | translate | titlecase`. That render is why DET-66's two new labels
  are the dictionary's own words for `dataqualityruledimension` and `dqscore`
  ("Dimension", "Quality Score"), and why Relevance leads the list.
- `apps/atlas/src/app/search/components/cards/data-quality/data-quality-card.component.html`
  (legacy): the card each result rendered — `data-quality-pie` at
  `dqscore.raw * 100`, then `dqscore.raw | percent: '1.0-1'`, then
  `dataqualityruledimension.raw | lowercase`, then the rule description as the
  card's text. DET-65 ports the row. The description line is the rule card's
  `definition` in Aurelius, which DET-60 already prints from the card (the
  resolved rule entity carries its own `ruleDescription` as its description).
- `apps/atlas/src/app/search/components/data-quality-list/data-quality-list.component.html`
  (legacy): the box and stat list, which **does** print the count in parentheses.
  `showCount` keeps that shape for DET-56/DET-60 and lets DET-65's row print the
  rule card's shape — the two legacy templates, one component.
- [DD-444](../7-24-dq-rules-governance-banner/design.md#dd-444-the-rules-box-seeds-from-the-relationship-end-not-a-quality-index)
  (7.24): the box's seed and the deferred return, quoted in 16.5j's origin. The
  box keeps its seed; only the score row and the sort list arrive.

## Deviations

Against Apache Atlas: none. Data-quality scores are m4i/Aurelius demo furniture
(ATLAS has none, ASQ-08).

Against the demo, one new row and one retirement:

- [DV-207](../../../../docs/architecture/conversion/deviations.md): the demo's
  box listed only the results — a rule associated with a field but never scored
  by the scanner was absent from the box, because the engine answer had no row
  for it. Aurelius keeps DET-35's seed, so the rule's card stays and prints no
  score row (DET-65). Nothing is hidden, and the score appears exactly where the
  scanner measured one. The row supersedes
  [DV-205](../../../../docs/architecture/conversion/deviations.md) (7.25c),
  whose Relevance/Name hold was the honest answer while the score had no source:
  DET-66 returns the legacy's two options over 16.5j's rows, with no wire change
  and no per-card read.

The legacy box's own query also carried the dimension facet the popover asked
(`dataqualityruledimension`, DV-168): unchanged, still the empty popover line.

## Acceptance

Unit (offline, `npx nx test aurelius-atlas-webapp -c ci`, and `npx nx build
aurelius-atlas-webapp` as the type gate):

- `src/app/search/shared/catalogue-card.component.spec.ts` (DET-65): a rule card
  mounted with a row prints the pie, the percent to one decimal, and the
  dimension lowercased, with no count; a rule card mounted without one prints no
  block; the same card with a `quality` roll-up and a row prints the row (DET-65
  over DET-60) and never both; a negative or absent score prints no row; a card
  with no row still prints DET-60's roll-up when it holds one.
- `src/app/search/details/sections/related-sections.state.spec.ts` (DET-65,
  DET-66): the box's cards carry the field's rows by GUID, unmatched cards carry
  none; the sort list holds Relevance, Name, Dimension, Quality Score in order;
  Dimension and Quality Score order ascending with a card the field cannot place
  taking DET-59's last place (a descending ask is DET-21's plain reversal);
  ties fall back to the label order (DET-59); the other boxes keep their own
  lists and comparators.
- `src/app/search/details/details.component.spec.ts` (DET-65, DET-62): opening a
  field whose view carries rows paints them on the matching rule cards without a
  second request; opening a dataset leaves the box as DET-35 states; the score
  box, the stats bar, and the navigation keep their DET-56/DET-58/DET-36 places.
- `src/app/search/details/sections/section-config.spec.ts` (DET-66): the field
  layout's rules row names its sort set, and no other layout row gains it.
- `src/app/i18n-completeness.spec.ts` (SHL-08): the box's two sort labels ride
  existing keys, so the catalogues need no new entry (checked, not changed).
- `libs/angular/aurelius-atlas-ui/src/lib/quality-dimension-list/quality-dimension-list.component.spec.ts`
  (DET-65): `showCount` off prints the row without the count, on keeps DET-56's
  shape.

Route/E2E (Level 2, on the dev stack):

- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp_quality_scores.py`
  (grows one scenario, DET-65/DET-66): open a demo field 12.9 scores — a
  `FUNC_ORGANIZATION` field with one Accuracy and one Completeness rule — and
  state that each rule card prints its percent and dimension, that the score
  box and stat above it still print the roll-up, and that the sort select holds
  Relevance, Name, Dimension, Quality Score. The scored values are read from the
  door's own answer, not hardcoded twice.
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp_quality_rules.py`
  (DET-35's scenario, unchanged expectations): the box still lists every rule of
  the end, including one with no score (DV-207).
