# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-865. The screen hands the box its score rows; the store joins them by GUID

- **Status:** Proposed
- **Increment:** 7.25e
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** The details screen passes the opened view's `ruleScores` (AVS-13)
into `RelatedSectionsState.seed` beside the verdict GUIDs 7.25b already passes
(DD-848's parameter), and the store joins each row to the section card whose GUID
it names (DET-65). A card with no row carries nothing. The join is one map lookup
per card at view build time, over what the seed already holds — no request, no
store read, no new state signal.

**Why.** The box's rows come from the field, and the screen holds the field's
view; the box's cards come from the search door's chunks and know nothing about
the field. Something has to marry the two, and the sections store is the one
place that holds both (its `SectionRecord.resolved` map is the same join DET-18
and DET-53 already do). Doing it in the store keeps the card dumb (DD-616) and
keeps DET-62's rule — "no extra call, no poll, no client-side roll-up" — literally
true. 7.25b's verdict boxes proved the shape from the other side: the screen
owns the rows, the shared chrome draws them (DD-848), and the box needed no
knowledge of where its rows came from.

**Considered and rejected.** _A door that answers rule cards with their score for
one field_ — the pair argument of 16.5j's DD-863, and it would make a box's
search-door read depend on which field asked; _the card fetching its own score_ —
DV-198 refused the per-card fetch for less data than this; _a screen-side join in
`Details`_ — the sort must see the rows (DET-66), and the sort lives in the store,
so a screen-side join would leave DET-66 unimplementable.

## DD-866. One card prints the score row; the ui list grows `showCount`

- **Status:** Proposed
- **Increment:** 7.25e
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `CatalogueCard` grows one optional input, `ruleScore`, and prints it
as one UIC-37 row in DET-60's place (DET-65). `QualityDimensionList` grows one
input, `showCount` (default true), which prints or hides the parenthesised count.
No new card component and no new list component.

**Why.** The legacy shipped a card component per entity type and a dimension list
per surface, so its rule card and its roll-up list were separate code. Aurelius
has one rich card (VCF-05, DD-616) and one dimension list (DD-447), and DET-60/
DET-65's rows are the same three glyphs — pie, percent, word. The only real
difference is the count, which the roll-up prints and the rule card does not, so
that one glyph becomes the one input. A second card component for rules would
re-fork the trail, chips, description, and people rows the box needs unchanged,
and a rule-specific row markup would drift from DET-56/DET-60's percent shape the
moment either moves.

**Considered and rejected.** _A `ruleScore` field on the card's data_ — DD-863's
pair argument, in Angular's terms; _drawing the row in `Details` around the card_
— the row belongs in DET-60's place, which is inside the card; _two ui components_
— the fork above.

## DD-867. The rules stat stays the section count

- **Status:** Proposed
- **Increment:** 7.25e
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** The Data Quality Rules stat keeps its value as the DET-17 seed
count (DET-36, DET-24). It does not become the count of score rows, and the score
stat (DET-58) keeps reading the `overall` roll-up.

**Why.** The legacy's two numbers came from one document field: its
`dataQualityRules` stat and its `dataQuality` stat both read `dqscorecnt_overall`
on the field's search document (`field-details.component.ts`), so the box, the
stat, and the score all agreed by construction — and all three described the
scanner's results, not the field's rules. Aurelius' stat rule is uniform across
every box (DET-24: a section's stat is its seed count), and DET-36 chose the seed
count for exactly that reason (DD-444). With scores on the cards now, the two
readings can differ — an associated rule the scanner never scored adds a card and
no score row (DV-207) — and the choice is which agreement to keep: the stat and
the box's count line agreeing with each other (DET-24), or both agreeing with the
scanner. The first is this webapp's own invariant and the one a person can check
by counting cards, so it stays. The legacy's number survives where it belongs:
the score stat's percent and the roll-up's counts (DET-58, DET-56), which read
the same totals 14.5 derives from those same scores.

**Considered and rejected.** _Point DET-36 at `ruleScores.length`_ — the stat
then disagrees with the box's own count line whenever a rule is unscored, which
DET-24's uniformity exists to prevent; _show both numbers_ — the stats bar has one
heading per box (DET-23) and inventing a heading is the demo's vocabulary, not
the legacy's.
