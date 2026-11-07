# Design decisions: 7.22d — Lineage diagram: the toolbar, the PNG, and the page entries

> **Purpose:** the `DD-NNN` entries of this increment, written before the code and
> updated while it changes. Read-only history: every entry ever made also lives in
> [`docs/architecture/conversion/design-log.md`](../../../../docs/architecture/conversion/design-log.md),
> which is the archive (an entry lives in exactly these two places, and the archive
> is never edited — DD-001). New entries are numbered consecutively across the
> repository: check the archive's topmost number and the sibling `specs/*/design.md`
> files for the largest `DD-NNN` in use before taking the next.

| Id      | Title                                                                           |
| ------- | ------------------------------------------------------------------------------- |
| DD-397. | The toolbar rides the diagram state, not a shared component                     |
| DD-398. | PNG metadata reads the runtime config and the session                           |
| DD-399. | The save-all-views ZIP stays out                                                |
| DD-400. | The lineage fetch state is a page signal, not the box's secret                  |
| DD-402. | The drawer's tab strip is full width                                            |
| DD-403. | Dismissing the quickview deselects the diagram                                  |
| DD-404. | The relation rows name their source and target (row shape superseded by DD-411) |
| DD-405. | The Selection tab carries the search card                                       |
| DD-406. | The Browse tab regains the organization tree as a nested list                   |
| DD-407. | The save captures the view at the reader's zoom                                 |
| DD-408. | The diagram's text inherits the app's brand font                                |
| DD-409. | Each connection gains a wide transparent hit path                               |

## Decisions

### DD-397. The toolbar rides the diagram state, not a shared component

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision:**
LDG-27's toolbar lives inside the lineage viewer component, rendered only in
the diagram state, with `title` tooltips; the control column is markup in the
viewer's template, not a reusable toolbar component.

**Reason:**
modelview2's toolbar is one template fragment bound to that component's state
(fullscreen flag, save-in-progress flag, the viewer's own service calls). A
shared "icon toolbar" abstraction has exactly two users in the webapp (this
box and nothing else yet) and would have to accept four callbacks and two
flags to stay generic (DD-388's "port the parts this page needs" again).
`title` is the webapp's tooltip idiom (WBP-02's lean posture; the legacy's
`models4insight-tooltip` is not ported).

**Alternatives considered:**

- A shared `UiToolbarComponent` in `libs/angular/aurelius-atlas-ui`:
  rejected — the same "build it when a second page needs it" rule as DD-397's
  predecessor DD-115 applies.

**Consequences:**
the fullscreen class, the save flag, and the tooltips all stay local to the
viewer; a future repository-model page wanting the same chrome copies or
extracts then, with a second example in hand.

### DD-398. PNG metadata reads the runtime config and the session

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision:**
LDG-31's `Software` field composes `Aurelius Atlas/${appName}/${appVersion}`
from the runtime `/config.json` values (LDG-07's shape, SHC-02/SHC-03), and
`Author` reads the signed-in user's email from the session service when the
id token carries it; the legacy's `git-version.json` build artifact and its
repository project/branch fields collapse to the constants the spec names.

**Reason:**
the legacy bakes `git-version.json` at build time and reads the repository
coordinates from a model-management service that exists only on the
repository-models page; the lineage page itself never had a project or branch,
which is why its `Source` was always `Generated model`. The webapp already
ships the name and version at runtime (DD-85's config, checked by
`test__webapp_image.py`) and its session service already reads id-token claims
(governance-responsibilities reads them the same way).

**Alternatives considered:**

- Baking a build stamp into the bundle: rejected — duplicates what
  `/config.json` carries; the config is the documented single source (SHL-10's
  channel).
- Leaving `Author` out entirely: rejected — the claim usually exists, the skip
  covers when it does not, and the legacy's footer parity (7.21a, DD-182)
  shows the id-token read is idiomatic here.

**Consequences:**
`Software` reads identically in dev and prod (the config is served per
environment); the chunk writer must skip empty fields (LDG-31 pins it, and the
legacy's `if (!value) continue` matches).

### DD-399. The save-all-views ZIP stays out

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision:**
The batch ZIP (`saveAllViewsAsImages`, the `window[...]` debug hook, the JSZip
dependency) is not ported.

**Reason:**
it is a developer-console affordance that renders every view of a repository
model and zips the PNGs; the lineage page has exactly one view, named
"Lineage", so the batch and the single save are the same call. The JSZip
dependency and a `window` global both run against WBP-02's lean-deps /
no-global-state posture for no user-visible gain.

**Alternatives considered:**

- Porting the hook behind a dev flag: rejected — it would render offscreen
  copies of the diagram, a legacy memory leak (`modelview2.destroy` exists
  because of it) with no feature behind it here.

**Consequences:**
LDG-30's single-save flow is the whole save surface; a future repository-model
page (no such page is planned in this conversion) would revisit the batch with
a purpose.

### DD-400. The lineage fetch state is a page signal, not the box's secret

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision:**
LDG-32's stat ("Available"/"Unavailable", blank while pending) reads the fetch
state from a page-level signal that owns the lineage call, rather than the box
re-exposing its internal state. The box and the section config consume the same
signal.

**Reason:**
this is DET-23/DET-29's established rule verbatim — each detail page's component
owns one fetch state and the section config's stat functions read it — and the
legacy matches it: the dataset page (not `app-lineage-model`) polls
`lineageModelStatus$` onto `datasetDisplayService`, and the stats template
binds the page's state, not the component's. The nav link's placement already
comes from the section config (DD-383), so the stat must be readable there
without mounting the box.

**Alternatives considered:**

- The box publishing state through a service or `Output`: rejected — DET-23's
  rejected alternative again; the page-level signal already exists as the
  place the fetch lives.
- Stat always "Available" once mounted: rejected — wrong while pending, and
  the legacy's blank-while-loading is the pinned shape.

**Consequences:**
7.22b's box moves its fetch into a signal the page creates (a small refactor in
this slice's first step); the section config's `stats: s => lineageState(s)`
reads it; the LDG-10 states stay the box's business — the stat only maps the
state to a word.

### DD-402. The drawer's tab strip is full width

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision.** The quickview's tab strip gains Bulma's `is-fullwidth` class:
each tab cell grows to an equal share of the drawer's width and its label
centers in the cell (LDG-19).

**Reason.** The reader asked for wide, centered tabs. The strip sat
left-packed, so the four labels huddled at the drawer's left edge above a
400 px body. Bulma's class is the documented idiom for exactly this shape
(`li { flex-grow: 1 }`), and the anchors already center their text by default.

**Alternatives.** Center the strip with `justify-content: center` on the list.
It keeps the tabs narrow but floats them mid-air with ragged edges — the
tab-row border then ends where the last label ends. Second, a custom grid. It
loses: Bulma already ships the rule.

**Consequences.** When a fifth tab ever appears (a governance addon, 7.8), the
cells shrink equally instead of overflowing the strip.

### DD-403. Dismissing the quickview deselects the diagram

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision.** Every closing path of the drawer — the scrim, the close button,
Escape, or a view choice — clears the shared selection signal, so the diagram
loses its selected paint when its panel goes away (LDG-25). A second effect in
the model browser watches `active` and clears the selection when the drawer
closes; the existing selection effect then only restores the tab.

**Reason.** The reader reported the bug from the legacy: close the panel, and
the box stays painted in the selection color with no way to see what it was.
The legacy has the same flaw — its close hides the panel but never
deselects — so this is a deliberate break, not a port miss. The panel and the
diagram read one signal (DD-390's seam), so the clear costs one effect and the
two effects settle on one state.

**Alternatives.** Keep the legacy's rule and paint nothing. It loses: the
reader's complaint is that the paint lies about what is open. Second, clear
only on the scrim. It loses: the three dismissal paths would disagree with
each other.

**Consequences.** The e2e scenarios that pinned "close keeps the selection"
flip (LDG-25). The diagram's own clear paths (a second click on the node) are
unchanged.

### DD-404. The relation rows name their source and target

- **Status:** Superseded by DD-411 (the ends stay; the one-line arrow row
  becomes the legacy's three-line row — 7.22c's design)
- **Increment:** 7.22d
- **Date:** 2026-11-07

> Superseded: the parity round found the legacy's relationship row is a
> three-line shape (ends with icons, the middle em line) — DD-411 keeps the
> ends (this entry's reader ask) in that shape.

**Decision.** A relation row in the Model tab shows its ends in the Name cell:
`source → target`, read from the model's elements by id (LDG-23). The keyword
filter matches the two end names too. Relations without a resolvable end show
the empty string, as before.

**Reason.** The reader reported it: the legacy's relation rows show the
relation's own name, which for a lineage document is always "Data Lineage" —
the table's relation half is unreadable because every row says the same thing.
The ends are the fact the reader wants ("NL3-PLANT-001 → nl3-load-job"), and
the document already carries them on each relation. The legacy hides them one
click deeper (the Selection tab's referenced-concepts table).

**Alternatives.** Show the relation name and append the ends in a second
column. It loses: the tables are sortable two-column shapes and a third column
breaks the header pair. Second, port the legacy's rows unchanged. It loses the
feature the reader asked for.

**Consequences.** `LineageEntity` gains `sourceName`/`targetName` fields (empty
for the other kinds), the parse-to-rows step gains one end-name lookup, and the
tests' fixtures carry the two new fields.

### DD-405. The Selection tab carries the search card

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision.** When the selected concept is an element, the Selection tab shows
the results screen's search card (`aurelius-atlas-ui-entity-card`: the entity's
name, the type badge, no icon) above the fields. The card's title navigates to
`/search/details/<guid>` — the entity's own details page. Relations and views
get no card (LDG-20).

**Reason.** The reader asked for the convenient jump the legacy's search card
gave, and the card is already the webapp's shape for "this entity, open it":
the results screen and the browse landing both use it. The lineage concept's id
is the Atlas guid itself (DV-68's chain writes it), so the card's guid is the
real route, not a lookup. A relation or a view has no details page, so the
card's condition is the element kind.

**Alternatives.** A link built from `m4i_original_id` in the properties table,
as the legacy's quickview deep-links. It loses: the guid is already the id
here, and a raw link in a key/value table is the least findable place on the
panel. Second, the whole card with icon. It loses: the drawer is 400 px wide
and the type text already repeats a row below.

**Consequences.** The panel's component imports the shared card and the
Router. The card fires a real route, so the details page's own loading phase
unmounts the drawer — no stale panel survives the jump.

### DD-406. The Browse tab regains the organization tree as a nested list

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision.** The Browse tab draws the model's `ar3_organizations` as a nested
list under the view dropdown: folder rows with a chevron fold and unfold their
children, concept leaves select their concept on a click, and the selected
concept's leaf is marked. The parse gains the organizations tree (LDG-23).
Supersedes DD-395.

**Reason.** The reader asked for the legacy's tree as the place where future
diagrams and views will hang — a flat dropdown cannot grow a hierarchy. DD-395
dropped the tree because the shipped document's folders are a constant
("Other", "Relations", "Views"), but the cost it feared (a `MatTree`-class
component plus a path index) was the overestimate: a recursive `@for` over the
parsed children is the whole component, and the parse is fifteen lines.

**Alternatives.** Keep DD-395's dropdown only. It loses the extension point
the reader named. Second, port `MatTree`. It loses: WBP-02's lean-deps posture
— the tree needs no virtual scrolling at document size, and Bulma has no tree.

**Consequences.** DD-395 moves to Superseded. The unlabeled root container
renders no row, so its folders sit at the top level. A collapsed folder keeps
its own row (the reader must be able to reopen it) and hides only its
children. The e2e scenario gains the three folder names.

### DD-407. The save captures the view at the reader's zoom

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision.** The save-as-image flow stops touching the d3 zoom transform. It
clones the live `<svg>` — the clone carries the current transform, so the PNG
shows exactly the zoom and position on the screen — and draws the clone into
the canvas at the container's measured size (LDG-29/LDG-30). The legacy's
zoom-reset-then-restore is dropped.

**Reason.** The reader reported the jump: the legacy resets the view to
identity to render, then restores, and the two transitions visibly flicker the
diagram while the button spins. The reset was there because the legacy
re-serializes the zoom group with a default transform. Here the serializer
already copies the live transform attribute, so the capture needs no
round-trip, and the restore raced any zoom event the reader fired during the
render.

**Alternatives.** Keep the legacy's order. It loses the reader's complaint and
the race. Second, render at identity and crop. It loses: the whole point of
the save is "what I am looking like right now."

**Consequences.** The viewer deletes its `applyTransform()` helper and the
save service loses its `saveAroundZoomReset` wrapper. The unit test pins the
capture at a non-identity transform: the d3 handler's transform is unchanged
after a save, and the canvas size is the container's box.

### DD-408. The diagram's text inherits the app's brand font

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision.** The lineage `<svg>` drops its hard-coded `"Segoe UI"` font stack
and inherits the app's brand family (`--bulma-family-primary`, the webapp
font) like every other element. The 12 px node/edge font sizes stay.

**Reason.** The reader noticed the diagram renders in a different face than
the rest of the page. The legacy's scss pins `"Segoe UI"` on its svg, which is
an off-brand default on every platform the webapp ships to — on this Linux
box it fell back to a serif-leaning default. Inheriting is one deleted
declaration and makes the diagram follow the theme for free.

**Alternatives.** Port the legacy's stack. It loses the brand and nothing. A
third: pin the font on the labels only. It loses: inheritance covers the
labels and future text the same way.

**Consequences.** The viewer's unit spec pins the absence of a `font-family`
declaration on `.lineage-svg` so the pin cannot silently return.

### DD-409. Each connection gains a wide transparent hit path

- **Status:** Proposed
- **Increment:** 7.22d
- **Date:** 2026-11-07

**Decision.** Under the visible 1 px edge, each connection draws an invisible
second path with the same geometry: a 10 px transparent stroke with
`pointer-events: stroke`. The click target is the group, so a click anywhere
within 5 px of the edge selects the relation (LDG-17).

**Reason.** The reader reported the edges unclickable. The visible stroke is
1 px wide, and a pointer must land inside it — on a diagonal curve that is a
sub-pixel aim. The legacy carries the same flaw (its handler sits on the thin
path), so this is a deliberate fix, not a port miss. The wide twin is the
documented SVG idiom for thin-line hit testing.

**Alternatives.** Grow the visible stroke: rejected — it would change the
diagram's pixels. A transparent `<rect>` per edge: rejected — a curve has no
cheap bounding shape, and the rect would swallow clicks meant for nodes.

**Consequences.** The e2e scenario clicks an edge through the hit path. A
straight horizontal edge has a zero-height bounding box, so the e2e clicks it
with `force: true` — the real mouse event still hit-tests the stroke.
