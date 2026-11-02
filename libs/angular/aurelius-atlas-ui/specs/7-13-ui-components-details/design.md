# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-154. The entity card emits `entityClicked`; the caller navigates

The ported `entity-card` (7.13) emits `entityClicked(guid)` on a title click and
does not navigate. The legacy `DetailsCardComponent` injected `Router` and, on a
title click with no parent listener attached, navigated to
`search/details/{guid}` itself — its template probed `entityClicked.observers`
to choose emit-or-navigate.

**Reason.** The ui lib is dumb by workspace rule (ADR 053, user rule: components
are dumb and live in `aurelius-atlas-ui`); an injected `Router` inside a lib
component re-creates the coupling the port exists to remove, and the
`observers.length` probe is a side-channel, not an API. Emitting always and
letting the app route is the DD-135 pattern (`SearchField` emits, the caller
filters).

**Alternatives.** Port the probe (emit-if-observed, else navigate): keeps the
legacy one-liner call sites, at the cost of a Router in the lib and behaviour
that changes with the parent's subscription list. A `routerLink` on the title
anchor: the details route belongs to 7.6, the lib must not know its path.

**Consequences.** 7.6 wires `entityClicked` to the router. The card is
testable and storyable with zero app services.

### DD-155. The select is one field with a `searchRequested` output

The ported `select` (7.13) is the Bulma select field plus a search button that
emits `searchRequested`. The legacy `SelectComponent` embedded a
`SearchModalComponent` (a repository-fed `sortable-table-shell` inside a modal,
selected row confirmed into the field) and sat on the reactive-form
`AbstractControlShell` base.

**Reason.** The modal's data comes from `@models4insight/repository` — exactly
the API coupling 7.2 set aside for the app slices (7.7 owns the editor
anatomy). The presentation half (field, options, null/no-data messages,
timestamp display, required help) is pure, so it ports now; the modal half
arrives as app wiring listening to `searchRequested`. The reactive form
dissolves into `value = model()` exactly as DD-135 did for `SearchField`, and
the `compareWith` default becomes strict equality — the lodash `isEqual` deep
compare was a legacy default the Aurelius callers never relied on.

**Alternatives.** Port the whole component including the modal: drags the
repository and `task-manager` into the lib. Defer the select entirely to 7.7,
per 7.2's table: the details screens want a pure select today, and the
presentation/data split lets 7.7 wire only the modal.

**Consequences.** 7.7 composes select + modal; the lib stays pure. Option
identity is strict reference equality — callers pass stable objects.

### DD-156. The brand ships a dark ink ramp on Bulma's dark hosts

The brand theme (DD-148, DD-151) pins the light ink chain in `:root` — body
`#4a4a4a`, the neutral text ramp, `.content` — and `:root` out-cascades
Bulma's own `[data-theme=dark]` block (equal specificity, later source).
The result: under a dark scheme (the storybook theme switch, any future
`DarkModeService` use) the surfaces flip to Bulma's dark scheme and the
ink stays light-mode grey — illegible. This adds a dark ink ramp emitted
on both of Bulma's dark hosts, `[data-theme="dark"]` (the explicit
toggle, `DarkModeService`'s attribute) and `:root:not([data-theme])`
inside `prefers-color-scheme: dark` (the OS path, Bulma's `system-theme`
pattern): the text chain re-pins to Bulma's dark-scheme lightnesses over
the DD-151 neutral hue (text 71% `#b5b5b5`, strong 93% `#ededed`, weak
53% `#878787` — ~9:1 on the 9% surface), the body ink/background return
to the scheme tokens, `.content` follows, the link lifts to Bulma's own
dark adaptation (`link-on-scheme-l`, 73% — `#0073dd` is ~3.9:1 dark-on-
dark), and the ui lib's legacy `.technical` type ink (pure `#0000ff`,
~2:1) lifts to the same 75% lightness Bulma's contrast loop derives.
`.technical` is the only legacy type colour that fails on dark: orange,
teal and the grey all read 8:1+ and stay.

**Reason.** The switch must show the real app theme, and the app's dark
mode (7.11's `DarkModeService` ships the toggle, 7.12 defers the theme)
has no usable ink. Bulma 1's scheme machinery is the platform: its dark
lightnesses are the WCAG-calibrated defaults, and its `generate-on-scheme-
colors` contrast loop is the exact precedent for lifting `#0073dd`/
`#0000ff` — the ramp mirrors those numbers instead of inventing greys.
The chrome bands stay pinned (SHM-01: "the brand colours do not follow
the scheme"): the navbar's `#f5f5f5`/`#4a4a4a` and the footer's blue/
white are the legacy chrome in either scheme, and a light navbar over a
dark page is Bulma's own `.navbar.is-light` idiom.

**Alternatives.** Unpin the ink from `:root` and let Bulma's schemes own
it: correct, but it deletes the DD-151 legacy ramp (Bulma 1's dark ink is
221°-tinted, the demo's is neutral) and out-of-scope churn on a light-
only slice. A full brand dark palette (every accent re-tuned): the demo
has no dark mode to measure against (the legacy Aurelius is light-only —
verified in `.scratch/aurelius`), so every value would be invented; only
the ink that fails contrast is lifted, the rest of SHM-04 stays.

**Consequences.** The storybook switch previews a legible app; a future
theme-switch slice inherits the ramp. The webapp's `index.html` keeps
pinning `data-theme="light"` (SHM-01 untouched) — the dark ramp reaches
the app only through an explicit switch. Play tests cover the ramp on
the entity-card/breadcrumbs dark composition stories; the light ramp is
unchanged (SHM-03's measurements stand).
