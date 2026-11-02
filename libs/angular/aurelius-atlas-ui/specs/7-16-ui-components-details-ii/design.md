# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-189. The details chip is the classification chip; its sources project in

- **Status:** Proposed
- **Increment:** 7.16
- **Date:** 2026-10-22

**Decision.** `classification-chip` is the Bulma `tags.has-addons` chip of
`search/components/classification/`: icon lead tag, label tag with tooltip,
loading tag, and the optional propagation tag whose hoverable dropdown projects
the sources list via `[chip-sources]`. The legacy `ClassificationService` (the
type-definition lookup by name) and `ClassificationSourceService` (the
repository-fed source rows) are inputs and projection — name, description,
`propagated`, and the sources content arrive from the caller. The glossary-term
chip (`search/components/term/`) is the same atom with `is-info` on the lead
tag, so it is not a second component: the lead colour is an input.

**Reason.** The two legacy chips are byte-identical markup around one colour
class and one label key; a `term-chip` twin would be a copy. Everything the
chip's services fetched is a fact the caller already holds wherever the chip
renders (the details header reads classifications off the entity DTO; 2.3's
entity read carries them) — the service indirection existed to cache
per-name lookups, a data concern, and the lib's rule (UIC-15) is that the
caller supplies what it has. The sources rows stay projected rather than
modelled because their shape (a media row: name link, crumbs, type badge) is
the app's `classification-source` anatomy — the 7.6 deferral table's
repository-fed part — and the chip should not reach past a slot into it.

**Alternatives.** One generic `tag-chip` with colour + icon + label inputs
(refused — it erases the propagation dropdown, the chip's real behaviour, and
"details chip" named for no legacy source). Two components, classification +
term (refused — the copy-paste twin). Model the sources as `{guid, name}`
inputs with a built-in row (refused — the row is repository-fed, the wiring
7.6 defers).

**Consequences.** The chip is speccable and storyable with zero data (the
sources slot stories the dropdown's content). When 2.3 lands, the header
composes `@for (c of entity.classificationNames)` chips and feeds the slot
from the propagated-sources lookup — the chip itself does not change. The
term chip's key (`search.components.term.term`, "Term") becomes the term
call site's lead label input.

### DD-190. The type-name badge is extracted from entity-card

- **Status:** Proposed
- **Increment:** 7.16
- **Date:** 2026-10-22

**Decision.** `type-name` is its own component: the `span.icon-text` badge
(icon, `typeAlias ?? typeName`, base-type suffix) of
`search/components/type-name/`, with `iconsByType` as caller inputs (UIC-15).
7.13 inlined this badge inside `entity-card` (UIC-12); `entity-card` now
renders `type-name`, and UIC-12's rendered output is unchanged — its spec is
the extraction's regression proof.

**Reason.** The badge's call sites in the legacy app outnumber the card's: the
details header's `.subtitle.name` line, the propagated-sources rows, the
editor (7.7), the results cards. 7.13 inlined it because the card was the
only component shipping it then; the details audit found three more call
sites, and an inlined badge gets copied at each. The `iconsByType` index the
legacy badge reads is app meta (UIC-15's split), so the standalone form needs
no app code: icon and class are inputs, as the card already passes them.

**Alternatives.** Keep the badge inlined and let the header compose the badge
markup by hand (a third copy of the badge's markup in the webapp, inside the
skeleton 2.3+7.6 then edits again). Export the badge as a directive on
`entity-card`'s internals (refused — the lib's components are the public
surface; internals are not).

**Consequences.** One badge implementation; `entity-card`'s inputs pass
through to it (the public API is unchanged — UIC-12's spec stays the
guard). The details header composition (2.3+7.6) uses it for the type line
without touching the card. `classification-chip`'s sources slot rows use it
as their badge (DD-189).

### DD-191. Details navigation is a shell; the scroll directive stays app-side

- **Status:** Proposed
- **Increment:** 7.16
- **Date:** 2026-10-22

**Decision.** `details-navigation` ports the shell of
`details/components/navigation/`: `box.is-paddingless` around a Bulma
`dropdown.is-up.is-right`, the toggle button (caller icon input, `is-active`
toggled on click), and the `nav.menu` with the label input and the
`ul.menu-list` fed by `ng-content`. The legacy `DetailsNavigationItem`
directive — click scrolls the target into view — is not ported into the lib;
items are caller markup, and the app wires their behaviour.

**Reason.** The shell is presentational and complete on its own (the Bulma
dropdown's open/close is pure CSS once `is-active` toggles). The directive is
DOM behaviour on the application's document (`document.body` is the legacy
label's target): a lib component that scrolled the page would own layout the
app owns — the purity rule's same line as `breadcrumbs`' routing split
(UIC-11). Keeping `li`s as projected content also means the nav composes with
any anchor scheme: the 7.6 skeleton's same-page `#section` hrefs today, the
wiring increment's hash-router links later, without the lib changing.

**Alternatives.** Port the directive too (a lib scrolling the host document
is library overreach, and the target ids are app anatomy). Emit
`itemClicked(target)` like `section-stats` (refused for the nav: the legacy
nav's items are arbitrary projected markup, the directive is the wiring — an
emit would only cover component-owned anchors, i.e. it would cover the shape
that isn't here).

**Consequences.** The webapp's 7.6 side nav swaps its inline `nav.menu` for
this shell and (in 2.3+7.6) adds a small app-side directive for scroll —
named in 7.16's deferral table. Storybook stories the shell with static
items; the toggle's `play()` test proves the interaction.

### DD-192. The count bar is section-stats: one component, two call sites

- **Status:** Proposed
- **Increment:** 7.16
- **Date:** 2026-10-22

**Decision.** `section-stats` ports the `nav.level` count bar the legacy
details screens duplicate — `default-details.component.html` (one stat:
properties) and `gov-quality-details.component.html` (three: non-compliant,
compliant, properties) — as one component: `items: { label, target, count }`,
`p.heading > a` (href `#target`) + `p.title` per item, `itemClicked(target)`
on activation (DD-154's emit-instead-of-navigate pattern; the anchor's href
is the keyboard path).

**Reason.** The two bars are the same Bulma block with a different item
count, and the details header (2.3+7.6) and editor (7.7) repeat it again —
the Aurelius pattern is "a heading-link that jumps to the section, with its
count above the fold". The legacy count came from a service stream; here the
count is a string the caller renders (it is a count, not a number with
locale semantics — the legacy template interpolated it raw). Making `target`
a plain id keeps the href honest for the same-page case the skeleton is
(7.6), and `itemClicked` lets the app intercept (the nav directive's
smooth-scroll, analytics, hash-router links).

**Alternatives.** A `properties-count` special case (refused — the gov-quality
bar proves the shape generalizes). Bulma `level` as slots per item (refused —
items are homogeneous, an array input is the smaller API).

**Consequences.** The 7.6 skeleton's inline count bar becomes
`section-stats` with one item when the wiring increment lands (the skeleton
stays as specced until then — DET-02's zero-row bar is its contract).
Gov-quality (7.8) composes three. The strings ride the caller's inputs; the
bridge keys (`search.details.default.properties`,
`search.details.govQuality.*`) already exist.
