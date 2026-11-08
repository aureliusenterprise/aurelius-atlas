# 7.22g Model viewer: colour views and the drawer's colour legend

- **Status:** proposed
- **Pull request:** —
- **Records:** UIC-30, UIC-31; DD-420. Amends nothing: UIC-29's canvas keeps
  its words and gains two inputs, and the colour-by deferral rows of 7.22b
  and 7.22c are rewritten by this slice (their tables' only rows that change
  — see Deviations). Relies on UIC-29 and DD-419 (7.22f, the shared canvas),
  LDG-24 and DD-393 (7.22c, the View tab and the routed drawer), DD-415 (the
  shared state), DD-128 (the dictionary bridge), and the library's
  dumb-component rule (`libs/angular/AGENTS.md`).

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The legacy's modelview2 carried a colour view: the host passed a
`bucketMapping` (concept → category) and every element in a category drew
with its legend colour instead of its class fill, while the drawer's View tab
listed the categories in a "Color legend" table whose colour squares the
reader could re-pick. The platform's model-compare and consistency-metrics
apps fed it (the compare legend, a violation report's colour column — that
is where the "heatmap" colours came from). On the Atlas details page the
input was never fed (7.22b's deferral row), and 7.22b/7.22c deferred the
whole mechanism with it.

The reviewer asked for the functionality here. Two facts from the legacy
shape this slice:

1. the ar3 document carries no categories — only per-element inline fills,
   which the shipped producer never writes (DD-389) — so the categories were
   always a runtime input from the host, never parsed data, and
2. the mechanism was three reactive stores (`bucketMapping`, the palette, the
   `legend` join) that the canvas and the drawer both read, with the drawer's
   picker writing the legend.

Delivered here:

- Two dumb inputs on the `ModelViewer` canvas (UIC-30): `categories`
  (concept → category, the legacy's `bucketMapping`) and `categoryColors`
  (category → hex, the legend edits). Each element draws its category's
  legend colour instead of its class fill, exactly the legacy's precedence
  chain, lookup keys included.
- The legend join as one pure function (`deriveCategoryLegend`) and the
  palette as a literal (UIC-30, DD-420).
- The drawer's View tab gains the Color legend table (UIC-31, the legacy's
  `legendTableConfig`): one row per category, each colour a picker, rendered
  only when a colour view exists. A pick repaints the category on the canvas
  through the shared state (the legacy's `updateLegendColor`).
- The two signals and the pick seam on `LineageModelState` (the app's single
  owner, DD-415), and the shell's pass-through to the canvas.
- The stories: a bucketed chain with palette colours, one with a picked
  override, and a playground whose legend rows hold native colour pickers —
  the same input the View tab ships — so a reviewer repaints a category and
  watches the canvas.

Explicitly not delivered here:

| Not delivered                                                 | Lands with | Why                                                                                                                                                    |
| ------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A category producer on the details page                       | —          | The legacy had none either — the details page never fed `bucketMapping` (7.22b's row, corrected by this slice). The inputs are host-supplied, as there |
| The palette select (Diverging/Qualitative/Rainbow/Sequential) | —          | One palette is what every live legacy consumer used (`qualitative`, DD-420); the select only mattered to model-compare                                 |
| The fixed `compare` legend and `isPalletteFixed`              | —          | They belong to the platform's model-compare app, which this repo does not host                                                                         |
| The inline `ar3_style` fill/line colours                      | —          | The shipped producer emits no style block (DD-389's standing reason); the canvas keeps its class fills as the fallback                                 |
| Picked-colour persistence                                     | —          | The legacy's picks lived in a component store and died with it; session-only is the parity answer (DD-420)                                             |

## Semantics

Two new rules.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UIC-30 | The `ModelViewer` canvas takes two more dumb inputs (DD-420): `categories` (concept id → category name, the legacy's `bucketMapping`) and `categoryColors` (category name → hex, the legend edits), both null by default — with no `categories` the drawing is unchanged, which is the state every legacy page except model-compare lived in. A `deriveCategoryLegend(categories, categoryColors)` join answers each distinct category, in first-seen order, with its picked colour or the next colour of the twelve-colour literal palette (the `google-palette` deviation, DD-420). A node fills its category's legend colour instead of its class fill, and a connection strokes it instead of black — the legacy's `colorMapping ?? class` precedence, and its view-id-first, concept-second lookup chain on both (`modelview-node.service.ts`, `modelview-connection.service.ts`). The markers and dashes (LDG-36) and the state strokes (LDG-17/LDG-18) are untouched. The join is exported so the drawer renders the same legend the canvas paints with. |
| UIC-31 | The View tab (LDG-24, widened) shows the legacy's Color legend table — the `modelview2.modelBrowser.view.colorLegend` label over a Category/Color table, one row per legend entry — only when a colour view exists (the legacy rendered it under its `legend$` guard). Each row's colour is a picker (the legacy's `ColorSquareComponent`, ported as a native colour input — DD-420's zero-dependency deviation); picking emits `{category, color}` (the legacy's `updateLegendColor`). The app wires it: `LineageModelState` owns the `categories` (null until a host supplies them, the legacy's host-fed posture) and the picked `categoryColors`, the drawer writes the pick, the viewer shell passes both maps to the canvas, and every element in the category repaints while the panel stays open. The picks are session-only.                                                                                                                                                                                                                           |

## Aurelius origin

`libs/modelview2/src/lib/color-view.service.ts` (the three stores and the
two reactive joins), `shapes/node/modelview-node.service.ts` and
`shapes/connection/modelview-connection.service.ts` (the
`colorMapping ?? inline ?? class` precedence and the view-id/concept lookup
chain), `model-browser/view/view.component.{ts,html}` (the legend table, its
config, and `updateLegendColor`), `libs/components/src/lib/color-square/`
(the picker), and the `colorLegend` dictionary leaf. The stores collapse into
two plain signals and one pure function (DD-420); the node/connection
precedence and lookup chain are kept as written; the picker is the native
input. The legacy's dead parts are not ported because they were dead: the
selection tab's `selectedEntityColor$` and its `updateLegendColor` copy,
`getBucketById`, the `isCreating*` flags, and the picker's
`enableColorPicker`/`position` inputs had no live call sites.

## Deviations

None against Apache Atlas (no server surface changes). Against the legacy
renderer, each deliberate:

- The palette is a literal twelve-colour list, not the `google-palette`
  package (DD-420). Every live legacy consumer used the qualitative palette;
  the list is that family's classic twelve. A thirteenth category wraps to
  the first colour — the legacy generated more.
- The picker is a native `<input type="color">` styled as the legacy square,
  not `ngx-color-picker` (DD-420). Same job (pick a hex), zero dependency;
  the browser's own picker replaces the vendored popup.
- The three reactive stores become two signals plus `deriveCategoryLegend`
  (DD-420). The canvas stays dumb (UIC-29's rule): the caller owns the data,
  the join runs wherever it is read. The legacy's known pick-wiping fragility
  (its legend regeneration dropped picks when the mapping re-arrived) cannot
  happen: overrides are state of their own and win over the palette.
- The palette select, the fixed `compare` legend, the inline `ar3_style`
  fills, and any details-page category producer stay out — the four
  not-delivered rows above, each with its reason.
- 7.22b's and 7.22c's deferral tables said "no details-page input feeds it";
  this slice delivers the mechanism and rewrites those two rows to point
  here. The sentence stays true of today's page (no producer ships): the
  correction is that the mechanism now exists for a host that has one.

## Acceptance

- Vitest (lib, `aurelius-atlas-ui`):
    - `category-colors.spec.ts` (new) — the join (UIC-30): empty answer with
      no categories, first-seen palette order, a picked override winning,
      the empty category naming nothing, the thirteenth-category wrap; the
      lookup (UIC-30): view id first then concept, untabled answers null, a
      category missing from the legend paints nothing (UIC-30).
    - `model-viewer.component.spec.ts` — the colour view on the drawing: no
      categories keep the class fills and black stroke, categories ink the
      node fills and the connection strokes with their legend colours, a
      picked colour repaints its whole category (UIC-31's canvas half), and
      the view-id/concept chain holds on the DOM.
    - The stories: CategoryColors (three buckets, palette colours pinned in
      `play`), CategoryColorsCustom (a picked override), and Playground
      (the join pinned in `play`, then the "gold" row's picker driven: both
      gold nodes take the picked colour and the row follows, the other
      categories keep theirs).
- Vitest (webapp, `aurelius-atlas-webapp`):
    - `view-tab.component.spec.ts` — the legend hidden without categories
      (the legacy's null-legend guard), the rows rendered in first-seen
      order with override colours winning, a picked swatch emitting its
      category and hex (UIC-31).
    - `model-browser.component.spec.ts` — the drawer's end-to-end seam:
      categories on the shared state make the View tab list the legend, a
      swatch change writes `state.categoryColors` (UIC-31).
- Playwright (e2e): unchanged. No producer exists on the page today, so the
  shipped chain draws as before — the existing suite is the pin that the
  null-category default changes nothing.
- Gates: `nx test aurelius-atlas-ui -c ci`, `nx test aurelius-atlas-webapp
-c ci`, `nx lint` on both, `nx build aurelius-atlas-ui`,
  `nx build-storybook aurelius-atlas-ui`, `nx e2e aurelius-atlas-webapp`.
