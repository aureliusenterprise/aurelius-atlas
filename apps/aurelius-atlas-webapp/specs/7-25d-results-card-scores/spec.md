# 7.25d The data-quality scores: every card, the scored dimensions only

- **Status:** in review
- **Pull request:** #462
- **Records:** DET-64 new; DET-60, DET-61 and DET-63 amended; DD-860 and DD-861
  beside this spec, DD-860 supersedes DD-855; DV-202 corrected. Relies on 7.25c
  (DET-56..DET-63, DD-851..DD-857, DV-202..DV-205), 16.5d (VCF-04/VCF-05, DD-616),
  16.1 (AVS-01, AVS-08), 14.5 (ASQ-02/ASQ-04/ASQ-05, DD-528..DD-532), and 12.9
  (DD-858/DD-859, DV-206: the demo corpus ships 42 per-field scores).

## Scope

7.25c drew the score surfaces but kept two of its decisions that the demo
disproved. It printed the score list only inside a details screen, because it
read the legacy's `SHOW_DATA_QUALITY` token as a switch that turned the results
page off. It printed every dimension the roll-up holds, including the ones with
a count of 0, because it read the legacy's dimension gate as a presence test.
The legacy's own gate is a truthy test, and 0 fails it, so the legacy hid those
dimensions. The demo catalogue now ships scores (12.9), which makes both halves
visible: a search for a scored dataset answers a card with no scores while the
same entity's page shows them, and every score box fills with `0% Timeliness
(0)` rows for dimensions no rule ever measured.

This increment prints the score list on the card of both screens, and prints
only the dimensions the roll-up actually scored.

| Delivered                     | Holds                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------- |
| `catalogue-card.component.ts` | the score block with no mount-site switch (DET-61 as amended, DD-860)         |
| `results.component.html`      | the results row, unchanged markup, now printing the block (DET-61 as amended) |
| `details.component.html`      | the section card without the switch input (DET-60 as amended)                 |
| `section-config.ts`           | `qualityRows`: a dimension with a count of 0 prints no row (DET-64, DD-861)   |

Not in scope:

| Not delivered                                                              | Lands with | Why                                                                                                            |
| -------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------- |
| A score box, stat, or sort on the quickview panel or the Model Browser tab | –          | DV-203 stands: the legacy draws no quality markup there                                                        |
| A server setting or a user preference for the score list                   | –          | the block rides the data the door already answers (DET-62, AVS-01)                                             |
| A count of 0 in the stat or the box's pie                                  | –          | DET-58 and DET-63's source gate stay: no source answers the word or the placeholder, never a 0                 |
| A roll-up change on the server                                             | –          | 14.5's ASQ-04/ASQ-05 already sum and count the dimensions this screen reads. Nothing about the data moves here |

## Semantics

The ids continue DET. "The score rows" is `EntityCard.quality` (AVS-01) as 7.25c
defines it, and "the score list" is the UIC-37 `QualityDimensionList` shape the
details box draws (DET-56). "A scored dimension" is a score row of one of the
five dimensions whose `count` is greater than 0. `overall` is not a dimension.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-60 | Amended, shape only. A card prints the score list in the legacy place, as its own block after the trail and the classification chips and above the card's description and people rows. The list is the same one DET-56 draws: the scored dimensions in the fixed order, `overall` left out, each row the pie, the percent, the dimension word and the count. The card of a details section and the card of a results row print it the same way (DET-61 as amended). A card whose `quality` holds no scored dimension prints no block and no placeholder, as before (DET-63's card half). A card with a partial set prints only the dimensions it scored, as before. The block's place in the card, the list component, and the read behind it do not change (VCF-05, DET-62).                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| DET-61 | Amended, behaviour. The score list prints on the card of every screen that shows a card, whatever the screen. The mount-site switch retires: the card holds no input for it, and no screen turns it off (DD-860 supersedes DD-855). The card still reads no server setting and no user preference (DV-202 as corrected): the block appears exactly when the card holds a score source, and the two screens' cards cannot disagree because they are the same component (VCF-05). The governance mark keeps its own rule and its own column (VCF-19/VCF-20, UIC-38), and a card that carries both prints both: the mark in the quality column, the score list in the content blocks. DV-202's old screen rule is gone with this row. A scored entity on the search results answers a card with its score list, as the demo app's search cards did.                                                                                                                                                                                                                                                                                                                                                               |
| DET-63 | Amended, one clause. "Sourceless" means the same thing in all four surfaces: no `overall` row, or one with a `count` of 0. The box then shows its placeholder and the stat its word (DET-56, DET-58), a card prints nothing (DET-60), and a sort takes the missing row as the last place (DET-59). A score of `null` or a negative score in a row never renders: the row is skipped, the box keeps its other rows, and no call is retried or reported (DET-49's posture). A dimension with a count of 0 no longer prints, whatever the surface that draws it. DET-64 states that rule. Because the roll-up sums the five dimensions into `overall` (ASQ-05), a source always holds at least one scored dimension, so a box that is not sourceless never draws an empty list.                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| DET-64 | A dimension the roll-up holds with a count of 0 prints no row, on the box or on a card. The row builder drops it before the list sees it, so the box (DET-56), the stat (DET-58), the card block (DET-60) and the dimension sorts (DET-59) cannot disagree about which dimensions show. The rule follows the legacy's own gate: each dimension template renders under `searchResult['dqscore_' + dimension]?.raw`, a truthy test on the count, and a count of 0 fails it. The frozen oracle proves what the legacy measured: of its 684 documents, `dqscorecnt_timeliness` and `dqscorecnt_validity` are 0 on all 684, so a legacy page never drew a Timeliness or Validity row anywhere (LAS-12, 14.1). A dimension whose count is greater than 0 prints even when its score is 0, because a scored dimension answers a real measured result. A dimension row whose score is `null` or negative still prints no row (DET-63), and the count gate never turns a held row into a placeholder: the placeholder belongs to the sourceless case alone. The score sorts keep their own posture (DET-59): a card that holds no scored row for the sorted dimension sorts last, whether the row is absent or 0-count. |

## Aurelius origin

- `search/components/data-quality-list/data-quality-list.component.{html,ts}`
  (legacy, 7.25c's own cite): the five dimension templates, each gated on
  `searchResult['dqscorecnt_' + dimension]?.raw`. JavaScript reads `0` as false,
  so the legacy's own list hides a dimension whose count is 0. 7.25c read that
  gate as a presence test and printed the row (DET-63), which is the clause
  DET-64 corrects.
- `libs/python/aurelius-atlas-core/tests/fixtures/legacy-app-search-atlas-dev.json`
  (14.1's frozen oracle): the counts the legacy's own documents answered.
  `dqscorecnt_timeliness` and `dqscorecnt_validity` are 0 on all 684 documents,
  `dqscorecnt_uniqueness` on 677, and `dqscorecnt_accuracy` on 632, so the
  dimensions with nothing measured held a 0 count rather than no field. The 81
  documents with totals print exactly the scored dimensions DET-64 keeps.
- `libs/python/aurelius-atlas-core/tests/fixtures/legacy-app-search-atlas-dev-quality.json`
  (12.9's source): the 42 per-field rows the demo's boxes now render, each of
  one dimension of accuracy or completeness, which is why the other three print
  0 for every demo entity.
- `search/components/cards/config/show-data-quality.ts` and
  `search/results/results.component.ts` (legacy): the switch 7.25c ported as
  DET-61. The repo carries no copy of either file (the webapp's sources are not
  vendored, unlike Atlas's `dashboardv2`/`dashboardv3`), and DV-202 recorded the
  claim rather than a citation. The demo's own search cards showed per-entity
  scores, which is what DET-61 as amended prints.

## Deviations

Against Apache Atlas: none. Atlas 2.4.0 has no data-quality screen, and the
score documents and engine stay as 14.5 answers them.

Against the demo, one correction:

- [DV-202](../../../../docs/architecture/conversion/deviations.md), corrected in
  place: its cell claimed the legacy's `SHOW_DATA_QUALITY` token reaches every
  details card and stays off on the results page. No copy of that file exists in
  this repository, so the claim was unverifiable, and it decided against what
  the demo app showed. The card now prints the score list on both screens
  (DET-61 as amended). The deviation that stands is the smaller one: Aurelius
  has no injection token for a shared card at all, because one component serves
  both screens (VCF-05), and it needs none now that no screen switches the list
  off.

## Acceptance

Unit (offline, `npx nx test aurelius-atlas-webapp -c ci`, and `npx nx build
aurelius-atlas-webapp` as the type gate):

- `src/app/search/shared/catalogue-card.component.spec.ts` (DET-60, DET-61,
  DET-64): the block prints with no switch input at all; the same scored card
  mounted by a results host prints it; the zero-count dimensions drop out of the
  row list; a card with no scored dimension prints no block and no placeholder;
  the governance mark and the score list still print together in their own
  corners; the block's place between the chips and the description is unchanged.
- `src/app/search/details/sections/section-config.spec.ts` (DET-63, DET-64):
  `qualityRows` drops a dimension whose count is 0 and keeps a dimension whose
  score is 0; `hasScoreSource` and `overallRow` keep their gate; `dimensionScore`
  keeps its last-place posture for a 0-count row.
- `src/app/search/details/details.component.spec.ts` (DET-56, DET-63, DET-64):
  the box draws only the scored dimension rows; the placeholder and the stat's
  word still answer the sourceless view; the stats bar and the side navigation
  keep the DET-58 places.
- `src/app/search/results/results.component.spec.ts` (DET-61 as amended): a
  scored card in the results list draws its score block, and an un-scored card
  draws none.
- `src/app/search/details/sections/related-sections.state.spec.ts` (DET-59):
  unchanged green. The sorts read the row's score through `dimensionScore`, so
  the row builder's drop cannot move a card's place.
- `src/app/i18n-completeness.spec.ts` stays green untouched: this increment adds
  no `@@` id of its own.

E2E (`npx nx e2e aurelius-atlas-webapp`): the 7.25c scenario carries the change.
The scored dataset's box answers one row (`70% Completeness (2)`) instead of five,
the Fields card block answers one row, the scored dataset's results row now
prints the block, and the un-scored twin answers the placeholder and the word as
before (DET-56, DET-58, DET-63). The scenario names DET-64 beside its old rules.
