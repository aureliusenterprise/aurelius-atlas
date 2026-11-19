# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-713. The chip-and-suggest box becomes a dumb ui-lib component

- **Status:** Proposed
- **Increment:** 7.32
- **Date:** 2026-11-19
- **Supersedes:** — (adds UIC-44; splits DD-341's "the picker is one webapp
  component" into the box (here) and the search (DD-341, DD-711))

**Decision.** `aurelius-atlas-ui` gains `TokenPicker` (UIC-44): the box, its
chips, its input, its suggestion panel, and the DD-335/DD-336 focus, keyboard
and ARIA model — the anatomy 7.7a built inside the classification box and 7.7c
copied into the relationship picker. Its whole surface is inputs and outputs:
`selected` chips, `rows`, `single`, `invalid`, `text`, `label`, the three
caller-localised strings, `labelId`, `errorId`, `idBase`; `typed`, `picked`,
`removed`, and `entered` (focus moved into the box from outside, which is where
the empty-box browse belongs, DD-343). A row is `{key, name, type?, icon?,
iconClass?, trail?}`, and the component builds nothing from them: a consumer outside the Atlas
product can hand it a badge name and a trail from any source (UIC-15). DD-714 settled what shape
the trail takes — crumbs, not a joined string. The webapp's `EntityRelationshipInput` shrinks to the wiring:
`ViewSearchService` behind the 250 ms debounce, the door body and limits
(DD-711), the client name-prefix check, the exclusions, and the card→row map.

**Reason.** The port's own rule is that presentational parts are dumb library
components and data wiring stays in the app (UIC-07, DD-137, DD-341). The
relationship picker was the one visible part of the editor that broke it: 340
lines with the box, the keyboard, the markup and an HTTP client in one class,
and no story or Chromatic coverage because it was not a library component. Its
box is also a near-copy of the classification box's markup and 118 lines of
SCSS, so the two drift. Moving the box out gives it the tests and the story the
rest of the library has, leaves the picker at the data half it was always
meant to be (DD-341), and gives the next chip-and-suggest control a component
instead of a third copy.

**Alternatives.**

- Move the search into the editor too, and delete the webapp component (refused
  — the `EntityEditor` already carries the form's whole state and 95 tests; the
  debounce, the timers and the exclusions are the picker's own concern and their
  tests belong with the picker).
- Extract only the panel and keep the chips and input in the webapp (refused —
  the box is one anatomy: its border, its `:focus-within` ring, and the
  full-width panel offset belong together, DD-335. Half a box is a second copy
  of half a box).
- Reunit the classification box in the same pass (refused — its chips are
  classifications with a tooltip and a propagation dropdown, its rows are types
  rather than entities, and reuniting them would rewrite 7.7a's shipped EDT-05
  tests for no user-visible change).
- Keep the `.aurelius-relationship-*` class names inside the library (refused —
  a library component cannot carry editor vocabulary in its own stylesheet; the
  names move to `.aurelius-token-*`, and the tests and e2e selectors follow the
  component, which is the port's usual order, UIC-01).

**Consequences.** The box's element classes move from `.aurelius-relationship-*`
to `.aurelius-token-*`, so four editor-spec queries and the two e2e files that
reach inside a picker change with it. Everything a reader or an assistive
technology sees is unchanged: the field's own ids keep the
`editor-relationship-<field>-*` shape (EDT-17), because the webapp passes the
`idBase` the editor's label and error lines already use. The row's parts stop
being built inside the template and are built once in the webapp, which is what
let the row markup drop out of the component. The classification box and its
duplicated SCSS stay as they are: they are now the known duplicate this
component exists to absorb, and the next increment that touches EDT-05 can fold
it in.

## DD-714. A row's trail is the Breadcrumbs component, printed without links

- **Status:** Proposed
- **Increment:** 7.32
- **Date:** 2026-11-19
- **Supersedes:** none (amends UIC-11, merged; DD-713's row `trail` is crumbs, not a joined string)

**Decision.** `Breadcrumbs` gains a `links` input, off by `true` as shipped. With
`links: false` every crumb renders as the plain-text `<span class="truncate">` the
active crumb already used — none is `is-active`, none carries `aria-current`, no anchor
exists, and `itemClicked` never fires. `TokenRow.trail` becomes
`readonly Breadcrumb[]`, and the picker's row prints it with that component.
The row itself becomes a `<div class="dropdown-item" role="option">` rather than a
`<button>`, with the states Bulma writes for `a.dropdown-item, button.dropdown-item`
restated in the picker's scss through Bulma's own custom properties, and with the
crumb wrap pinned to one line through the `--aurelius-breadcrumbs-wrap` custom
property the trail component reads.

**Reason.** Every other trail in the product renders through `Breadcrumbs` — the details
header (DD-606) and the card family (DD-616) — so the picker's trail was the last place
reading a hand-joined `A / B` string: its own font size, its own separators, no crumb
icons, and no shared truncation. That string existed only because DD-713's row was a
`<button>`: a button cannot contain the component's anchors. The constraint was the wrong
way round. An `option` in a combobox listbox must not contain interactive descendants
anyway — the picker owns the keyboard and sets `aria-activedescendant`, so a crumb inside
an option is a tab stop assistive technology cannot reach and a second activation inside
one choice (the flaw 16.5e's DD-624 removed from the active crumb, one level up).
Dropping the `button` element for the ARIA-correct `div role="option"` is what lets the
row print the trail the rest of the product prints.

**Alternatives.**

- Keep the joined string and style it to look like a trail (refused — a second
  presentation of the same thing, drifting from the component on every style pass; the
  crumb icons alone mean the row reads differently from the card it mimics).
- Render `Breadcrumbs` with its links on inside the option (refused — nested interactive
  controls inside an `option`, and a crumb click would both navigate and pick the row).
- Keep the `<button>` and project the crumbs as plain spans (refused — a button still may
  not contain interactive content, so the plain spans would be a fourth crumb layout in
  the library, which is the duplication this removes).
- Give the picker a separate row-trail component (refused — one more component to keep in
  step with `Breadcrumbs` for a mode flag's worth of markup).

**Consequences.** UIC-11 gains a second amendment note, and the row's parts in the
webapp are the crumbs `trailOf` already builds (minus the entity's own crumb), so the
join and the name-only mapping leave the app too. The row's accessible name keeps the
same parts in the same order, but its trail's crumbs now read as separate items —
separated by a space and by no `/` in the flat string, since Bulma draws the separator in
CSS — so the accessible-name pins in the two specs change with it. A row keeps Bulma's
item paint by restating its states, which is a rule the picker must now maintain if Bulma
changes them; the alternative, leaving the row unpainted, was rejected because it would
silently drop the hover and active states of every suggestion row. The trail keeps its
muted 7.31 ink and takes the highlighted row's inverted ink, or it would sit unreadable
on the link-blue `is-active` paint. Dropping the `button` also costs its SonarQube
suppression: the 7.7a decision let a flagged option carry an inline `//NOSONAR` marker,
which works on a `<button>` because Prettier keeps a comment glued to that tag — but it
splits one off a `<div>`, so a marker there lands off-line and stops working. The option
lines therefore stay flagged alongside the listbox line, which 7.7a already accepted,
until the server's S6819 `allowedRoles` parameter lists `listbox`/`option`; the popup's
comment records why no marker sits there.
