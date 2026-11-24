# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

The score roll-up itself (ASQ-01..ASQ-08, DD-528..DD-532) and the card shape
that carries it (AVS-01, AVS-08, ADR 064) stand unchanged: this increment reads
them and draws them, and adds no backend surface.

## DD-851. The score box is a layout box, not a card section

- **Status:** Proposed
- **Increment:** 7.25c
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `SectionDef` grows a third `kind`: `"score"` (next to
`"gov-quality"`, 7.25a). A score layout's row of the box list carries it with
the layout's title, the `data-quality` anchor, and empty `seedKeys` and
`facets`. `DetailsComponent.sectionViews` draws it the way it draws the
governance box today — one entry of the layout's order, the renderer picked by
`kind` — over a computed built from the opened view (DD-852), and the shared
card chrome never sees it. `section-config.spec.ts` pins the seven rows in
order, the negative five, and that a score entry yields no card view.

**Why.** The legacy's `#data-quality` div is a box, not a
`details-cards-list`: it has no keyword, no sort, no funnel, no page, and no
count line, and the score rows never page. Reusing the card-section store would
buy none of DET-17..DET-22's machinery and would need them all switched off —
seven off-switches in a store that already runs the box lists of nine layouts.
The `kind` seam 7.25a cut for the governance box is exactly this shape, and
`sectionViews` already renders a mixed list in config order, so the box lands
in the legacy position with one branch.

**Considered alternatives.**

- _Hand the box to the sections store as a seedless section._ Rejected — DET-56
  forbids the chrome's keyword, sort, facets, and count line, so every one of
  its rules would need suppressing, and `countFor` would report a stat the spec
  says is a percent.
- _A template block after the sections loop, like the Compliance Chart box
  (DET-54)._ Rejected — the chart box is unique to the rule page, so one `@if`
  in the template is enough for it. The score box sits in the middle of seven
  layouts' box orders, and a template block cannot hold a position in a
  config-driven list; 7.25a already settled that mixed boxes ride the config.

**Consequences.** `SectionDef.kind` is the single marker a reader looks at, so
the new value needs the docstring's company (three kinds, three stores). The
box's rows arrive through `sectionViews` rather than the template, so a future
score box for another layout is a config line — and the negative half (five
layouts never gain it) is a config absence, pinned in the same spec file.

## DD-852. One derived score view, shared by box, stat, and nothing else

- **Status:** Proposed
- **Increment:** 7.25c
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** A pure helper in `sections/section-config.ts` —
`qualityRows(quality)` and `overallRow(quality)` — turns a `CardQuality[]` into
DET-56's five rows in the fixed order and DET-58's `overall` row, skipping a
row whose score is `null`, `undefined`, or negative (DET-63). The details
screen keeps one computed over them, `scoreView`, built from the view the
screen already holds; the box, the stat, and their two spec tests read it, and
nothing else derives scores again. The helpers live in `section-config.ts`
rather than a new store file because they read no state and call nothing: they
are the layout module's own mapping, like `layoutForTypeName`.

**Why.** DET-63 forbids a second read; three surfaces (box, stat, and their two
tests) must not each re-implement "drop `overall`, order five, skip garbage".
`details.component.ts` already keeps one computed per box (the compliance
chart's score, the lineage word), and a fourth fits the file's pattern.

**Considered alternatives.**

- _A `quality.state.ts` store._ Rejected — a store implies a read; there is no
  read (DET-63). DD-841 justified its store because the governance box runs a
  search and a verdict call; this increment runs neither.
- _Derive the rows server-side into a single `overallScore` field._ Rejected —
  it would amend the wire shape (AVS-01) to carry what five rows already
  answer, for a screen that needs the rows themselves (DET-56).

**Consequences.** The helpers are the single place DET-63's skip rule lives; if
the door ever answers a negative score, one function changes. The box and stat
refresh with the view's own read — no subscription, no polling (DET-63), the
same posture DET-24's counts already have.

## DD-853. The score stat is a `StatSource` kind, with the legacy's word pair

- **Status:** Proposed
- **Increment:** 7.25c
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `StatSource` grows `{ kind: "score" }`, handled in
`DetailsComponent.statCount` beside `properties`, `lineage`, and `end`: it
returns DET-58's percent for a positive-count `overall` row, else the stat's
`unavailable` word. `StatDef.unavailable` — the field LDG-32 introduced for the
lineage pair — carries it, and no new field is added to the config table. The
lineage kind keeps its own three-state rule (blank while loading) untouched.

**Why.** The stats bar is already a config list whose values are picked by a
`kind` discriminant, and DET-58's stat has the same shape as the lineage's: a
heading that shows a word rather than a count. Reusing `unavailable` keeps the
legacy's per-layout key choice (`...unavailable`, and the collection page's odd
`...dataQualityUnavailable`) in the config, where the other 60-odd layout
strings live, instead of a switch in the renderer.

**Considered alternatives.**

- _Render the score stat from the template, outside the `stats()` computed._
  Rejected — the bar is `section-stats` over a mapped list; a special case would
  reorder the bar or fork its markup, and DET-24's pin already asserts the whole
  list.
- _Show `0%` for a sourceless entity._ Rejected — DET-58 and DD-369's posture:
  the legacy gates on the count, and every other sourceless quality surface
  prints nothing (DET-63).

**Consequences.** `section-config.spec.ts` gains a stat-order pin per layout
(including the dataset's odd bar: no Subsystems/Processes headings there, and on
the system layout the score follows Collections even though the box list holds
Subsystems and Processes). `details.component.spec.ts`'s DET-24 pin moves to the
seven-new-order lists and keeps its "no zero" assertion.

## DD-854. Score sorts are a per-section option list over the cards' own rows

- **Status:** Proposed
- **Increment:** 7.25c
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `SectionDef` grows `sorts?: "name" | "score"`, default `"name"` —
DET-59's seven-option list for the ten `"score"` sections, DET-21's pair for
everything else (and DET-45's own five for the governance box, which keeps its
`GovQualityState`). `RelatedSectionsState` builds `sortOptions` per section from
the flag and its `sorted` gains a score branch: order by that dimension's row in
each card's `quality`, cards without the row last, ties by display text with
`localeCompare` and the raw name as tie-break, reversed for a descending ask.
Labels ride the `dqscore_<dimension>` keys; `Name` keeps DET-21's raw literal.

**Why.** The door can sort on `quality.<dimension>.score` (AVR-06), but the
sections store is one read of the seed GUIDs with client-side filter, sort, and
paging (DET-20..DET-22, DD-615): re-sorting server-side would re-read a box on
every sort change, break the seed-order "Relevance" (DET-21), and diverge from
every sibling box's behaviour for no gain — the cards already carry their rows
(AVS-01). The tie-break rule is the webapp's own label-sort convention (DD-493,
DD-497, DD-727), which the legacy's engine never had.

**Considered alternatives.**

- _Push the score sorts to the door._ Rejected — see above; the increment would
  grow read logic and a stale-seed race to match what the browser already holds,
  and it would contradict AUD-07's precedent only where a push was actually
  needed (a whole-index order), not a page of nine within a box.
- _Add the five dimensions as facet groups._ Rejected — DET-59 names no facet
  change and the legacy boxes offer none (the funnel's groups are
  VCF-09/VCF-10's, unchanged).

**Consequences.** `SORT_OPTIONS` becomes a function of a section rather than a
module constant, so `related-sections.state.spec.ts` pins each box's list. The
score branch is the store's second non-relevance comparator (Name is the
first), so `sorted` keeps one ordering helper both branches call — the tie rule
stays in one place.

## DD-855. The card's score list is a mount-site input, not a card prop

- **Status:** Proposed
- **Increment:** 7.25c
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `CatalogueCard` grows `showScores = input(false)` and prints
DET-60's block only when it is on and the card has rows: the block sits in
`[card-content]` after the chips and before the description, and it is the
shared `QualityDimensionList` (UIC-37) with `notAvailable` left empty (no
placeholder on a card). The details sections pass `true`; the results screen
passes nothing. `entity-card`'s `showQuality` (the quality column) keeps its
meaning — the governance mark — and is untouched (VCF-20).

**Why.** The legacy's switch is `SHOW_DATA_QUALITY`, off on the results page and
on nowhere else, and Aurelius has no injection-token idiom for cards:
`CatalogueCard` is one component mounted by two screens (results, details
sections), so a plain input expresses DET-61 exactly and keeps the card's
default conservative. The block lives in the content column, not the quality
column, because the score list is content (the legacy prints it inside the
card's media content, and the quality column holds only the mark today).

**Considered alternatives.**

- _Turn `showQuality` on and put both marks in the quality column._ Rejected —
  it would redefine a live seam (VCF-20) and stack two different quality concepts
  in a narrow column built for a triangle and its dropdown.
- _A `showQuality`-style computed on `card.quality` like `showGovQuality()`._
  Rejected — DET-61 is a rule about the screen, not about the data: a scored
  entity on the results screen must print nothing, and a data-derived switch
  would make that unachievable (DV-202).

**Consequences.** The results screen and the details screen share one card with
one visible difference, pinned in `catalogue-card.component.spec.ts` both ways.
The `quality-badge` component (UIC-39) stays unwired — DET-60 asks for the
legacy's dimension rows, not the badge's single pie; UIC-39's landing needs a
spec that wants a badge, and deleting or wiring it here would invent one.

## DD-856. The score surfaces are pinned by config spec plus one e2e scenario

- **Status:** Proposed
- **Increment:** 7.25c
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** The seven layouts' box, stat, and nav orders are pinned
structurally in `section-config.spec.ts` (the file that already pins the
governance box's position on nine layouts), the four render rules in
`details.component.spec.ts`, the sort rules in
`related-sections.state.spec.ts`, and the card rule in
`catalogue-card.component.spec.ts`. One Playwright scenario rides the sample
catalogue: open a scored dataset, read the box's rows and the bar's percent,
sort a Fields box by Completeness, read a card's score block, then the negative
(entity with no scores: placeholder plus `Unavailable`, and a results row with
no block). No unit test re-asserts the sample catalogue's numbers.

**Why.** The layout orders are data — a table check catches a misplaced box in
one line, where a render test needs a fixture per layout. The render rules are
behaviour, and DET-56/DET-58/DET-60/DET-61 are each about what appears in a
state a config table cannot express (sourceless, partial rows, screen of
mount). The e2e scenario follows the webapp's rule that e2e guards user
interactions and the real data chain (the 14.5 roll-up answering a stored
score), not computed-style pins.

**Considered alternatives.**

- _A visual (Storybook) test per layout for the box._ Rejected — the box's
  markup is UIC-37's, already story-tested in the ui library; what is per-layout
  here is the order, which is data (above).
- _Assert the score values from the sample import in e2e._ Rejected — the
  scanner's scores are data the suite does not control (12.2's job runs on a
  schedule), so the scenario asserts presence, order, and the negative state and
  leaves the numbers alone (DD-369's posture for values, DV-204).

**Consequences.** `trace.json`'s gaps stay as they are (the increment is webapp
code; the Python trace check covers the door it reads). The two retired pins —
DET-19's "no quality column" and DET-24's "no Quality stat" — are updated, not
deleted: DET-19's assertion survives about the quality _column_, and DET-24's
about a sourceless layout (the process page keeps it), so the increment closes
DD-369 without losing either guard.
