# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[Design Log's rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision is a new entry
that supersedes the old one.

## Entries

### DD-542. The theme override reaches the platform through a `color-scheme` meta

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** The document head carries `<meta name="color-scheme">`. The pre-render script and
`DarkModeService` keep its content equal to the `data-theme` choice (`light`/`dark`), with
`light dark` for Auto and the app's light default when nothing is stored. The brand sheet sets
`color-scheme: light dark` on `:root` and maps the meta back onto the property through a `:has`
rule for the two explicit values.

**Reason.** Native controls, scrollbars, and the UA canvas key off the CSS `color-scheme`
property, which nothing in the repo set, so dark mode left them light (the audit's only
deterministic finding). The meta is the platform's data model for the override. It alone is a
presentational hint that any author CSS out-ranks, so the mapping rule is required. The
`data-theme` attribute stays the source of truth for the app's own surfaces (DD-156's ramp), so
this governs only the UA-drawn parts.

**Alternatives.** Set `color-scheme` from `data-theme` in CSS alone: it would hardcode `light`
as the root default (SPL-05's default and the no-JS path disagree), and the guide bans a single
scheme as the root declaration. Follow the OS for native UI and ignore the override (leave the
meta always `light dark`): a pinned scheme then paints light controls on a dark page.

**Consequences.** The pre-render gains two lines, so the CSP `script-src` hash moves; CHT-112's
test pins all three nginx copies. The service's attribute writer became one scheme writer for
the attribute and the meta (SPL-15). A meta-less host skips the sync, so stories and the jsdom
unit document need no meta.

### DD-543. The Modal opens as a native `<dialog>` in the top layer

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** The `Modal`'s layer becomes a `<dialog>` that the component opens with
`showModal()` while `active` is set. It keeps Bulma's `.modal is-active` classes, so the layer
geometry, the card anatomy, and the scrim stay Bulma's CSS; the component's SCSS resets the UA
sheet and keeps the UA `::backdrop` transparent (the `.modal-background` div paints the
dimming, as today). Escape arrives as the `cancel` event; the handler prevents the bare close
and routes the card anatomy through `cancelRequested`. An effect records the opener on open and
restores focus to it when the layer goes away. The public API is unchanged.

**Reason.** The Bulma `div` layer is hand-rolled: nothing focuses on open, Tab walks out of the
open modal, the page behind stays reachable, and Escape works only when focus sits inside
(UIC-40). The native dialog gives the top layer, the focus confinement, the inert background,
and the platform dismissal for free. The library's own `Drawer` already rides a `<dialog>` with
the UA reset (DD-162), and a11y linters flag a nameless open `dialog`, which the named one
fixes. The guide's dismissal and scroll rules assume the native element.

**Alternatives.** Hand-wire focus trapping, inert, and Escape on the Bulma layer: re-implements
what the platform ships, the pattern the audit names as the legacy one. CDK overlay: a
dependency the purity standing rejects (DD-157). Move the Drawer's `open`-attribute path over
too: DD-162 chose it for the slide-out animation, and the modal has no such animation.

**Consequences.** jsdom has no `showModal`, so the component guards the call and falls back to
the `open` attribute; the focus rows run only where the platform offers it. The `cancel` event
replaces the hand-rolled Escape listener, and the card anatomy loses its `role="dialog"` (the
element carries the role). The webapp's `.modal` selectors survive because the classes stay. A
browser without the top layer keeps the old behaviour (a plain Bulma layer).

### DD-544. The overlay parts contain their scroll instead of the body

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** Four parts gain `overscroll-behavior: contain`: the modal dialog, its
`::backdrop` (also `overflow: hidden`, plus a transparent background), the drawer scrim (also
`overflow: hidden`), and the drawer body. No rule touches `overflow` or `position` on `<html>`
or `<body>`.

**Reason.** A wheel over an open overlay's scrim, or a gesture inside it, scrolls the page
behind (UIC-41). The CSS Overscroll Behavior spec makes `contain` work on a non-scrollable
container once that container has an `overflow` value, and the guide names the `overflow:
hidden` body lock as the legacy workaround: it removes the scrollbar (a layout shift), can jump
the page scroll, and breaks sticky elements.

**Alternatives.** The body lock: banned by the guide, and the navbar's fixed positioning is the
sticky case it breaks. A wheel listener with `preventDefault`: re-implements containment in JS,
misses touch, and fights the drawer's own scrolling body.

**Consequences.** Support for containment on non-scrollable containers is new (Chrome/Edge
144, Firefox 150; not Safari), so the fix is a progressive enhancement: browsers without the
rule keep the chain only for the no-overflow case, and the focus/inert work of DD-543 stands on
its own. The rule must not be moved to a `:modal` selector: the no-top-layer fallback (jsdom,
old browsers) renders the layer through the `open` attribute, and containment applies to that
too.

### DD-545. The drawer keeps `aria-modal` and marks the background inert

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** The `Drawer` keeps its `aria-modal="true"` claim and its non-modal `open` attribute
(DD-162 stands). The component makes the claim true: while the drawer is open, an effect walks from
the drawer element to `<body>` and marks every sibling at each level `inert`; the cleanup removes
every mark (MODAL-TRAP-001). A Tab handler wraps focus inside the panel, and the exiting layer gains
`inert` while it slides out (MODAL-CLOSE-001).

**Reason.** The accessibility audit flagged the mismatch: `aria-modal="true"` tells a screen reader
that everything outside is unreachable, but nothing enforced it, so Tab walked straight out of the
open drawer into the page behind. The review choice was between dropping the claim and honouring
it. Honouring it keeps the announced behaviour (a modal drawer) that the product intends, and the
`inert` attribute is the platform's own way to make a subtree unreachable, with no focus bookkeeping
in JS. `showModal()` stays out because DD-162 chose the `open` attribute for the slide-out
animation, and the top layer removes the scrim's click-through and the animation's stacking
context.

**Alternatives.** Drop `aria-modal` and leave the drawer non-modal: honest, but it announces a
modeless panel while the product blocks the page behind it in practice. Hand-rolled focus trapping
without `inert`: the audit's legacy pattern, and it misses click and cursor access, which `inert`
closes too. `showModal()`: superseded by DD-162 for the animation, restated here for the record.

**Consequences.** The walk must skip the drawer's own ancestor chain, so nested mounts (the
webapp's aux outlet wraps the drawer) still mark the whole shell; the spec pins that the drawer
chain never gains `inert`. Because the drawer's layer sits inside the outlet, the walk marks the
header, the footer, and the routed band. The webapp tests that mount a drawer must not hold focus
outside it while open. The exit-animation window keeps a visible panel that no longer takes focus
or clicks.

### DD-546. The document title follows the route through `AtlasTitleStrategy`

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** The app provides `AtlasTitleStrategy` for `TitleStrategy` (DD-546). It reads the
deepest route's `data.title` and sets `<page title> - <app name>` through the `Title` service, or
the bare app name with no title. It walks the primary outlet only, so the drawer's aux routes never
rename the tab. The details screen additionally sets the entity name into the title once the entity
answers (TITLE-001).

**Reason.** Nothing in the app ever set `document.title`: every route left the tab labelled with
the static `index.html` text (WCAG 2.4.2). The router's `TitleStrategy` is the platform hook for
this, and this Angular version declares `updateTitle` abstract, so the strategy implements it
directly instead of relying on the base `title` transform. Keying the walk to the primary outlet
keeps the alerts drawer and the editor drawer from overwriting the page's name while they ride the
aux outlets.

**Alternatives.** Set the title from each component's constructor: repeats the app-name concat in
eight components and fights the router on back navigation. `title` on the route definitions alone:
the built-in strategy uses the last title and skips the suffix, and the details screen needs a
data-loaded rename the route statics cannot do.

**Consequences.** Route data carries three `$localize` titles (browse, results, details), which
join the `shell.title.*` keys in the vendored dictionaries and both catalogues (the completeness
gate, SHL-08). The details effect runs once per entity load, so a purge or delete leaves the last
name until the next navigation.

### DD-547. The lineage graph gets a roving-stop keyboard model

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** The `ModelViewer` exposes its `<svg>` as `role="group"`, `tabindex="0"`, named
`<view> lineage model` through a `canvasLabel` input (SVG-001). On the focused root, Arrow keys
pan and +/- zoom through the same d3-zoom the mouse uses. The nodes form one roving tab stop: the
active node is `role="button"` named by its drawn label, Arrow keys move to the nearest neighbour
by model coordinates, and Enter/Space emit the node-click action (KEY-GRAPHIC-CLICK-NO-KEYBOARD).
Node keydowns stop propagation so the root does not also pan. Connections stay pointer-only.

**Reason.** This was the audit's only critical finding: every node acts on a click event only, so
a keyboard user cannot open any entity from the graph (WCAG 2.1.1). A graph is the case the ARIA
authoring practices handle with a composite widget rather than one tab stop per node: one stop on
the canvas, arrow keys inside it. Nearest-neighbour by model coordinates keeps arrow order
predictable because the model already lays the graph out left-to-right. One stop, not one per
node, because a lineage graph can hold hundreds of nodes and a tab-per-node walk traps the reader.

**Alternatives.** `tabindex="0"` on every node: hundreds of tab stops per graph. A hidden list
mirror of the graph beside the svg: a second source of truth that drifts. `role="application"`:
the audit bans it outside true application modes, and the group plus arrow keys pattern needs it
nowhere.

**Consequences.** The nodes are a roving stop, so only one is in the tab order at a time, and the
spec pins the wrap-free nearest-neighbour walk and the Enter/Space action. Connections keep the
pointer-only contract (DD-348's intent, reported not changed): their action is a pan-to, which a
reader can reach through the endpoints. The webapp passes the view name into `canvasLabel`;
Storybook's stories carry their own labels.

### DD-548. The details section header stacks on its own width

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** `DetailsCardSection` hosts itself as a CSS size container
(`container: aurelius-card-section / inline-size`). The stacked control layout, which the media query
ran below a 768px viewport, runs below a 768px container instead, and the level and the control row
gain the `flex-direction: column` the viewport-based Bulma rules do not apply at a wide viewport. The
control row also shrinks into the width that is there (`flex-shrink: 1`, `min-width: 0`, above
Bulma's pinned `.level > .level-right`), so a long title never pushes it out of the box.

**Reason.** Found on the booted dev server: between a 769px viewport and about 830px, a section's
control row (sort pair plus search box, roughly 526px of content) rode out of its card, because
Bulma pins the row to its content and stacks only on the viewport. The cards are much narrower than
the viewport and their titles differ in length, so wrapping the row produced a half-state no design
has: the short-title sections kept the row beside the title while a long-title one wrapped the
search box below it. A container query makes every section on the page jump to the stacked layout at
the same moment, because they share one width. The 768px threshold stays Bulma's own number.

**Alternatives.** Raise the viewport media breakpoint: the mixed layout survives whenever one title
is long, at any viewport. `flex-wrap` alone (the first fix, replaced): stops the overflow but is the
half-state itself. An `@container` on the webapp's page column: the ui-lib then needs the host to
opt in, and a future caller gets the mixed layout by default.

**Consequences.** The section's layout rides its own box, so a details screen rendered in a narrow
drawer or a split view stacks correctly with no host wiring. The container threshold is a component
fact (768px, the width a moderate title needs beside the control pair), noted here because the media
query it replaces named Bulma's breakpoint instead.

### DD-549. Live regions are native output elements

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** The six persistent live regions this increment shipped (LR-001, LR-003, LR-004, LR-005,
TABLE-004, TABLE-005) are `<output>` elements instead of `<p role="status" aria-live="polite">`. The
status role and the polite live region are `<output>`'s implicit semantics, so the attributes are
dropped and the specs select the region by its tag. The spec's `role="status"` wording stands as the
semantic contract: an `<output>` answers to that role.

**Reason.** SonarCloud's rule Web:S6819 (MAJOR, new code on PR 336) flags the explicit role. The ARIA
`status` role maps inconsistently across screen readers on a generic host, while a native `<output>`
carries the same role through the platform's own mapping.

**Alternatives.** Suppress the rule at each site: six suppressions for a change that swaps one tag.
Move each region into its component's template: the regions already are per-component, and the role
attribute was the only finding.

**Consequences.** `<output>` defaults to `display: inline`. The regions sit in the `is-sr-only` clip
pattern, so the box model changes nothing. A reader who looks up a spec rule for a persistent status
region finds the element in the component's own spec.

### DD-550. The hero keeps its create button inside the page

- **Status:** Accepted
- **Increment:** 7.30
- **Date:** 2026-11-13

**Decision.** The hero's controls row carries a `hero-controls` class. One rule in
`search-layout.component.scss` gives that row's `.level-item` elements the room to change size
(`flex-grow: 1`, `flex-shrink: 1`, `min-width: 0`, above Bulma's pinned `.level-item`). The search
field takes the width the column has, and the `+` button keeps its own size.

**Reason.** Found on the booted dev server. From a 769px viewport to about 950px, the hero's title
column and after-title column sit side by side, and the after-title column is narrower than the
search field plus the `+` button. Bulma pins a `.level-item` to its content, and `.is-mobile` keeps
the row on one line at every width, so the row rode out of the hero and the `+` fell off the page.
The same family as DD-548, found the same way.

**Alternatives.** A container query like DD-548's: the hero is a full-width band, so its column
width follows the viewport, and the stacked half-state DD-548 removed has no design here because
`.is-mobile` already commits the row to one line. Dropping `.is-mobile`: below 769px the row would
stack under the title, a change to every phone width to fix a tablet one. A viewport media query:
it fixes the same window, but the class rule needs no breakpoint to remember.

**Consequences.** The field narrows to about 250px at the tightest width, which still shows the
placeholder. The unit spec pins the `hero-controls` hook, not the pixels (repo rule: layout ships
as structure). The live browser check covers 420px to 1280px.
