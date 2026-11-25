# 7.51 The layout's first row leaves the details screen

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-878 (here). No new rule ids. Cites DET-15 and DET-16 (7.21a:
  the layout's first row, the description box beside the People box), DET-10 and
  DD-321 (the description renders as markdown, an empty one shows the italic
  placeholder), DET-23 and UIC-28 (the People box's three labelled rows and its
  person click), DET-39 and DD-518 (the person page omits the row), HEADING-002
  (the section `h2`), and DD-877 (7.50: the Compliance Chart move this one
  follows).

## Scope

The entity details screen (7.20) still drew the layout's first row itself: the
description box and, on the layouts that carry one, the People box beside it
(DET-15, DET-16). This increment moves the row into one new component, with no
change to what a user sees.

The change (no behaviour, template text, or string change):

- A new `search/details/first-row.component.ts` holds `DetailsFirstRow`, a
  template component. It paints the row the screen painted — the
  `#description-details` box with its `title is-3` heading, its markdown or its
  italic "No description available." placeholder, and the `#people-details` box
  with its People box — and nothing else. It injects no store, no router, and no
  HTTP client.
- The screen keeps the guard. The template still says
  `@if (layout()?.descriptionBox !== false)` — deciding that the person page has
  no first row at all (DET-39, DD-518) reads the layout row, so it is the
  screen's, not the row's. The row is handed six values (both titles, the
  description, the rows, the empty label, and whether the People box is there)
  and paints them, and it re-emits the person click for the screen to route.
- The `Markdown` and `PeopleBox` imports move with the markup: the row was their
  only use on the screen.
- The spec does not split. The details screen has no shared test helper to drive
  a child against, so the row's render tests (DET-10's description, DET-16 and
  DET-23's People box, DET-39's absent row on the person page) stay in
  `details.component.spec.ts` driving the whole screen — 7.48's shape, and the
  same call 7.50 made. Nothing moves, so every pinned class, id, and anchor is
  unchanged.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the e2e pins `#description-details` and `#people-details`, both unchanged); the
rest of the screen's anatomy moving out (the stats bars and the header — later
Phase 6 increments); a Storybook story (the webapp has none, by the
ui-lib-only convention); or a change to `java-map.md` and `deviations.md`
(nothing here touches Atlas behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The row renders from its inputs alone.** `DetailsFirstRow` touches no HTTP
  service, no router, and no store. It paints what it is handed; the person page
  never mounts it, because the guard that skips it stays in the screen.
- **The description and the People box stay as DET-10 and DET-23 state.** The
  markdown element, the placeholder paragraph, the three labelled rows, and the
  `personClicked` hop are byte-identical DOM, so DET-23's "clicking a person
  routes the screen" still lands on `onCardClick` exactly as before.
- **The two boxes keep their landmarks.** `#description-details` and
  `#people-details` move as text, not as ids, so DET-16's placement and every
  side-navigation anchor to them resolve at the same node.
- **1,047 tests stay green** across 85 files, unchanged: no test moves, so no
  count changes; DET-10, DET-16, DET-23, and DET-39 still pass against the whole
  screen, which now renders the row through the child.
- **The string catalogue is unchanged.** The placeholder span carries the same
  `@@search.components.description.notAvailable` id in its new file, and the two
  titles print from the layout row, so both locale fixtures stay byte-equal
  (SHL-08).
- **The trace tool sees no change.** No test moves, so
  `uv run aurelius-atlas-trace check` reports the same single pre-existing
  finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `DetailsFirstRow`. The row, its description,
and its People box are already ported and specced at the type layouts (DET-15,
DET-16, DET-23). Moving Aurelius code between Aurelius files adds nothing a
parity test can see, so this increment adds no row to `java-map.md`.
