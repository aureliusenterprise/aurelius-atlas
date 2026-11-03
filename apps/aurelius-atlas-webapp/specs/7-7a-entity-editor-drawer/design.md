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
