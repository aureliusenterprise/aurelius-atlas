# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-755. The parent-safe check is a second EntityDiscovery validation

- **Status:** Proposed
- **Increment:** 18.4
- **Date:** 2026-11-20
- **Relates to:** PME-07 (the parent-group check), HCA-01 (the `SINGLE` child ends), DD-590 (the rewind),
  RPS-01, RPS-03.

**Decision.** `EntityDiscovery` gains `validate_parent_safe(entity, entity_type, guid)`, next to
`validate_parent_groups` (PME-07). It walks the entity's parent-side relationship attributes (a `SET` attribute
whose opposite end is a `SINGLE` child end), reads each named candidate, and refuses when a candidate already
holds an active edge on its own parent family to a different parent. This is the check PME-07 already runs for
one entity, now run for each candidate. It runs on the wire door inside the writer, where PME-07 runs, and on
the view door as a step before `sections` apply, so both refuse before any edge is written (RPS-01, RPS-03).
When `unsafe_reparent` is true the writer skips the check. A candidate held by a parent the same request also
updates to drop it is released and never refused: a deliberate move made in one request is not an implicit
reparent (RPS-02). Because the view door edits one entity, it never releases, so it refuses an unflagged held
candidate on every add. A candidate a request creates is read on the parents it declares, resolved through the
request's own GUID assignments so a declaration naming the written parent by its placeholder is not held.

**Reason.** The two doors already share `EntityDiscovery` and the same store internals, so one method covers
both and reports in the same `INSTANCE_CRUD_INVALID_PARAMS` shape PME-07 uses. The check has to run on the
candidate, not the edited entity, because PME-07 looks only at the entity being written. Neither door has
ever inspected a candidate's existing parents. Running it before the write means the view door's rewind
(DD-590) leaves nothing applied on a refusal. Releasing a candidate the same request moves is the difference
between an implicit reparent -- which leaves two parents -- and a client that updates both parents in one call
to move deliberately; the editor never sends the old parent, so it is always refused there.

**Alternatives.**

- **Check inside `RelationshipStore.create`.** The wire door does not create edges through the store. It
  maps them through `RelationshipMapper` and writes them in one `store.write`, so the store never sees a
  wire-path parent-side edge. A store check would guard the door path only and miss the wire path.
- **Check in the webapp only.** Any API client or import re-parents freely, the same gap PME-10 left for the
  sibling picker. The corruption DV-186 shows is exactly what a client-side-only rule permits.
- **Reuse PME-07 directly.** PME-07 compares the filled parent attributes of one entity's own type. The
  candidate is a different entity reached through an edge, so it needs its own pass and its own error text.
- **Refuse even a same-request move.** A client that reorganises a tree in one bulk call -- the child dropped
  from the old parent and added under the new in the same request -- is refused for a move it states in full,
  and has to send the flag to do work it already described exactly.

### DD-756. The opt-in is a query parameter named unsafeReparent

- **Status:** Proposed
- **Increment:** 18.4
- **Date:** 2026-11-20
- **Relates to:** DD-39 (the query parameter models), AVW-02 (the view body ignores unknown keys), RPS-04.

**Decision.** The opt-in is `unsafeReparent`, a `FlagParam` read by `Boolean.valueOf` (absent means false) on
the wire `createOrUpdate` endpoints and on the view door `POST /entity`. It is a parameter, not a body field.

**Reason.** The wire write endpoint takes a single entity body that must equal the Apache Atlas request shape
parity checks, so it carries no spare field. The view body ignores unknown keys (AVW-02), so a body field
would be silently dropped unless plumbed explicitly, and a client could not tell a typo from an absent flag.
A query parameter is the existing convention for these routes (`minExtInfo`, `deleteType`), read through a
parameter model the same way, and uniform across both doors. The name leads with `unsafe` so a reader sees
the risk before sending it.

**Alternatives.**

- **A field inside the view body.** The door drops unknown keys (AVW-02). Making one meaningful means
  widening the body schema for one flag, and it does not exist on the wire door at all.
- **A header.** The codebase passes no behavioural flags by header, so it adds a new mechanism.
- **A per-relationship-attribute request option.** The flag is about the write as a whole, and the picker sets
  it (or not) per save, not per attribute.

### DD-757. The view door clears the old parent edge on a moved child

- **Status:** Proposed
- **Increment:** 18.4
- **Date:** 2026-11-20
- **Relates to:** DD-755, HCA-04 (the wire replaces the edge), DV-186, RPS-05.

**Decision.** With `unsafeReparent`, the view door's `sections` step, before creating a parent-side edge to a
held candidate, deletes the candidate's active edges on its parent family that point elsewhere (RPS-05). The
wire path gains the same move in its own mapper, since before this increment neither path ever cleared an edge
of another relationship. The candidate then holds one parent. Without the flag the save never reaches this
point, because DD-755 refused it.

**Reason.** The door created edges through `RelationshipStore.create`, which only rejects an identical
`end1/end2/label` pair and never touches the candidate's inverse `SINGLE` end. That is the bug: the old
parent edge stays and the child ends under two parents, breaking 18.2's cardinality (DV-186). Clearing the
old edge on the opt-in makes the door agree with the wire path and with HCA-04's "one parent" rule, so both
doors move a child the same way.

**Alternatives.**

- **Route the door through `EntityWriter` instead of `sections`.** The door deliberately applies a view's
  complete desired state in its own steps with its own rewind (DD-589). Rewiring it onto the writer is a
  larger change than the one clearing step.
- **Let the door double-parent and clean up later.** A two-parent child breaks the `SINGLE` read, the
  governance rule, and the lineage page. There is no safe later.
- **Refuse the move even with the flag.** Then a child that legitimately changes parent can never do so on
  the parent side at all.

### DD-758. The picker filters on a stored boolean of whether an entity has a parent

- **Status:** Proposed
- **Increment:** 18.4
- **Date:** 2026-11-20
- **Relates to:** LAS-04 (the derived breadcrumb and `parentguid`), AVR-03 (the door's field table),
  DD-628 (the derivation version), RPS-06, RPS-07.

**Decision.** The App Search document gains a stored boolean `hasparent`, written next to `parentguid` in the
indexer's derivation as true when the entity's breadcrumb is non-empty (LAS-04). The view door's field table
answers a card field `hasParent` from it, kind boolean, missing false, and the editor's parent-side picker
adds `filters.hasParent: false` to its search and keeps the existing prefix check. Because a derived field
joined the document, the derivation version goes from `2` to `3` (DD-628), so every stored document is
re-derived.

**Reason.** The picker must hide held candidates in Elasticsearch, before its 10-row cap, or the panel shows
two of ten rows and looks empty. The stored breadcrumb cannot answer the filter on its own: an entity with no
parent has no `parentguid` in the document at all, and Elasticsearch treats a missing field as neither true
nor false, so a filter for "no parent" would match nothing. And "has a parent" has no value to match on, since
any parent GUID would do, which would need a terms query over every parent in the store. A stored boolean
answers both directions exactly, at the price of one re-index guarded by the derivation version.

**Alternatives.**

- **Filter on `parentguid` with an exists/missing clause.** It answers the false case but not the true one,
  and the door's field table has one clause shape per kind. A special case for a single field is not worth it.
- **Filter client-side on the card's breadcrumb.** The search page is capped, so hiding after the fetch
  under-fills the panel and misleads the author.
- **Resolve each candidate's parents client-side.** The picker shows ten rows, so ten candidate reads per
  keystroke is far heavier than one stored boolean the door already filters on.

### DD-759. Only the parent-side picker filters

- **Status:** Proposed
- **Increment:** 18.4
- **Date:** 2026-11-20
- **Relates to:** PME-10 (the disabled sibling picker), HCA-06 (one pick on a child attribute), RPS-07.

**Decision.** The `hasParent: false` filter rides the parent-side (`SET`) picker only. The child-side
(`SINGLE`) picker, such as a dataset's `parentDataset` or a field's `parentField`, keeps searching every
candidate. The editor learns which pickers are parent-side from a fourth type slice: the drawer's open also
asks `GET /api/atlas/v2/types/typedefs?type=RELATIONSHIP` (TYR-05) and keeps the relationship definitions.
`buildRelationshipFields` reads the opposite end of each picker's relationship there. A `SET` attribute whose
other end is a `SINGLE` child end gets the field's `parentSide` flag, and only that picker sends the filter.
The picker also drops a card the search answered with `hasParent` true, because a stored mark can lag the
edges and such a pick would only be refused.

**Reason.** On the child side, choosing an entity that already has a parent is the normal way to move the
edited entity: the author is reparenting the thing they are editing, and PME-10 already handles the sibling
conflict by disabling the other picker. Filtering there would hide the very entity the author means to
attach. The corruption the increment prevents is on the parent side, where the edited entity adds a child it
does not own. The entity typedef the form already reads carries the attribute's own cardinality but not the
opposite end's, and both ends of a hierarchy name the same type. So no answer the editor holds can tell the
two ends apart. The relationship definitions are the single source of that fact, and the server's guard reads
the same definitions (DD-755), so the client's filter and the server's refusal agree. The definitions slice is
small (35 relationship types on the shipped dictionary) and the editor already fetches three of these slices
on open (VDE-02, DD-611), so the cost is one more read of the same kind, cached by the door's client.

**Alternatives.**

- **Filter both sides.** On the child side it hides the legitimate move and fights PME-10's model.
- **Filter neither.** Leaves the parent-side corruption the increment is about.
- **Answer a parent-side flag on the for-type door.** AVW-11 pins the answer to `{type, superTypes}` of whole
  typedefs, and an accepted rule is not edited for an increment (its body is superseded, not widened). The
  door also says its answer is the whole typedefs unchanged, so a second shape for the widgets breaks the
  reason the door returns typedefs whole.
- **Name the parent-side attributes in the webapp.** The dictionary names eight of them (HCA-01), so a list
  in the webapp is a second copy of the metamodel that goes stale when a model author adds a hierarchy.
- **Guess from `isContainer` or the attribute name.** `isContainer` is false on every one of the eight ends,
  and the names differ per dictionary, so neither tells a hierarchy from a plain association.
