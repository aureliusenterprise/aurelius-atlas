# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an
accepted entry is never edited except its status line, and a changed decision is a new entry that
supersedes the old one.

## DD-608. The editor opens through the read door's client, in the drawer's own read

- **Status:** Proposed
- **Increment:** 16.5c
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `EditorState.loadEntity` asks `ViewEntityService` (DD-605) instead of the Atlas
entity GET: the drawer keeps its own read (DD-322 stays, the details store never feeds it), and
the view answers the form seed, the tag box, and the picker seeds. The save's success evicts the
saved guid before firing the tick, so the details re-read asks the door even when the drawer rode
the cache (VDR-07). The entity the merge saves onto is the view itself: the attribute values are
its `attributes`, the tags its `classificationNames`, the ends its `sections`.

**Reason.** ADR 064 R1 says one screen rides one shape family, and 16.5b proved the view carries
everything the details screen needs. The editor's read is the same entity at the same GUID: a
second door for it would re-open the split R1 closes. Riding the cached client means a drawer
opened from the details screen often paints with no request at all.

**Alternatives.**

- The editor keeps its Atlas GET beside the view: two reads of one entity, and the save's merge
  needs both because each answers a different shape (fails R1).
- The details store hands its view to the drawer: the drawer is routable on its own
  (`create/:type`, DD-330), so it must be able to read without a details screen under it (fails
  DD-322).

**Consequences.** `loadEntity` becomes a call through the cached client, and its failure paths
keep the alert lines of EDT-02. The quality mode read (`storedCheckKind`) already reads
`attributes`, so it works on the view unchanged. 16.6 retires the Atlas GET's last webapp caller
with this.

## DD-609. One door POST saves the entity, the tags, and the ends; the client diff retires

- **Status:** Proposed
- **Increment:** 16.5c
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `EditorState.save` posts one door body: `typeName`, the full `attributes` map from
the form, `updateTime` for an update, the tag box's names as `classifications`, and one
`sections` entry per picker the form rendered. A create names no guid. The answer is the stored
entity's live view (AVW-07), and its `guid` is where the create's real guid lands (DD-592). The
temporary numeric GUID seed, the `guidAssignments` remap (DD-325), the POST-add plus
DELETE-each tag sequence (DD-326), and the `mergeRelationshipsOntoEntity` echo of DD-340 retire
with this one request.

**Reason.** The door exists for exactly this call (DD-589): it diffs every named set against
what the entity carries now, applies the difference through the same internals, and rolls the
whole request back when a later step fails (DD-590). The client sequence cannot promise that,
and each of its partial failures is a state the person has to notice themselves. DD-340's
key-drop dance existed because Atlas's POST moves a reference left in `attributes` back onto the
relationship: the door reads ends only from `sections`, so the dance has no partner left.

**Alternatives.**

- The client keeps the sequence and only adds `updateTime`: the lost-update hole stays open for
  tags and ends, where two stewards' edits silently overwrite (fails AVW-04's purpose).
- The client sends only what changed: the door's sets are complete desired states (AVW-02), and
  a partial set would remove what the editor never rendered, such as an end hidden by the type.

**Consequences.** One request per save, so the save's failure handling is one path (VDE-06..08)
instead of a sequence's five. The create's tags ride the entity body inside the door
(CLS-10's path), and the answer names the real guid, so the remap retires. The save's audit
records are the door's (AVW-10), which are the ones the Atlas paths write for the same effect,
so the audits e2e scenario is unaffected.

## DD-610. A conflict re-edits from the stored view, beside the person's edits

- **Status:** Proposed
- **Increment:** 16.5c
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** A 409 `ENTITY_VERSION_CONFLICT` (AVW-04) is a normal answer, not an alert. The
editor replaces its base with the answer's `view` — the stored entity as it is now — keeps every
value the person typed in the controls, shows one line that the entity changed since it opened,
and lets a second Save ride the stored `updateTime`. The tag box and the pickers re-seed from
the new view only for what the person never touched: a tag or end they chose stays chosen.

**Reason.** DD-591 scheduled this as "a reload-and-reedit path, not an error page," and its
answer carries the stored view for exactly this moment. The person's edits are the drawer's form
values, not the base entity, so re-seeding the base costs nothing typed: the merge (EDT-06)
already reads values from the controls and falls back to the base. Refusing the second Save, or
asking the person to reopen the drawer, would throw away the edit the conflict line just told
them about.

**Alternatives.**

- An alert and keep editing (EDT-08's shape): the next Save conflicts again forever, because the
  old `updateTime` stays in the body — the alert would be a loop.
- Reload the screen and lose the edits: the stored view would replace typed values, and DD-591
  names the person's edit material the point of answering the view.
- Last-write-wins silently: the overwrite AVW-04 exists to prevent.

**Consequences.** The conflict needs a new line in the bridge catalogue (VDE-11), and the drawer
keeps a second signal — the view the save merges onto — apart from the view it opened with.
The name-taken 409 (AVW-06) is not this path: a create's conflict has no stored view, and its
answer is the EDT-08 alert shape naming the holder (VDE-07).

## DD-611. The form's type material comes from slices, cached by name in the client

- **Status:** Proposed
- **Increment:** 16.5c
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The editor asks three small things instead of one big one.
`GET /api/aurelius/v1/types/for-type/{name}` (AVW-11) answers the entity's type chain, and
`ViewTypeService` caches each chain by type name. The tag box's applicable classifications and
the enum widgets' options come from `GET /api/atlas/v2/types/typedefs` filtered to
`type=CLASSIFICATION` and `type=ENUM` once per session. The create picker lists entity typedef
headers from `GET /api/atlas/v2/types/typedefs/headers?type=ENTITY` (TYR-08), labelled by the
`nameDisplay` of the name as DD-379 sets. The whole-typedefs dump of EDT-04 retires.

**Reason.** The dump costs the server every registered definition (over a thousand) so one
drawer can render one type's form. AVW-11 exists because 16.3's spec named the editor's need,
and DD-593 scheduled the cache with it: "Caching by type name belongs to the client cache
record (16.5)." The two filtered searches stay because the shipped entity defs reference enum
and classification types outside the entity chain, and their answers are small (5 enum-typed
classification defs and 10 enum-typed entity attributes in the shipped model, read from the
model JSON). The headers route answers identity fields only, which is everything the picker
row shows, because entity defs carry no display names (DD-379's finding).

**Alternatives.**

- Keep the dump: the drawer's cold open transfers the whole registry to render one form (fails
  AVW-11's purpose).
- Chain one typedef-by-name call per supertype: a chain walk of requests, the shape DD-593's
  single chain answer exists to avoid.
- A server slice for the enums and classifications beside the chain: more door surface than the
  need, since two filtered Atlas searches exist today and answer exact lists (kept honest by
  AVW-12).

**Consequences.** `EditorState`'s `typedefsDef` signal is replaced by a chain signal and two
small maps, and the picker and tag-box computeds read them. The chain cache is keyed by name, so
two editors for one type share it, and a type change mid-session (impossible through the door,
VDE's type rule) needs no invalidation. `getTypedefs`/`getTypedefHeaders` stay — the types
screens ride them (TYR-08).

## DD-612. The door's set keys carry tags, ends, and meanings; the door names the relationship type

- **Status:** Proposed
- **Increment:** 16.5c
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The save body speaks the door's keys, and three of them are asymmetric by design.
The answer shows `classificationNames` while the request takes `classifications`, so the tag box
seeds from one key and saves through the other. The picker seeds read the answer's `sections` by
attribute name while the save sends one `sections` entry per rendered picker. A `meanings`
picker is the exception on the way in: its seeds read `sections.meanings` (VDR-02's ends answer
term assignments too), but its save rides the door's `meanings` key as term GUIDs, because
AVW-05 applies term assignments through 5.2c's bookkeeping and not as a plain edge. The save
sends no relationship type name at all: `relationshipTypeName` (EDT-16) retires, because the
door picks the relationship type itself — an attribute's only type, else the type an edge of the
entity already carries (REL-17's rule, `_relationship_type_name`).

**Reason.** The asymmetries are the door's contract, not accidents: names out (the answer is a
view, and a view shows names, AVS-01), GUIDs and intents in (the desired state names entities,
AVW-09). The meanings key exists because a term assignment is a relationship with its own
validation and history bookkeeping, and the door keeps that path in one place. The type-name
rule is the one the 2.3 read already applies to the same entity: a client-sent type could
disagree with the entity's existing edges, and two writers picking different types for one
attribute is how orphan edges are born.

**Alternatives.**

- Save meanings as a `sections` entry: the door accepts it, because `meanings` is a wired
  relationship attribute (the glossary model's endDef2) and the plain edge answers
  `meaningNames` the same way (probed against the merged door). It skips the term-side
  validation and the assignment audit the `meanings` key runs through 5.2c's internals
  (GTA-04), so the editor must not take the quieter path.
- Keep sending `relationshipTypeName`: the door ignores it, and an ignored field suggests the
  client still decides (fails AVW-09's shape).
- Seed tags from the Atlas `classifications` objects: the view answers names only (VDR-05), and
  the box only ever used `typeName` plus the def description for its tooltip, which the
  classification-slice map (DD-611) answers.

**Consequences.** The save body builder is a pure function over the view plus the form values
plus the pick maps, specced in `view-as-entity.spec.ts` beside its retirement twin. The chip
tooltip keeps its def description through the slice map, so EDT-05's rendering is unchanged.
The REL-17 pick-up rule cannot surprise the picker: its search target comes from the def chain
(EDT-13) and stays, and an end the door placed under a different relationship type still answers
the same section on the next read.

## DD-613. The door's create body carries its wanted ends, so a mandatory relationship attribute passes

- **Status:** Proposed
- **Increment:** 16.5c
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `_entity_for_create` folds the save's wanted `sections` ends into the create body as
`relationshipAttributes` — each live end its `{guid}`, one object for a `SINGLE` attribute, a list for
the rest, a delete intent left out (it names nothing to create). 2.4's create path then builds those
edges from the body's own relationship attributes, exactly as the Atlas POST one body did (DD-340's
world), and EVL-08 sees a mandatory relationship attribute held. The door's `sections` step still runs
after and keeps AVW-05's replace semantics: its diff finds the edge the body already made and changes
nothing, and a create that names no end stays refused by the create path as it always was.

**Reason.** The door applies its sets after the attributes step (AVW-05), but 2.4's create validates
the whole entity before any edge exists, so a relationship attribute the type makes mandatory
(a COMPOSITION end that is not the container's, as `ozone_bucket.volume` is) refused every create of
it — even a request that named the end in its `sections` (AVW-09), which the door had not yet applied.
AVW-03 passes those EVL refusals unchanged, so the door answered a caller who did nothing wrong. The
Atlas sequence the door replaces never had this gap: its one POST body carried `relationshipAttributes`
and created the edges inside the create.

**Alternatives.**

- Skip EVL-08's mandatory check for a create through the door: it hides a real constraint the type
  declares, and a create that names no end would then store a half entity (fails AVW-03's unchanged
  validation, and leaves AVW-09's constraint unenforced).
- Run the `sections` step inside the attributes step: the door loses AVW-05's clean order (sets after
  attributes) and its per-step internals, for a case the body already carries whole (fails DD-589's
  shape).

**Consequences.** A create whose picker is empty still refuses, naming the mandatory attribute — the
create path's own message, unchanged. The create that lands the edge answers its live view with the
end among its `sections` (the answer read, not the body, VDE-06). The e2e mandatory-relationship
scenario (`test__the_editor_requires_a_mandatory_relationship`) rides the door from here, and
`test__a_create_with_a_mandatory_relationship_end_lands_the_edge` pins the door's rule.
