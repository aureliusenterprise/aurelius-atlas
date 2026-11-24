# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design
log apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

## DD-860. The card prints its score list on every screen, with no switch

- **Status:** Proposed
- **Increment:** 7.25d
- **Date:** 2026-11-24
- **Supersedes:** DD-855 (Proposed, 7.25c, the card's score list is a mount-site
  input)

**Decision.** `CatalogueCard` loses `showScores`. The card prints DET-60's block
exactly when its own `quality` rows hold a scored dimension (DET-64), on a
details section and on a results row alike. `results.component.html` passes
nothing new, and `details.component.html` drops the `[showScores]="true"` binding
and the switch's comments.

**Reason.** DD-855 kept a boolean input because DET-61 read the legacy's
`SHOW_DATA_QUALITY` injection token as a switch that turned the results page off.
DV-202 recorded that reading without a citation: no copy of
`show-data-quality.ts` or the results component exists in this repository (the
Aurelius legacy webapp is not vendored, unlike Atlas's `dashboardv2`/`dashboardv3`),
so the claim could not be checked. 12.9 put the demo's real scores behind the
screens, and the decision showed its cost: a search for a scored dataset answers
a card that hides scores the same entity's page prints. The demo app showed
per-entity scores on its search cards, which is what DET-61 as amended prints.
DD-855's own rejected alternative turns out to be the right shape: the data
decides, because the block appears whenever the door answered a score source
(AVS-01, DET-62). DET-61's surviving rule is the honest half of DV-202: Aurelius
has no injection token for a card, because one component serves both screens
(VCF-05), and it needs none now that no screen turns the list off.

**Alternatives considered.**

Keep the input and pass `true` from the results screen (refused: DET-61 is about
what the user sees, not about a knob, and an input that is always `true` on both
mount sites is dead code that the next reader must decode). Keep the input for a
future preference (refused: no spec asks for one, and DET-62 rules the block by
the data the screen already holds; a switch would be a second answer to DET-63's
one source question). Read `showScores` from a server setting (refused: DV-202's
standing rule, the card reads no setting of its own).

**Consequences.** `catalogue-card.component.spec.ts` loses its DET-61 mount-site
test and gains the block on a default-mounted (results-shaped) card. The 7.25c
e2e scenario's DET-61 half flips from "prints no block" to "prints the block".
The comment block in `details.component.html` that cited the switch retires with
the binding. Because both screens now share one rule, a future difference between
them needs its own spec row, not a silent input.

## DD-861. A dimension with a count of 0 prints no row

- **Status:** Proposed
- **Increment:** 7.25d
- **Date:** 2026-11-24
- **Supersedes:** none; amends DET-63's clause (7.25c)

**Decision.** `qualityRows` drops a dimension row whose `count` is 0, before the
list, box, stat, and card see it. DET-64 states the rule; DET-63's "a 0-count
dimension stays" clause is gone.

**Reason.** 7.25c's DET-63 read the legacy's gate as a presence test. The legacy's
own template gates each dimension on
`searchResult['dqscorecnt_' + dimension]?.raw`, which is a truthy test, and
JavaScript reads `0` as false, so a 0 count hides the row. The frozen oracle
proves what the legacy measured: `dqscorecnt_timeliness` and `dqscorecnt_validity`
are `0` on all 684 documents and `dqscorecnt_accuracy` on 632, so a legacy page
drew a Timeliness row nowhere, and the five-row boxes 7.25c printed were five
rows the legacy never drew. On the demo's data (12.9) it shows on every scored
entity: the 42 baked rows score accuracy and completeness, so the box fills with
`0% Timeliness (0)`, `0% Uniqueness (0)` and `0% Validity (0)` rows for
dimensions no rule measured. Dropping them makes the box say what was measured.
The drop lives in `qualityRows`, the one builder the box, stat, card and sorts
share (DD-852), so DET-56/58/60/59 cannot disagree about which dimensions show.
The count gate is separate from DET-63's score gate: a dimension with a count
above 0 prints even when its score is 0, because a score of 0 is a real measured
result, not an absence. The placeholder belongs to the sourceless case alone
(DET-56, DET-63), and ASQ-05 sums the five dimensions into `overall`, so a source
always holds at least one scored dimension and a non-sourceless box never draws
an empty list.

**Alternatives considered.**

Hide the row only on the card and keep it in the box (refused: the same five
rows are the same list, and DET-63's posture is that the surfaces agree). Filter
in the UIC-37 list component (refused: the list is dumb and the rule is a
catalogue rule about the roll-up, not a presentation rule; the details box and
the sorts read the rows without the list). Hide the row only when its score is
also 0 (refused: it conflates the count gate DET-64 states with DET-63's score
gate, and a dimension measured 0 times at 0 is different from one measured
thrice averaging 0).

**Consequences.** The 7.25c spec's DET-63 row and its e2e `five-row box` note are
amended, and the e2e box assertion drops to its scored rows (one Completeness row
over the seeded fields). `details.component.spec.ts`'s five-row case,
`catalogue-card.component.spec.ts`'s four-row case, and
`section-config.spec.ts`'s `qualityRows` case re-baseline to the scored subset.
The score sorts (DET-59) do not move: `dimensionScore` reads a row's score
directly, so a 0-count row was already last. `section-config.ts`'s DET-63 comment
and `hasScoreSource`'s doc are retargeted to DET-64.
