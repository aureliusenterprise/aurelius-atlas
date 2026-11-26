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
takes a stylesheet with `:host { display: block; }` so it sits in the page flow,
plus the one margin Bulma cannot give it there (the fix DD-885 records): the
1.5rem block spacing the bar lost when it became its host's only child.

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
18-line sheet hold the bar. No test moves, so the suite stays at 1,047 across 85
files (DET-24, DET-25, DET-40, DET-52, and DET-58 pass against the whole screen,
which now paints the bar through the child, and the e2e pins on the bar's boxes
and counts are unchanged). The one `$localize`-free i18n string in the region
(`@@search.details.default.properties`) moves as text with its id, so both locale
fixtures stay byte-equal (SHL-08's gate untouched). No `AGENTS.md` change: the
details feature documents its own components in their file headers.

## DD-885. The moved boxes keep the block spacing on their own host

- **Status:** Proposed
- **Increment:** 7.52 (a fix, 2026-11-26)
- **Date:** 2026-11-26
- **Supersedes:** –

**Decision.** The three details parts that paint a top-level box — 7.51's first
row, 7.52's stats bar, and 7.50's Compliance Chart box — each give their `:host`
the Bulma block rhythm (`margin-bottom: var(--bulma-block-spacing)`) next to the
`display: block` they already carried. The screen's own boxes are unchanged.

**Reason.** Bulma's vertical rhythm for a box comes from `.box:not(:last-child)`
and, for a `.columns` row, from `.columns:not(:last-child)` (bulma.css:3129,
9640). While the markup sat in `details.component.html`, every box had a sibling
after it, so the rules matched and each gap measured 24px. A part host holds
exactly one top-level box, so inside the host that box _is_ the last child, the
rule stopped matching, and the box dropped to `margin-bottom: 0`. The row and the
grouped bar then pulled further apart from their target: the `.columns` carries
`margin-bottom: -12px`, which the column's 12px padding used to cancel once the
rhythm returned, so the visible gap went 24px → 0px on both sides of the stats
bar (`#description-details` → bar → `.aurelius-details-section`, measured on the
running stack). The shipped stylesheets claimed "Bulma carries … its Bulma
margins", which is what let the regression through: no test reads a computed
margin, and the DOM stayed byte-identical, so every structural pin stayed green
while the page lost its rhythm. This entry corrects that claim in DD-877, DD-878,
and DD-879 rather than superseding them — the extractions stand, only their
one-line note about the sheet was wrong (all three are still Proposed).

**Alternatives.** _Put the parts back in the screen_ — undoes DD-877–DD-879 to
fix a margin. _A `margin-top` on the following box_ — each box would need to
know which box precedes it, and the guard-wrapped ones (`@if (complianceChart())`)
come and go, so the rule could not be static. _A wrapper with a `gap` around the
screen's flow_ — changes every sibling pair at once, including the chips row and
the Properties accordion whose spacing never moved (the row keeps its 12px from
Bulma's `.field` rule and the accordion was already the last flow child before
the split, so it never lost a margin). _Restoring the rhythm from the screen's
sheet with `::ng-deep` or a global rule_ — an emulated-encapsulation parent
cannot style a child's markup, which is the reason DD-877 gave for moving the
five rules at all.

**Consequences.** The three sheets grow by one rule each and their comments now
say what the rule is for. The `--bulma-block-spacing` token is global, so the
rule tracks the theme's block spacing instead of a hard-coded 1.5rem. No test
moves: the parts have no computed-style pin today (Storybook covers
`aurelius-atlas-ui` only, and AGENTS.md keeps computed-style pins out of e2e), so
this class of regression stays untested by tooling and is caught by eye or by the
screenshot pass in `docs/contributor-guide/user-documentation-plan.md`. If the
details screen gains visual coverage, the pin belongs there — measure the gap
between `#description-details`, the stats bar's `.box`, and
`.aurelius-details-section` at 24px, and the same across the grouped bar (the
person layout) and the chart box (the rule layout), where the sample data holds
no Person or Rule entity to check by eye.
