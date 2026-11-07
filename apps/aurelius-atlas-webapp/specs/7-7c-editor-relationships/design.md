# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-338. One def-driven picker per relationship attribute, duplicate names merged

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-05

**Decision.** The editor builds one picker per relationship attribute of the
entity's definition and its supertype chain (EDT-13), the same walk and the
same merge rule EDT-03 uses for plain attributes: first definition wins by
name. The shipped store carries exactly three names the defs hold twice
(`hive_column.table`, `spark_ml_directory.model`, `spark_ml_directory.
pipeline`); the merged field keeps the first definition's
`relationshipTypeName` and sends it in every entry (EDT-16). The stock
dashboard instead seats a "--Select a Relationship Type--" select above the
disabled input for exactly those names.

**Reason.** 7.7a replaced the legacy's ten hand-written m4i forms with one
entityDef-driven form (DD-323) and the same logic applies here: the shipped
defs carry `relationshipAttributeDefs` for every type a shipped
relationshipDef names at an end (the server synthesizes them from the 75
relationshipDefs at the read path), so the form
needs no hand-written field and no per-type editor. The duplicate selector
exists in the stock dashboard to let the user pick which edge to write when
one name has two owners; in the shipped catalogue the three owners sit on
types nobody creates from this editor (a Hive column, a Spark ML directory),
and the server's own array path already takes the request entry's
`relationshipType` first, else the single type the name resolves to. A
merged field with the first definition's type sends exactly that.

**Alternatives.** (a) Port the stock dashboard's type selector (refused —
three shipped types only, none creatable through the editor's type picker
filters an ordinary user reaches; the select would be chrome for an
unreachable state). (b) Render two pickers for a duplicated name (refused —
both would edit the same `relationshipAttributes` key, and last-rendered
would silently win at save). (c) Send no `relationshipType` and let the
server resolve the name (kept as a fallback only when the def carries no
`relationshipTypeName` — the server's error for an ambiguous name would then
surface as EDT-08's alert, which is honest, but the defs do carry the name).

**Consequences.** The picker set reads the defs, never the catalogue of
types; a future type needs no editor change. The three duplicate names write
the first owner's edge — recorded here, since the stock dashboard offered a
choice there.

### DD-339. The picker searches `GET /search/attribute`, the stock dashboard's own contract

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-05

**Decision.** A picker's suggestion search is
`SearchService.searchUsingAttribute` (`GET /api/atlas/v2/search/attribute`)
with `typeName` the attribute's target type, `attrName` "name",
`attrValuePrefix` the typed text, and `limit` 10 (EDT-14). Debounce 250 ms,
minimum one character. The client drops the edited entity and the already-
chosen guids from the results.

**Reason.** The legacy picker searched the App Search entity index, which
this product does not port (DD-140), so 7.7a deferred the pickers until the
search contract got its own decision. The stock Apache Atlas 2.4 dashboard —
the product's parity reference (ADR 046) — does not use that index either:
its `CreateEntityLayoutView` points every relationship select at
`searchApiUrl('attribute')` with exactly these parameters. The ported server
answers that endpoint today (increment 4.x, SRC-11; the Angular twin
`searchUsingAttribute` shipped in 7.3), so the picker costs no server work
and no new client method. Probed against the live server: the endpoint finds
`DataSet`s and `AtlasGlossaryTerm`s by name prefix, and an unknown `typeName`
answers an empty list rather than an error, which is what makes the picker
safe for a target type the shipped store has no typedef for.

**Alternatives.** (a) `GET /search/basic` with `query` "text\*" (refused —
it scores over every weighted string field, so a `qualifiedName` or owner
substring wins rows the dashboard's picker would not show; and it misses
glossary terms entirely, whose searchable string is the name the index
tokenises oddly — probed: term exact-name queries answer empty against the
live store while the attribute search finds them). (b) `GET /search/dsl`
with a `where name like "text*"` clause (refused — it works, but the stock
dashboard's contract is `search/attribute`, and DSL string-escaping of typed
text is one more surface). (c) The full-text search (refused — the stock
picker is a name-prefix lookup, not a scored relevance list).

**Consequences.** The suggestion list is a name-prefix list, exactly what
the stock product showed. The client-side exclusion of the edited entity is
the only filter — the stock's select2 "already selected" behaviour — and
needs no server rule. The 250 ms debounce and limit 10 are the stock
numbers, so result-set cost matches the product being replaced.

### DD-340. Full-replace save, ACTIVE-only seed, `DELETED` edges stay dead (Java parity)

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-05

**Decision.** A save sends, for every picker the form rendered, that key's
full value in `relationshipAttributes` — a list of one object per chip for a
`SET`/`LIST` field, the one object (or null when emptied) for a `SINGLE`
field, no `relationshipGuid` (EDT-16). The merge also drops the rendered
keys from `attributes`, so the picker is the only writer of the key. The
seed keeps only `relationshipStatus: "ACTIVE"` entries (EDT-15) and a
`DELETED` entry is never echoed back. A removed edge whose entity is picked
again stays `DELETED` in the store — the port keeps Apache Atlas 2.4's
reading, and the editor's UI says the edge is gone (no chip) even while the
read still lists it tombstoned.

**Reason.** Probed against the live server in every direction: an omitted
key is untouched (so the pass-through rule of EDT-06 keeps working for
unrendered keys), a present key is a full replace (the server marks edges
dropped from the list `DELETED` and keeps them in the read — the seed rule
exists because of that), `[]` clears all edges, and a client-made
`relationshipGuid` on a new entry changes nothing (the array path maps by
position and label; only the import mode honours a given edge guid,
`RelationshipMapper._map_object_id` / `RelationshipMapper._get_or_create`).
A `SINGLE` key clears with null, not `[]` — probed: `[]` answers 400
`ATLAS-400-00-021` "ObjectId is not valid []", and null answers 200 with the
edge `DELETED`. Null alone is not enough when the def carries the same name
as a plain attribute too: the server moves an `attributes` copy of a
relationship-named value back into `relationshipAttributes` and it re-
attaches the edge (`compactAttributes` / EWR-06, probed on `hive_table.db` —
the edge stayed `ACTIVE` until the `attributes` copy went too). Dropping the
rendered keys from `attributes` is therefore part of the save rule, and it
makes the picker the key's only writer.
The re-add case was probed three ways — bare re-add, re-add with a fresh
edge guid, re-add with the tombstone's original edge guid — and the server
keeps every one `DELETED`. That is Java parity, not a port bug: Java's
`EntityGraphMapper#mapArrayValue` finds the current edges by label (in any
state), `updateRelationship` returns the current edge untouched when it
already reaches the wanted target, and only `activateEntityRelationships`
flips a `DELETED` edge back — for an entity the import reactivates, never
for a live update. The relationship API refuses the pair too
(`RELATIONSHIP_ALREADY_EXISTS`, probed: 409 ATLAS-409-00-004), so no client
path revives a tombstone on either product. The editor therefore must never
echo a `DELETED` seed entry: the seed filter is what keeps a reopened editor
from silently re-listing a removed relationship.

**Alternatives.** (a) Fix the server to revive a re-added edge (refused —
the expected responses come from the Apache Atlas 2.4 source and its tests
(ADR 052); Java keeps the edge `DELETED` on a live re-add, and the
reactivation rule that exists there, `activateEntityRelationships`, is
already ported as IMP-04). (b) Echo the seed's `relationshipGuid`s on kept
entries so the server "updates" the right edge (refused — the array path
ignores a given guid outside import mode, probed; the position-based
current-edge lookup already keeps a kept edge untouched and exact). (c) Show
`DELETED` entries as struck-through chips the user can delete again (refused
— they are not relationships; Java's own read lists them for audit, and this
product's details screen does not show them either).

**Consequences.** A user who removes a relationship and re-picks the same
entity sees a chip, and the save reports success, while the store keeps the
edge `DELETED` — the same silence Apache Atlas 2.4 has. The rule lives in
the spec's EDT-16 so the behaviour is named, not discovered. The spec's e2e
avoids a re-add assertion (it can only assert parity).

### DD-341. The picker component lives in the webapp; the chip leads with the entity type

- **Status:** Proposed (the `iconsByType` refusal superseded by
  [DD-378](../7-21a-details-sections/design.md#dd-378-the-type-to-icon-map-enters-the-webapp-the-badges-lead-with-their-icon)
  — the map now ships; the chip's word lead stands, by its dictionary
  display name since
  [DD-379](../7-21a-details-sections/design.md#dd-379-type-and-classification-names-render-their-dictionary-display-name))
- **Increment:** 7.7c
- **Date:** 2026-11-05

**Decision.** The picker is one webapp component
(`entity-relationship-input`), not a ui-library component. It reuses the
ui-library chip (UIC-16 with the UIC-24 delete) and the DD-335/DD-336 box
anatomy via the editor's own SCSS. The chip's lead word (the
`leadLabel`/`leadColor` inputs DD-189 added) is the chosen entity's own
`typeName` in the `is-info` colour — the term chip's pattern (EDT-14).

**Reason.** The ui library is the dumb-component contract of 7.2: a
component there takes data and emits events, and never injects an HTTP
client. The picker's whole job is a live `searchUsingAttribute` round trip,
which is data-access wiring; the classification box beside it — the same
anatomy — sits in the editor for the same reason. The webapp's editor owns
the search service (7.3) and the box already lives at
`search/editor/`. The chip lead stands in for the legacy's `iconsByType`
type icon: that map is app metadata the webapp never ported, and the term
chip's word lead ("Term", DD-189) proves the chip renders a word lead
without a new part. The target type as the word tells the user what the chip
is — which two shipped pickers (a `DataSet`'s `model` and its `schema`, both
pointing elsewhere) need — and costs no catalogue string.

**Alternatives.** (a) A ui-library `relationship-input` component (refused —
it would need the search injected, breaking 7.2's dumb rule, or a second
component with an output-callback round trip that duplicates what one
webapp component does directly). (b) Port an `iconsByType` map (refused —
hundreds of type→icon entries of legacy app metadata, no shipped screen
indexes them, and DD-189's colour/word inputs exist exactly so chips need no
icon). (c) Lead with the relationship name (refused — it repeats the field
label above the box).

**Consequences.** One more webapp-private control beside the editor and the
box; the ui library is untouched, so no story and no UIC rule joins (7.7a's
acceptance precedent). Chip wording is English `typeName` text — the same
raw type names the details screen's `type-name` component already prints.

### DD-342. The save's in-flight state is named as a rule; its dead CSS joins this increment

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-05

**Decision.** Two changes, one rule. (a) While a save is in flight, the
Save button also carries Bulma's `is-loading` class (the CSS spinner the
framework ships) beside the disabled + `aria-busy` state 7.7a already
applied. (b) The whole in-flight behaviour — from the click until the
server answers (the span `editor-state.save()` guards), spinner, disabled
button, and the `search.services.entityUpdate.save` status line under the
footer — becomes a named rule, EDT-18, with a unit test that watches the
states across a flush and an error.

**Reason.** A user reported that a save on a slow server looked like
nothing happened. The mechanism was there and works, but its signal is
one notch of button fade — on a two-second POST a working save and a
dead one looked the same. Bulma's `is-loading` is the framework's own
answer, adds no string (SHL-08) and no SCSS, and what shipped untested
had no rule id to keep it working (7.7a's acceptance predates the
convention that shipped behaviour carries a named test). The failure path
stays as 7.7a designed it (EDT-08: the drawer stays open, the alert rides
the Alerts bell) — a slower-server notification redesign is out of scope
here.

**Alternatives.** (a) Move the failure alert into the drawer (refused —
EDT-08 is accepted 7.7a behaviour, and a changed decision needs its own
increment). (b) A new in-flight visual treatment (refused — Bulma's
spinner plus the existing status line is the smallest visible signal).
(c) Leave it untested (refused — EDT-18 is one unit test).

**Consequences.** One class binding on one button; no new strings, so
SHL-08 and the catalogue gates are unmoved. The rule joins 7.7c's spec
because the increment owns the editor right now; the 7.7a spec is not
edited (accepted records do not change).

### DD-343. An empty focused picker browses five candidates; the panel copies the classification box

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** A picker whose box gains focus with an empty input runs the
same `searchUsingAttribute` round trip with no prefix and `limit` 5 — a
browse of up to five entities of the target type — instead of an empty
panel; clearing the text back to empty browses again. The panel's
placement adopts the classification box's shipped treatment verbatim:
Bulma's `is-up` (the list opens over the fields above the box) with
Bulma's own `0.25rem` menu offset — no custom geometry on the picker.

**Reason.** A user trying the pickers reported both: the empty box gave
no hint of what could be picked (the legacy select2 opened a list on
focus too), and the panel's placement read wrong twice over — first a
slit of dead space below the box, then (after a flush fix) an overlap of
its border. The user named the fix: "the classifications input does this
well already". The box's `is-up` + offset geometry measures a clean ~3px
of clearance with no overlap, and the pickers sit where the box sits —
low in the form, above other controls — so the same placement is the
right one here too. The server probe (dev store): `attrValuePrefix=""`
is a valid `startsWith ""` filter that matches every entity of the type,
and the omitted parameter behaves the same — the browse is the stock
search with an empty prefix, no new endpoint. Five is the suggestion
count, not the search's page: typed search keeps the stock's 10 (DD-339).

**Alternatives.** (a) Keep the empty panel (refused — the user's
intuitiveness report; the legacy picker's focus-opened list is the parity
behaviour DD-339 retargets). (b) Browse with `limit` 10 (refused — the
panel is a hint, not a results page; five keeps it glanceable, and typed
search gives the full ten when the user actually looks). (c) Re-browse on
every focusin inside the box (refused — chip→delete tabbing would refire
the search; one browse per box entry). (d) Zero Bulma's offset and hang
the panel flush below the box (refused — measured: the panel's rounded
shadow overlaps the box's border; the user preferred the box's treatment
outright, and one geometry across both controls is the smaller surface).

**Consequences.** The browse's exclusions are the typed search's (chosen
entities and the edited entity never show). A type with no entities shows
an empty panel exactly as a no-match search does. One class on the
wrapper and one `searchFor` extraction in the component; the component
SCSS keeps no offset rule of its own (Bulma's `is-up` carries it); no new
strings (SHL-08). The e2e's typing scenarios are unaffected — Playwright's
fill focuses and types within the debounce window, so the browse request
never fires — and an upward panel keeps its rows visible, as the box's
e2e scenarios already rely on.

### DD-344. The shared select's placeholder rides a static empty value

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** The ui-library `select`'s placeholder option carries a
static `value=""` attribute, not the `[value]=""` binding it shipped with.
A null model now lands the control on that option, so an unchosen select
shows its `-- … --` placeholder text (UIC-14 amended, 7.13 spec).

**Reason.** A user opening the editor's create drawer found the "Entity
type" select blank: no chosen type, and no placeholder to say so.
Live-probed: Angular's `[value]=""` writes the property, which for an
option falls back to its label text — no content attribute is left, so
`option.value` reads `"-- Please select a value --"`, ngModel's `""`
matches no option, `selectedIndex` stays `-1`, and the native control
renders an empty box. A `value=""` attribute makes the match and the
placeholder shows. The same defect blanked every consumer whose model
starts null — the create drawer is the shipped one (the settings theme
select always binds a row, so it never showed). Fixing it inside the
shared component (rather than a caller workaround, e.g. a synthetic empty
first row) keeps the placeholder UIC-14 describes real for every call
site; the ui library stays HTTP-free and its dumb contract holds.

**Alternatives.** (a) The editor passes its own first row (refused — the
component already owns the placeholder option; a caller-side fake row
duplicates it and re-appears at the next call site). (b) Accept the blank
box (refused — the user's report; a required select that renders nothing
before the pick looks broken). (c) Keep the binding and select option 0
in code (refused — the DOM's reflection rule is the root; the static
attribute is the one-line cause fix).

**Consequences.** One attribute in the shared template; the regression
test ("shows the placeholder in the control while nothing is chosen")
pins the rendered selection, which every earlier test read through
`optionLabels()` and could not see. The record joins this increment's
design (the increment owning the editor now, DD-337's precedent); the
7.13 UIC-14 row is amended, accepted text aside.

### DD-345. The details screen renders bare into the layout's container

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** The details template drops its own `section.section >
div.container` wrapper and renders its boxes directly, like the browse
screen does. The search layout owns the page inset (DD-150, placed with
the layout per DD-218); the details screen is its second consumer to use
it as intended.

**Reason.** A user compared the details page against the browse page and
reported a margin around the edges that "doesn't align with the title or
search bar/plus button". Measured live: the layout insets every routed
page once (its `section.section > div.container`), and the details
template opened a second pair, so its boxes sat one container in from
every other screen — 96px vs 48px on a 1418px viewport, and the boxes'
right edges stopped short of the hero's `+` button. DD-218 already names
the rule ("the pages render top-level, the layout insets them"); details
was the only page breaking it. Measured again after the fix: header box
and browse card share one left edge, and both right edges meet the `+`
button's.

**Alternatives.** (a) Give the layout a per-route inset (refused — one
inset is the rule DD-218 set, and one page broke it). (b) Keep the
wrapper and shrink its padding (refused — a second container is dead
structure, and its `.container` max-width re-centres the page rather than
aligning it).

**Consequences.** The template header and SCSS header comments no longer
claim an own inset. No selector changes: the specs and e2e drive the
`.aurelius-details-*` classes, none of which named the wrapper, and the
`.aurelius-details` class itself had no consumer and left with the div.
DET-01's rule text never named the wrapper, so the 7.6 spec stands.

### DD-346. The editor pencil is the demo's bare link-blue edit icon

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** The details header's edit button is a chromeless button
holding `<span class="icon is-large has-text-link">` around FA6
`faPenToSquare` at `size="2x"` — the demo's edit affordance, measured
live: a 48px icon box, a 32px pen-to-square glyph, link blue
(`rgb(0, 115, 221)` = the theme's `$blue`/Bulma `link`), no border, no
fill. Bulma's `is-ghost`, the `faPen` glyph (f304), and the first fix's
keppel bordered pill (f303 `faPencil`) all leave. The sheet resets the
UA's button chrome (no Bulma `button` class is applied) and adds a
`:focus-visible` outline, which the demo's plain anchor gets from its
own focus styling.

**Reason.** The user compared the button against the live demo twice.
The first fix read the vendored legacy dashboard (`buttons_tmpl.html`,
`btn btn-action btn-sm`, `fa-pencil`) because the demo would not load
(its Keycloak login looped) — and was wrong on all three counts the user
named (colour, style, icon): the demo at `google.aurelius-atlas.com` is
not the vendored v3 dashboard but a newer Angular app (Bulma + FA6,
M4I components) whose details header renders
`a.icon.is-large.has-text-link` with `fa-icon size="2x"` of FA's
`fa-edit` — in FA6 that icon is `faPenToSquare` (f044), and the demo's
link blue is exactly this theme's `$blue` mapped to Bulma's `link`
(SHM-04), so `has-text-link` lands on the same colour natively. Measured
after this fix: the same glyph, the same blue, the same 48px bare box.

**Alternatives.** (a) The legacy `btn-action` keppel pill, `faPencil`
(refused — the first attempt at this record; the user reported "wrong
color, style and different icon" — the vendored dashboard is not what
the demo shows). (b) `is-info is-light` or any Bulma button variant
(refused — the demo's icon has no button chrome at all). (c) The bare
`fa-icon` without the `icon is-large` box (refused — the box is the
demo's hit target and spacing, and the repo idiom: `details-navigation`
and the navbar carry their glyphs the same way).

**Consequences.** The EDT-09 unit test pins the glyph by identity
(`icon()` is `faPenToSquare`) — the second unnoticed-glyph lesson after
DD-344. The e2e selector (`button.aurelius-details-edit`) and the
`aria-label` are unchanged; the button keeps keyboard semantics the
demo's anchor only gets from its href. Any future parity work that
cites "the demo" must measure the live app first — the vendored v3
source under `apps/aurelius-atlas-dashboard` is the legacy baseline for
REST/behaviour, not the look of the demo's newer UI.

### DD-347. The editor's commit pair moves to the drawer's foot bar

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** The Drawer gains a fixed foot bar: content with the
`drawer-footer` attribute projects into it, below the scrolling body
(UIC-25). The editor moves Save out of the drawer head into the bar and
adds Delete beside it (EDT-19). Delete shows in edit mode only and only
for a holder of the `atlas-write` grant (EDT-09's seam). The hold IS the
confirm: no modal, no second click. A completed hold sends
`DELETE /api/atlas/v2/entity/guid/{guid}` with no `deleteType` (EDL-04,
the server strategy), closes the drawer, and lands on browse. A refused
or failed delete alerts through the alerts store (EDT-08's shape) and
keeps the drawer open. The busy pair (the spinner, `aria-busy`, and the
status line) rides the acting button in the bar (EDT-18 amended). The
strings reuse catalogue keys (`search.components.editor.delete`,
`search.services.entityDelete.delete`), so SHL-08 holds.

**Reason.** The user reported the head crowded once the editor grew the
pickers, and asked for a static footer with the save and delete buttons.
The legacy editor had exactly that shape (its footer: Delete holdable
beside Save, delete lands the user on the search screen), and the demo
app carries the same footer. The settings and alerts drawers never
project a footer, and the bar hides while empty (`:empty`), so the slot
is additive.

**Alternatives.** (a) Keep Save in the head and add Delete beside it
(refused: the user asked for the head to hold the title and the X only).
(b) A confirm modal for delete (refused: the legacy pattern is the hold,
which the user named. A modal would also add a string the frozen
dictionary cannot carry). (c) Land on details after a delete (refused:
the deleted entity has no details to show. The legacy lands on search,
browse here).

**Consequences.** The e2e selector `button.aurelius-editor-save` is
unchanged, so EDT-12's scenarios ride it as they are. EDT-10 in the 7.7a
spec is amended in place (PR #258 has not merged), and its deferral row
for the delete flow now defers only the UX polish the legacy never had
(tooltips, keyboard hold). The delete itself leaves 7.9's plate.

### DD-348. The hold-to-confirm directive is a ui-library port, pointer-only

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** `aurelius-atlas-ui-hold` (the `Holdable` directive) lives in
the ui library. It listens to pointer events: pointerdown starts a 50 ms
sweep, and pointerup, pointerleave, or pointercancel before the time ends
fires `held(false)`. After `holdFor` seconds (default 3) it fires
`held(true)` once and stops the sweep. While held it writes the fraction
(0 to 1) into the host's `--aurelius-hold-progress` custom property. The
caller paints any progress itself, so the directive carries no colour
(UIC-03). The Delete button's look (the donut that grows over the hold) is
DD-349's.

**Reason.** The reference (`models4insight-holdable`, Aurelius 17) is a
reusable directive on the same mechanic: a timer on mousedown, a cancel on
mouseup or leave, a confirm at the deadline. Pointer events cover mouse
and touch in one set, so a phone confirms a delete too. The legacy's
mouse-only listener does not. The ring belongs to the caller because the
ui library bans literal colours (UIC-03) and the ring is the Delete
button's design, not the directive's. A keyboard hold is out: the legacy
never had one, and a hold needs a keydown/keyup pair with its own focus
story (deferred, in 7.7a's deferral table).

**Alternatives.** (a) Keep the directive in the webapp (refused: the shape
is reusable chrome with no data wiring, which is the ui library's line
per UIC-15). (b) Copy the legacy's mousedown/mouseup (refused: it drops
touch, and pointer events are the modern superset). (c) Drive the fill
with a Web Animations keyframe (refused: the caller's CSS needs the live
fraction anyway, and a custom property keeps the directive paint-free).

**Consequences.** The directive carries no text of its own: the legacy's
`holdable.tooltip.single/plural` strings ride the caller's button, not the
directive (the caller carries the tooltip, DD-351, and EDT-19). The spec drives timers
with `vi.useFakeTimers()`, because the zoneless test env runs no
`fakeAsync`. The editor's spec fires the directive's output directly
instead of replaying a pointer sweep. The sweep itself is specced at the
directive's own spec.

### DD-349. The Delete's hold fills a donut that grows over the hold's seconds

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** The Delete is a solid danger button (Bulma's `is-danger`).
While the hold runs it behaves like Bulma's own `is-loading`: the label
clears (Bulma's `color: transparent`, so the button keeps its width) and a
donut appears in the spinner's place. The donut is the spinner's look, an SVG
circle stroked 2px in `--bulma-loading-color` at 1em, centred where the
`is-loading` spinner sits (on the danger fill that token is the light text
colour, so the ring reads on the red, as Bulma's own spinner does). The
circle carries `pathLength="1"`, so one CSS animation of
`stroke-dashoffset` (1 to 0) draws the ring clockwise from the top (the SVG
rides a quarter turn). The animation plays exactly once (`forwards`): its
duration is the hold's own seconds, which the template binds once
(`--aurelius-hold-duration` from `deleteHoldSeconds`) and hands to both the
directive and the ring, so the drawing and the clock cannot drift apart, and
at the end of the run the ring is fully closed and stays there. An early
release drops the holding state, which removes the animation, so the next
press draws afresh.

**Reason.** The reviewer asked for a donut like the loading spinner that
fills clockwise over the hold. An SVG stroke is anti-aliased, so its edges
are smooth. A CSS mask over a bordered box (the first cut) re-clips with
hard, jagged edges, and a conic-gradient `mask` is aliased the same way. The
spinner's own anatomy (2px stroke, `--bulma-loading-color`, 1em, centred) is
what a user already reads as "working", so reusing it makes the hold legible
alongside the caller's tooltip (DD-351). Driving the length from one number
keeps the ring and the confirm in step.

**Alternatives.** (a) A CSS `mask` conic over a bordered circle (refused:
aliased, jagged edges). (b) The directive sweeping a `--aurelius-hold-progress`
custom property the caller fills each frame (refused: per-frame JS, and the
reviewer wanted a CSS animation timed to the hold). (c) Canvas (refused: no
markup, and a stroke is simpler). (d) The ring inside the button's edge, the
shape first shipped in this increment (refused: the reviewer wanted the
spinner-like donut in the label's place; the solid danger fill the reviewer
also asked for stays).

**Consequences.** The look rides the caller's SCSS, not the directive
(UIC-03, and the directive stays paint-free per DD-348). The SCSS shows the
donut on the directive's `data-aurelius-hold="holding"` host attribute, so
that attribute must carry the literal word (the directive writes it
imperatively; a `@HostBinding` on a signal stringifies the Signal object, not
its value, and the states never match). `@property` is not needed:
`stroke-dashoffset` animates natively. The in-flight DELETE keeps Bulma's
real `is-loading` spinner (EDT-18), so the button shows the growing donut
while held and the stock spinner while the request runs. The editor spec
asserts the donut markup, the danger class, and the shared duration number;
the animation itself is reviewed in the Storybook mock (`Holdable`, Closing
once), whose play() test asserts the one play and the closed end.

### DD-350. The commit pair rides Bulma's `buttons` container, normally sized

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** The Delete and Save sit in Bulma's `buttons is-right` container
(the reviewer asked for the button guide's spacing, and normal size). The
carrier div lost its hand-rolled `display: flex` and `justify-content:
flex-end`. Bulma's container carries the display, the `0.75rem` gap between
the buttons, and the right alignment. Both buttons dropped `is-small`, so
they take Bulma's normal control size. The editor's own SCSS keeps one rule
only: the projected foot div grows across the drawer's foot bar, because
that bar is a flex row and a content-sized child cannot reach the right
edge.

**Reason.** Bulma's Button documentation makes the `.buttons` container the
only way a group of buttons gets its spacing (the gap), and a bare flex div
re-invents it badly. The hand-rolled pair had no gap at all, and its
right-alignment never worked: the child sized to its content, so pushing its
own content right moved nothing. The reviewer also asked for the normal
size, which in Bulma is the absence of a size class.

**Alternatives.** (a) A `gap` on the existing hand-rolled div (refused: the
button guide's own container exists, and reusing it retires the custom
rule). (b) Keep `is-small` (refused: the reviewer asked for the normal
size).

**Consequences.** The Holdable stories drop `is-small` too, so the mock and
the app show the same button. The mock's pinned demo button keeps its inline
`font-size` (that is the story's enlarged display, not a size class). The
drawer's foot story already used `buttons is-right`, so the two screens now
share one idiom.

### DD-351. The Delete carries the legacy hold tooltip; its key is vendored

- **Status:** Proposed
- **Increment:** 7.7c
- **Date:** 2026-11-04

**Decision.** The Delete carries a tooltip that says "Hold for 3 seconds",
the legacy directive's own words. The reviewer asked for a hold
instruction. The string is the Aurelius `holdable.tooltip.single` /
`holdable.tooltip.plural` pair (the legacy directive's own translation
file), vendored into both dictionaries and both catalogues. Singular rides
one second, plural rides any other count, the legacy's rule. The caller
(the editor) carries it as the button's native `title`, so the directive
stays text-free (DD-348). The Holdable and drawer stories show a static
"Hold for 3 seconds" tooltip, since a story owns no dictionary.

**Reason.** A hold is not obvious: nothing says a click does nothing, so
the tooltip is the instruction. The legacy shipped the same string on the
same control, so this restores rather than invents. The native `title` is
the app's own tooltip idiom (the classification chip's description uses
it, and the legacy chip's tooltip was a `title` too), so it needs no
overlay component, no positioning, and no colour (UIC-03). The number
rides the one `deleteHoldSeconds`, the same value the directive and the
ring already share (DD-349), so the words cannot disagree with the clock.

**Alternatives.** (a) A hand-written literal "Hold to delete" in the
template (refused: SHL-08 keeps every shown string in the catalogue, and
the legacy string already says this better, with the count). (b) The
directive writing its own `data-tooltip`, as the legacy did (refused:
DD-348 keeps the directive paint-free and text-free, and the ui library
has no dictionary to read). (c) A Bulma or ui-lib tooltip component
(refused: none exists, and a `title` is what the legacy used).

**Consequences.** This is the increment's one dictionary addition, against
the "no key is added" line every EDT rule repeats (SHL-08). The vendored
JSON fixtures and both XLIFF catalogues gain the pair, so
`i18n-completeness` (SHL-08) stays green and names the keys rather than
dropping them. The Dutch text is new (the legacy `holdable` file ships
English only) and follows the catalogue's existing style, which
`i18n-completeness` then holds to. The tooltip stays through the hold: the
animation only clears the label's colour (DD-349), and the ring carries the
countdown. The 7.7a deferral row now defers the keyboard hold alone, not
the tooltip.
