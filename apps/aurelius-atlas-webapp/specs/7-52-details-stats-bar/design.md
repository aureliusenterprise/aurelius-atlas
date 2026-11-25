# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-879. Both stats bars move as one component; the count math stays in the screen

- **Status:** Proposed
- **Increment:** 7.52
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The stats bar under the first row moves into one component,
`DetailsStatsBar`, in the details feature. It holds both bars the screen drew:
the grouped boxes of the layouts that group their bar (DET-40, DD-518 — the
person page's four headed boxes) and the flat bar every other layout keeps
(DET-24), including the default layout's single Properties level while no layout
is in hand. It takes five signal inputs — the grouped boxes, the flat stats, the
default Properties title, the property count, and a `hasLayout` boolean — and
re-emits the clicked heading's anchor as `statClicked`. It injects nothing. The
screen keeps `stats()`, `statsGroups()`, and `statCount()`, because those read
`layout()`, the properties, the lineage, the sections, and the score to fill the
live counts, and pushing them into the bar would hand a painter five stores (DET-
06). The bar answers one exclusive-or with its two inputs and paints; the screen
routes the anchor. The `SectionStats` import rides with the flat bar. The bar
takes a one-rule stylesheet with `:host { display: block; }` so it keeps its
place in the page flow, and no rule moves out of the screen's sheet because none
existed for these boxes.

**Why.** The two bars are one region the screen already made mutually exclusive
with `statsGroups().length` — a layout answers groups or flat, never both. One
component keeps that invariant in the place the screen drew it; two components
would need the screen to re-test the same length to pick one, which moves the
decision without moving any paint. The counts are the line DD-874, DD-877, and
DD-878 all drew: `statCount` is the one member on the screen that fans out to the
most stores (properties, lineage, sections, score), so it is the clearest
store-ownership boundary, not a paint move. `hasLayout` passes the `@if (layout())`
nullability check as data because it only guards DET-24's fallback against a
not-yet-loaded layout — the bar never branches on a store, only on a value the
screen already read. Passing the group list and the flat list together (rather
than one discriminated union) keeps the markup byte-identical to the screen's two
`@if` blocks, which is what the DET-56/DET-58 placement walk pins.

**Considered and rejected.** _Two components, `StatsGroupsBar` and `StatsBar`_ —
the screen would test `statsGroups().length > 0` to choose, so the invariant
moves nowhere while a shared wrapper or a third condition appears for the
`@else` fallback; one component is fewer moving parts for the region's real shape.
_Move `statCount` and its store reads into the bar_ — `statCount` fans to
`properties()`, `lineageWord()`, `scoreWord()`, and `sections.countFor()`; that
relocates store ownership into a painter, which DD-877 rejected and the DET-06
rule forbids. _A `hasLayout` structural directive in the screen instead of an
input_ — the flag is one boolean the screen already has, and a directive adds a
contribution to the module for a single `@if`; the input is the smaller concept.
_A shared details test harness so the bar gets its own spec_ — the details spec
owns its `setup`/`arrive` helpers inline (unlike the editor's
`editor-testing.ts`), and extracting them is a test refactor, not a paint move;
DET-24, DET-25, DET-40, and DET-52 keep driving the whole screen, as 7.48, 7.50,
and 7.51 do.

**Consequences.** `details.component.ts` drops one import and gains one (780
lines), its template drops from 344 to 300, and its stylesheet stays at 65;
`stats-bar.component.ts` (102 lines with its doc and inline template) and its
11-line sheet hold the bar. No test moves, so the suite stays at 1,047 across 85
files (DET-24, DET-25, DET-40, DET-52, and DET-58 pass against the whole screen,
which now paints the bar through the child, and the e2e pins on the bar's boxes
and counts are unchanged). The one `$localize`-free i18n string in the region
(`@@search.details.default.properties`) moves as text with its id, so both locale
fixtures stay byte-equal (SHL-08's gate untouched). No `AGENTS.md` change: the
details feature documents its own components in their file headers.
