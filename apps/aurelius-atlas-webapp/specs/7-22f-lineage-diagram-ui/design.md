# Design decisions: 7.22f — Lineage diagram: the drawing becomes a shared canvas

> **Purpose:** the `DD-NNN` entries of this increment, written before the code and
> updated while it changes. Read-only history: every entry ever made also lives in
> [`docs/architecture/conversion/design-log.md`](../../../../docs/architecture/conversion/design-log.md),
> which is the archive (an entry lives in exactly these two places, and the archive
> is never edited — DD-001). New entries are numbered consecutively across the
> repository: check the archive's topmost number and the sibling `specs/*/design.md`
> files for the largest `DD-NNN` in use before taking the next.

| Id      | Title                                                               |
| ------- | ------------------------------------------------------------------- |
| DD-419. | The lineage drawing is a shared UI-lib canvas with the shell on top |

## Decisions

### DD-419. The lineage drawing is a shared UI-lib canvas with the shell on top

- **Status:** Proposed
- **Increment:** 7.22f
- **Date:** 2026-11-08

**Decision.** The drawing of 7.22b/7.22e moves to `aurelius-atlas-ui` as the
`ModelViewer` component (UIC-29) — named for the model it draws, not for
lineage, because an archimate document draws here too — with the four data
modules it reads (`ar3-types.ts`, `archimate-shapes.ts`, `connection-path.ts`,
and `lineage-shapes.ts`) under `src/lib/model-viewer/`. Its API is four
`input()`s (`model`, `view`, `selected`, `highlightedGuid`), one `output()`
(`conceptSelected`), and two public methods (`resetZoom`, `svgElement`). It
injects nothing (WBP-02). The webapp's `LineageViewer` keeps its selector and
becomes the shell: the drawing area, the control column, the fullscreen
flag, the save flow (handed `svgElement()`), the shared state, and the
drawer routes. The toggle that LDG-17 drew inside the viewer moves to the
shell's click handler, because the canvas answers clicks and the shell
decides what a click means. `ar3-types.ts` holds the reader types the canvas
consumes (`Ar3View`, `Ar3DiagramModel`, `Ar3RelationOptions`) and the two
concept-id helpers. The webapp's `parse-ar3.ts` keeps its own richer
interfaces and re-exports those names, so every existing import path keeps
working and structural typing bridges the two (the webapp's `Ar3Model`
satisfies the lib's `Ar3DiagramModel` because each element carries the one
field the canvas reads, `type`). The badge helper stays in the webapp: the
canvas must not import the app's `TypeIconClass`, so 7.22e's `ar3BadgeClass`
folds into the webapp's `lineageBadgeClass`, which already answered the same
pair. The lib's `package.json` gains `d3-selection`/`d3-zoom` peer
dependencies, and eight stories ship with the component. The canvas inks its
own text with a fixed dark colour (`.node-text`, `.connection-label`): the
white ground rect keeps the picture light in every theme, so text left
inheriting the page colour turns illegible in dark mode. A named connection
anchors its label at the path's midpoint beneath the line (`text-anchor`
riding the `<text>` element, `startOffset="50%"`, a hanging baseline, and no
template whitespace inside the `textPath` — surrounding whitespace offsets
the anchor toward the source).

**Reason.** The user asked for a reusable, dumb viewer in the UI library with
stories per shape. The lib's rules make that split mechanical: components are
dumb (`input()`/`model()`/`output()` only, no services with side effects),
the purity script already forbids app imports in the lib, and every component
ships a story. The seam the code already drew is the seam that moves: the SVG
is one subtree, and the shell's DOM (`#screenshot-container`, the controls)
wraps it. Keeping the toggle in the shell is what makes the canvas honest:
LDG-17's "one selected concept, the same click clears it" is page behaviour
(the drawer route follows it), and a canvas that also cleared its own input
would fight its caller. `svgElement()` instead of a `save()` method keeps the
save's dependencies (Keycloak, config, html2canvas) on the app side, where
they already are.

**Alternatives.** (1) A directive set (`[aureliusNode]`, `[aureliusEdge]`)
over caller-written SVG templates. It loses. The caller re-implements the
draw order, bounds, and marker defs to use it, which is the whole port.
(2) The canvas owning selection with a `model()` two-way input. It loses.
The page's selection is a route (DD-415), and two-way state across the
package line lets the canvas write the URL the shell owns. (3) Keep the
viewer component's name in the lib and move the shell away. It loses. The
e2e suite pins `aurelius-atlas-webapp-lineage-viewer`, and the lib selector
rule asks for `aurelius-atlas-ui-<name>`. (4) Copy the archimate tables into
the webapp too, so no package crosses. It loses. The tables are the canvas's
own data, the drawer's two copies already ride the DD-418 drift-pin pattern,
and a fourth copy with no consumer is dead data.

**Consequences.** The lib test target runs the drawing specs (289 tests), and
the webapp suite drops to 542. The two archimate drift pins stay where their
components live: the canvas's spec pins the lib copy, and the webapp's two
drawer specs keep pinning theirs. `parse-ar3.spec.ts`, `lineage-state`, and
the drawer tabs need no edit, because the re-exports hold the old import
paths. The stories are the first place a reviewer sees the archimate
language without a seeded backend. The d3 zoom rides the canvas, so a caller
that only shows a picture gets pan/zoom for free, and the shell's reset
button is one forwarded call. DD-418's builder limit is unchanged: the
canvas's literal fill copy moves with it, pinned by its own spec.
