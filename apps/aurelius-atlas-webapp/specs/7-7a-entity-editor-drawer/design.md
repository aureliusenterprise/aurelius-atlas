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

### DD-326. Classifications save through one replace call, not the add/remove diff

- **Status:** Proposed
- **Increment:** 7.7a
- **Date:** 2026-11-03

**Decision.** After the entity POST succeeds, the editor replaces the entity's
classifications with one `PUT /api/atlas/v2/entity/guid/{guid}/classifications`
call carrying the form's final own-classification list (CLS-08, the client
method since 8.7). The editor's tag box shows only the classifications the
entity owns (`entityGuid` equal to the entity's guid); classifications
propagated from other entities appear on the details screen but not in the
form (EDT-05). Save is exactly two requests: entity, then classifications.

**Reason.** The legacy `EntityUpdateService` diffs the form's classifications
against the loaded ones and issues one POST-add and one DELETE per difference
(0 to N + M calls), because its m4i editors render only some of an entity's
classifications and the diff must not touch the rest. The 7.7a form is the
whole own-classification set by construction (EDT-05 lists every applicable
classification), so the replace endpoint says exactly what the form says. The
replace call is already ported on both sides (server CLS-08, client 8.7) and
answers 204 with the authorization checked per classification (AUZ-08). The
two-step shape (entity POST, then classifications) is the legacy shape and
the server's own model: an entity POST ignores classifications given inside
it (2.4's deferral table notes it lands with 3.3), so they cannot ride the
same call.

**Alternatives.** (a) Port the diff (refused — same end state, more calls,
two endpoint families, and its reason — hidden classifications the diff must
preserve — does not exist in this form). (b) Send classifications inside the
entity body (refused — the server ignores them there; the deferral table in
2.4 says so).

**Consequences.** A save that only touches attributes still sends the
classifications list it read; that is harmless (a replace with equal content)
and keeps one code path. A refused classification replace leaves the entity
saved (the two steps are not one transaction, the legacy's known shape
carried forward), so EDT-08's failure alert fires with the user's edits kept.
Propagated classifications stay out of reach of both the form and the replace
body, so a save cannot sever an inherited tag.
