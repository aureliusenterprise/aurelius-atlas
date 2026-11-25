# 7.55 The side navigation leaves the details screen

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-882 (here). No new rule ids. Cites DET-25 (the side
  navigation: the opened layout's anchors, in legacy order, as the rendered box
  set), DET-02 (the no-entity empty shape — with no layout named, the default's
  one `#properties-details` entry), DET-06 (only the screen touches the router),
  DD-191 and DD-381 (the shell's scroll behaviour is app-side; a nav item is a
  `routerLink` over the current route with the anchor as its fragment), and
  DD-881 (7.54: the properties move this one follows).

## Scope

The entity details screen (7.20) still drew the side navigation itself: the
sticky circular drop-up at the foot of the screen with the opened layout's
anchors as its menu items (DET-25, UIC-18). This increment moves it into one new
component, with no change to what a user sees.

The change (no behaviour, template text, or string change):

- A new `search/details/side-nav.component.ts` holds `DetailsSideNav`, a
  template component. It mounts the 7.16 shell and projects the menu list the
  screen projected — the `ul.menu-list` container, one `routerLink` item per
  layout entry, and the default layout's single `Properties` entry when no
  layout is named — and nothing else. It injects no store, no router, and no
  HTTP client.
- The screen keeps the layout read. `layout()` still resolves the type's row
  there, because deciding which layout a type takes is the screen's, not the
  navigation's. The part is handed the layout's own entry set and one boolean
  saying whether a layout was named at all — that boolean is what picks the
  layout's set over the default's single entry, and it is the same read the
  screen already makes for the card sections and the stats bar (DET-06).
- The `DetailsNavigation` and `RouterLink` imports move with the markup: this
  was their only use on the screen. The part also owns the shell's menu label
  (`@@search.details.components.navigation.details`, the legacy 'Details') and
  the `.aurelius-details-nav` class, both used nowhere else — the class is the
  hook the unit tests and the e2e select the menu through, and it lands on the
  same element as before.
- The spec does not split. The details screen has no shared test helper to drive
  a child against, so the navigation's tests (DET-25's item set and order, the
  fragment hrefs, and the click routing) stay in `details.component.spec.ts`
  driving the whole screen — 7.48's shape, and the same call 7.50–7.54 made.
  Nothing moves, so every pinned item, href, and route is unchanged.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the e2e and unit pins on `.aurelius-details-nav .menu-list a`, the
`.menu-label` text, and the fragment hrefs are unchanged); the Data Quality
score box, the card sections, or the Lineage Model box moving out (they ride the
layout's section loop and own their fetches); the rest of the header (the title,
the type-name line, the trail, the edit affordance, the loading line — later
leaves); a Storybook story (the webapp has none, by the ui-lib-only convention);
or a change to `java-map.md` and `deviations.md` (nothing here touches Atlas
behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The navigation renders from its inputs alone.** `DetailsSideNav` touches no
  HTTP service, no router service, and no store. It paints the entries handed to
  it; the layout row lookup stays in the screen's `layout()`.
- **The rendered DOM is byte-identical.** The part mounts the shell with the
  same class and label and projects the same `ul.menu-list`, so DET-25's item
  set, the legacy order, and DD-381's `routerLink` fragment hrefs come out of
  the same selectors as before — the extra wrapper element is unsized and
  unstyled, and the shell's sticky positioning lives on a div inside the ui
  component, not on the mounted element.
- **The default shape stays DET-02's.** With no layout named, the menu holds its
  one `Properties` entry pointing at `#properties-details`, exactly as the
  no-entity state left it; with a layout, the menu holds that layout's set.
- **Scrolling stays app-side.** Each item is a `routerLink` over the current
  route with the anchor as its fragment (DD-381), and the screen's own scroll
  effect does the scrolling (DD-191) — the part adds no scroll code and owns no
  router.
- **1,047 tests stay green** across 85 files, unchanged: no test moves, so no
  count changes; DET-25, DET-02, and DET-06 still pass against the whole screen,
  which now paints the navigation through the child.
- **The string catalogue is unchanged.** The one `i18n` string in the region
  (the menu label) and the one inside the loop (the default entry) carry the
  same ids in their new file, so both locale fixtures stay byte-equal (SHL-08).
- **The trace tool sees no change.** No test moves, so
  `uv run aurelius-atlas-trace check` reports the same single pre-existing
  finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `DetailsSideNav`. The sticky navigation shell
is already ported and specced in the ui library (UIC-18, 7.16) and its items at
the details screen (DET-25, DD-381). Moving Aurelius code between Aurelius files
adds nothing a parity test can see, so this increment adds no row to
`java-map.md`.
