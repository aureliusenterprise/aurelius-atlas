# 7.22f Lineage diagram: the drawing becomes a shared canvas

- **Status:** proposed
- **Pull request:** —
- **Records:** UIC-29; DD-419. Amends nothing: the drawing rules LDG-12..18
  and LDG-33..36 keep their words and move with the code, and the chrome
  rules LDG-27..31 stay in the webapp unchanged. Relies on LDG-12..18 (7.22b),
  LDG-27..31 (7.22d), LDG-33..36 and DD-418 (7.22e), DD-417 (the inset),
  DD-415 (the shared state), and the library's dumb-component and story rules
  (`libs/angular/AGENTS.md`).

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

7.22b built the renderer inside the details page's viewer, and 7.22e widened it
to the archimate language. The drawing now answers to two products: the
details page, and any other place that holds an ar3 document. The legacy kept
the same picture inside one `modelview` component, chrome and all, so no other
page could draw a model without the toolbar, the save flow, and the routing.
This slice cuts the picture out of the shell.

The canvas moves to `aurelius-atlas-ui` as `ModelViewer`: the SVG, the
shape/glyph/marker tables, the bounds group, the d3 zoom, and the two state
strokes. The webapp's `LineageViewer` keeps what the page owns: the box's
drawing area, the control column, the fullscreen toggle, the save-as-PNG
flow, the shared state, and the drawer routes. The split is the lib's rule
(WBP-02 and the dumb-component rule): the canvas takes `input()`s, answers
with `output()`s, and injects nothing.

Each shape family gains a Storybook story, so a reviewer can check the
lineage pair, the six basic shapes, the ten layer fills, the junctions, the
folder, and all sixteen relation rows with an eye, without a seeded backend.
The lib rule "Every component ships a story" has had no diagram to prove it
until now.

Delivered here:

- The `ModelViewer` canvas in `aurelius-atlas-ui` (UIC-29), with the moved
  data modules (`ar3-types.ts`, `archimate-shapes.ts`, `connection-path.ts`,
  `lineage-shapes.ts`). The name says "model", not "lineage": an archimate
  document draws here just as well.
- The webapp's `LineageViewer` reduced to the shell (same selector, same
  e2e surface).
- Eight stories per shape family in the lib — the seven of the shape
  families plus one drawing every glyph-table type.
- The canvas spec in the lib: the drawing tests LDG-12..18 and the archimate
  block LDG-33..36 move from the viewer spec with their ids.

Explicitly not delivered here:

| Not delivered                             | Lands with | Why                                                              |
| ----------------------------------------- | ---------- | ---------------------------------------------------------------- |
| A second host page for the canvas         | —          | The extraction is the deliverable, no caller beyond the page     |
| Storybook visual snapshots of the canvas  | —          | The repo has no Chromatic/VRT runner, the stories are manual     |
| The save-PNG flow inside the canvas       | —          | The flow reads the page's config and session, the shell keeps it |
| A published npm package split for the lib | —          | The lib is workspace-internal, as UIC-01..28 already are         |

## Semantics

One new rule. The moved rules keep their text where they were written, and
the tests that named them move with them.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UIC-29 | `ModelViewer` is a dumb canvas in `aurelius-atlas-ui` (DD-419). It draws the `view` of the `model` it is given, with the rules of LDG-12..18 and LDG-33..36, and owns no state beyond its zoom. Its inputs are `model`, `view`, `selected`, and `highlightedGuid`, and its one output is `conceptSelected` with the clicked concept (`ref ?? id`, LDG-17). It injects no service and routes nowhere, so the caller answers its own clicks. `resetZoom()` restores the identity transform for the caller's toolbar (LDG-16/LDG-29), and `svgElement()` hands the live SVG to a caller that serialises it (LDG-30). It fills its host element, so the caller sizes the drawing. The drawing keeps a fixed dark ink for its node names and connection labels (`.node-text`, `.connection-label`), so no theme can make them illegible on its light ground, and a named connection draws its name anchored at the path's midpoint, beneath the line (LDG-14). It ships a story per shape family (the lib's story rule). |

## Aurelius origin

No new legacy port. Every drawing rule cited here was ported and pinned in
7.22b (LDG-12..18) and 7.22e (LDG-33..36), and the code moves unchanged apart
from what the boundary forces (DD-419). The one legacy fact worth keeping:
the legacy's `modelview.component.html` fused the drawing, the toolbar, the
fullscreen flag, and the save button in one component, and Aurelius itself
copied that whole component into the details page instead of sharing the
picture. This slice is the split the legacy never made.

## Deviations

None against Apache Atlas. One deliberate difference against the legacy
renderer:

- The canvas stops where the picture stops (UIC-29). The legacy's
  `modelview` component owned toolbar, fullscreen, save, and selection state
  next to the SVG, so its consumer could not reuse the drawing. The shell
  keeps those duties, and the canvas reports clicks instead of acting on
  them. The rendered pixels do not change: the same style rules ride the
  canvas, the same DOM (`svg.lineage-svg`, `g.node`, `g.connection`) sits
  inside the shell's container, and 7.22b/7.22d's e2e pins pass unchanged.
- The archimate fill tables cross a package boundary (DD-419). The lib owns
  the tables and the canvas's literal style copy, and the webapp keeps its
  two drawer copies with their drift pins. The builder limit that forced the
  copies (DD-418) is unchanged, so the copies multiply by site, not by
  package.

## Acceptance

- Vitest (lib, `aurelius-atlas-ui`):
    - `model-viewer.component.spec.ts` (new) — the drawing tests moved from
      the viewer spec over hand-built models: draw order and shape paths
      (LDG-12), the bounds group and the inset (LDG-15, DD-417), fills,
      classes, glyphs, and names (LDG-13), the connection path and marker
      (LDG-14), the hit path (DD-409), the no-font rule (DD-408), the zoom
      extent and `resetZoom` (LDG-16), the click emit and the selected input
      (LDG-17), the highlight input (LDG-18), the background rect (LDG-28's
      ground). The archimate block moves whole: the eight dash-proof markers
      (LDG-36), the goal octagon with glyph (LDG-33..35), the unlabelled
      junction (LDG-33), the per-relation markers and dashes (LDG-36), and
      the shipped style block pinned against both fill tables (DD-418).
      New: the named connection's centre/below anchor (LDG-14) and the
      fixed dark ink (DD-419).
    - `archimate-shapes.spec.ts` — moved with the module, unchanged.
    - The stories: eight over the shape families, the fills, the junctions,
      the relation table, the states, a named connection, and every
      glyph-table type in one grid. Each checks its own node/icon/path
      counts in `play`.
- Vitest (webapp, `aurelius-atlas-webapp`):
    - `lineage-viewer.component.spec.ts` — reduced to the shell: the 50vh
      area (LDG-15), the click-through to state and routes (LDG-17/DD-415),
      the forwarded highlight input (LDG-18), the toolbar tooltips (LDG-27),
      the fullscreen toggle and Browse copy (LDG-28), the two drawer routes
      (DD-415), the reset forward (LDG-29), and the save seam handed the
      canvas's SVG at the container's size without moving the view (DD-407).
    - `lineage-shapes.spec.ts` (new) — the badge seam DD-405 after
      `ar3BadgeClass` folded into `lineageBadgeClass` (DD-419).
    - `model-tab.component.spec.ts`, `selection-panel.component.spec.ts` —
      imports only, the fill tables now come from `aurelius-atlas-ui`.
- Playwright (e2e): unchanged. The selector, the `#screenshot-container`,
  the `g.node`/`g.connection` DOM, and the control classes all survive the
  split, so 7.22d's suite guards it as written.
- Gates: `nx test aurelius-atlas-ui -c ci` (with check-purity),
  `nx test aurelius-atlas-webapp -c ci`, `nx lint` on both,
  `nx build aurelius-atlas-ui`, `nx build-storybook aurelius-atlas-ui`, the
  purity script (WBP-02), `nx e2e aurelius-atlas-webapp`.
