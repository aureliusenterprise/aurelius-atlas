# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-388. The renderer is a ported lineage viewer, not the modelview2 library

- **Status:** Proposed
- **Increment:** 7.22b
- **Date:** 2026-11-07

**Decision.** The webapp gains a purpose-built lineage viewer under
`search/details/lineage/`: the ar3 reader (LDG-11), the lineage shape table
(LDG-13/LDG-14), the connection path maths (LDG-14), the bounds normalisation
(LDG-15), and the zoom directive (LDG-16). The modelview2 library itself is not
ported, and no `libs/angular/` model-viewer package is created.

**Reason.** The details page uses a narrow slice of the library: one view, two
node shapes, one arrow, pan/zoom, selection, and the highlight. The rest of the
library (the browse tree over `organizations`, the fuzzy search, the view tabs,
the colour-by pipeline, the repository-model store) answers to the platform app,
which Aurelius Atlas has no equivalent of. WBP-02 forbids the library's
idioms wholesale (NgModule, `@models4insight/*`, ngx-translate,
state-owning `BehaviorSubject`s), so a copy is impossible, and a full rewrite
in Angular idiom would be several times the slice budget for behaviour no page
renders. A ported viewer is the smallest change that renders the page: roughly
the 900 lines of the ar3 reader, the shapes, and the path maths, versus the
library's 4,200 plus the ten workspace libs it imports.

**Alternatives.** Port the library whole as `libs/angular/modelview`. It loses:
the closure includes `redux`, `utils`, `task-manager`, `metamodel`, and eight
submodules of `components` — a workspace-wide port for one page. Second, embed
the legacy dashboard in an iframe. It loses: the legacy app is not shipped
(ADR 053), and an iframe buys no state sharing with the details page (the
highlight, the future selection panel). Third, a canvas/SVG library rewrite
(d3-hierarchy, elkjs). It loses: the layout already happens server-side
(8.1's graphviz), so the browser maths left is the path builder — one ported
function.

**Consequences.** The viewer lives in the webapp, beside the two layouts that
embed it (LDG-09). If the platform-style explorer ever lands, it starts from
this core and grows the tabs on top; nothing here boxes it in. The quickview
(7.22c) and the toolbar (7.22d) extend this viewer's own signals and methods,
which is why LDG-16 keeps `resetZoom()` and LDG-17 keeps the selection signals
public now.

### DD-389. The ar3 reader parses the lineage subset

- **Status:** Proposed
- **Increment:** 7.22b
- **Date:** 2026-11-07

**Decision.** `parseAr3Model` (LDG-11) reads elements, relations, and one view's
nodes and connections. It ignores `ar3_organizations`, nested `ar3_viewRef`
groups, `ar3_properties`, and `ar3_style` blocks, and it throws on a document
whose `ar3_model` key is missing.

**Reason.** The document the box receives has one producer: 8.2's fixed rule set
(a setting-free constant in `lineage.py`). It emits exactly two concept types,
one relation type, and one view, and 8.2's own scenario fixture
(`scenarios/fixtures/graph.extract.json`, built and verified against the 8.1
extract) shows no organization, no view reference, and no style block in that
output. Parsing fields the producer never emits is code no test can reach —
ADR 049's rule cut the other way. The legacy reader parses them because the same
reader must digest a full repository model in the platform app.

**Alternatives.** Port the legacy reader field-for-field, properties included.
It loses: 7.22c's selection panel will want the properties dict, and that slice
adds it back with its own tests — a field parsed now but unused until 7.22c has
no covering test in this slice. Second, `any`-typed passthrough: hand the raw
JSON to the components and pluck fields at render time. It loses the seam that
makes LDG-11 unit-testable against the fixture without a browser.

**Consequences.** When 7.22c merges the metadata rows into the selection panel,
it extends the reader's types (properties arrive with the panel's tests). The
throw on a malformed document keeps LDG-10's failure state honest: a producer
that changes its contract fails loudly in the reader's test, not silently in the
drawing.

### DD-390. Per-element state rides component signals, not per-node stores

- **Status:** Proposed
- **Increment:** 7.22b
- **Date:** 2026-11-07

**Decision.** The legacy's per-node and per-connection `BasicStore` services
(`ModelviewNodeService`, `ModelviewConnectionService`) become the inputs and
computed signals of the two standalone components. The viewer holds the shared
state (the parsed model, the selected entity/connection, the highlighted guid)
in signals and passes the slices down.

**Reason.** Each legacy store held one component's fields and republished them as
Observables; WBP-02 bars state-owning `BehaviorSubject`s and NgModules, and
signals are the replacement the webapp's rules name. The only genuinely shared
state — the selection (LDG-17) and the highlight (LDG-18) — sits once on the
viewer, where 7.22c's panel can read it. The legacy needed a DI trick (a
component-scoped store per row) because a template context could not annotate a
node; a standalone component with typed inputs needs none.

**Alternatives.** One service-store for the whole view (the legacy
`ModelExplorerService` shape). It loses: the viewer component can own that state
directly, and a service adds an injection seam nothing else consumes. Second,
NgRx or another state library. It loses: nothing in the port needs middleware.

**Consequences.** The zoneless change-detection story stays the webapp's (no
`ChangeDetectorRef` manual pushes; signals mark dirty). The e2e click assertions
(LDG-17) read DOM classes, so the state shape is free to change under them.

### DD-391. Parity fixtures come from the shipped chain, not the legacy app

- **Status:** Proposed
- **Increment:** 7.22b
- **Date:** 2026-11-07

**Decision.** The renderer's fixtures are vendored copies of
`apps/aurelius-atlas-lineage-model/scenarios/fixtures/graph.extract.json` (and
its 8.1 parent), cited in the test file. No model-view JSON from the legacy
snapshot enters the tree, and no running legacy app is consulted.

**Reason.** The legacy renderer had no fixtures of its own worth vendoring: its
spec mocks the parser, and its real models came from the legacy Flask chain,
which Aurelius Atlas does not run. What matters for parity is the contract of
the document (DV-68's passthrough, verified at 8.1/8.2 against Aurelius's own
scenario method), and that verification already exists in this repo — the
fixture is the same bytes the aux chain answers (ADR 052's "expected responses
read from the source and its own tests, each citing where", applied to the
Aurelius product). The visual rules (fills, strokes, the zoom extent) are cited
from legacy source lines in the spec instead, since pixels are pinned by unit
tests per the webapp's e2e rule.

**Alternatives.** Screenshot-diff against a running legacy app. It loses: no
legacy Atlas exists to run (ADR 052 rules out a Java Atlas, and the Aurelius
dashboards need the legacy Flask backend Aurelius Atlas replaced). Second,
hand-authored fixtures. It loses the citation chain that makes them trustworthy.

**Consequences.** A change to 8.1's output contract shows in both suites: 8.2's
scenario (same fixture bytes) and this renderer's parse test (the vendored copy,
diffed against its source by the fixture's header comment). The copy is small
(the two-relation graph), so a refresh is a copy-paste.

### DD-392. A failed fetch renders the legacy's empty message

- **Status:** Proposed
- **Increment:** 7.22b
- **Date:** 2026-11-07

**Decision.** When the LDG-01 call fails (400/401/502), the box shows the same
empty message as the `204` (LDG-10). The box adds no retry button and no error
text.

**Reason.** The legacy does exactly this (`lineage-model.service.ts` catches
anything, including the 204, and deletes the model), and the webapp already owns
a better channel for failures: 7.19's alert path raises drawer alerts from the
shared error chain, where a 502 from the aux API lands without the box's help
(the LM-12 body is descriptive). A second, static error inside the box would
contradict 7.19's posture while adding nothing the drawer does not say. Keeping
the screen equal to the legacy's is also the honest parity choice: the rule says
what the reader sees, and the failure is visible elsewhere by design.

**Alternatives.** Render an error state with a retry button. It loses: no
legacy screen shows one, and 7.19's deferred "retry affordance on the box" note
in 7.22a's DD-386 stands — if that lands, it is a new rule, not this slice.
Second, hide the box on failure. It loses: the reader cannot tell a broken
feature from an entity without lineage.

**Consequences.** The state machine has two visible resting states (empty,
diagram), which the unit tests pin. If product later wants the 401 (a session
gone) to read differently from a 204, that is a new LDG rule with its own DD.

### DD-417. The drawing sits off the top-left corner by default

- **Status:** Proposed
- **Increment:** 7.22b
- **Date:** 2026-11-08

**Decision.** The bounds group (LDG-15) adds a fixed 20px to its
`-minX/-minY` translate (`BOUNDS_INSET`, `lineage-shapes.ts`), so the model's
top-left node starts 20px inside the drawing area instead of flush at its
origin. Amends LDG-15. A deliberate deviation from the legacy, recorded in
this spec's Deviations.

**Reason.** A reader asked for the graph to be "offset slightly from the top
corner by default". The legacy seats the model flush (`ModelviewService`: the
group translates by exactly `-minX/-minY`), which puts the first node's 2px
stroke and its label against the drawing's dashed edge — the corner reads as
cropped rather than placed. 20px matches the control column's own inset (the
legacy's `padding: 10px` doubled by the button row's margin, near enough) and
is small enough to keep the layout's proportions at the 0.5 zoom floor.

**Alternatives.** (1) Zoom-to-fit with padding on load (d3's
`zoom.transform` to a fitted transform). It loses: the fit depends on the
container's measured size, which the units and jsdom cannot pin, it moves the
reader's zoom state before they touched it, and the saved PNG (LDG-29/LDG-30)
captures the fitted transform — a bigger deviation than asked for. (2) CSS
padding on the svg. It loses: the background rect (the legacy's
`#modelview-background`) would no longer cover the padded band, and panning
under the padding exposes it. (3) A one-off transform extra on the zoom
group. It loses: `resetZoom()` restores the zoom group's identity (LDG-16)
and the save serialises it, so the inset would vanish on reset and drift with
the reader's pan; on the bounds group it composes with the zoom and survives
both, as the legacy's own bounds shift does.

**Consequences.** One constant and one subtraction in `boundsTransform()`;
the LDG-15 test's expected literals gain the inset (`translate(20, 20)`,
`translate(-980, -480)`), and a new test pins that the inset rides the bounds
group — pan moves the zoom group, `resetZoom()` clears only the zoom group,
the seating stays. The PNG the save produces gains the same 20px margin the
screen shows, since the clone carries the group. The e2e pins no coordinates,
so nothing downstream moves.
