# Design decisions: 7.22d — Lineage diagram: the toolbar, the PNG, and the page entries

> **Purpose:** the `DD-NNN` entries of this increment, written before the code and
> updated while it changes. Read-only history: every entry ever made also lives in
> [`docs/architecture/conversion/design-log.md`](../../../../docs/architecture/conversion/design-log.md),
> which is the archive (an entry lives in exactly these two places, and the archive
> is never edited — DD-001). New entries are numbered consecutively across the
> repository: check the archive's topmost number and the sibling `specs/*/design.md`
> files for the largest `DD-NNN` in use before taking the next.

| Id      | Title                                                          |
| ------- | -------------------------------------------------------------- |
| DD-397. | The toolbar rides the diagram state, not a shared component    |
| DD-398. | PNG metadata reads the runtime config and the session          |
| DD-399. | The save-all-views ZIP stays out                               |
| DD-400. | The lineage fetch state is a page signal, not the box's secret |

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
