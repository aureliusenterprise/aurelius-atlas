# Design decisions: 7.22g — Model viewer: colour views and the drawer's colour legend

> **Purpose:** the `DD-NNN` entries of this increment, written before the code and
> updated while it changes. Read-only history: every entry ever made also lives in
> [`docs/architecture/conversion/design-log.md`](../../../../docs/architecture/conversion/design-log.md),
> which is the archive (an entry lives in exactly these two places, and the archive
> is never edited — DD-001). New entries are numbered consecutively across the
> repository: check the archive's topmost number and the sibling `specs/*/design.md`
> files for the largest `DD-NNN` in use before taking the next.

| Id      | Title                                                           |
| ------- | --------------------------------------------------------------- |
| DD-420. | The colour view is plain data, a pure join, and a native picker |

## Decisions

### DD-420. The colour view is plain data, a pure join, and a native picker

- **Status:** Proposed
- **Increment:** 7.22g
- **Date:** 2026-11-08

**Decision.** The legacy `ColorViewService` mechanism arrives as plain data
(UIC-30/UIC-31). The lib module `category-colors.ts` holds the twelve-colour
literal palette (`CATEGORY_PALETTE`), the `deriveCategoryLegend(categories,
overrides)` join, and the `categoryColor(legend, categories, viewId,
conceptId)` lookup — the legacy's `(bucketMapping, palette) → legend →
colorMapping` chain run as one pure function. The `ModelViewer` canvas gains
two dumb inputs, `categories` and `categoryColors`, both null by default, and
applies the legacy's precedence itself: a node's fill and a connection's
stroke take the category's legend colour over the class rule, and the lookup
answers the element's view id first and its concept second, as the legacy's
node and connection services did. The webapp's `LineageModelState` owns the
two signals and the `setCategoryColor` seam; the viewer shell passes the maps
to the canvas; the View tab renders the Color legend table from the same
join and emits the picker's `{category, color}` (the legacy's
`updateLegendColor`), which the drawer writes to the state. The picker is a
native `<input type="color">` styled as the legacy square.

**Reason.** The lib's rule keeps the canvas dumb (UIC-29/DD-419): a
component-scoped store like the legacy's is impossible there, and would be
wrong even if it were — the canvas and the drawer are different trees that
must agree on one legend, which is why the legacy had to hoist the join into
a store. Plain inputs plus an exported pure function give the same single
truth with nothing to inject. The null default is parity: on every page but
model-compare the legacy's `bucketMapping` was never fed, so null means
"today's drawing, unchanged", and the existing suites stay the pin for that.
The native colour input replaces `ngx-color-picker@12` (a 2021-era Angular
12 dependency in an Angular 22 app) for the same job — pick a hex — with no
dependency; the legacy's own square is a flat colour box, which CSS does to
the native input directly. Session-only picks are the parity answer: the
legacy's lived in a component store and vanished with it.

**Alternatives.** (1) Port `ColorViewService` as an injectable in the webapp
and pass the resolved `colorMapping` to the canvas. It loses. The canvas must
still join per element (view id, then concept), so the join must ship in the
lib anyway; a store on top duplicates it and re-creates the legacy's known
fragility, where a `bucketMapping` change regenerated the legend and wiped
the reader's picks. (2) Keep the `google-palette` dependency. It loses. Its
other three palettes serve the select, which no live legacy consumer used
(both fed a fixed legend or the qualitative default), and twelve fixed
colours cover any category count this page will see; a wrap beats a
generating dependency. (3) Parse the inline `ar3_style` fills as the third
precedence level. It loses for now. The shipped producer emits no style block
(DD-389's standing reason), so the level has no producer to test it against;
the class-fill fallback already covers its null answer. (4) A shared
`ColorLegend` component in the lib. It loses. The table needs the app's
`SortableTable` (already the lib's), but its rows, labels, and wiring are
drawer-specific; a second component would re-state the View tab's fields for
one call site.

**Consequences.** The canvas's DOM keeps its shape: the fills are inline
`[style.fill]`/`[style.stroke]` bindings over the class rules, so every
existing pin (the style block, the state strokes, the e2e DOM) holds. The
drawer's View tab grows one guarded table; with no producer on the page the
tab reads exactly as 7.22c shipped it, which its spec pins. The
`categories`/`categoryColors` pair is the host seam a future heatmap or
violation report writes, exactly where the legacy's three `@Input`s stood.
Picks for a category a later document lacks are inert (the legend simply has
no such row), so the override map never needs cleaning.
