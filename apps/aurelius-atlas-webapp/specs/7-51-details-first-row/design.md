# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-878. The layout's first row is one presentational component; the layout guard stays in the screen

- **Status:** Proposed
- **Increment:** 7.51
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The first row the layouts draw under the header (DET-15, DET-16):
the description box and, beside it, the People box (DET-23) moves into one
component, `DetailsFirstRow`, in the details feature. It takes six signal inputs
— the description title, the description text, the People box's title, the rows,
the empty label, and whether the People box is present — and paints the row
verbatim: the `#description-details` box with its `title is-3` heading, its
markdown or its italic placeholder, and the `#people-details` box with its People
box (UIC-28). It re-emits the person click as `personClicked` and injects
nothing. The screen keeps `@if (layout()?.descriptionBox !== false)`, because
deciding that the person page has no row at all (DET-39, DD-518) reads the layout
row, and the screen already holds that layout. The `Markdown` and `PeopleBox`
imports move with the markup, which was their only use on the screen. The row
takes a one-rule stylesheet with `:host { display: block; }` so the Bulma
`.columns` keeps its margins in the page flow (the same fix 7.49 and 7.50 made),
and no rule moves out of the screen's sheet because none existed for these boxes.

**Why.** The row is the screen's next own-markup leaf after 7.50's box: 36
template lines, no store read inside them, and its two boxes share one guard and
one `.columns` row, so splitting them would invent a seam the layout does not
have. Both inputs come from values the screen already computes
(`description()`, `people()`, the layout's titles), so the contract is pure
hand-off. Keeping the guard in the screen is the same line DD-874 and DD-877
drew: `layout()` is a store read, and a painter that reads it becomes a second
reader (DET-06). Passing `peopleBox` and `peopleTitle` as plain inputs rather
than the whole layout keeps the child ignorant of layouts — it answers one yes/no
and prints two strings.

**Considered and rejected.** _Move the `descriptionBox` guard into the row_ — the
guard reads `this.layout()`, so moving it means moving the layout store access
into a painter, which DD-877 rejected for the same reason one leaf later. _Split
the description box and the People box into two components_ — the layouts place
them in one Bulma row with one guard, and the default layout renders the
description alone in the same row; two components would need a shared row wrapper
to keep the pixels, which is more structure than the region has. _A shared
details test harness so the moved tests get their own specs_ — the details spec
owns its `setup`/`arrive`/`arriveRule` helpers inline (unlike the editor's
`editor-testing.ts`), and extracting them is a test refactor, not a paint move;
the tests keep driving the whole screen, as 7.48, 7.50, and the DET-39 person
test do.

**Consequences.** `details.component.ts` drops two imports and gains one (780
lines), its template drops from 371 to 344, and its stylesheet stays at 65;
`first-row.component.ts` (83 lines with its doc and inline template) and its
11-line sheet hold the row. No test moves, so the suite stays at 1,047 across 85
files (DET-10, DET-16, DET-23, and DET-39 pass against the whole screen, which
now renders the row through the child, and the e2e pins on `#description-details`
and `#people-details` are unchanged). The one `$localize` in the region is an
`i18n` attribute with an id, not a `$localize` call, so it moves as text and both
locale fixtures stay byte-equal (SHL-08's gate untouched). No `AGENTS.md` change:
the details feature documents its own components in their file headers.
