# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-711. The relationship picker searches the view family's door and names the row's type and trail

- **Status:** Proposed
- **Increment:** 7.31
- **Date:** 2026-11-19
- **Supersedes:** DD-339 (the picker's `GET /search/attribute` contract; amends
  EDT-14, adds EDT-33)

**Decision.** A picker's suggestion search is `ViewSearchService.search`
(`POST /api/aurelius/v1/search`, VSR-03) with `filters.typeName` naming the
field's target type and every type under it (the `any` of `typeName` and
`superTypeNames` the results screen sends, VSR-04), `limit` 10 for typed text
and 5 for the empty-box browse (DD-343), and the typed text as the query with a
trailing `*` so a word still matches the beginning of a stored name (AVR-04,
DD-711). The client keeps the cards whose `displayText` begins with the typed
text, case-insensitively, which is the `STARTS_WITH` on `name` the stock
attribute search applied server-side (SRC-11). The row is the card's fields:
`displayText`, the `typeName` badge (DD-379's display name, DD-378's icon), and
the stored `breadcrumb` by the shared trail rule (VDR-06, VDR-11) — the badge on
the name's line and the trail under it, as the rich card's title line and trail
sit (VCF-01). The option's accessible name is name, type, then trail (EDT-33). The exclusions,
the 250 ms debounce, the box, the chips, and the save stay DD-338..DD-341's.

**Reason.** Names repeat in a catalogue, and the picker showed one name per row,
so two `Orders` tables in different domains were indistinguishable before the
pick. The catalogue cards already answer that (16.5d's VCF-01 card prints the
type badge and the trail), and the legacy Aurelius picker did the same: it
seated a full details card per suggestion row. The type is already on the
header the old search returned (`typeName`), so only the trail was missing. A
breadcrumb is derived data of the App Search document (`breadcrumbguid`,
`breadcrumbname`, `breadcrumbtype`, LAS-04) and the Atlas search and header
endpoints answer nothing trail-like, so a faithful trail is unreachable on
DD-339's endpoint. The view door answers 16.1's cards (AVR-08), which carry the
breadcrumb, and the webapp already rides that door for results (VSR-03) — one
door for "the entities, as the product shows them". A qualified name is not a
substitute: it is sanitised lowercase tokens (`--`-joined), not display names,
and an entity created in this editor has a qualified name equal to its name, so
it would read as no trail at all.

**Alternatives.**

- Stay on `GET /search/attribute` and print `qualifiedName` as the detail line
  (refused — for most picker targets it repeats the name; a created entity has
  none, and a scanned one shows `order-management--order-processing…` where the
  cards show labelled crumbs).
- Stay on `GET /search/attribute` and fetch each hit's view through
  `GET /aurelius/v1/entity/guid/{guid}` (refused — one extra request per hit per
  keystroke; the read door answers one entity, and the picker shows ten).
- Add a breadcrumb to the Atlas header answers (refused — `AtlasEntityHeader`
  is a frozen public contract, ADR 046; the trail is 16.1 view data).
- Keep the browse unfiltered and rely on the door's ranking (refused — the door
  matches whole analysed tokens, so `sales` misses `sales_table` without the
  `*`, and a browse panel that ignores the typed text suggests the wrong rows).

**Consequences.** EDT-14's endpoint sentence is amended in place and DD-339 is
superseded, never edited (DV-177 records it). The door's `simple_query_string`
is looser than a server-side prefix (an `Or` of token matches), so the client's
`displayText` prefix filter carries the stock picker's contract; a card whose
name does not begin with the text never shows. A target type the shipped store
has no typedef for answers no cards exactly as DD-339 left it (EDT-13). The
door needs `ENTITY_READ`, which a picker's writer already holds. The row grows
two lines, so `.dropdown-item` drops its `white-space: nowrap` and clips each
line on its own.

## DD-712. The drawer grows a `size` input; the editor asks `wide`

- **Status:** Proposed
- **Increment:** 7.31
- **Date:** 2026-11-19

**Decision.** The `Drawer`'s panel takes a `size` input, `narrow` (default) or
`wide` (UIC-43). `narrow` keeps 28rem; `wide` is 44rem; the CSS cap
`min(…, 100vw)` stays, so a viewport narrower than the size is unchanged (the
panel already pins the inline-end edge and the head, subhead, body and foot
slots do not follow the width, DD-157, UIC-25). The entity editor passes
`wide`; the settings panel and the alerts drawer pass nothing and render today's
panel byte for byte.

**Reason.** On a large screen the editor — the product's data-entry surface,
with a two-column-capable form and a markdown editor — held the same 28rem
panel as the settings list and the alerts feed, leaving most of the screen
unused (the user's feedback). The width is a layout choice of each caller, not
an anatomy rule, so it enters as an input with the current value as its default.
7.7d's markdown editor stacked its Write/Preview tabs because two prose columns
do not fit 28rem (DD-321); a 44rem editor panel makes the pair worth revisiting
later, and this increment deliberately keeps the shipped tabs — growing a
component's box is not a licence to restyle what sits inside it.

**Alternatives.**

- One wider size for every drawer (refused — the alerts feed and the settings
  list do not ask for it, and a 44rem settings panel reads as a stretched form).
- A fluid `min(50vw, …)`-style width for all callers (refused — every screen's
  drawer screenshots and every existing width pin move at once, and the two
  feed drawers gain nothing).
- A CSS class the caller passes through (refused — an untyped class string makes
  the two sizes invisible in the component's API; the ui library's rule is
  inputs, UIC-01).

**Consequences.** The drawer spec text (7.15's ALR anatomy, 7.16's UIC-25) stays
true: the anatomy is unchanged and only a new input is added, which the ui
library's additive-API rule allows (UIC-01). The editor's e2e drawer selectors
(`.aurelius-drawer`, `.aurelius-drawer-panel`) are class-based and unaffected.
7.7d's note that the editor "is a 28rem drawer" describes the reason for its
stacked tabs and is left as history; the tabs stand.
