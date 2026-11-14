# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an
accepted entry is never edited except its status line, and a changed decision is a new entry that
supersedes the old one.

## DD-604. The read door answers its entity's own relationship ends

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-14

**Decision.** `GET /entity/guid/{guid}` passes `ends` to `view_of`: the entity's ACTIVE edges,
read through the registry's relationship attributes and the graph helpers the 2.3 read uses, and
answered under the attribute name each edge belongs to, as `{guid, name, typeName, status}` —
AVS-04's merge clause, which no door has answered until now. The read is the entity document plus
one batched read of its ends: the store answers every end GUID of the entity in one `get_many`,
and a SINGLE-cardinality attribute's one object is listed like any other end. A stored derived
pair naming a read end loses its place to it; the pairs of unmated attributes stay. The dedupe
applies to the stored pairs only: two read attributes can name one entity at the same time — the
process that both feeds and produces a dataset (REL-17) — and each of them answers it, so one box
of the screen never empties another.

**Reason.** The screen's People box, person stats and section seeds key by relationship attribute
(`dataEntity`, `domainLead`), which only the entity's own edges know; the stored document's pairs
key by the end's type field and carry no attribute name. AVS-04 already names this source and
`view_of` already takes the parameter — the door never passed it. A batched ends read is not the
walk ADR 064 R1 rejects: one entity, its own attributes, one round.

**Alternatives.**

- The client keeps the Atlas GET beside the view: two reads for one screen, and the shape family
  splits again (fails R1, R2).
- The screen derives ends from `relations` pairs: pairs have no attribute name and no status, so
  the People box and stats could not key or filter (fails VDR-03).
- Recompute the derived document live: the rejected join of ADR 060, per open.

**Consequences.** The door's answer grows one batched read per open; the 2.3 read's helpers
(`relationship_type_name`, `edges_for_label`) are its shared machinery, so edge semantics cannot
drift. DELETED edges answer nothing, as the screen's EDT-15 rule already drops them — the client
rule stays and never fires. 16.5c's save answer can pass the same ends for the written entity.

## DD-605. The GUID cache lives in the door's client, not the page's store

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-14

**Decision.** The GUID-keyed view cache ADR 064 schedules lives in `ViewEntityService`
(`aurelius-atlas-data-access`, root-provided): the last 50 views by guid, an in-memory map that a
page reload clears. `view(guid)` answers a cached view synchronously and asks the door otherwise;
`evict(guid)` drops one entry. `DetailsState` (page-scoped) evicts on the editor's save tick
before re-reading (DD-327 kept), and the crumb and property links ride the same cached read. The
supersede of DD-318's "no cache" is ADR 064's own follow-up clause; DD-318's fetch states (the
guid guard, the loading line, the alert paths) stand untouched in the store.

**Reason.** Crumb and property links walk a chain a click at a time and a save's re-read asks for
the guid just opened: without a cache each step re-reads what the last answered. The cache must
outlive one screen to serve the walk, so it cannot live in a page-scoped store; and it must not
know the webapp's event types, so the eviction is the store's call, not the service's subscription.

**Alternatives.**

- The page store caches: dies with the screen, buys nothing for the walk.
- `shareReplay` on the request: keyed by nothing, or by the wrong key — the guid needs a real map.
- A TTL: the freshness rule (R7) says live-at-read; a saved entity is the only stale risk and the
  tick already covers it, so time adds a knob and no correctness.

**Consequences.** DD-318's posture is superseded for this screen's read only, by name; the Atlas
GETs and the bulk card read keep DD-318's rule. A saved entity opened in a second tab can show
its pre-save view until reload — accepted, session memory, marked in the service.

## DD-606. The trail fills DD-317's seam from the view, opened entity last

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-14

**Decision.** `DetailsBreadcrumbState` (DD-317's seam) stays and the screen fills it: on every
view arrival, `setTrail` with the view's `breadcrumb` (stored order, top down — each crumb's
name, or its type, or its guid) plus the opened entity's own crumb last, which the breadcrumbs
mark active through `activeGuid` (7.13's contract). Icons ride the app's type map, as the header
badge's do (DET-26); a type the map never saw gets no icon. The screen's binding and crumb
routing (DET-06) do not change — the seam's contract holds as written. An entity without a
document shows its own crumb alone; no entity shows nothing.

**Reason.** The seam was drawn for exactly this fill (DD-317's consequence: "a later increment
fills it from an endpoint's answer"), and the view now carries the trail the indexer stored
(LAS-04). The legacy trail ended with the opened entity itself — the `activeGuid` input's
contract — so the entity's crumb belongs to the trail, not to the component.

**Alternatives.**

- Drop the store, derive crumbs in the component: one seam deleted, DET-12's spec pair rewritten
  for no behaviour change.
- Leave the entity crumb to the component: the trail of a parentless entity renders empty under
  the component's guard, and a page shows no name above its own title.

**Consequences.** DET-12's "renders empty" pins flip to filled trails; the direct-visit case now
shows a trail too (the document carries it without any walk). The `breadcrumbtype` of an
unmapped crumb renders the raw name, as DET-26's badge does.

## DD-607. The chips answer the entity's own classifications

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-14

**Decision.** The header's chips are the view's `classificationNames` (DD-090's stored field),
each by its dictionary display name — DET-09's rendering kept. Propagated tags stop showing: the
field holds the classifications the entity owns, and AVS's rule leaves the propagated names to
their source. The deviation is DV-166 in the ledger, in this increment's PR. The card bodies'
chips keep the bulk-read `classifications` and show propagation as today — their source is the
Atlas read, unchanged until 16.5c moves the card bodies.

**Reason.** The view answers one field set for every consumer (R2), and the read door's shape is
16.1's, fixed. The editor's box never let a propagated tag be edited (DD-326) and the mutation
door protects it from a save's diff (AVW-08): the tag is not the entity's to manage, and showing
it in the header promised control the screen never had. The detail GET's full classification
bodies were only ever read for their `typeName`.

**Alternatives.**

- The door answers propagated names too: a new field or a widened one, for a screen that cannot
  act on them — and the card and the trail would disagree with the editor.
- The screen keeps the Atlas GET for its chips: a second read per open for one chip row (fails R1).

**Consequences.** A field inheriting `PII` from its entity shows the chip on the entity's page
only, not on the field's; DV-166 says so. The unit pins that read `classifications` re-key to
`classificationNames`; the e2e chip scenario (EDT-05, a tag added to the entity itself) is
unaffected.
