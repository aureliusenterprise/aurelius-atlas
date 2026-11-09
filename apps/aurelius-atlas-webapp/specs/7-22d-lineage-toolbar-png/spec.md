# 7.22d Lineage diagram: the toolbar, the PNG, and the page entries

- **Status:** proposed
- **Pull request:** —
- **Records:** LDG-27..32; DD-397..400, DD-407..409 (the reader-feedback
  round), DD-414/DD-415 (the card's place and glyph; the routed drawer — amends
  LDG-25's seam and DD-405), DD-416 (the strip pinned and marked; the drawer's
  routes leave the page's scroll alone); amends DET-32 and DET-33 again (the
  stats entries and navigation links their rows hold out, DD-383's rule — the
  stat and link return with the finished box); relies on LDG-01..26
  (7.22a/7.22b/7.22c), DD-390 (the viewer's signals), SHC-02/SHC-03 (the config
  name and version the PNG metadata reads), SHM-04 (the pinned navbar the
  fullscreen top offset reads), DD-128 (the bridge — the strings are 7.22c's
  vendored `modelview2.` keys)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

With the diagram drawn (7.22b) and the quickview reading (7.22c), two pieces of
the legacy box remain. The first is the chrome around the drawing: the header's
**Browse** button, the control column over the canvas (view info, fullscreen,
reset zoom, save view as image), and the save itself — the legacy renders the
SVG to a canvas, injects PNG `tEXt` metadata, and downloads `<view name>.png`,
entirely in the browser. The second is what 7.21c's DD-383 held out: the stats
entry ("Available"/"Unavailable", blank while fetching) and the side-navigation
link, in the legacy positions of both layouts — they come back with the finished
box, because a link to a box that is not rendered strands the reader.

Delivered here:

- the toolbar: the header's Browse button and the four controls, tooltips from
  the vendored dictionary (LDG-27)
- fullscreen: the drawing region fixed under the pinned navbar, toggled
  (LDG-28); reset zoom (LDG-29)
- save view as image: SVG → canvas → PNG with the legacy's `tEXt` metadata and
  filename, canvas-taint fallback included (LDG-30, LDG-31)
- the stats and navigation entries on both layouts, read from the hoisted
  lineage state (LDG-32)

Explicitly not delivered here:

| Not delivered                                        | Lands with | Why                                                                          |
| ---------------------------------------------------- | ---------- | ---------------------------------------------------------------------------- |
| The "save all views" ZIP and its `window` debug hook | —          | A developer console helper for multi-view repository models (DD-399)         |
| `modelview/api/convert` (server-side rasteriser)     | —          | Dead in the legacy snapshot too — cited in 7.22a's origin list; never called |
| Colour/palette affordances                           | —          | 7.22b's deferral (no buckets on this page)                                   |

## Semantics

Rules LDG-27..32, closing the band. All label keys are vendored with 7.22c's
LDG-26 (`modelview2.*` plus the `search.details.*` stat/nav keys already in the
catalogue): no new fixture content in this slice.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| LDG-27 | The diagram state of the box gains the legacy's toolbar: the header's right side carries the Browse button (`modelview2.browse`, label plus search icon) and the drawing's top-right control column (local markup, not a shared toolbar — DD-397) carries, in the legacy order, the View-info button (`modelview2.viewInfo`, opens the quickview on the View tab), the fullscreen toggle (`modelview2.toggleFullscreen`), the reset-zoom button (`modelview2.resetZoom`), and the save-view-as-image button (`modelview2.saveViewAsImage`, camera icon, `is-loading` while converting). All are icon buttons with the named tooltip (the legacy's `models4insight-tooltip` posture — `title` attribute, the webapp's idiom).                                                                                                                           |
| LDG-28 | The fullscreen toggle sets a fixed-position class on the drawing region: top at the pinned navbar's height (the `NAVBAR_SCROLL_OFFSET` pair's 68 px — the legacy's `4.25rem` measured on the same navbar), full width, `100vh`, above the page; toggling again restores it. In fullscreen the control column also carries the Browse button (the legacy's fullscreen-only copy).                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| LDG-29 | The reset-zoom button returns the d3 transform to identity (the viewer's `resetZoom()`, LDG-16). The save flow does not touch the transform: it captures the drawing at the reader's current zoom and position — the clone carries the same transform the screen shows (DD-407, in place of the legacy's zoom-around-save).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| LDG-30 | Save view as image draws the viewer's `<svg>` (cloned, fixed to the container's measured width and height — the Firefox rule the legacy carries) through `XMLSerializer` → a data-less blob URL → an `Image` → a `<canvas>`, and reads the canvas back as a PNG blob. When the canvas draw fails (the `foreignObject` labels taint the canvas on some engines), the fallback renders the container with html2canvas instead (the legacy's two-path converter). The download carries the file name `${view name}.png` via an anchor `download` (no `file-saver` dependency).                                                                                                                                                                                                                                                                            |
| LDG-31 | Before the download, the PNG bytes gain one `tEXt` chunk per metadata field (keyword NUL value, CRC32 as the legacy's table-driven util — ported as pure functions: split a PNG at its chunk boundaries, append the chunks before `IEND`, rejoin): Title = the view's name, Author = the signed-in user's email when the Keycloak session carries one, Description = the view's description, Creation Time = the current UTC time, Software = `Aurelius Atlas/${appName}/${appVersion}` from the runtime config (LDG-07's file — DD-398), Source = `Generated model` (the value the legacy's lineage page always wrote: it had no repository project/branch to name). Fields with no value are omitted (the legacy's `if (!value) continue`).                                                                                                          |
| LDG-32 | Both layouts regain their DD-383 hold-outs from the box's own state signal (hoisted per DD-400): the dataset stats bar gains Lineage Model (`search.details.dataset.lineageModel`) between Child Datasets and Producers and the side navigation gains the same link (`#lineage-model`) between Child Datasets and Producers (the legacy's positions); the process stats bar gains it between Systems and Inputs, the navigation likewise. The stat's value is the box's state: `search.details.dataset.available` / `...unavailable` (process pair on the process page), blank while the fetch is pending — never a count (the legacy's shape, DET-24 amended with it). The DET-16 table rows and DET-32/DET-33's orders now include the lineage box's stat and nav entries; the Data Quality and Data Entities hold-outs stay out unchanged (DD-369). |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
cited by path:

- `libs/modelview2/src/lib/modelview.component.html` (L1–53 header and control
  column, the `[class.is-fullscreen]` target, the `[class.is-loading]` save
  button, the fullscreen-only Browse copy) and `modelview.component.ts`
  (`openBrowser`, `openViewInfo`, `resetZoom`, `saveViewAsImage`,
  `isFullscreen`) — LDG-27/28/29/30. The save's zoom reset-and-restore is not
  ported (DD-407).
- `libs/modelview2/src/lib/modelview.component.scss` — LDG-28: the fixed
  fullscreen block (`top: 4.25rem`, `z-index`, 100vh).
- `libs/modelview2/src/lib/save-view-as-image.service.ts` — LDG-30/LDG-31: the
  two-path converter (`drawSVG2Canvas` with the fixed-dimension clone and its
  Firefox comment; `drawHTML2Canvas` with the `screenshot-container` clone
  fix-ups), the metadata composition (`Title`/`Author`/`Description`/
  `Creation Time`/`Software`/`Source`, the empty-field skip) and its `${view
name}.png` name. The service's repository fields (`branch`, `projectId`,
  version) collapse to the constants LDG-31 names (DD-398).
- `libs/modelview2/src/lib/utils/png-metadata.ts` — the chunk split/create/
  join/CRC32 utils, ported as pure functions (LDG-31).
- `dataset/dataset-details.component.html` — LDG-32: the stats `level-item`
  (available/unavailable under the `#lineage-model` nav item, the spinner
  template while loading) and the navigation entry between Child Datasets and
  Producers; `process-details.component.html` — the same pair between Systems
  and Inputs.
- `modelview.component.ts` (`saveAllViewsAsImages`, the `window[...]` hook, the
  JSZip batch) — not ported (DD-399).
- `libs/repository/src/lib/modelview-convert/**` — not ported (dead; 7.22a's
  origin list carries the citation).

## Deviations

None against Apache Atlas (no server surface; the save is browser-only).
Against the Aurelius product:

- the metadata's `Software` reads the runtime config instead of the legacy's
  `git-version.json` build artifact, and `Author` reads the Keycloak session
  instead of the legacy `AuthenticationService` store (DD-398; DV-141's
  keycloak-angular swap covers the token, and the email is an id-token claim —
  absent means the field is omitted, as the legacy skipped empty fields).
- the save-all-views ZIP console hook stays out (DD-399).
- the download rides an anchor `download` attribute instead of `file-saver`
  (one dependency kept out; WBP-02's lean-deps posture).
- the save keeps the reader's zoom instead of the legacy's reset-and-restore
  (DD-407): the legacy's jump-back visibly flickered the view and its
  capture-and-restore raced other zoom events.
- the diagram's text inherits the app's brand font instead of the legacy's
  hard-coded `"Segoe UI"` stack (DD-408).
- each connection gains a 10 px transparent hit path under the visible edge
  (DD-409): the legacy's 1 px stroke is nearly unhittable — a flaw the legacy
  itself carries (its click handler sits on the thin path).

## Acceptance

- Vitest (unit):
    - `png-metadata.spec.ts` — CRC32 against a known vector, a chunk split/
      append/join roundtrip on a minimal PNG byte string, the empty-field skip
      (LDG-31).
    - `save-view-as-image.spec.ts` — with a stubbed canvas/URL layer: the
      serialize→draw→PNG path, the fallback taken when the first path throws,
      the `${view name}.png` name, and the save leaving the d3 transform alone
      at any zoom (LDG-29, LDG-30, DD-407).
    - `lineage-viewer.component.spec.ts` — amended: the toolbar renders only in
      the diagram state with the five named tooltips; the fullscreen class
      toggles; View-info opens the drawer on the View tab (LDG-27, LDG-28).
    - `section-config.spec.ts` — amended: both rows' stats and nav orders
      include the lineage entries in the named positions; the stat source kind
      is `lineage` (LDG-32).
- Playwright (e2e, authenticated, chromium + firefox + webkit): on the seeded
  lineage (7.22b's graph): the stats bar reads Lineage Model → "Available"
  (casefolded, the uppercase transform) in the named position and the side nav
  lists the link (LDG-32); the unconnected process reads "Unavailable"; the
  save button downloads `Lineage.png` (Playwright's download assertion) and the
  saved bytes carry a `tEXt` chunk with `Title\0Lineage` (LDG-30/31 read back
  from the download); the fullscreen toggle adds and removes the class (LDG-28).
- Gates: `nx test aurelius-atlas-webapp -c ci`, `nx lint`, the purity script
  (WBP-02), `nx e2e aurelius-atlas-webapp`.
