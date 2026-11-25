# 7.54 The properties accordion leaves the details screen

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-881 (here). No new rule ids. Cites DET-11 (the properties
  accordion: the entity's attributes as the legacy `sortable-table-shell`
  table-or-noData swap, VDR-04's merge and DET-10's single-prose attribute kept
  out of the rows), DET-02 (the no-entity empty shape), DET-06 (only the screen
  routes), DD-154 (a property link routes the screen), and DD-880 (7.53: the
  chips-row move this one follows).

## Scope

The entity details screen (7.20) still drew the properties accordion itself: the
expandable box with the entity's attributes as the two-column table, or the "No
data available" line when there are none (DET-11). This increment moves it into
one new component, with no change to what a user sees.

The change (no behaviour, template text, or string change):

- A new `search/details/properties.component.ts` holds `DetailsProperties`, a
  template component. It paints the accordion the screen painted — the
  `#properties-details` anchor, the `title is-3` heading, the Key/Value table
  with one `PropertiesItem` per row, and the italic no-data line — and nothing
  else. It injects no store, no router, and no HTTP client.
- The screen keeps the rows and the routing. `properties()` still reads the
  entity and runs `viewProperties` (the view's merge, the filter, the sort, the
  blacklist) there, because deciding what the entity carries is the screen's,
  not the accordion's. The accordion is handed the rows and the title and
  re-emits a property link's guid for the screen to route (DD-154, DET-06).
- The `Accordion` and `PropertiesItem` imports move with the markup: this was
  their only use on the screen. The accordion keeps its legacy anchor id
  (`#properties-details`, the side navigation's and the stats bar's scroll
  target) and starts expanded, as 7.20 left it — both ride into the child as
  template constants, not inputs.
- The spec does not split. The details screen has no shared test helper to drive
  a child against, so the accordion's tests (DET-11's rows, count, no-data line,
  and property-link routing) stay in `details.component.spec.ts` driving the
  whole screen — 7.48's shape, and the same call 7.50–7.53 made. Nothing moves,
  so every pinned class, id, row, and route is unchanged.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the e2e and unit pins on `#properties-details`, the table, and the rows are
unchanged); the rest of the header (the title, the type-name line, the trail, the
edit affordance, the loading line — later leaves); the card sections, the score
box, the Lineage Model box, or the side navigation moving out (they own their
fetches and the UIC-27 chrome); a Storybook story (the webapp has none, by the
ui-lib-only convention); or a change to `java-map.md` and `deviations.md`
(nothing here touches Atlas behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The accordion renders from its inputs alone.** `DetailsProperties` touches no
  HTTP service, no router, and no store. It paints the rows handed to it; the
  merge, filter, sort, and blacklist stay in the screen's `properties()`.
- **The table-or-noData swap stays as DET-11 states.** With rows, the Key/Value
  table with one `PropertiesItem` per value; with none, the no-data line in place
  of the whole table, headers included — byte-identical DOM, so DET-11's "no
  placeholder while rows render" and the zero-row empty shape (DET-02) hold.
- **The anchor and the expanded default stay.** `#properties-details` moves as
  template text (not an input), so DET-25's navigation and the stats bar's
  `#href`s still land on the same node, and the box opens expanded as 7.20 left
  it.
- **A property link still routes.** A click on a property's link re-emits its
  guid as `linkClicked`, and the screen routes it to that entity's details
  exactly as before (DD-154, DET-06).
- **1,047 tests stay green** across 85 files, unchanged: no test moves, so no
  count changes; DET-11, DET-02, and DET-06 still pass against the whole screen,
  which now paints the accordion through the child.
- **The string catalogue is unchanged.** The three `i18n` strings in the region
  (Key, Value, and the no-data line) carry the same ids in their new file, and
  the title prints from the layout row, so both locale fixtures stay byte-equal
  (SHL-08).
- **The trace tool sees no change.** No test moves, so
  `uv run aurelius-atlas-trace check` reports the same single pre-existing
  finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `DetailsProperties`. The accordion, its table
and no-data swap, and its property-value renderer are already ported and specced
at the details screen (DET-11, DD-154). Moving Aurelius code between Aurelius
files adds nothing a parity test can see, so this increment adds no row to
`java-map.md`.
