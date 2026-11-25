# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-881. The properties accordion is one presentational component; the merge and routing stay in the screen

- **Status:** Proposed
- **Increment:** 7.54
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The properties accordion (DET-11): the entity's attributes as the
legacy `sortable-table-shell` table-or-noData swap inside an expandable box
moves into one component, `DetailsProperties`, in the details feature. It takes
two signal inputs — the rendered `DetailProperty` rows and the box's title —
re-emits a property link's guid as `linkClicked`, and paints nothing else. It
holds its own anchor (`#properties-details`) and its own expanded default as
template constants, not inputs. The screen keeps `properties()` (which reads the
entity and runs `viewProperties`: the view's merge, the filter, the sort, the
blacklist, DET-11's rule), the title computation, and `onLinkClick` (DD-154,
DET-06). The `Accordion` and `PropertiesItem` imports ride with the markup, which
was their only use on the screen. The accordion takes no stylesheet — Bulma's
`table`, the accordion, and `PropertiesItem` carry it — so the child needs none,
like the chips row (7.53).

**Why.** The accordion is the same clean leaf 7.50–7.53 set: a painter on a
hand-built list with one re-emitted event, no custom SCSS, and no store. It is
bigger than the chips row (a table plus a no-data swap) but no wider in contract
— two inputs, one output — because the count/merge math lives entirely in
`properties()`, which the screen keeps. Leaving `properties()` and `viewProperties`
in the screen is DD-881's only judgement call, and it is the same line every leaf
here draws: DET-11's merge, filter, sort, and blacklist are the screen's reading
of the entity (VDR-04, DET-10's single-prose drop), so pushing them into the box
would hand a painter the entity and the filter rules (DET-06). The anchor and the
expanded default are template constants, not inputs, because no caller of this
box needs to change them — the side navigation and stats bar point at
`#properties-details` and 7.20 always opened it expanded; an input for a value
every mount sets the same way would be a knob nobody turns.

**Considered and rejected.** _Move `properties()`/`viewProperties` into the box_ —
that relocates DET-11's merge-and-filter of the entity into a painter, the
store-shaping DET-06 forbids, the same rejection DD-879 (stats counts) and DD-880
(chips filter) made. _Pass the accordion `expanded` as a model output_ — the box
opens expanded and the screen never reads or writes its state (no test or rule
pins a collapsed properties box), so a two-way binding adds surface for a control
nobody drives; a static `true` keeps DET-11's "renders expanded" exactly. _A
shared details test harness so the accordion gets its own spec_ — the details spec
owns its `setup` helpers inline (unlike the editor's `editor-testing.ts`); DET-11
keeps driving the whole screen, as 7.48 through 7.53 do. _Fold in the side
navigation (it also points at `#properties-details`)_ — the nav is a second
self-contained leaf (UIC-18's projection); bundling it would name the increment
for two things and grow the contract for no gain over its own leaf.

**Consequences.** `details.component.ts` drops two component imports and gains one
(777 lines), its template drops from 290 to 260, and its stylesheet stays at 65;
`properties.component.ts` (78 lines, doc plus inline template, no stylesheet)
holds the accordion. No test moves, so the suite stays at 1,047 across 85 files
(DET-11, DET-02, and DET-06 pass against the whole screen, which now paints the
accordion through the child, and the e2e and unit pins on `#properties-details`,
the table, and the rows are unchanged). The region's three `i18n` strings move as
text with their ids (Key, Value, the no-data line), so both locale fixtures stay
byte-equal (SHL-08's gate untouched). The header box (title, type-name line,
trail, edit affordance, loading line) and the card sections, score box, Lineage
Model box, and side navigation stay in the screen — the card and lineage boxes own
their fetches and UIC-27 chrome, and the header is the container DD-880 kept. No
`AGENTS.md` change: the details feature documents its own components in their file
headers.
