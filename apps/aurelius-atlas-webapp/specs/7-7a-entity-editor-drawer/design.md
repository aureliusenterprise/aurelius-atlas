# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-322. The editor is the drawer outlet's third panel, not a full-screen route

- **Status:** Proposed
- **Increment:** 7.7a
- **Date:** 2026-11-03

**Decision.** The entity editor is a routed component in the app-root `drawer`
aux outlet, beside the settings panel and the alerts panel (DD-166's shape):
the details pencil navigates the outlet to `edit-entity/<guid>`, the search
hero's `+` to `create-entity`, and dismissal navigates the outlet away (EDT-01).
The primary screen underneath does not change. The editor owns its entity
read (EDT-02) and shares no store with the screen below it.

**Reason.** The user set the direction on 2026-11-03: "I'd like the editor to
be in a drawer similar to the alerts and settings drawers." The legacy editor
is a full-screen route (`/search/edit-entity/:id`), and its store hand-off
(the shared `EntityDetailsService` the resolver primes) is the reason: the
legacy details screen and editor talk through that store. This product's
7.20 details screen fetches its own entity (DET-08) and the ui-library drawer
(7.16) already ships the scrim, focus trap, and dismissal set the editor
needs. Keeping the screen underneath is also the 7.20 lesson: the URL of the
details screen stays the entity's address while the user edits it.

**Alternatives.** (a) The legacy full-screen route (refused — user direction;
and it trades away the context the drawer keeps for free). (b) The ui-library
modal (refused — the user named the drawer, and the long form scrolls in the
drawer's body today; the modal's card anatomy fits a short confirm, not a
form). (c) Sharing the details screen's `DetailsState` (refused — two screens
writing one store is the coupling the legacy resolver clears around; the
editor's one extra read is cheaper than the staleness).

**Consequences.** The outlet swaps: opening the editor closes the settings or
alerts panel, and the open state rides the URL (DD-166's semantics, tested
there). The routed-panel pattern repeats a third time: `active = true` for
the component's life, dismissal flips it and navigates the outlet away. The
e2e drives the drawer through the outlet, as the alerts scenarios do.

### DD-323. One generic entityDef-driven form replaces the ten hand-written forms

- **Status:** Proposed
- **Increment:** 7.7a
- **Date:** 2026-11-03

**Decision.** The editor renders one form built from the entity's own entity
definition (EDT-03): `name` and `definition` fixed, every other attribute one
input by its attribute type (string, numeric, boolean, date, enum, multi),
unique attributes other than `name` disabled, and relationship attributes
absent until 7.7b. The form model is a pure helper: typedef in, field
descriptors and a merge function out. The legacy's ten hand-written `m4i_*`
editor forms are not ported.

**Reason.** The legacy picks the form from a static map of ten `m4i_*` type
names (`editors-by-type.ts`); every one of them carries the old product's
governance fields (`businessOwner`, `dataDomain`, `inputToProcesses`, …) on
types this server never answers (the 7.6/7.20 deferral of the m4i types).
Porting them verbatim would ship ~2,400 lines with no type to render. The
type definitions the server already serves carry the same knowledge the ten
templates encode by hand — the field list, the types, the enums, the
multiplicity — so the generic form needs no new server endpoint and no new
client method (`TypeDefsService` exists since 7.10). The user chose this
option for 7.7a on 2026-11-03 over hand-written forms per shipped type.

**Alternatives.** (a) A hand-written template per shipped Atlas type
(DataSet, Process, Entity) (refused at the user's choice — it duplicates the
typedef knowledge the server has, and every added type means a new template;
the generic form covers them at once). (b) Pull in Formly (refused — the
legacy does not use it, the field surface here is small, and a form
generation library is a dependency this slice does not need). (c) Ship only
`name`/`definition`/classifications and no other attributes (refused — every
string attribute of the shipped types is worth editing, and the generic form
costs nothing extra once the descriptor mapping exists).

**Consequences.** A field label for an attribute the catalogue does not know
is the attribute's own name — per-attribute translation of invented types is
out of reach for any client, and the shipped types' two important fields
(`name`, `definition`) ride the catalogue keys the fixtures already carry.
The deviation is Aurelius-product (the legacy form family), not Apache Atlas:
Atlas's own dashboard edits the same fields from the same type metadata, so
this choice moves toward Atlas, not away. `deviations.md` gains no row (the
7.20 reasoning: the difference is from the Aurelius product). 7.7b adds the
relationship attributes as their own field kind; the descriptor seam is
already there.

### DD-324. The affordance gate reads `atlas-write` from the token, not `DATA_STEWARD`

- **Status:** Proposed
- **Increment:** 7.7a
- **Date:** 2026-11-03

**Decision.** The details pencil and the search hero's `+` render only when
the signed-in token holds the `atlas-write` role of the server's client: the
claim path is `resource_access.<atlasClientId>.roles`, and `atlasClientId` is
a new key of the runtime configuration (`config.json`, served per deployment,
defaulting to `aurelius-atlas-server` — the server's own `auth_client_id`,
settings.py). The check is a signal reader on the `Session` service. The
editor route itself stays ungated (EDT-09).

**Reason.** The legacy gates the two affordances with
`*models4insight-keycloak-role-permission="'DATA_STEWARD'"`, a realm role of
the old product's identity provider. This product's authorizer is the four
client roles of the server's client — `atlas-read`, `atlas-write`,
`atlas-types`, `atlas-admin` (DD-300, AUZ-01/AUZ-02) — and `DATA_STEWARD` is
none of them, so a verbatim port would hide the editor from every user this
realm can mint. The browser's own token already carries the answer: the dev
realm mints the server-client roles into `resource_access["aurelius-atlas-server"]`
of the webapp's `aurelius` client tokens (verified against the dev realm on
2026-11-03), and the server enforces exactly that claim on every write (AUZ-07).
Gating the affordance on the claim the server enforces keeps the lie
impossible: what the user can click, the server accepts.

**Alternatives.** (a) Keep `DATA_STEWARD` (refused — no holder in this
product's realm; the affordance never appears). (b) Ask the server whether
the user may edit (refused — no such endpoint, and the roles are already in
the token the client holds). (c) Show the affordances to everyone and let the
write 403 (refused — a pencil that always fails is a defect the user finds
alone; the legacy also gates the buttons, and this is the same shape with the
right role).

**Consequences.** The runtime configuration grows one key: `config.ts`, the
dev `dev/config.json`, and the webapp chart's `configmap-config.yaml` plus its
values (the template lists the keys by hand, so the chart and its render test
change in this PR too). The webapp `AGENTS.md` records the pairing: the key
names the client whose roles the server's authorizer reads — change it with
the server's `auth_client_id`, like the issuer pair before it. Token roles are
read once per page load, so a role grant lands at the next reload, not
mid-session. The dev realm's `aurelius-writer` holds `atlas-write` and the
e2e sign-in user is `aurelius-writer`, so the e2e writer scenario needs no new
identity; a reader scenario asserts the affordances' absence for the realm's
`aurelius-reader`.

### DD-325. Create sends a negative temporary guid; the server's `guidAssignments` names the entity

- **Status:** Proposed
- **Increment:** 7.7a
- **Date:** 2026-11-03

**Decision.** The create payload carries a client-made negative numeric
`guid` and a uuid `qualifiedName`; the server assigns the real guid, and the
editor navigates using the real one from the response's `guidAssignments`
(EDT-06). What the legacy sentinel loses is its other role — the create/edit
discriminator several shared-store components tested with
`guid.startsWith('-')`; here the mode rides the route segment (EDT-01).

**Reason.** The server reads the guid's shape (live-probed on the dev
server, 2026-11-04): a negative numeric guid is accepted as a new entity —
the server assigns the real guid and echoes `{"<temp>": "<real guid>"}` in
`guidAssignments` (EWR-13) — while a uuid-shaped guid is read as a reference
to an existing entity and the write is refused with
`ATLAS-404-00-00A "Referenced entity <uuid> is not found"`. The webapp's own
e2e seed helper (`_seed_entities`, 7.4a) already creates through this idiom
with guids `-0`, `-1`. The `qualifiedName` seeding is a client job either
way: omit it and the server refuses with "mandatory attribute value missing
in type Referenceable" (also probed).

**Alternatives.** (a) A uuid temporary guid (first draft of this entry —
refused by the probe above: the server reads a uuid guid as a real
reference). (b) Send no guid at all (works — the server invents its own
negative key — but then the `guidAssignments` key is not knowable by the
client, and the real guid must be read from `mutatedEntities.CREATE[0]`
instead; the negative-client-guid keeps one lookup path for both the single
create and the deferred bulk).

**Consequences.** The payload shape stays what the server already accepts
and the e2e helpers already send. A user-visible consequence: after create,
the address is the server's guid, never the temporary one.

### DD-326. Classifications save through the add/remove diff, not the replace call

- **Status:** Proposed
- **Increment:** 7.7a
- **Date:** 2026-11-03

**Decision.** After the entity POST succeeds, the editor applies the
classification difference between the tag box and the entity's own
classifications at load (the same diff the legacy `EntityUpdateService`
runs): the tags gained ride one
`POST /api/atlas/v2/entity/guid/{guid}/classifications`, the tags lost ride
one `DELETE /api/atlas/v2/entity/guid/{guid}/classification/{name}` each, and
a kept tag sends nothing. The editor's tag box shows only the classifications
the entity owns (`entityGuid` equal to the entity's guid); classifications
propagated from other entities appear on the details screen but not in the
form, so the diff can never touch them (EDT-05).

**Reason.** This entry first specified the replace call
(`PUT .../classifications`, CLS-08) on the ground that the 7.7a form is the
whole own-classification set, so a replace says what the form says. That
premise failed against the fact: `updateClassifications` on both sides
(Apache Atlas 2.4's `EntityGraphMapper`, and this product's port in
`aurelius_atlas_core/entity_classifications.py`, covered by
`test__entity_classifications.py`) _changes attached tags_ — every given
classification must already be attached to the entity, and a name the entity
does not carry answers `CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY`. A live
probe against this server confirmed it end to end: a create mode's new tag
through the PUT answers 400/404, and through POST-add plus DELETE it lands
and reads back (204/204). The replace also cannot remove: a tag missing from
its body stays attached. Only the diff expresses attach-and-detach.

**Alternatives.** (a) The replace call (refused — factually broken, above;
this entry's first shape, corrected in the same increment before any
acceptance). (b) Send classifications inside the entity body (refused — the
server ignores them there; the deferral table in 2.4 says so).

**Consequences.** A save's writes are 1 (entity) + 0..N + 0..M calls; a save
that only touches attributes sends no classification call at all (the diff is
empty — cheaper than the replace's always-one). A refused classification
write leaves the entity saved (the steps are not one transaction, the
legacy's known shape carried forward), so EDT-08's failure alert fires with
the user's edits kept. Propagated classifications stay out of reach of the
diff, so a save cannot sever an inherited tag. Create mode: the gained tags
are stamped with the real guid from `guidAssignments` before the POST-add
(the attach names its entity, and a temporary guid is refused — live-probed).
The save fires the `EntitySaved` tick (DD-327) after the last write.

### DD-327. The save fires a one-way "entity saved" tick to the screen underneath

- **Status:** Proposed
- **Increment:** 7.7a
- **Date:** 2026-11-03

**Decision.** After the save's second call answers, the editor fires a
one-way event — a root-provided `EntitySaved` signal carrying `{guid, seq}`
— and navigates. A details screen that is already mounted for that guid
subscribes and re-reads its entity. The editor and the details screen share
no entity data, only the tick (the exception to DD-322's no-shared-store
rule, scoped to one event).

**Reason.** The drawer opens over the primary screen without changing it
(EDT-01), and the save navigates to the same URL the screen underneath
already holds — Angular reuses the mounted details component, its guid
effect sees no change, and without the tick the landed screen paints the
pre-edit entity. EDT-12's read-back (the new text on the details header
after a save) fails on the stale component. The seq counter re-fires on a
repeat save of the same guid and lets a screen mounted _after_ the save
(the create flow's landing) skip a tick its own URL read already answers.

**Alternatives.** (a) A route resolver priming a shared store (refused —
the DD-322 alternative (c), the legacy's coupling). (b) A forced outlet
remount on the save navigation (refused — the router has no clean "remount
the reused component" lever; a `:refresh=` query parameter would leak chrome
into the entity's URL). (c) No tick, and the e2e reloads the page before
the read-back (refused — the user would see stale data until a manual
reload; the legacy's full-screen editor never had this state, its save
always created the details component fresh).

**Consequences.** One tiny root signal joins the two screens' otherwise
independent reads; the tick carries only the guid, so it can never feed a
stale value. The editor's drawer component still owns its read end to end
(DD-322 holds for the entity, the event is not entity data).

### DD-328. The save's navigation is one compound outlet command, not a string path with a trailing outlet

**Status:** Proposed (correction found while proving the increment, before
acceptance — it replaces what the plan's step 1 said, so no accepted decision
changes.)

**Decision.** The save lands on the entity's details with one root compound
command — `router.navigate([{ outlets: { primary: ["search", "details",
realGuid], drawer: null } }])` — not the path form
`router.navigate(["/search/details", realGuid, { outlets: { drawer: null } }])`
the plan first sketched.

**Reason.** The router applies a trailing `{outlets}` command of a string-path
array inside the _primary child_ segment group the path walked into, not the
root group where the named outlet lives (router
`createUrlTreeFromSegmentGroup`/`updateSegmentGroupChildren`: the outlets map is
taken from the walked group's children, and a child the command list does not
name — here the root's `drawer` — is copied back untouched). So the path form
re-reads the details URL and leaves the `(drawer:edit-entity/<guid>)` segment
mounted: the e2e's URL assertion caught the drawer surviving its own save.
Unit tests cannot see this — they spy `Router.navigate` and never run the
router. The compound command anchors at the root (its first command is the
outlets map), which is also what `close()` and the settings and alerts panels
already use.

**Alternatives.** (a) A `relativeTo`-rooted string command (refused — same
anchoring rule, still not the root's own children; the compound is the
router's documented form for this). (b) Two navigations, one for the primary
and one to clear the drawer (refused — a double location change, and the
second can race the first's activation).

**Consequences.** The save navigation reads as one root-level instruction;
the same compound shape already closes the drawer from `close()`, so the
editor has one outlet idiom end to end. The e2e's URL identity assertion
(EDT-01's no-reload proof) is what pins this — the unit specs assert the
call, the e2e asserts the landed URL.

### DD-329. A datalist pick commits through `change`, and the chosen tags reuse the chip

**Status:** Proposed (correction found in review of the delivered drawer,
before acceptance — it adds what EDT-03 and EDT-05 must render, so no
accepted decision changes.)

**Decision.** Three fixes from user review of the running drawer. (a) The
classification input commits an add on both `keyup.enter` and the control's
`change` event, and clears itself only when the add actually happened. (b) A
chosen tag renders as the `classification-chip` component, not a plain Bulma
tag: the webapp passes the type's description as the tooltip, and the chip
gains a `deletable()` input (UIC-24) that seats a `button.delete.is-small`
inside the label tag and emits `remove`. (c) A boolean field renders with
Bulma's checkbox anatomy: a `label.checkbox` wrapping the input and a bare
text node.

**Reason.** (a) With the native suggestion popup open, Enter or a click
commits the value through the control's `change` event, never `keyup.enter`,
so the real-browser add path missed every pick, and the unconditional input
clear hid the failure. Playwright's `fill` plus Enter bypasses the popup, so
the e2e could not see it. A kept-on-miss input shows the user what did not
apply. (b) The legacy editor showed chosen classifications the way the
details screen shows them — as chips, like its relationship input — and the
details screen already reuses `ClassificationChip` (UIC-16), so the chip is
the shared atom and a new lib input is the smallest change. (c) The box sat
flush against its label text; Bulma gives the text its gap only when the
label wraps a bare text node, and a wrapper span drops it.

**Alternatives.** (a) A custom dropdown instead of the native datalist
(refused — the datalist works once `change` is wired; a custom popup is a
new component for no added rule). (b) A second chip component for the editor
(refused — the chip's lead, tooltip, and tag shape are identical; only the
delete differs, and Bulma's `tag > button.delete` is one conditional in the
shared template). (c) Keep the plain tag plus a separate delete button
(refused — the user asked for the legacy look, and two elements drift from
Bulma's insets; the unit and e2e selectors move to the chip's own classes).

**Consequences.** The editor and the details screen paint classifications
with one atom, so a future chip change lands on both. The lib's public API
grows two inputs and one output on `ClassificationChip` (UIC-24). The unit
specs and the e2e name the chip's delete class
(`.aurelius-classification-chip-delete`) and the host keeps
`.aurelius-editor-tag` on the chip element, so the tag-count and text
selectors stay the same.

### DD-330. The create type rides the drawer route, and the picker stays

**Status:** Proposed (refinement of the delivered drawer, from user review
before acceptance — it changes what EDT-04 renders, so no accepted decision
changes.)

**Decision.** The create route becomes `create-entity/:type?`. The bare
segment opens the picker alone. A type pick (or re-pick) navigates the
`drawer` outlet to `create-entity/<type>`; the editor seeds the entity from
the route parameter through the same `beginCreate` path (DD-325), and the
picker stays above the form as the "Entity type" field, selected at the
route's type, so switching types is a URL change. Editing renders the type
as static read-only text (the static label EDT-04 always required).

**Reason.** The user asked to switch the type after the first pick. With the
picker replaced by the form, a wrong pick abandons the drawer; with the type
in the path, the switch is one dropdown change, the URL names what the form
builds, and a reload of the drawer keeps the type. The route owns the mode
already (DD-325's "no store sentinel"), so the type belongs to the route
too — the component reads `:type` and the seed effect replaces the stored
entity, which clears the tag box and the typed fields (EDT-04's switch).

**Alternatives.** (a) A "Change type" link that clears the store signal and
shows the picker again (refused — the type vanishes from the URL, a reload
loses it, and a second "picker visible" state enters the component). (b) The
picker as a field with the switch kept in the store only (refused — the URL
would lie: `create-entity` with a Process form). (c) Reuse the `Select`'s
`disabled` for the edit-mode type (refused — it would send the entity's type
through the picker exclusion filter; plain text is what EDT-04 always said).

**Consequences.** The outlet's create URL is the type's address, matching
`edit-entity/:guid`. An in-flight switch shows nothing stale: the form gate
holds until the route arrives with the type. The form-rebuild signature
gains the type name so a switch to a field-less type drops the old form. The
drawer's `close()` and the save's compound navigation are unchanged (DD-328
holds). The spec's EDT-04 is amended in the same PR.

### DD-331. The required-fields notification sits at the top of the form and dismisses

**Status:** Proposed (usability fix on the delivered drawer, from user review
before acceptance — it changes where EDT-07's line renders, so no accepted
decision changes.)

**Decision.** The EDT-07 notification renders at the top of the form, above
the first field, with Bulma's notification delete button. The X hides the
line until the next Save attempt, which shows it again.

**Reason.** The line sat after the last field: on a wide type (the shipped
`aws_s3_object` carries a dozen fields) a failed Save on a short screen
showed only the yellow box below the fold — the user must scroll to find the
reason, then scroll again to find the field. At the top the reason is in
view when the Save bails. Bulma's `notification` already seats a `button.delete`
in the corner; its aria-label rides the drawer X's key (EDT-11's set, no new
catalogue key).

**Alternatives.** (a) Scroll to the first invalid control on a failed Save
(refused — the drawer scrolls with the page behind it and a programmatic
scroll moves the user's own position; the top line works with no motion).
(b) Hide the line once the form turns valid (kept — that already happens:
the gate is `form().invalid`); (c) dismiss forever (refused — a second
failed Save must say so again; the next Save resets the dismissal).

**Consequences.** The notification keeps its `role="alert"` announcement;
the dismissal is one local signal, no state leaves the component. The unit
spec pins the order (notification precedes the first field) and the
dismiss-then-save round-trip.

### DD-332. An invalid control paints with Bulma's `is-danger`

**Status:** Proposed (usability fix on the delivered drawer, from user review
before acceptance — it adds how EDT-07 shows the bad fields, so no accepted
decision changes.)

**Decision.** Every control with a shown error (the same `showError` gate as
the help line: touched, or a Save was attempted) carries Bulma's danger
state: text, number, date, and the multi rows take `is-danger` on the
control, a textarea on its `textarea` element, and the enum rides the
`Select`'s own `invalid` input (the lib paints `select.is-danger` + the
help line, UIC-14's shape). Red borders replace the invisible invalid state.

**Reason.** The drawer painted nothing on an invalid control: the error was
only the small help line under the field and the star by the label, easy to
miss on a dozen-field form (user report on `aws_s3_object`). Bulma's form
general guide defines `is-danger` as the control's invalid paint — the
red border is what the user asked to see, and it appears exactly when the
help line appears, so one gate drives both.

**Alternatives.** (a) A red label (refused — Bulma does not paint labels for
field state; the guide's control border is the convention). (b) Angular's
`ng-invalid` CSS without the class (refused — re-implementing the Bulma
palette; the class is the library's own signal). (c) Painting on every
invalid control before any touch (refused — a fresh form would open all-red;
the touched/attempted gate is EDT-07's existing rule).

**Consequences.** No SCSS of its own — Bulma carries the border and the
help-line colour. The enum path reuses the lib's shipped `invalid` input, so
the ui library changes not at all. The EDT-07 unit spec pins the class on
the name input after a failed Save.

### DD-333. The create `+` matches the demo's square cyan button

**Status:** Proposed (visual fix on the delivered drawer family, from user
review before acceptance — it changes no rule, only the button's Bulma
classes and icon seat.)

**Decision.** The hero's create-entity `+` (EDT-09) renders like the
demo's own: a default-size Bulma `button.is-info` with the plus seated in
a `span.icon.is-small` — the same icon idiom the search field's submit
button uses (UIC-05). It drops `is-small` and `is-primary`.

**Reason.** Ours carried `is-small` (2em against the 2.5em field and
submit button beside it) and `is-primary` (the brand turquoise, which
washes into the hero band); the bare `fa-icon` without the `icon` wrapper
made it 52px wide where the demo's is a 40x40 square. The demo's button
is `button.is-info` — cyan `rgb(23, 162, 184)` — and the brand theme
already maps Bulma's info to that exact cyan (`$cyan` in the brand
variables, the Bootstrap-palette port), so the class alone lands the
demo's colour (user reports: too short, wrong colour, too wide).

**Alternatives.** (a) `is-medium` on all three (refused — the search field
is the lib's default-size `input`, and resizing the lib component for one
caller is out of scope for a chrome tweak). (b) SCSS height/colour pins on
the button (refused — the two classes already equal the demo; Bulma owns
the sizing and the palette). (c) A custom brand class (refused — the demo
uses `is-info`; parity is the point).

**Consequences.** Template-only change, no SCSS, no lib change, no new
catalogue key. Live-measured against the demo: field, submit button and
`+` all 40px tall, `+` 40x40, background `rgb(23, 162, 184)` — the
demo's values.

### DD-334. The editor drawer's route segments are `create` and `edit`

**Status:** Proposed (naming fix on the delivered drawer family, from user
review before acceptance — it renames the two route segments EDT-01
names.)

**Decision.** The drawer's editor routes rename: `edit-entity/:guid` ->
`edit/:guid`, `create-entity` -> `create`, `create-entity/:type` ->
`create/:type`. The URLs read `(drawer:edit/<guid>)` and
`(drawer:create/<type>)`.

**Reason.** The `drawer` outlet already names the panel —
`(drawer:create-entity)` says "entity" twice (user request: shorter).
The other outlet members are single words (`settings`, `alerts`), and the
mode test (`routeConfig.path.startsWith("create")`) is unaffected.

**Alternatives.** (a) Keep the old segments as aliases (refused — nothing
deep-links them yet: no docs page, no bookmark rule, and the e2e set is
in-repo; an alias pair doubles the route table for no migration).
(b) `new` instead of `create` (refused — the component's mode flag, the
picker code, and EDT-01/04/06 all say create).

**Consequences.** Three route paths, three navigate sites, the unit
expectations, and the e2e URL patterns rename together. The legacy's
`create-entity`/`edit-entity` full-screen routes (7.0's port note) are
historical record and keep their names in the spec's Java/legacy porting
table.

### DD-335. The classification box is one chip-and-caret control with a drop-up panel

**Status:** Proposed (usability fix on the delivered drawer, from user
review before acceptance — it changes how EDT-05's box presents, not what
it stores or sends.)

**Decision.** The tag box becomes one bordered box carrying the Bulma
input's own look (border, radius, height, focus ring, built from the
control custom properties Bulma exposes at root scope): the chosen chips
sit inline before the caret and the text input is borderless inside it,
so the whole control reads as one field that grows with its tags
(the demo's shape, user-chosen). The suggestions leave the native
`<datalist>` (user: "not wild about how the search suggestions are
presented") for a styled panel: a Bulma dropdown on the box, open while
the box holds focus, filtered on the typed text, scrolling when the
matches outgrow it. The box is the form's last field, so the panel
opens UPWARD (Bulma's `is-up`) and stretches to the box's full width
(the component's own rule — Bulma has no dropdown full-width modifier).
A pick commits on `mousedown`, before the blur closes the panel; Escape
inside the box closes the panel only, stopping the event so the drawer
stays open. DD-329's `(change)` commit retires with the datalist.

**Reason.** The old box was a chips row above a separate full-width
input — two controls where the demo shows one. And a `<datalist>`
popup is browser-chrome: unstyled, unlike the app, and its filter is
the browser's own. One box keeps the eye on one field; the panel can
match the theme, filter as the box filters, and open upward because the
box sits at the form's bottom edge, where a downward panel lands past
the fold.

**Alternatives.** (a) Keep the datalist, style impossible (refused —
user report). (b) A chips row kept above the box (refused — the demo
nests the chips in the border; user picked that). (c) A downward panel
(Bulma's default, refused — the user asked for a drop-up, and the box
is the form's last field). (d) Click-commit instead of mousedown
(refused — focus moves to the button first and the box's focusout
closes the panel before the click lands; mousedown is the listbox idiom).
(e) `position: fixed` to escape the drawer's clipping (refused — the
panel stays inside the drawer's scroll port, scrolls with it, and the
box is rarely near the port's top edge; measured live).

**Consequences.** The component grows ~60 lines of state (focus, panel
open, filtered matches) and ~50 lines of SCSS; the ui library changes
not at all — the chips are the shipped `ClassificationChip` (UIC-24).
The panel is `role="listbox"` with `aria-expanded` on the input.
Keyboard: typing filters, Enter adds an exact-or-filtered-first name
(unchanged), Escape backs out of the panel layer by layer. The unit
specs replace DD-329's datalist-pick test with panel filter/pick/Escape
pins. Live-probed: 40px bordered box, blue focus ring, panel 367px over
a 369px box opening above it, picked tag never re-offered.

### DD-336. The classification box is a keyboard combobox and disables when it has nothing to offer

**Status:** Proposed (accessibility fix on the delivered drawer, from user
review before acceptance — it adds how EDT-05's box is operable and when
it yields, changing no stored value or request.)

**Decision.** Four things, all on the tag box (EDT-05, on top of
DD-335's box):

1. The input is a proper combobox (ARIA 1.2): `role="combobox"`, named by
   its label through `aria-labelledby`, `aria-controls`/`aria-expanded`,
   `aria-autocomplete="list"`, and `aria-activedescendant` pointing at the
   open panel's active option. Down/Up move the active option (the panel
   rows carry matching ids and `aria-selected`); Enter adds it. A match
   that starts with the typed text leads the list, so Enter commits the
   closest name — the old exact-else-first rule kept in the panel order.
2. With nothing left to add (no applicable type remains for the entity's
   type), the input and its box disable and take the input's muted look,
   and the "No classifications available" help line shows (it now shows
   whenever nothing applies, not only when the box is also empty, so a
   dead input is explained). Chosen tags keep their delete — that is the
   chip's control, not the input's, so a full box can still hand a tag
   back even with no more to add.
3. The panel rows clear the 24px target floor (2.5rem desktop, 3rem on
   coarse pointers), and the panel already caps at 15rem and scrolls, so
   on a phone it stays inside the drawer rather than running off-screen.
4. (In the ui lib, UIC-24's row amended) the chip's delete — Bulma's
   `delete.is-small`, a 1rem dot — grows to Bulma's own `is-large` size
   (2rem) on coarse pointers through the dimensions variable Bulma
   exposes, so the strokes scale with it and no geometry is redrawn.

**Reason.** Screen readers had nothing to announce: the label was a
`<p class="label">` that never named the input, the panel was an
unconnected `listbox`, and the mouse-only pick left keyboard users with
Tab-to-each-row at best (the user's accessibility review). On a 390px
drawer the old rows and the tiny chip delete sat under the touch-target
floor, and the empty box invited typing that could only match nothing
(the user's second ask). A combobox is the ARIA pattern for exactly this
control; the browser-vetted alternative was refused below.

**Alternatives.** (a) A native `<select>` (refused — it cannot carry the
chips and free-text filter in one box; DD-335 already moved off the
`<datalist>` for the same look reason). (b) roving tabindex that moves
DOM focus into the panel (refused — the listbox pattern's
`aria-activedescendant` keeps focus in the input so typing and arrowing
share one control; roving focus fights the filter-as-you-type). (c)
disable the whole field including the chips (refused — deleting a wrongly
chosen tag is still valid when nothing new applies). (d) widen the chip
delete with a `::after` hit-area from the editor via `::ng-deep` (refused
— Bulma draws the X with the button's own `::before`/`::after`, so a third
pseudo is wrong, and the editor styling a lib child's internals is the
wrong owner; the lib owns its control). (e) a `width <= 768px` media
query for touch (refused — touch is capability, not width; used
`pointer: coarse`).

**Consequences.** The combobox state is ~4 signals (box focus, panel
open, typed text, active index) plus a re-clamp effect; the active index
resets on focus and re-clamps as the filter narrows. Enter's meaning
narrows to "add the active option" while the panel is open, and stays
"add the exact typed name" while it is shut (the pre-DD-335 rule, so a
full-name add with the panel dismissed still works — the e2e's fill-and-
Enter path is unchanged). No new catalogue keys: the disabled box reuses
the shipped `noClassifications` line. Live-probed on a 390px viewport and
under a coarse-pointer emulation: 40px rows (48px coarse), the chip
delete 32px (from 16), the panel drop-up inside the viewport, the
active row painted and matching `aria-activedescendant`, Enter committing
it, and the box disabled with the help line on a type with nothing
applicable.

### DD-337. The chip delete keeps its small dot and grows an invisible touch ring

**Date:** 2026-11-04 · **Status:** Proposed · **Specs:** EDT-05 (7.7a), UIC-24 (7-16)

**Context.** DD-336 grew the chip's delete dot itself (Bulma's `is-large`,
2rem) on coarse pointers to clear the touch-target floor. The review
screenshot settled it: a 32px circle on a 24px tag looks wrong — the mark
dominates the name it belongs to.

**Decision.** (ui lib, UIC-24's row amended again.) On coarse pointers the
dot stays Bulma's `is-small` (1rem) and the target grows invisibly
instead: `--bulma-delete-dimensions` goes to 2.25rem (a 36px target,
border-box maths), a 0.625rem transparent border absorbs the difference,
and `background-clip: content-box` keeps the painted circle at 1rem.
Bulma draws the X as a share of the padding box, which the border holds
at 1rem, so the glyph is pixel-identical to the desktop chip. Negative
margins — Bulma's own `.tag .delete` offsets minus the border — take the
added box back out of the tag's layout, so the dot keeps its exact seat
and nothing spills.

**Alternatives.** (a) Keep `is-large` (refused — the review's complaint,
verbatim: "the delete buttons look way too large in comparison to the
tags/pills"). (b) Grow the dot to `is-medium` (1.5rem, 24px = tag height)
(refused — flush with the tag's top and bottom edges, still the largest
thing on the chip). (c) Padding + `background-clip: content-box` instead
of a border (refused — with border-box sizing the padding shrinks the
rendered dot instead of widening the hit area, and percentage widths of
the X bars resolve against the padding box, which padding inflates — the
border version keeps both exact).

**Consequences.** The visible chip is identical on desktop and touch; the
36px target exists only as invisible geometry. Live-probed under a
coarse-pointer emulation: dot 16px (was 32), target 36px (floor: 24px),
X strokes unchanged, tag height unchanged.

### DD-354. The editor's form layer is Signal Forms, not Reactive Forms

- **Status:** Proposed
- **Increment:** 7.7a
- **Date:** 2026-11-04

**Decision.** The editor's form is an Angular Signal Form. The model
is a signal holding one plain value per rendered field, and
`@angular/forms/signals`'s `form()` wraps it in a field tree. The required
marker and the unique-attribute lock of EDT-03 are schema rules over the same
field set the template walks. Each native input binds with `[formField]`. The
Select and the picker-style controls keep their value-and-event contract and
write the model in their handlers. The classification box is not a form field
at all. Its typed text is a plain signal. DD-323's helper pair
(`form-fields.ts`) is unchanged. It is form-library-neutral.

**Reason.** The user chose the framework on 2026-11-04, while the editor was
still unreleased: "I'd like to refactor anyways, the editor is not on main yet
and refactoring now will incur the least cost." The form fits Signal Forms
better than Reactive Forms on its own terms. The field set is dynamic (EDT-03
builds it from the type definition), and Signal Forms derives the field tree
from the model, so a rebuild is one model swap. The old code needed a rebuild
guard, a `buildForm()` factory, and a manual subscription to grow a multi
list. The new code needs a seed helper and one effect. The editor is otherwise
signal-first already, and a `FormControl` was the one island of RxJS left in
it. The library is stable since Angular 22.0, and the workspace runs 22.2.

**Alternatives.** (a) Keep Reactive Forms (refused at the user's choice — it
works, and Angular keeps it supported. The cost of switching rises with every
dependent slice, and 7.7c and 7.7d are next). (b) The compat bridge,
`compatForm` (refused — it keeps `FormControl` objects inside the model and
the value tree loses its plain shape. The bridge exists to migrate a large
form piecemeal, and this form is one component). (c) Template-driven forms
(refused — the field set is built at runtime, which template-driven forms
handle poorly). (d) Port the ui-library `markdown-editor` (EDT-20) at the same
time (deferred to 7.7d's branch, where the component lives. A control
implements either the value-accessor interface or the Signal Forms control
interface, never both, so its port rides its own increment).

**Consequences.** Two framework facts shaped the code. `form()` compiles its
schema when it is created, so the model, the injector, and the field set must
exist first. And `form()` builds its own effects, which Angular forbids inside
an effect, so the rebuild effect creates the form through `untracked`. The
touched-state rule of EDT-07 reads `touched()`/`invalid()` signals instead of
control properties. The number fields seed `null` when empty, because the
number input's own empty value is `null` — the merge helper already deletes an
empty number (EDT-06), so the saved body does not change. The DOM the EDT
tests pin is the same DOM, and no EDT rule changes meaning. The `@for` over a
multi field's rows tracks the field node rather than the row's index: Signal
Forms keeps a stable identity for each item of an array field, and the
framework's field-state guide names tracking by that identity as the pattern,
because it keeps every input wired to its own part of the model when rows are
added or removed. The picker values of 7.7c stay on their own signal, not in
this model: a picker holds a chip list the save merges separately (EDT-16),
not an attribute the form writes. The legacy form family's port (DD-323) does
not name a form library, so no ledger row changes.
