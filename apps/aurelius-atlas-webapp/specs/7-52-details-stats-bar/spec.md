# 7.52 The stats bar leaves the details screen

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-879 (here). No new rule ids. Cites DET-24 (the flat stats bar
  of the layout's `section-stats` with live counts), DET-25 (a heading link
  routes its anchor as the fragment), DET-40 and DD-518/DD-519 (the grouped
  stats bar of the person page's four headed boxes), DET-52 (the verdict and
  property counts in the bar), DET-58 (the score stat's word), DD-381 and DV-156
  (the heading click scrolls, no section filter), DD-369 (a sourceless stat is
  left out), and DD-878 (7.51: the first-row move this one follows).

## Scope

The entity details screen (7.20) still drew the stats bar itself: the grouped
boxes on the layouts that group (DET-40, DD-518) and the flat bar on every other
(DET-24). This increment moves both into one new component, with no change to
what a user sees.

The change (no behaviour, template text, or string change):

- A new `search/details/stats-bar.component.ts` holds `DetailsStatsBar`, a
  template component. It paints whichever bar it is handed — the grouped boxes
  (each a heading over its one or two level-item links) or the flat bar (the
  layout's `section-stats`, or the default layout's single Properties level
  while no layout is in hand) — and nothing else. It injects no store, no
  router, and no HTTP client.
- The screen keeps the count work. `stats()`, `statsGroups()`, and `statCount()`
  still read the layout, the properties, the lineage, the sections, and the
  score, because filling the live counts is the screen's, not the bar's. The
  bar is handed both lists, the default Properties title and count, and whether
  a layout is in hand, and paints them; it re-emits the clicked heading's anchor
  for the screen to route (DET-25).
- The `SectionStats` import moves with the flat bar (the row was its only use on
  the screen); `RouterLink` stays, because the side navigation still uses it.
- The spec does not split. The details screen has no shared test helper to drive
  a child against, so the bar's render tests (DET-24's flat bar, DET-40's
  grouped boxes, DET-25's anchor routing, DET-52's counts) stay in
  `details.component.spec.ts` driving the whole screen — 7.48's shape, and the
  same call 7.50 and 7.51 made. Nothing moves, so every pinned class, id, and
  count is unchanged.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the e2e pins the stats bar's boxes and counts, both unchanged); the header
moving out (the last own-markup region — 7.53, a later Phase 6 increment); a
Storybook story (the webapp has none, by the ui-lib-only convention); or a
change to `java-map.md` and `deviations.md` (nothing here touches Atlas
behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The bar renders from its inputs alone.** `DetailsStatsBar` touches no HTTP
  service, no router, and no store. It paints the lists handed to it; the count
  math (`statCount`) stays in the screen, which reads the stores.
- **The two bars stay mutually exclusive, as the screen left them.** A non-empty
  `statsGroups` list paints the grouped boxes and nothing else; an empty one
  paints the flat bar. DET-40's grouped bar and DET-24's flat bar never both
  render, so DET-56/DET-58's "stats bar keeps its place" walk is unchanged.
- **The heading links still route.** A flat-bar or grouped-bar heading click
  re-emits its anchor as `statClicked`, and the screen routes it as the URL
  fragment exactly as before (DET-25, DD-381, DV-156: scroll only, no section
  filter).
- **The default layout's Properties level stays.** With no layout in hand
  (`hasLayout` false, DET-24's fallback), the bar paints the single Properties
  level with the same `@@search.details.default.properties` label and the same
  `.aurelius-details-property-count`, so DET-24's default bar is unchanged.
- **1,047 tests stay green** across 85 files, unchanged: no test moves, so no
  count changes; DET-24, DET-25, DET-40, DET-52, and DET-58 still pass against
  the whole screen, which now paints the bar through the child.
- **The string catalogue is unchanged.** The Properties label carries the same
  `i18n` id in its new file, and every other string prints from the layout row,
  so both locale fixtures stay byte-equal (SHL-08).
- **The trace tool sees no change.** No test moves, so
  `uv run aurelius-atlas-trace check` reports the same single pre-existing
  finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `DetailsStatsBar`. The flat and grouped bars,
their counts, and their heading anchors are already ported and specced at the
type layouts (DET-24, DET-40). Moving Aurelius code between Aurelius files adds
nothing a parity test can see, so this increment adds no row to `java-map.md`.
