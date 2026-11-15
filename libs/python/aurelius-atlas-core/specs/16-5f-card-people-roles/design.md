# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an
accepted entry is never edited except its status line, and a changed decision is a new entry that
supersedes the old one.

## DD-626. The card's roles ride the stored document, not a per-card read

- **Status:** Proposed
- **Increment:** 16.5f
- **Date:** 2026-11-15
- **Supersedes:** none (amends DD-617's flat row and DV-167)

**Decision.** The indexer fills `deriveddomainleadguid`, `deriveddataownerguid` and
`deriveddatastewardguid` on each mapped entity's document, read from the entity's
`domainLead`, `businessOwner` and `steward` relationship attributes with the membership
test the same file already uses for parents (`collection_elements` on
`entity_type.relationship_attributes`, LAS-04). The read door answers them in
`card.relations` (AVS-10), and the card renders the labelled rows (VCF-15).

**Reason.** A card resolves through the search door in one round (ADR 064 R1): its people,
breadcrumb and derived relations all come from the stored document, and no per-card entity
read exists. The legacy demo took the other route — each card component read its own
entity and asked `relationshipAttributes.domainLead` and friends — which is exactly the
per-entity walk 16.5's doors retired. 16.5d left the card flat because the document had
nothing to answer (DV-167); the fields the legacy mapping already declared were never
filled by its pipeline (all 684 fixture records `null`). Filling them here puts the roles
where the card already looks, with the attribute-keying `read_ends` proved for the view
door (VDR-02, DD-604).

**Alternatives.**

- The demo's per-card entity read: one round per card on both screens, the N+1 the doors
  exist to remove (fails ADR 064 R1).
- Read the roles off the view door only, cards stay flat: the results rows would lose the
  roles the demo shows there, and 16.5d's one-card-two-screens rule (DD-616) would break.
- Leave it out (DV-167 standing): the review asked for the roles; the document is the only
  place a card can find them.

**Consequences.** The document gains three name/GUID pairs (ASD-06). A freshly written edge
shows on a card only after the indexer's round, so the demo's immediate-roles behaviour
deviates by that delay (DV-167 amended). `card.relations` gains three keys; VCF-17 pins
that the People facet (VCF-09, keyed `m4i_person`) and the opened entity's box (VDR-03)
are unaffected, because the role keys are different attributes.

## DD-627. Each role field keeps the name/GUID pair, though the legacy named only the GUID

**Decision.** Each role field ships as a pair like the derived relations do (LAS-05):
`deriveddataownerguid` with the GUIDs and `deriveddataowner` with the names at the same
positions, first-wins deduped. The legacy mapping declared only the three `…guid` fields.

**Reason.** The card links each person by name, and the door answers a card's people from
the document alone: the sibling `derivedperson` pair already carries both lists for exactly
this reason (AVS-02, ASU-03 — an end the store dropped keeps its stored name). A GUID-only
role field would make the door read each person entity to label it, undoing the one-round
rule DD-626 exists to keep.

**Alternatives.**

- GUID-only, as the legacy declared: the door reads each role end per card (fails DD-626's
  premise).

**Consequences.** ASD-06 names six fields where the legacy named three. The name lists are
keyword-mapped with their GUID siblings (ASD-02 extended); 16.6 retires the wire with them.

## DD-628. The source hash carries a derivation version, so the round backfills the roles once

- **Status:** Proposed
- **Increment:** 16.5f
- **Date:** 2026-11-15
- **Supersedes:** none (amends ASD-03)

**Decision.** `source_hash` folds in a derivation version, `1` for a document as 14.2 wrote
it and `2` for one carrying ASD-06's role fields. Every stored version-1 document's hash
then differs from its entity's current hash, `awaits_document` marks it stale, and the
indexer's round re-derives and fills it once (ASD-04's set, ASD-07). The card keeps the
flat row for a document still awaiting that round (VCF-16).

**Reason.** The role fields are derived from edges, so they are not in the hash's inputs
(ASD-03 hashes the entity's own fields and listed relationships). Without a version, an
entity that never changes keeps a version-1 document forever and its card stays flat for
years. The version is the smallest lever that turns the existing staleness rule into a
one-time backfill: it costs one re-derivation per entity, then settles. A full reindex
(14.2's `run_once` from scratch) is the blunt alternative and re-writes documents that
need nothing.

**Alternatives.**

- A full reindex on deploy: re-writes every document including correct ones, and an
  operator step our deploys do not have.
- Lazy-on-read fill in the door: the door reads edges per card again (fails DD-626).
- No backfill, roles only on documents written after 16.5f: a card's roles depend on when
  its entity last changed, which reads as a random bug.

**Consequences.** Version `1`/`2` constants live with the hash. The first round after the
deploy is larger than a normal one — bounded by ASD-04's pages, no new mechanism. VCF-16's
flat row is the visible face of a document in that window, and it disappears as the round
reaches each entity.
