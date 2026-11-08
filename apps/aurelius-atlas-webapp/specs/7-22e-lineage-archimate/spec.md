# 7.22e Lineage diagram: the archimate shape language

- **Status:** proposed
- **Pull request:** —
- **Records:** LDG-33..37; DD-418. Amends LDG-13 and LDG-14 (7.22b), because the
  archimate shape, glyph, and marker sets those rows left with the explorer land
  here. Relies on LDG-09..18/LDG-20/LDG-23 (7.22b/7.22c), DD-388/DD-389 (the
  ported viewer and the reader subset, amended), DD-417 (the inset),
  DV-68/DTM-11 (the ar3 contract the shipped producer writes), and DD-128 (the
  dictionary bridge).

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The viewer of 7.22b draws one language. It shows two rectangles and one arrow,
because the shipped producer (8.2) emits only the lineage pair. The legacy
renderer speaks two languages. Its modelview2 library carries a full archimate3
language with about 60 element types drawn as six basic shapes, layer fills per
element class, a type glyph per element, and eleven relation styles built from
eight arrowhead markers. The reader, the drawer's tables, and the selection
panel already carry the archimate rows of that document. LDG-11 parses any
`ar3_*` type, and LDG-23's tables list any element. So today an archimate
document renders as a field of identical rectangles with no glyphs and plain
lines.

This slice ports the drawing half of that language. The reader stays as 7.22b
narrowed it, with one addition. The legacy's relation parser reads two
per-type attributes: `@accessType` on an access relation and `@isDirected` on an
association. Two of the relation styles depend on them, so the reader gains
them. The shipped producer still emits only the lineage pair, so this slice is
preparation. An archimate document from a model extraction now draws the way the
legacy drew it.

Delivered here:

- The node-shape table: six basic shapes, the junction and grouping flags, and
  the path formulas (LDG-33).
- The fill-class table and the ten layer fills, on the drawing and the glyphs
  (LDG-34, LDG-35).
- The glyph table over the legacy's icon paths, in the drawing and the two
  drawer icon sites (LDG-35).
- The relation styles: eight markers in the defs, eleven styled relation types
  plus the lineage pair, and the two reader attributes (LDG-36).
- The full human-readable type and verb tables of the legacy metamodel (LDG-37).

Explicitly not delivered here:

| Not delivered                                       | Lands with | Why                                                                                                      |
| --------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| The colour-by pipeline and `style`-block fills      | —          | The shipped producer emits no style block (DD-389), so the legacy's per-view palette has nothing to read |
| `ar3_ArchiDiagramModelReference` nested view groups | —          | 7.22b's deferral (DD-389) stands: the producer emits none, and the explorer surface has no page          |
| The browse tree over `ar3_organizations`            | —          | 7.22c's deferral (DD-406) stands: no page asks for it yet                                                |
| The archimate icon's `.link` fill                   | —          | The legacy stylesheet carries that rule with no type that names it. It is dead in the legacy too.        |

## Semantics

Rules LDG-33..37. Every table below is the legacy's, kept verbatim. Where the
legacy disagrees with itself, the quirk stays and Deviations names it. The
lineage pair of 7.22b (LDG-13/LDG-14) is unchanged and rides these tables as two
more rows, so its tests stay green as written.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LDG-33 | A node is drawn as the basic shape its element type names in the legacy's `ar3Elements` table (65 rows, verbatim): `rectangle`, `rounded` (12 px corner radius), `ellipse`, `octagon` (12 px cut), `grouping` (a folder tab over a body), or `waved` (a waved bottom). The table's two flags decide what else shows. An `ar3_AndJunction` or `ar3_OrJunction` draws its ellipse with no icon and no name label. The `ar3_Grouping` draws with no icon. Every other row shows both. The path formulas are the legacy's `basicShapes` verbatim, computed from the node's `@w` and `@h`. A type the table does not name keeps 7.22b's LDG-13 fallback: a plain rectangle with the icon and the name shown.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| LDG-34 | The node's `node-shape` path gains the fill class of the legacy's `ar3Classes` table (65 rows, verbatim), and the drawing's style block carries the ten layer fills of `archimate3.scss` verbatim: business `#ffffb5`, application `#b5ffff`, technology and physical `#c9e7b7`, motivation `#ccccff`, implementation `#ffe0e0`, strategy `#f4deaa`, junctions `#000000` (and) and `#ffffff` (or), and location `#ff8c00`. The lineage pair keeps 7.22b's two fills. The legacy's one value `implementation & migration` is kept as `implementation` (see Deviations). The classes `composite` (the grouping) and `unknown` name no rule, so those nodes stay uninked, as in the legacy. A type neither table names gets no class and no fill.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| LDG-35 | Each node shows the type glyph of the legacy's `definitions.ts` table (64 rows: 62 archimate paths plus the two lineage paths of 7.22b). The glyph takes its colour from the icon fills of `archimate-icon.component.scss` (the same ten layers) and keeps the legacy's black glyph stroke. Three icon sites read this one table: the drawing's node icon, the drawer's Selection-tab Type row, and the Model-tab tables' icon cells. So an archimate element answers with its glyph everywhere, because the legacy drew the same component in all three. `ar3_Unknown` carries no glyph row, as in the legacy. The card badge of DD-405 stays lineage-only, because the legacy's badge table had no archimate entry either.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| LDG-36 | The defs block carries the eight markers of the legacy's `ar3RelationDef` table verbatim (id, refX/refY, sizes, path, fill, stroke). Each marker path keeps `stroke-dasharray: 999`, so a dashed connection never dashes its own arrowhead. The `generic-arrow` marker equals 7.22b's marker, so its pin holds. A connection's stroke follows the relation's own type through the legacy's `ar3Relations` table verbatim. The model relation wins over the view connection's type, as in the legacy. Access grows the `access-read` marker at the start and the `generic-arrow-open` marker at the end from its `@accessType` value (Read, Write, or ReadWrite) and dashes `2,2`. Aggregation and Composition mark the start. Assignment runs `assignment-start` to `generic-arrow`. Association marks the end only when `@isDirected` is truthy. Flow, Influence, Realization, Serving, Specialization, and Triggering each name their end marker and dash. `lineage_relation` keeps `generic-arrow`. Any other type draws the plain line, as the legacy's style function answered. That covers the generic `ar3_Relationship` a connection carries when its relation is missing. The reader (LDG-11, amended) reads `@accessType` only for an `ar3_Access` row and `@isDirected` only for an `ar3_Association` row, which is the legacy's own gating, and keeps them with the relation. |
| LDG-37 | The human-readable type table (LDG-20's, amended) is the legacy metamodel's `elements` and `relations_by_tag` in full. Every `ar3_*` element keeps the legacy's name, and `ar3_Unknown` keeps the placeholder "-- Please select a type --". Bare `ar3_Element` and `ar3_Junction` carry no name. Each of the eleven archimate relation tags keeps its verb in the relation table (Accesses, Aggregates, Assigned to, Associated with, Composes, Flows into, Influences, Realizes, Serves, Specializes, Triggers) beside the lineage pair. The drawer's Type rows and the Model tab's italic relation line read these tables unchanged.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit
`b057389828c10497dd52d9efd4c16547c282c005`), `libs/modelview2/src/lib/` and
`libs/metamodel/src/lib/`, cited by path:

- `shapes/languages/archimate3.ts` — LDG-33/LDG-34/LDG-36's four tables: the
  `ar3Elements` shape rows, the `ar3Classes` fill classes, the `ar3Relations`
  style rows, and the `ar3RelationDef` marker rows, all verbatim. The file's
  `grouping` and `wavedRectangle` path builders are the two shapes
  `basic-shapes.ts` does not carry.
- `shapes/basic-shapes.ts` — the rectangle, rounded, ellipse, and octagon path
  formulas (LDG-33), verbatim.
- `archimate3.scss` — the ten node layer fills (LDG-34), verbatim.
- `libs/components/src/lib/archimate-icon/{definitions.ts,shapes.ts}` — the 62
  archimate glyph paths and their colour classes (LDG-35), verbatim, including
  the Deliverable row's colour disagreement that the legacy shipped (see
  Deviations).
- `archimate-icon.component.scss` — the ten icon fills and the black glyph
  stroke (LDG-35). Its `.link` rule names no type and stays out.
- `modelview.component.html` L153-170 and
  `shapes/connection/modelview-connection.component.svg` — LDG-36's drawing
  posture: the defs loop that styles each marker's fill and stroke, the
  `stroke-dasharray: 999` on every marker path, and the
  `[attr.marker-start]`/`[attr.marker-end]` url-or-null bindings beside
  `[style.stroke-dasharray]`.
- `parsers/archimate3/parse-relation.ts` — LDG-36's two attributes. The reader
  reads `@accessType` only inside the `ar3_Access` branch and `@isDirected` only
  inside the `ar3_Association` branch. The rest of that parser's options
  handling feeds the colour-by pipeline, which stays out (DD-389). The verb
  phrases of LDG-37 ride the same file's `humanReadableTypes` table.
- `libs/metamodel/src/lib/metamodel.ts` — LDG-37's `elements` and
  `relations_by_tag` tables verbatim, the placeholder and the two nameless rows
  included.
- `shapes/node/modelview-node.component.{ts,svg}` — LDG-33/LDG-35's node
  posture: the shape path under the clip, the `archimate-icon` beside it, and
  the label gate the junction flags drive.

## Deviations

None against Apache Atlas. No server surface is added, and the shipped
producer's contract (DV-68/DTM-11) is untouched. Each difference against the
legacy renderer is kept or fixed deliberately:

- The legacy class value `implementation & migration` becomes `implementation`
  (LDG-34, DD-418). In the legacy that string reached the DOM as a class
  attribute, so the browser split it into four classes, and only
  `implementation` matched a fill rule. The kept value is the one class that had
  an effect. The rendered colour is the same, and no attribute holds an
  impossible value.
- Colour-by, the `style`-block fills, and the per-view palette stay out (DD-389
  stands). The legacy's node colour precedence starts at those styles, and the
  shipped producer emits none of them. The layer fills are the floor the legacy
  drew under them.
- The fill rules ship as literal copies inside each component that uses them
  (DD-418). The Angular builder drops an imported constant interpolated into a
  component's `styles`, so the tables cannot ride as strings. Each copy names its
  source table in a comment, and three tests pin every declaration of each table
  into the shipped style block, so a drifted copy fails CI.
- Three legacy quirks stay as parity, not fixes. The Deliverable row's node
  class is `technology` while its glyph colour is `implementation`, so the
  legacy rendered a green node with a pink glyph, and this port does the same.
  An association checks the truthiness of its `@isDirected` attribute, not its
  word, so the string `"false"` draws the arrow. And the generic
  `ar3_Relationship` type has no style row, so a connection whose relation is
  missing draws a plain line.

## Acceptance

- Vitest (unit):
    - `archimate-shapes.spec.ts` — the junction and grouping flags and the shape
      families (LDG-33), the six path formulas at a fixed size (LDG-33), the
      plain-rectangle fallback with LDG-13 unchanged, the fill-class table with
      the `implementation & migration` row and the uninked `composite` and
      unknown classes (LDG-34), the node fill block (LDG-34), the glyph paths
      and colours with the Deliverable quirk (LDG-35), the eight marker rows
      against the legacy table and 7.22b's `GENERIC_ARROW` (LDG-36), the
      twelve-type style table with the access combinations and the association
      truthiness (LDG-36), and the plain line for an unstyled type.
    - `lineage-viewer.component.spec.ts` — amended: over a hand-built archimate
      document, the defs carry all eight markers with the `999` dasharray
      (LDG-36), a goal node draws its octagon, motivation class, and glyph
      (LDG-33/LDG-34/LDG-35), a junction draws an unlabelled ellipse, and each
      connection rides its relation's markers and dash (LDG-36). The shipped
      style block is pinned to carry every fill of both fill tables (DD-418).
      7.22b's lineage document tests pass unchanged, LDG-14's `generic-arrow`
      pin among them.
    - `parse-ar3.spec.ts` — amended: each option is read only for its own
      relation type (LDG-36's gating). The LDG-11 literals gain the empty
      options.
    - `lineage-metamodel.spec.ts` — the full name table with the placeholder and
      the two nameless rows, and the twelve verbs (LDG-37).
    - `model-tab.component.spec.ts` and `selection-panel.component.spec.ts` —
      amended: an archimate row renders its glyph and colour class (LDG-35), the
      card badge stays plain (DD-405), and each component's shipped style block
      is pinned against its fill table (DD-418).
- Playwright (e2e): unchanged. The seeded chain is lineage-only, so the shipped
  path rides 7.22d's suite. The archimate language is pinned in units, and the
  tables are reviewed as code (ADR 052).
- Gates: `nx test aurelius-atlas-webapp -c ci`, `nx lint`, the purity script
  (WBP-02), `nx e2e aurelius-atlas-webapp`.
