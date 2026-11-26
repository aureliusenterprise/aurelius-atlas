# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-877. The Compliance Chart box is one presentational component; the layout guard stays in the screen

- **Status:** Proposed
- **Increment:** 7.50
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The Compliance Chart box the rule page draws between the stats bar
and its first card section (DET-54, DD-849) moves into one component,
`ComplianceChartBox`, in the details feature. It takes one signal input, `chart`
— the layout's title and two legend strings plus DET-51's score — and paints the
box verbatim: the `title is-3` heading, the two legend rows (non-compliant first
with the red swatch, compliant second with the green), and the quality pie at size
8 (UIC-36). It injects nothing. The screen keeps `complianceChart()` and its
`@if (complianceChart(); as chart)` guard, because deciding which layout has a
chart at all — reading the layout row and the verdicts store — is the screen's
job, not the box's; the box is mounted only when a chart is in hand. The five
stylesheet rules the box owned move into the new stylesheet with `:host { display:
block; }` so the box keeps its place in the page flow — plus the one margin
Bulma cannot give it there (the fix DD-885 records): the 1.5rem block spacing
the box lost when it became its host's only child — and the `DataQualityPie`
import leaves the screen for the child.

**Why.** This is the details screen's smallest own-markup leaf: eighteen template
lines, one computed input, zero event handlers, and its own SCSS — the exact
shape 7.46–7.49 set for a presentational extraction (signal input, no injection,
markup moved byte-for-byte so every pinned class, id, and the e2e's
`.aurelius-details-compliance-chart` pin stay identical). The screen's bigger
regions wait: the header carries a wide contract (title, type, chips, trail, and
four handlers — the 7.49 over-scope trap), and the stats bars need the click
handlers and the nav helpers that read the store. Starting with the box lets the
phase's shape prove out on the leaf with no contract to design. Leaving the guard
in the screen rather than passing all layouts in and letting the box check is the
same line DD-874 drew for the governance lines: the guard reads two stores
(`layout()` and the verdicts), so pushing it into the child would hand the child
store it must not read (DET-06) and turn a painter into a second reader.

**Considered and rejected.** _Extract the whole layout guard too (the `@if` and
the `computed`)_ — `complianceChart()` reads `this.layout()` and
`this.ruleVerdicts.score()`; moving it means moving the verdicts store access and
the `scorePercent`/`hasScoreSource` mapping the screen already does, which is
store-ownership relocation, not a paint move (that belongs to the header/store
work of later increments, not a paint-only PR). _A structural directive on the
box_ — a directive cannot own the box's per-kind SCSS or take `display: block`
for the flow; a component is the smaller concept. _Move the DET-50/DET-54 tests
into a new `compliance-chart.component.spec.ts`_ — the details screen has no
shared test harness (unlike the editor's `editor-testing.ts`, the screen's spec
owns its own `setup`/`arrive`/`arriveRule`), so a separate spec would either
rebuild that harness (a Phase 6-scope test extraction) or drive the child with a
fake chart (which stops pinning DET-50's box placement between the stats and the
first section). The tests stay driving the whole screen, as 7.48 did.

**Consequences.** `details.component.ts` is the same length (782 lines: it drops
the `DataQualityPie` import and gains `ComplianceChartBox`), its template drops
from 398 to 371, and its stylesheet from 98 to 65; `compliance-chart.component.ts`
(66 lines with its doc and inline template) and its 43-line stylesheet hold the
box. No test moves, so the suite stays at 1,047 across 85 files (DET-50 and DET-54
pass against the whole screen, which now renders the box through the child, and the
e2e rule-page test's pins are unchanged). No string id changes (the box prints its
text from the layout's bridge keys), so the catalogue and both locale fixtures
stay byte-equal (SHL-08's gate untouched). No `AGENTS.md` change: the details
feature documents its own components in their file headers.
