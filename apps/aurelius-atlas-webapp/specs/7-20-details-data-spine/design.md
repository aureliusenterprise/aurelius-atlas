# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-317. The breadcrumb trail is app state with no source until an endpoint exists

- **Status:** Proposed
- **Increment:** 7.20
- **Date:** 2026-11-03

**Decision.** The details screen's breadcrumb trail renders from an app-side
store — a signal holder (`DetailsBreadcrumbState`) that the details route
component provides, typed as the ui library's `Breadcrumb` list (DET-12). In
7.20 nothing fills the store, so the trail renders empty on every visit,
entered and direct. The store is the seam: a later increment fills it from an
API, and the screen's binding does not change. The screen derives no crumbs
from the entity read.

**Reason.** The legacy trail never read the entity. Its
`BreadCrumbsService` read the `breadcrumbguid`/`breadcrumbname`/
`breadcrumbtype` arrays off the App Search document (the legacy source:
`.scratch/aurelius/apps/atlas/src/app/search/components/bread-crumbs/`), and a
Flink job built those arrays at index time by concatenating the parent
document's trail (the legacy source:
`.scratch/aurelius/libs/m4i-flink-tasks/m4i_flink_tasks/operations/
synchronize_app_search/event_handlers/entity_created/entity_created.py`).
Aurelius Atlas has no App Search index (DD-140 refused the stack, ADR 054
consolidated the API) and no endpoint that computes a parent chain, so the
trail has no honest data source today. Deriving crumbs from the entity's
relationship ends would invent an m4i parent-chain mapping on a server that
ships the Apache Atlas model types — the speculative build DD-140 refuses. The
alternative legacy behaviour, a search lookup by guid to find the document
(`ElementSearchService`), is the same refused stack one call deeper. The user
set the direction on 2026-11-03: "wire up a frontend service to manage the
breadcrumb state that we can wire into the API later. The state can remain
empty for now."

**Alternatives.** (a) A client-side walk of the entity's
`relationshipAttributes` (refused — the parent-chain attribute names are m4i
type vocabulary the server does not ship, so the walk answers nothing or
wrong). (b) A new server endpoint that computes the chain (deferred — no Java
Atlas twin to port, so it enters as its own increment and decision; the
entity/relationship reads it would ride are live). (c) Delete the trail from
the screen until a source exists (refused — 7.6 shipped it under contract
(DET-01, DET-06), the ui component and its routing wiring are real, and the
empty trail is the same shape as the legacy component's own guard when no
document existed).

**Consequences.** The screen keeps DET-01's anatomy and DET-06's crumb routing
under test (proven at the component boundary, the 7.6 way, since the store
answers empty). The store is a thin seam: one provider, a signal, a reader, a
clear — no fetch, no logic to outlive the API join. The future endpoint is a
server increment with its own spec, and filling the store is one call in the
details route.

### DD-318. The details read drives loading, alerts, and the empty state — not a task strip

- **Status:** Proposed
- **Increment:** 7.20
- **Date:** 2026-11-03

**Decision.** The entity fetch lives in the screen's store, not in a route
resolver: a guid-keyed read (the latest guid wins, a superseded answer is
dropped, DET-08) with three states — in flight shows a localized loading line
(`@@search.services.entityDetails.retrieve`), a failed read adds an error
alert to the alerts drawer (7.15, the DD-214 failure idiom the search slice
already uses), and a 404 leaves the DET-02 empty state (the fallback title,
zero rows). The legacy stale-guard (`latestEntityId`) ports as the guid key.

**Reason.** The legacy screen showed reads on a task-manager strip: a busy
overlay driven by the `@ManagedTask` decorator
(`.scratch/aurelius/apps/atlas/src/app/search/services/entity-details/
entity-details.service.ts`). That strip never landed in this rewrite (7.11
chrome, 7.15 alerts superseded it, DD-214's failure matrix). This app already
has the two halves this read needs: the alerts drawer captures failed calls
(the `SearchState` error path is the pattern), and the skeleton already owns
a loading slot vocabulary the bridge carries. Keeping the state in the screen
follows WBP-03 (the screen owns state) and DD-186's route contract (the URL
is the whole address); the resolver's legacy body only clears an API cache
this client does not have, so a resolver would add a navigation-blocking hop
for no behaviour.

**Alternatives.** (a) A route `resolveFn` that awaits the entity before
rendering (refused — it blocks the route, and its failure path lands in the
router, far from the alerts idiom; the legacy resolver proved unnecessary
work: it resolves the id it was given). (b) A silent empty state on failure
(refused — DD-214 exists precisely to make frontend failure paths visible,
and a dead-looking screen on a 403 or 5xx is the failure UX that rule bans).
(c) NgRx or a service store outside the feature folder (refused — the
`SearchState` precedent: a feature-folder signal store, provided by the
layout or route component, destroyed with it).

**Consequences.** DET-13's three states are Vitest-visible (the loading line,
the alert, the empty fallback) and the failure path joins 7.19's matrix with
no new machinery. The alert text is the retrieve key the bridge already
carries in both locales, so 7.20 adds no catalogue strings. A future details
store (audit cards, classification writes, 7.9) grows this screen store
rather than a second one.

### DD-319. The brand re-emits the Bulma 0.9.4 helpers Bulma 1 dropped or renamed

- **Status:** Proposed
- **Increment:** 7.20
- **Date:** 2026-11-03

**Decision.** The brand library (`libs/styles/aurelius-atlas-brand`) carries
three rules Bulma 1.0.4 no longer ships, beside the 0.9.4 ramp it already
re-emits (DD-151): `.heading` (11px, uppercase, 1px tracking, 5px below, text
ink), `.is-paddingless` (`padding: 0 !important`), and `.is-marginless`
(`margin: 0 !important`). Apps and the ui library keep the 0.9.4 class names.

**Reason.** The legacy pages were built on Bulma 0.9.4, and the ported
templates kept its class names. Bulma 1 deleted the `.heading` element and
dropped the `is-` prefix from the spacing helpers (its CSS carries only
`.paddingless`/`.marginless`, and no `.heading`). The gap surfaced in the
7.20 visual comparison against the live demo: the details count bar rendered
in body text (16px plain, the demo measures 11px uppercase), and the details
drop-up's circular toggle (a `box is-paddingless`) kept its 1.25rem padding
and measured 100px against the demo's 60px. Measured 2026-11-03 against the
demo's compiled stylesheet.

**Alternatives.** (a) Rename the classes at each call site to the Bulma 1
spellings (refused — the ported templates keep the legacy names as the parity
reference, and `.heading` has no Bulma 1 successor to rename to). (b) Style
the two components locally (refused — `.heading` and the helpers are global
vocabulary, DD-151 already put the 0.9.4 ramp in the brand, and the ui
library's `section-stats` renders the same `p.heading`).

**Consequences.** Every surface that uses the three classes lands on the
legacy look, including the ui library's `section-stats` bar. The brand grows
one small compat tail; future legacy-visual gaps join it there rather than in
app stylesheets. The demo's `.heading` sets no font-weight, so none is
pinned.

### DD-320. The description box falls back to `description` on Atlas model types

- **Status:** Proposed
- **Increment:** 7.20
- **Date:** 2026-11-03

**Decision.** The description box shows `attributes.definition` when it is a
string, else `attributes.description` when it is a string, else nothing
(DET-10). The attribute the box shows earns no properties row: the screen
passes that key to `detailProperties` and the filter drops it, beside the
blacklist (DET-11).

**Reason.** The legacy `DescriptionComponent` reads `definition` because the
legacy entity types are the m4i governance types, which carry their text
there. This server ships the Apache Atlas model types (the 7.6 deferral),
whose description attribute is `description`. Read verbatim, the legacy rule
leaves the box empty for every entity this product holds: the visual
comparison against the live demo showed a seeded entity whose description sat
in the properties table while the box stayed empty. The legacy table drops
`definition` through the blacklist, for the same reason this record drops the
shown key: the text appears once on the screen. The user's review on
2026-11-03 reported the empty box.

**Alternatives.** (a) Keep the box `definition`-only and let `description`
ride the table (refused — the box is the screen's named section, and it stays
dead on every type the server answers). (b) Show the text in both places
(refused — the legacy blacklist exists to keep each attribute on the screen
once, and a duplicated paragraph reads as a defect). (c) Blacklist
`description` in the ported set (refused — the port stays verbatim, cited as
the legacy set; the drop is this product's rule and rides its own argument).

**Consequences.** DET-10 and DET-14 carry the fallback and the zero-row count
for the seeded `description`. The visual gap the review reported (an empty
Description box beside a one-row table) closes. When a type-specific layout
lands (the deferred dispatch), it picks its own attribute the same way,
through this one seam.

### DD-321. The description renders as markdown through marked, not ngx-markdown

- **Status:** Proposed
- **Increment:** 7.20
- **Date:** 2026-11-03

**Decision.** The ui library gains a `Markdown` component (selector
`aurelius-atlas-ui-markdown`, UIC line): it takes the text as a signal input
and renders it with the `marked` parser, its own per-component `Marked`
instance carrying the legacy Bulma renderer mappings (headings onto the title
ramp, blockquotes onto the Bulma message, tables onto the striped table,
images onto the Bulma figure). The HTML reaches the DOM through an
`[innerHTML]` binding, which Angular sanitizes. The description box renders
the entity's description through it (DET-10, amended), and an empty
description shows the legacy placeholder line — `search.components.description.notAvailable`,
italic and centered, the legacy `DescriptionComponent`'s `noDescription` template
(its `showPlaceholder` defaults on).

**Reason.** The legacy renders descriptions as markdown
(`.scratch/aurelius/libs/components/src/lib/markdown/`), and entity text in
this product is plain-markdown prose; the review asked for the same on
2026-11-03. The legacy component is `ngx-markdown`, and its Aurelius wrapper
registers its four Bulma renderers on the shared `MarkdownService` singleton
from the component constructor: any other consumer of that service silently
inherits the mappings, and the last component constructed wins. That is the
defect worth fixing on the way in. `marked` is the parser `ngx-markdown`
wraps; taking it directly drops the wrapper (and its optional peers — katex,
mermaid, prismjs, clipboard) and the global state, at one small dependency.
`marked` does not sanitize, so the sanitizer is the contract: Angular's HTML
context strips raw markup and neutralizes `javascript:` URLs (the pin in the
component spec). The webapp purity gate's ban on raw-HTML injection is about
`bypassSecurityTrust*` and `dangerouslySetInnerHTML`-style escapes; an
ordinary `[innerHTML]` binding is the sanitized path and carries no trust
call.

**Alternatives.** (a) Depend on `ngx-markdown` again (refused — the
component's own defect lives in that library's global `MarkdownService`
shape, its optional peers ride the lockfile, and the four renderer overrides
are all this product ever used). (b) Render descriptions as plain text
(refused — the review asked for markdown; entity descriptions in the wild
carry emphasis, lists, and links). (c) Sanitize with DOMPurify before binding
(deferred — Angular's built-in HTML sanitizer already runs on the binding,
and adding a second sanitizer answers no threat the first misses).

**Consequences.** DET-10 now covers markdown rendering and the placeholder
line; the empty-box assertion in its tests becomes the placeholder pin.
Descriptions render inside Bulma `content`, so typography comes from the
theme. Remote images inside markdown are blocked by the site's CSP
(`img-src 'self' data:`) — a deliberate consequence, recorded here: entity
descriptions carry text, not hosted images. The component is reusable: the
lineage/lineage-bearing screens that later show markdown reach for the same
selector.
