# 7.22b Lineage diagram: the box and the drawing

- **Status:** proposed
- **Pull request:** —
- **Records:** LDG-09..18; DD-388..392, DD-417 (the drawing's default inset,
  amends LDG-15); amends 7.21a's deferral table and DET-32/DET-33 (the dataset
  and process layout rows, this slice's boxes); 7.22e ports the archimate set
  behind LDG-13/LDG-14 (LDG-33..36, DD-418);
  relies on LDG-01..08 (7.22a, the data path), LM-01..LM-06 (the answer the box
  consumes), DV-68 (the ar3 contract), DET-15/DET-16 (the layout dispatch),
  DD-128 (the dictionary bridge), DD-140/DD-369 (no App Search, no Data Quality)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The legacy details page shows the lineage of an `m4i_dataset` or an
`m4i_generic_process` as a box titled **Lineage Model**: a spinner while the
model is fetched, a plain message when the entity has none, and otherwise an SVG
diagram — dataset and process rectangles joined by arrows, laid out left to
right by the server, pannable and zoomable (7.22a delivered the fetch,
LDG-01..08). 7.21a, 7.21b, and 7.21c deferred the box, its stats entry, and its
navigation link with this slice as their landing point. This increment draws it.

The legacy renderer is the modelview2 library — an archimate model explorer that
the lineage model only visits as one of its "languages". This slice ports that
language, not the explorer. The rules:

- the box on both layouts: the title, the pending state, and the empty message
  in the legacy positions and order (LDG-09, LDG-10)
- the model reader: parse the answer's `model` string into elements, relations,
  and the one view (nodes with positions, connections with bendpoints) — a pure
  function, the archimate3 reader narrowed to what the lineage document carries
  (LDG-11)
- the diagram: rectangles for `lineage_dataset` and `lineage_process` with the
  legacy fills, the connection path from the node rectangles and the server's
  bendpoints with the `generic-arrow` marker end, the model's own normalisation
  to its bounding box, and the node/connection labels (LDG-12..15)
- pan and zoom: d3-zoom over the drawing group, scale between 0.5 and 3
  (LDG-16)
- selection: a node or connection click marks it (the `.is-selected` stroke),
  a second click clears it (LDG-17)
- the highlighted entity: the page's own guid gets the highlight stroke, the
  legacy's `[highlightedEntity]` input (LDG-18)

Explicitly not delivered here, with the increment that will:

| Not delivered                                                        | Lands with | Why                                                                                                                                                                                |
| -------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The quickview (browse, model search, selection panel, view info)     | 7.22c      | The panel is its own port over the ported UI set; selection lands here only as the visual state it needs                                                                           |
| The toolbar (Browse/info/fullscreen/reset/save buttons) and PNG save | 7.22d      | The chrome rides the completed view; reset-zoom and fullscreen are the toolbar's commands (LDG-16 keeps them callable programmatically)                                            |
| The stats entry, the navigation links, the nav order                 | 7.22d      | A stat and a link to a box come back together with the finished box (DD-383's rule, kept); the box renders without them because the anchor `#lineage-model` exists from this slice |
| The Data governance addon in the selection panel                     | 7.8        | It queries governance quality, which stays deferred with 7.8 (DD-369)                                                                                                              |
| The repository model path (branch/version fetch, the folder tree)    | —          | The legacy Atlas app never uses it (`shell.standalone`): a deviation this slice records (LDG's Deviations)                                                                         |
| Colour-by (buckets, legend, palette editing)                         | —          | It serves the platform app's model compare; no details-page input feeds it (the legacy's `bucketMapping` input is dead on this page)                                               |

## Semantics

Rules LDG-09..18, continuing the band 7.22a opened. The strings ride the bridge
(DD-128): the box's three strings are catalogue keys already (`search.details.
dataset.lineageModel`, `...components.lineageModel.loading`,
`...noLineageModelAvailable`, `search.details.process.lineageModel`); the model
name "Lineage" is the server's data, not a string. The diagram's labels are the
model's data too — no new fixture keys in this slice.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LDG-09 | The `m4i_dataset` layout gains the box `<section id="lineage-model">` after Child Datasets and before Producers (the legacy order: the deferred position, DET-32's table); the `m4i_generic_process` layout gains it after Systems and before Inputs (DET-33's deferred position). The box's header shows the drawn view's name — the model's own data (the server's rule names the view "Lineage"), the legacy's `displayName` header — and the box renders the viewer for the opened guid. The nav/stat labels (`search.details.dataset.lineageModel`, `search.details.process.lineageModel`) arrive with 7.22d.                                                                                                                                                                                                                                                                                                                                                                                                        |
| LDG-10 | The box has three states from the LDG-01 call: pending → the loading message (`search.details.components.lineageModel.loading`); a `null` answer (LDG-03) → the empty message (`search.details.components.lineageModel.noLineageModelAvailable`); a model → the diagram. A failed call (LDG-04) renders the empty message too (the legacy's single fallback, kept deliberately, DD-392); the error itself reaches the 7.19 alert path through the shared chain, not the box.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| LDG-11 | The model reader is a pure function `parseAr3Model(model: string)` over the parsed JSON: the elements from `ar3_model.ar3_elements.ar3_element[]` (id `@identifier`, type `@xsi_type`, name from `ar3_name[0].value`), the relations from `ar3_relationships.ar3_relationship[]` (id, `@source`, `@target`, `@xsi_type`, name `ar3_name[0].value`), and each view from `ar3_views.ar3_diagrams.ar3_view[]` with its `ar3_node[]` (id `@identifier`, element ref `@elementRef`, `@x`/`@y`/`@w`/`@h`, label `ar3_label[0].value`) and `ar3_connection[]` (id, relation ref `@relationshipRef`, `@source`/`@target` view-node ids, `ar3_bendpoint[]` `{x,y}` list) — the legacy parser's field map (`parse-view-node.ts`, `parse-view-connection.ts`). A node's or connection's display name falls back from the view element to the referenced model element (the legacy's `modelNode.name ?? viewNode.name`). The reader throws on a document without `ar3_model`; the box treats a parse error as LDG-10's failure state. |
| LDG-12 | The diagram draws the first view of the model (the lineage document carries exactly one, `lineage_view`, named "Lineage" by the server's rule). Nodes render first, connections on top, each node a rectangle path from its `x,y,width,height` — the legacy's `basicShapes.rectangle` for both lineage types.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| LDG-13 | A node's fill follows its type class: `lineage_dataset` fills `hsl(240, 100%, 95%)`, `lineage_process` fills `hsl(171, 100%, 95%)`, stroke `#a0a0a0` 2px. Each node carries its type icon (the legacy's archimate-icon shapes for the two lineage types — the 16×16 database-card and gear paths), floated right, stroke `#000000`, fill blue for a dataset and `#00d1b2` for a process (the archimate icon set lands with 7.22e: LDG-35, DD-418). The name renders inside the rectangle, clipped and ellipsised like the legacy's `foreignObject` label.                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| LDG-14 | A connection's path runs from the source node's rectangle to the target's through the connection's bendpoints: the legacy's edge-anchored endpoints (the straightest entry/exit points on the two rectangles, bendpoints as waypoints), stroke none-fill black, `marker-end` the arrow marker the lineage language names (`generic-arrow`: the one `<defs>` marker this slice ports — the archimate marker set lands with 7.22e: LDG-36, DD-418). The relation's name labels the path centre when present.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| LDG-15 | The drawing normalises to the view's bounds: the group translates by `-minX, -minY` over all node positions (the legacy's `ModelviewService`), plus a fixed 20px inset (DD-417), so a model laid out at any origin fits its container (the legacy height, 50vh, as the box's drawing area) and sits slightly off the top-left corner.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| LDG-16 | Pan and zoom ride the SVG with d3-zoom, scale extent [0.5, 3] (the legacy's `SVGZoomDirective` exactly), applied as a transform on the drawing group; drag pans, wheel zooms. The viewer exposes `resetZoom()` on its API (7.22d's toolbar button calls it).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| LDG-17 | Clicking a node or connection selects its concept: a node selects the element it references (`ref ?? id`), a connection the relation it references (`ref ?? id`) — the legacy's rule. The viewer holds one selected-concept signal (the legacy's single `selectedEntity` slot); clicking the same concept again clears it, and the drawn element gains the selection class (`.is-selected` stroke `#40e0d0`). 7.22c's panel reads the signal; the seam survives this slice without a panel.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| LDG-18 | The viewer highlights the page's entity: given the opened guid, the node whose element id (or `ref`'s element id) equals it carries the highlight stroke (`hsl(141, 53%, 53%)`, the legacy `.is-highlighted`). No match highlights nothing.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
`libs/modelview2/src/lib/` and the two details pages, cited by path:

- `apps/atlas/src/app/search/details/components/lineage-model/
lineage-model.component.{ts,html}` — LDG-09/LDG-10's box: the spinner, the
  message, `[highlightedEntity]="entityId$ | async"`, and the silent catch that
  LDG-10 keeps as the one fallback.
- `dataset/dataset-details.component.html` L115 and
  `process/process-details.component.html` L74 — the `#lineage-model` anchors in
  LDG-09's positions.
- `parsers/archimate3/parse-model.ts`, `parse-elements.ts`,
  `parse-element.ts`, `parse-relations.ts`, `parse-relation.ts`,
  `parse-view.ts`, `parse-view-nodes.ts`, `parse-view-node.ts`,
  `parse-view-connections.ts`, `parse-view-connection.ts` — LDG-11's reader: the
  field-by-field mapping this rule restates (the XML-decoded names, the
  bendpoints, the `@relationshipRef` link, the `@elementRef` node link). The
  `ar3_viewRef` recursion, the organizations tree, and the properties dicts are
  the explorer's; the properties dict lands with 7.22c's panel, the rest stays
  unparsed (DD-389).
- `model-view.service.ts` — LDG-15's bounds (`minX/minY` over the view's nodes,
  `x - minX` on each node) and LDG-12's first-view selection (`findKey`).
- `shapes/languages/lineage.ts` and `lineage.scss` — LDG-13/LDG-14's shape and
  style table: the two rectangles, the two fills, the `generic-arrow` marker.
- `libs/components/src/lib/archimate-icon/{definitions.ts,shapes.ts}` (the
  `lineage_dataset`/`lineage_process` icon paths and their type classes) and
  `archimate-icon.component.scss` (the icon fills) — LDG-13's icons: the two
  vendored 16×16 paths, the only two icons of that set the lineage page draws.
- `shapes/basic-shapes.ts` (the rectangle path builder),
  `shapes/node/modelview-node.component.{ts,svg}` (the clip-path shape, the
  `foreignObject` label, the translate), `shapes/node/modelview-node.service.ts`
  (the color precedence, trimmed to the class fills — no bucket mapping, LDG-13)
  — LDG-12/LDG-13.
- `shapes/connection/modelview-connection.service.ts` (`getShortestLineEndpoints`
  and the bendpoint walk, LDG-14's path maths) and
  `modelview-connection.component.{ts,svg}` (the path, the arrow markers, the
  `textPath` label) — LDG-14.
- `svg-zoom.directive.ts` — LDG-16, the [0.5, 3] scale extent verbatim.
- `shapes/node/modelview-node.component.ts` (the click toggle on
  `selectedEntity`, the `is-selected`/`is-highlighted` host classes) and
  `modelview.component.html` (the style block: the two selection/highlight
  strokes) — LDG-17/LDG-18.

## Deviations

None against Apache Atlas: the box consumes 8.2's shipped contract; no server
surface is added. Against the Aurelius product (DD-388..392 carry the detail):

- the renderer is not the modelview2 library: the archive keeps its explorer
  (browse tree, fuzzy search, view tabs, colour-by, repository models) out of
  the webapp (WBP-02 forbids its NgModule/ngx-translate/BasicStore idioms; the
  details page uses none of that surface). What the page uses — the ar3 reader,
  the lineage shapes, the path maths, the zoom — is ported in signals/standalone
  idiom (DD-388).
- the ar3 reader is the lineage-shaped subset (LDG-11): nested view groups,
  organizations, properties, styles, and the `ar3_ArchiDiagramModelReference`
  view-ref nodes are not parsed; the server's own rule set emits none of them
  (DD-389, and 8.2's scenario fixture proves the shape).
- a failed call shows the legacy's empty message (LDG-10): the legacy swallows
  every failure into that state; this port keeps the screen and adds nothing
  visible — the request's 502/401 still reach the drawer through the shared
  error chain (7.19, ALR rules), which the legacy had no equivalent of.
- the drawing sits 20px off the area's top-left corner (LDG-15, DD-417): the
  legacy seated the model flush at the corner, where the first node's stroke
  touched the drawing's edge; readers asked for air. The inset is a constant
  on the bounds group, so pan, zoom, reset, and the saved PNG all ride over
  it unchanged.
- the viewer keeps no Redux store: each legacy per-node `BasicStore` service
  becomes the component's own signals (DD-390, WBP-02's rule that state lives in
  signals).

## Acceptance

- Vitest (unit, the new `search/details/lineage/` components):
    - `parse-ar3.spec.ts` — the field mapping (LDG-11: ids, refs, bendpoints,
      names; a malformed document raises) over a fixture vendored from 8.2's
      `apps/aurelius-atlas-lineage-model/scenarios/fixtures/graph.extract.json`
      (the 8.1-verified model document, cited: the expected node and connection
      positions are that document's, so the parity pin is the shipped chain's
      output, not the legacy's screenshots — DD-391).
    - `lineage-viewer.component.spec.ts` — the first view draws, bounds
      normalise to the origin plus the inset (LDG-12/LDG-15: the group
      transform over the fixture; DD-417: the inset, and the reset leaving it
      in place), the fills, classes, and icon paths per type (LDG-13), the path
      `d` and the arrow marker for a two-node fixture (LDG-14), the zoom extent
      constant and the reset (LDG-16), the click toggle (LDG-17), the highlight
      class (LDG-18).
    - `section-config.spec.ts` — amended: the dataset and process rows carry the
      lineage box between their named neighbours (LDG-09's positions; the stats
      and nav rows stay 7.21c's until 7.22d).
- Playwright (e2e, authenticated, every browser): extending DET-34's seeded
  mini-graph (the process that produces and consumes the dataset): the dataset's
  details screen shows the box titled "Lineage" with two rectangles (the
  dataset, the process — names from the model, LDG-13) and the arrow between them
  (LDG-12/14); clicking the process node marks it selected (LDG-17); the opened
  dataset's own node carries the highlight (LDG-18); the unconnected process
  answers the 204 (LDG-03 → LDG-10: the empty message, no diagram). The box
  renders over the aux chain from 7.22a's compose.
- Gates: `nx test aurelius-atlas-webapp -c ci`, `nx lint`, the purity script
  (WBP-02), `nx e2e aurelius-atlas-webapp`.
