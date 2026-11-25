# 7.53 The classification chips row leaves the details header

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-880 (here). No new rule ids. Cites DET-09 (the header binds
  one chip per classification), VDR-05 and VDR-12 (the entity's own tags and the
  propagated ones, DV-197), UIC-16 (the propagated chip's hoverable source
  dropdown), DD-834 (the two legacy header rows kept as one), DD-836 (the shared
  propagated-chips control the cards mount too), and DD-879 (7.52: the stats-bar
  move this one follows).

## Scope

The entity details screen's header (7.20) still drew the classification chips row
itself: the opened entity's own tags as plain chips, and the propagated tags as
the shared propagated-chips control (VDR-05, VDR-12). This increment moves that
row into one new component, with no change to what a user sees.

The change (no behaviour, template text, or string change):

- A new `search/details/classification-chips.component.ts` holds
  `ClassificationChips`, a template component. It paints the row the header
  painted — one `ClassificationChip` per own tag, and the shared
  `PropagatedChips` control beside them — and nothing else. It injects no store,
  no router, and no HTTP client.
- The screen keeps both lists and the routing. `classifications()` and
  `propagatedClassifications()` still read the entity and filter and display-name
  the rows there, because deciding what the entity carries is the screen's, not
  the row's. The row is handed the two lists and re-emits a propagated source
  click for the screen to route (DD-836: a card mounts the same control but must
  not open itself, so the mount decides).
- The row hides itself when both lists are empty — its guard reads only its two
  inputs, no store — so the guard moves with it, unlike the layout-guarded first
  row (7.51) and the count-guarded stats bar (7.52).
- The `ClassificationChip` and `PropagatedChips` component imports move with the
  row (`PropagatedChips`' type import stays, the screen's members still build the
  entries); the cards keep mounting the shared control directly (DD-836,
  unchanged). The row has no stylesheet — Bulma and the chip carry it — so the
  child needs none.
- The spec does not split. The details screen has no shared test helper to drive
  a child against, so the row's tests (DET-09's one-chip-per-classification,
  VDR-12/DV-197's propagated tag and its routing) stay in
  `details.component.spec.ts` driving the whole screen — 7.48's shape, and the
  same call 7.50, 7.51, and 7.52 made. Nothing moves, so every pinned class, row,
  and route is unchanged.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the e2e and unit pins on the chip row and its dropdown are unchanged); the rest
of the header (the title, the type-name line, the trail, the edit affordance,
the loading line — later leaves of 7.53 and 7.54); a Storybook story (the webapp
has none, by the ui-lib-only convention); or a change to `java-map.md` and
`deviations.md` (nothing here touches Atlas behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The row renders from its inputs alone.** `ClassificationChips` touches no
  HTTP service, no router, and no store. It paints the two lists handed to it and
  re-emits a source click; the filter and display-naming stay in the screen.
- **The chips and the dropdown stay as VDR-12 and UIC-16 state.** One plain chip
  per own tag, the propagated chips from the shared control, the hoverable
  trigger naming each tag's source entities — byte-identical DOM, so DET-09's
  "one chip per classification" and DV-197's "names its sources" walk unchanged.
- **A source click still routes.** A click on a propagated source re-emits its
  guid as `sourceClicked`, and the screen routes it exactly as before (VDR-12,
  DD-836: the header opens the clicked entity; the card's own mount does not).
- **The empty guard still hides the row.** With no own tags and no propagated
  ones, the row paints nothing — DET-09's "renders no chips when the entity
  carries none" — and that decision needs only the two input lengths.
- **1,047 tests stay green** across 85 files, unchanged: no test moves, so no
  count changes; DET-09, VDR-12, and DV-197 still pass against the whole screen,
  which now paints the row through the child.
- **The string catalogue is unchanged.** The row prints no string of its own (the
  chips take labels and the dropdown text comes from the shared control), so
  both locale fixtures stay byte-equal (SHL-08).
- **The trace tool sees no change.** No test moves, so
  `uv run aurelius-atlas-trace check` reports the same single pre-existing
  finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `ClassificationChips`. The own-tag chips, the
propagated chips, and their source dropdown are already ported and specced at the
header (DET-09, VDR-12, DD-834/DD-836). Moving Aurelius code between Aurelius
files adds nothing a parity test can see, so this increment adds no row to
`java-map.md`.
