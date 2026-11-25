# 7.50 The Compliance Chart box leaves the details screen

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-877 (here). No new rule ids. Cites DET-54 (7.25b as refined by
  7.25c: the rule page's Compliance Chart box), DET-51 (the rule's score), DD-849
  (the box's place between the stats bar and its first card box), UIC-36 (the
  quality pie at size 8), and DD-875 (7.49: the editor field-controls move this
  one follows).

## Scope

The entity details screen (7.20) still held one box of its own markup that is not
the page's anatomy: the Compliance Chart box the rule page draws between the
stats bar and its first card section (DET-54, DD-849). This increment moves it
into one new component, with no change to what a user sees.

The change (no behaviour, template text, or string change):

- A new `search/details/compliance-chart.component.ts` holds `ComplianceChartBox`,
  a template component. It paints the box the screen painted — the `title is-3`
  heading, the two legend rows (non-compliant first with its red swatch,
  compliant second with the green), and the quality pie at size 8 — and nothing
  else. It injects no store, no router, and no HTTP client.
- The screen keeps the guard. `complianceChart()` still reads the layout row and
  the verdicts store and returns the chart or `null`, and the template still says
  `@if (complianceChart(); as chart)` — deciding which layout has a chart at all
  is the screen's, not the box's. The box is handed the chart (the layout strings
  and DET-51's score) as one input and paints it.
- The box's five stylesheet rules move with it into the new stylesheet — an
  emulated-encapsulation parent cannot style a child's inner markup — and the box
  takes `display: block` so it keeps its place in the page flow (the same fix
  7.49 made for the field controls).
- The spec does not split. The details screen has no shared test helper to drive
  a child against, so the chart's render tests (DET-50's box placement, DET-54's
  pie and legend) stay in `details.component.spec.ts` driving the whole screen —
  exactly 7.48's shape, where the banner tests moved but kept driving the drawer.
  Nothing moves, so every pinned class, id, and landmark is unchanged.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the e2e rule-page test pins `.aurelius-details-compliance-chart` and the pie
element, both unchanged); the rest of the screen's anatomy moving out (the header,
the first row, the stats bars — later Phase 6 increments); a Storybook story (the
webapp has none, by the ui-lib-only convention); or a change to `java-map.md` and
`deviations.md` (nothing here touches Atlas behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The box renders from its input alone.** `ComplianceChartBox` touches no HTTP
  service, no router, and no store. It paints the chart handed to it and says
  nothing else; no chart, no box — but that guard is the screen's, so the box is
  only ever mounted with a chart in hand.
- **The pie and the legend stay as DET-54 states.** Size 8, the score DET-51's
  (`value` = the percentage), non-compliant first with the red swatch, compliant
  second with the green — byte-identical DOM, so DET-50's "chart sits between the
  stats bar and the Non-compliant box" still holds on the same `.box` walk.
- **1,047 tests stay green** across 85 files, unchanged: no test moves, so no
  count changes; DET-50 and DET-54 still pass against the whole screen, which now
  renders the box through the child.
- **The string catalogue is unchanged.** The box prints its title and legend from
  the layout row (the `search.details.govQuality.*` bridge keys), no `$localize`
  of its own moves, so both locale fixtures stay byte-equal (SHL-08).
- **The trace tool sees no change.** No test moves, so
  `uv run aurelius-atlas-trace check` reports the same single pre-existing
  finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `ComplianceChartBox`. The box and its score are
already ported and specced at the rule page (DET-54, DD-849). Moving Aurelius code
between Aurelius files adds nothing a parity test can see, so this increment adds
no row to `java-map.md`.
