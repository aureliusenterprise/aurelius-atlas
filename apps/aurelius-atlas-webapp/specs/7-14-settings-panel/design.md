# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-157. The drawer is a new ui-lib component, not a Modal or a dropdown

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The settings panel opens in a new `Drawer` component in
`aurelius-atlas-ui`: a fixed right-side panel with a scrim, styled with custom
SCSS on Bulma tokens, carrying the `Modal`'s dismissal set (`active` as
`model()`, backdrop click, close button, Escape → `dismiss()`).

**Reason.** The user chose a side drawer for the settings panel, and Bulma
1.0.4 ships no drawer — `sass/elements/` has no such layer; the overlay
primitives are modal and navbar-dropdown. A drawer keeps the page content
visible beside the settings (the point of a side panel), which the centred
modal does not. Building it on Bulma tokens (`--bulma-scheme-main`, the text
chain, the border ramp) makes DD-156's dark ink ramp apply to it for free.
The dismissal semantics copy the `Modal` because that component proved the
a11y pattern this repo accepts: the backdrop is the pointer path, Escape on
the dialog is the keyboard path (the S1077 precedent in `modal.component.html`).

**Alternatives.** Reuse `Modal`: centred, occludes the page — the user's
choice ruled it out, and a right-docked modal fights Bulma's centred
`.modal-content`. A Bulma `has-dropdown` under the gear (the navbar idiom
today): cramped for radios, selects and toggles, hover-open (unusable on
touch), and it dismisses on every outside click the panel needs to survive
while a control is used. `@angular/cdk`'s drawer/overlay: a new
third-party dependency the purity gate and the ui-lib's zero-overlay-dependency
standing do not justify for one panel.

**Consequences.** The drawer owns its focus choreography (focus moves to the
panel on open, Escape returns it to the opener) — the `Modal` defers this to
its buttons, the drawer has a focusable form. The component is generic
(`title`, projected content), so the 7.6 filters/detail side panels can reuse
it. Stories carry an OnDark variant like every overlay the lib ships.

### DD-158. The telemetry switch stops exports immediately and starts them on reload

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The telemetry setting is honoured asymmetrically: switching it
**off** calls the OpenTelemetry providers' shutdown (`trace.disable()` + the
meter provider's shutdown) so exports stop within the session; switching it
**on** stores the preference and takes effect on the next reload, and the
panel says so.

**Reason.** The SDK is assembled at bootstrap in `app.config.ts`: the
`NodeTracerProvider`/`MeterProvider` are built in `createAureliusOpenTelemetry`
provider factories and the propagation interceptor is registered with
`withInterceptors` — both are startup-time DI, not swappable at runtime.
Stopping is the one direction the SDK API supports cleanly (`shutdown()`
flushes and closes the exporter); starting needs a provider re-assembly DI
will not do mid-session. An honest one-way switch (off now, on after reload,
stated in the panel) beats a switch that silently does nothing until restart
in both directions.

**Alternatives.** Auto-reload the page on toggle: jars the user out of their
session (lost form state) to start telemetry — the least urgent reason to
reload. A runtime gate via a no-op proxy exporter/provider registered at
bootstrap: the real machinery the SDK hides (span processors, batch
exporters, the interceptor's active-span context) then runs with the toggle
off, which is exactly what "telemetry off" promises not to do. No toggle at
all: the user asked for one, and an off switch for browser telemetry is a
reasonable privacy affordance.

**Consequences.** The stored preference is read by `app.config.ts` before the
providers are built (off at bootstrap = providers are never created — not
even the no-op path). The panel's reload hint is a rule with a test (SPL-11).
A served-app scenario (no OTLP requests after off) lands with the 7.10 e2e
set that serves the app.

### DD-159. The theme choice is applied pre-render; SHM-01's light pin is superseded by a light default

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `data-theme="light"` pin on `index.html`'s root is removed.
A two-line inline script in the head applies the stored theme before the
first paint: the stored value (`light`/`dark`) is written, `auto` (or no
stored key with no value) **removes** the attribute and — because the app's
default must stay light (SHM-01's promise) — the script writes
`data-theme="light"` when nothing is stored. `DarkModeService.initialize()`
reads the same attribute, so the service and the page agree from the first
frame.

**Reason.** `DarkModeService.initialize()` treats the root attribute as the
highest-priority explicit choice; the 7.12 pin therefore outvoted a stored
`dark`/`auto` on every load — the switch could not survive it. The pin can
also not just move to runtime service code: Angular bootstraps after CSS,
so a service effect paints one frame in the wrong scheme (the classic
dark-mode flash). The inline script is the standard pre-render pattern and
keeps SHM-01's user-visible promise exactly — no stored choice ⇒ light under
any OS preference — with the default in the script + the service, not in
static html. 7.12's scope note anticipated the switch ("a later slice flips
the `data-theme` attribute"); this is that slice superseding the mechanism,
not the promise.

**Alternatives.** Keep the pin and let the service overwrite it after
bootstrap: not a flash problem only — `initialize()` returns the pin as the
user's explicit choice, so stored Dark is ignored outright. Drop the light
default and let no-stored-key follow the OS (Bulma's native behaviour):
breaks SHM-01 — the legacy app is light-only and the demo renders light
under a dark OS; the pin's promise was measured, and 7.12's specs assert it.

**Consequences.** SHM-01's row in 7.12 gains a supersede note (the promise
stands, the mechanism moves). The service's `updateDataThemeAttribute` must
**remove** the attribute for `auto` rather than write `data-theme=""` — the
empty attribute does not match Bulma's `:root:not([data-theme])` OS path, so
Auto would never follow the OS. The 7.12 spec's html-attribute assertions
keep passing because the script writes `light` when nothing is stored.

### DD-160. Settings are a facade over one owner service per category

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** `SettingsService` (webapp) is a thin facade: it exposes each
setting's signal and setter and delegates to exactly one **owner** service
per category — theme → `DarkModeService` (the ui-lib's existing owner),
language → `LocaleNavigationService`, time zone → `TimezoneService`, page
size → `PageSizeService`, telemetry → `TelemetryService`. Each persistence-
backed owner stores through a shared `UserPreference` helper (signal +
synchronous `localStorage` read at construction + write-through), which is
the only code touching `localStorage`.

**Reason.** The user asked for the `DarkModeService` facade pattern to extend
to the other categories. It generalises what the lib already does:
`DarkModeService` is the sanctioned persistence owner and the AGENTS.md
exception to the dumb-component rule, and it owns its key (`data-theme`).
One owner per key keeps a single writer per storage slot; the panel consumes
only the facade (one injectable, one test double); the bootstrap providers
(`DATE_PIPE_DEFAULT_TIMEZONE`, the telemetry gate) read the owners directly, which is
legal because `UserPreference` reads storage synchronously at construction.
The seam for the promised server-side persistence is the helper's internals
(GET/PUT behind the same signal API) — owners, facade, and panel do not
change then.

**Alternatives.** One monolithic `SettingsService` owning every key:
it would write `data-theme`, a key `DarkModeService` already owns — two
writers, and the webapp would fork the theme mechanism the lib ships. Panel
injecting the owners directly: no facade to double in tests, and every
setting change touches the panel's imports. A global signal store/ngrx: the
webapp has no global-store convention (AGENTS.md: feature state lives in
signal stores under the feature folder).

**Consequences.** The `SPL-10` rule is testable per owner: each owner is the
sole writer of its key. Adding a setting = one owner + one facade member;
the 7.6/7.7 screens consume owners directly (a table reads
`PageSizeService`, not the facade) — the facade serves the panel, owners
serve consumers. Server-side sync, when it lands, adds the PUT path in
`UserPreference` and a hydrate step at bootstrap (DD-161).

### DD-161. Settings are browser-scoped localStorage; server-side persistence is the follow-up slice

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The v1 settings store in `localStorage` under `data-theme`
(the theme's existing key) and `aurelius-atlas.settings.{timezone,pageSize,telemetry}`.
They are user-experience conveniences, scoped to the browser: nothing that
identifies a user, grants a permission, or belongs to the catalogue is kept
there. Server-side per-user persistence (Keycloak profile attributes, or the
Atlas session settings ADM-05 exposes) is a deliberate later slice behind the
`UserPreference` seam (DD-160).

**Reason.** The user chose localStorage for now and named Keycloak's user
profile as the server-side direction. The two server channels are not ready:
`GET /atlas/admin/session` (ADM-05) publishes settings but Atlas 2.4.0 has
no settings-write endpoint, and Keycloak profile writes need admin
token-roles — both are increments of their own. The privacy line matters for
DD-158's off switch: a browser-scoped store keeps the promise simple (off
means this browser sends nothing; nothing was sent about a user).

**Alternatives.** Cookies: sent to the server on every request for data the
server never reads. IndexedDB: asynchronous for values this small — the
synchronous bootstrap read SPL-07/SPL-11 need becomes an ordering problem.
Server-first now: blocks the panel on the 6.1 identity + a new endpoint,
putting a UI feature behind API work the user scoped later.

**Consequences.** DV-65 records the panel as a deliberate addition (Atlas has
none). A shared browser shares its settings — acceptable for v1, named for
the server-side slice to fix. Key names are documented in this entry so the
server-side slice can migrate them.

### DD-162. The drawer animates in and out; the layer's life is the exit animation's

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `Drawer`'s panel slides in from the right edge over a
fading scrim (200ms, ease-out) and plays the reverse on close (ease-in,
`forwards`). Dismissal is state-first: `active` flips to false at once —
focus restoration, the caller's binding, and `cancelRequested` all land
immediately — and a `closing` signal keeps the layer rendered for the exit
pass; the panel's `animationend` (name-checked, so content animations
bubbling out of the projected body are ignored) drops it. Reopening
mid-slide-out clears the flag and the enter animation plays on the layer
that never left. `prefers-reduced-motion: reduce` shortens the animations
to 0.01ms; it does not remove them. Plain CSS keyframes — no
`@angular/animations`, and the component stays a dumb
`aurelius-atlas-ui` component (its AGENTS convention): the animation is
styling, not service work.

**Reason.** The user asked for the drawer to be animated. A `@if (active())`
template removes the DOM on close, so an exit animation needs a second
signal to keep the layer alive; keying the layer's life to the exit
animation's end is the CSS-native answer (the same lifecycle modal
libraries use). State-first dismissal keeps every rule SPL-02 states —
focus returns on close, `active` is false on dismissal — true _on close_,
not 200ms later; tests and consumers never wait on motion. 0.01ms rather
than `animation: none` under reduced motion because the exit's
`animationend` is what removes the layer: no animation, no event, a
drawer stranded on screen.

**Alternatives.** `@angular/animations`: a new dependency for the lib's
peer set and a second styling system, for two translate keyframes. Enter
only (keep `@if (active())`): simplest, and the snap-out reads as a bug
next to the slide-in. Hiding with `visibility` after a timer: timers
instead of the animation's own event, to race on every speed. Transition
on a class toggle: keyframes were needed because the enter plays on
element creation, where a transition has no start state.

**Consequences.** Focus restoration fires when `active` flips, so it lands
before the slide-out finishes — the panel animates out behind the focus
move; acceptable, named. The drawer spec drives `animationend` manually
(jsdom runs no CSS animations, and ships no `AnimationEvent` constructor).
Storybook's polling `expect` absorbs the 200ms close in the `play()`
functions. Keyframe names are prefixed `aurelius-drawer-`; the exit's
`animationend` is matched by containment, because Angular's emulated
encapsulation decorates keyframe names (computed
`_ngcontent-ng-…_aurelius-drawer-out`), not by prefix.

### DD-163. The drawer styles itself with fallbacks; Bulma's modal tokens are `.modal`-scoped

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The drawer's head/body padding, scrim colour and z-band keep
the Bulma token names for the override seam, and add explicit fallbacks:
`var(--bulma-modal-card-head-padding, 2rem)`, a scrim spelled from the
root-scoped scheme ramp at Bulma's 0.86 alpha, and the existing z fallback.
The drawer ships no padding of its own beyond this.

**Reason.** The user asked for edge padding; measuring the live drawer
showed the real bug: Bulma 1 emits `--bulma-modal-*` on the
`.modal`/`.modal-card-*` selectors, not on `:root` — verified in
`node_modules/bulma/css/bulma.css` — so outside a modal the tokens are
undefined: bare `var(...)` collapsed the head/body padding to 0 and
painted the scrim transparent. A plain literal padding would fix the
symptom; the `var(name, literal)` form keeps the brand's override seam
(open the drawer's tokens to the brand ramp later) and documents the
scope trap.

**Alternatives.** Import Bulma's modal layer in the brand (it drags the
whole component's CSS for three tokens). Define the tokens on `:root`
in the brand (duplicates Bulma's values, and a brand-wide change to fix
one component). Plain literals (loses the seam).

**Consequences.** The drawer's computed padding is 2rem; the scrim is
Bulma's modal-background recipe, dark-ramp aware (DD-156). The fallbacks
drift if a future Bulma changes the modal defaults — named, low-risk,
the component owns its layer (DD-157).

### DD-164. The Appearance picker is the ui-lib Select; the Select gains `searchVisible`

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The settings panel's Appearance section is the ui-lib
`Select` with `searchVisible` off — the section heading is the control's
own label, the rows are the three modes (Auto first, selected). The
Select gains the `searchVisible` input (default on: the Aurelius modal
opener stays for repository pickers); off, the addons layout collapses
with the button and the field is a plain labelled dropdown.

**Reason.** The user asked for the component library's select. The
Select is the lib's only select, ported from Aurelius with a search
button welded in; an input is the minimal honest generalisation — the
button is the legacy `activateSearchModal` affordance, not part of
"pick one of three themes".

**Alternatives.** Keep the radios (rejected by the user). Native Bulma
select markup, as the Time zone section uses (duplicates the lib's
control, and loses the UIC-14 label pairing). Fork a plain select
component (a second select in the lib, no).

**Consequences.** The panel's `.select select` list gains a first
element (specs index it). The Select gains a `NoSearch` story. A
selected row can never be cleared — the placeholder is `hidden` and
`setTheme` ignores null; the panel always has a theme.

### DD-165. About shows one version; the server is not fetched

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The About section shows the app name and the app version
from the runtime config, and nothing else. The `getVersion` fetch and the
server line are removed, with them the `shell.settings.server` and
`shell.settings.serverUnavailable` strings (catalogues: 533 units).

**Reason.** The user set the rule: app and server always carry the same
number — one Nx release cuts the workspace, and the image labels derive
from it — so the server line can only echo the app version, and a
version the panel has to fetch can only be _shown_ to differ while the
fetch is in flight. Removing the row removes the question.

**Alternatives.** Show the fetched server version (states a known-true
equality, and adds an ADM-01 call per open). Show "app (server: same)"
(noise). Keep the fetch, show it on mismatch only (two code paths for a
state the release strategy rules out).

**Consequences.** The panel's construction fetch is `getSession` only
(SPL-07 keeps its degradation test). ADM-01's endpoint stands on the
server; the panel is no longer its consumer, and DV-03's parity scope
does not change.

### DD-166. The settings panel is a routed overlay in the `drawer` aux outlet

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `drawer` named outlet at the app root carries routed
overlays (SPL-14). The settings panel is a route (`(drawer:settings)`):
the header gear is a `routerLink` to it — with the panel open the link
targets the URL it is on, and the router cancels that duplicate
navigation, so the gear is a no-op; dismissal (backdrop, close, Escape)
navigates the segment away. The component opens at construction
(`active` starts true) and loads its chrome data then. Future drawers —
an alerts drawer is named — get their own outlet segments and compose in
the URL: `(settings:…)(alerts:…)`.

**Reason.** Switching language is a full-page navigation into the locale
tree (DD-128), and the user wants the reload to land on the same page
with the settings open. The URL is the only state that survives a full
reload, and named outlets are Angular's mechanism for putting an
overlay in the URL — the segment rides `localeHref()` untouched, so the
requirement falls out. (The term: auxiliary routes.)

**Alternatives.** A query param (`?settings=1`) — works, and invents a
parallel navigation system outside the router; the outlet form is the
router-native one, composable, and the Angular idiom. localStorage
"open" flag — reloads open, survives everything, unbookmarkable and
sticky. A service + effect — doesn't survive the reload, which is the
requirement.

**Consequences.** Closing destroys the panel, so the drawer's exit
animation (DD-162) is not awaited there — accepted, named; the DD-162
lifecycle remains for the drawer's own API (`close()` on a non-routed
drawer), and the enter animation plays on open, including after the
locale reload. Dismissal is destructive (no panel state to keep — the
facade owns it, DD-160). Deep links work: visiting
`/search/browse(drawer:settings)` opens the panel on that page. The
`serverUnavailable` fallback and the `open()` API are gone; the panel
spec drives the component directly (as the routed-component test
pattern prescribes).

### DD-167. Settings-drawer polish: lit gear, scheme-following band, Browser-default picker, `.label` headings

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** Four fixes from the user's review of the open drawer.
(1) The gear carries `routerLinkActive="is-active"`: Bulma styles
`a.navbar-item.is-active`, and the active state keys off the `drawer`
outlet segment — the gear is lit exactly while the panel route is open
(SPL-01). (2) The outlet band drops `has-background-light` for Bulma's
bare `.has-background` (`var(--bulma-background)`): the legacy light in
light mode, the dark scheme's surface in dark (SPL-05's theme switch
now repaints the page, not just the drawer). SHM-05's pinned chrome
bands are unchanged. (3) The time-zone picker binds the stored zone
directly — `null` when unset selects the "Browser default" option
(SPL-07); the browser's resolved zone is no longer injected into the
select, where it rendered blank whenever it was not one of the server's
ADM-05 ids. (4) Every settings section heading is a Bulma `.label` —
the form-controls guide's field label (the guide the user linked) —
replacing `.menu-label`; the Appearance heading already renders as
`.label` through the Select, so all six now match.

**Reason.** The gear gives no affordance that it owns the open panel.
`has-background-light` is Bulma's fixed light colour family, not a
scheme role, so a dark page kept a light band. A select whose value
matches no option renders empty — the "Browser default" option is the
honest display of an unset zone, since its effective value _is_ the
browser's, applied at the date pipe. `.menu-label` is the sidebar-menu
heading (uppercase, small, weak); inside a form column it reads as a
different component than the `.label` the Select shows.

**Alternatives.** (1) A signal shared header→panel — state the URL
already carries. (2) `has-background-scheme-main` — the body colour,
leaving no surface distinction from the footer band; `--bulma-background`
is Bulma's surface role and matches what cards/tables sit on. (3) Add
the resolved zone as an extra option — the list is the server's
(ADM-05), and a local zone the server may not accept is a false
promise. (4) Keep `.menu-label` — the inconsistency the user flagged.

**Consequences.** The band's computed background follows the scheme
(verified live in both modes). `timezoneValue` narrows to
`string | null` — the same value the facade stores, making the panel a
pure pass-through. The `.label` heads are normal-case and stronger
ink; the panel scss comment follows. No string ids change.

### DD-168. The navbar follows the scheme: the dark slate band

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** In dark mode the navbar leaves the pinned light band
(SHM-01's "the brand colours do not follow the scheme", for the navbar
only) for a neutral slate, #72757d — hsl(224, 4%, 47%), the faint cool
cast of $blue. The bar's chrome composes on the slate: ink #000 (5.6:1),
hover/active the light plate (Bulma's +8%/+12% deltas, DD-152's deltas
inverted for a dark band), the gear's `is-active` the white plate
(DD-152's selected pair), the `is-dark` Documentation button's
ink/border black (its pinned #363636 rides at 2.5:1 on the slate). The
account dropdown keeps Bulma's scheme composition. The footer stays
pinned (SHM-07 — blue/white reads the same in either scheme). The logo
keeps its brand size in both schemes.

**Reason.** The user's review: dark mode kept a light navbar. The
binding constraint is the logo, measured from the PNG: its wordmark is
navy `#151487` at ~11% lightness, so every dark surface (the scheme's
`#1f2229`, the brand blue `#0073dd`) collides with it (1.0–1.3:1) and the
wordmark's WCAG-3:1 floor (graphics) sets the bar's ceiling at ~47%
lightness. The slate is the darkest background that keeps the mark
legible (3.1:1); the user chose it over the brand blue, then over the
first bluer/lighter cut — 4% saturation, one step under the floor.

**Alternatives.** Brand blue #0073dd (the footer's blue — wordmark
3.5:1, the user declined: reads as a blue bar). A true dark band
(#131a26) with a light logo variant — the proper dark-mode look, needs
a design asset; the seam is this mixin's token block. Keeping the navbar
pinned light (the status quo the user rejected). Darkening the slate
below 47% (the wordmark falls under 3:1).

**Consequences.** The navbar tokens are a brand-theme block on both of
Bulma's dark hosts (0,2,0, out-cascading the light `.navbar` pins). The
logo's navy/cyan palette is now load-bearing across schemes: a future
rebrand or light-variant asset replaces this decision (supersede, don't
edit). The light band is untouched (SHM-05 stays the light-mode chrome).

### DD-169. Settings headings are the controls' accessible names

- **Status:** Accepted (the language `role="group"` clause superseded by
  [DD-428](../7-23-sonar-findings/design.md#dd-428-logout-is-a-native-button-and-the-language-group-a-fieldset-native-elements-over-aria-roles))
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** Every settings control's `.label` heading is its
accessible name (the Bulma form guide's labelled control, the guide
DD-167 adopted): Time zone and Page size are `label[for]`/`id` pairs on
the native selects, Telemetry on the checkbox (the label moves from the
old wrapping `.checkbox` — the checkbox is a plain control on the
section grid), Appearance rides the ui-lib Select's own
`label[for]`/`aria-labelledby`, and the language links — not a form
control — are a `role="group"` labelled by their heading. About is a
section title, not a field, and is not associated.

**Reason.** The user's review of the DD-167 layout: the headings looked
right and were wired to nothing — clicking a label did nothing, and a
screen reader announced bare "combobox"/"checkbox". The Bulma form
guide the headings already follow prescribes the association; DD-167
adopted the shape and left out the link.

**Alternatives.** `aria-labelledby` everywhere (works, and the
`label[for]` is the HTML-native form the guide shows; the group and the
Select use it where no single labelable control exists). Keeping the
wrapping `.checkbox` label (an accessible name, and the Bulma checkbox
idiom — rejected: the guide's stacked label/field shape is what DD-167
just standardised on, and the checkbox label had no text to wrap).

**Consequences.** Fixed ids (`settings-timezone`, …): the panel is a
singleton route, so collision is impossible. The checkbox loses
Bulma's `.checkbox` hover affordance (the label click replaces it). The
panel spec asserts each pair.

### DD-170. The active locale is filled with the Aurelius blue

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The active locale link in the settings drawer's Language
section is a solid Aurelius-blue plate (`#0073dd`, white ink): the
panel scss fills the `is-selected` button the template already marks
(SPL-06). The pair is pinned, not scheme-following — the same
`#0073dd`/white the footer's brand block pins (SHM-07).

**Reason.** The user's review: "For the locales can we ensure the
current locale is highlighted?" The SHC-04 port carries the
`is-selected`/`aria-current` marking (7.12), and the template binds
it — but Bulma 1 styles a selected button with nothing (verified:
`.button.is-selected` has no rule, and the rendered active and
inactive links measure identical ink and plate). The marker is
semantic, invisible; the highlight the user asked for is the missing
visual half of it.

**Alternatives.** `is-active` (Bulma composes an `l-delta` from it —
a shadow on the plate, not a fill; the same non-result). A check-mark
icon on the active link (a decoration needing a string and an id on
both locales, for what a fill says for free). `var(--bulma-link)`
(the scheme-following accent — rejected: DD-156 lightens it to 73%
in dark, and white ink on a 73% light-blue fails; the pinned pair
holds 4.6:1 in either scheme).

**Consequences.** `.buttons.has-addons` keeps the links joined, and
the fill joins them visually as a segmented control: the active plate
is blue, its neighbours stay plain. The panel spec asserts the
`is-selected` class on the active link (the scss fill itself is a
style, not a testable DOM fact).
