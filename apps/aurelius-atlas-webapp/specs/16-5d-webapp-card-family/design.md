# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an
accepted entry is never edited except its status line, and a changed decision is a new entry that
supersedes the old one.

## DD-614. The card's description falls back to the entity's `description`

- **Status:** Proposed
- **Increment:** 16.5d
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `view_derivation` fills the card's `definition` field with the entity's `definition`
attribute, else its `description` attribute, else none. The view's `attributes` map keeps both
values as the store holds them, and no other card field changes.

**Reason.** The card body's text rule is "definition then description" (DET-10/DD-320), but a card
carries only its `definition` field. The m4i governance types store their text under `definition`,
so the field served every card so far; the Apache Atlas model types (`DataSet` and its subtypes,
which the sample catalogue and every real registration carry) store the same text under
`description`, and their cards answer an empty field. The body of a `DataSet` card would render no
text while the same entity's details box shows its description. One fallback in the one derivation
makes the card field mean what the body rule needs everywhere, with no new field in the shared
shape (AVS-07's three readers stay in step without a wire change).

**Alternatives.**

- A second card field `description`: three model files, the Python client and the Angular mirror
  each gain a field that is always the same value as `definition` (fails AVS-01's field set without
  need).
- The webapp keeps reading `attributes` for the body: the card's whole point is that a body renders
  from the card alone, and a results card has no `attributes` to read (fails ADR 064 R2).

**Consequences.** A card of a `DataSet` answers its description text in `definition` (the field's
name is now a misnomer kept for the wire, as AVS-01's set is frozen). The details header's
description box reads `attributes` and does not change. The card of an entity whose two attributes
hold different texts shows the `definition`, the body rule's order.

## DD-615. The details sections resolve their cards through the search door

- **Status:** Proposed
- **Increment:** 16.5d
- **Date:** 2026-11-14
- **Supersedes:** DD-368's transport clause (the chunked bulk GET); DET-18's rules carry to the door

**Decision.** `RelatedSectionsState` resolves each chunk of 25 seed GUIDs with one
`POST /api/aurelius/v1/search` body: `filters.guid` the chunk, `limit` its length, no query, no
facets. A GUID the `cards` answer lacks is a deleted relation and a failed chunk drops its cards,
as DET-18 stated over the bulk answer. The card bodies render the answered `EntityCard` instead of
the bulk `AtlasEntity`. The `GET /api/atlas/v2/entity/bulk` call leaves the sections store; its
other callers (the Governance Quality rows, the person box's chunk, the tests' seeders) keep it.

**Reason.** This is what the legacy did: its section cards came from the search engine's documents,
which is why they could lead with a breadcrumb trail (DD-365's port records it). The door answers
the same GUID set in one round and carries the body fields the shared card needs — `breadcrumb`,
`definition`, `classificationNames`, the derived person relations — which the bulk shape has no
source for. Keeping the bulk read would keep two shapes under one card, the split ADR 064 R2
closes. The door's `guid` field is indexed exactly (AVR-03) and its `limit` bound (100) is four
times the chunk, so no chunking rule changes.

**Alternatives.**

- A bulk views door (`POST /entity/guids`): a fourth door for one caller, when the search door over
  the GUID field already answers the set (fails YAGNI).
- The sections keep the bulk read and the shared card grows a second input shape: the card becomes
  per-source again and the results row still cannot show a trail (fails R2).

**Consequences.** A section card of a not-yet-indexed entity waits for the indexer's beat: the
entity answers from the read door (a direct store read) before its document exists, so its card is
missing from the answer and DET-18's deleted-relation rule drops it until the next open. The 16.5b
e2e waits for the door to carry its seeded cards before it opens the screen. A `m4i_source` or
`m4i_dq_score` end has no document (DD-500), so its card answers with empty derived fields — the
body renders the title and badge alone, and the trail its own crumb.

## DD-616. One shared rich card for both screens

- **Status:** Proposed
- **Increment:** 16.5d
- **Date:** 2026-11-14
- **Supersedes:** DD-367's field set (its uniformity clause stands)

**Decision.** One app component (`search/shared/catalogue-card.component.ts`) renders a view-family
card for both screens: the plain ui `entity-card` shell, its `[card-content]` slot filled with the
breadcrumb trail (the card's stored `breadcrumb` plus its own active crumb, `trailOf`'s rule,
exported shared), the chips, the description markdown, and the flat people row. The results rows
and the section cards both mount it; the loading row stays the plain shell's.

**Reason.** DD-367 refused the trail and kept the people on the bulk shape because neither had a
source (DD-317's empty seam, DD-369's rule). The card carries both sources now (AVS-01, 14.2), so
the refusal's premise is gone, and the legacy showed one rich card everywhere. Two screens drawing
the same entity differently is the defect this increment was asked for: one component is the only
shape that keeps them equal under change (ADR 064 R2). `trailOf` moves to the shared module so the
details header and the card share the crumb rule (name, or type, or guid) rather than copy it.

**Alternatives.**

- Extend the ui-lib card: the trail needs the app's type-to-icon map and router, and the lib stays
  dumb (DD-154's split, UIC-15) (fails the lib's rule).
- Keep two components kept in sync by review: the divergence we just observed is what this avoids
  (fails the point).

**Consequences.** The results row gains visible fields (VCF-04 supersedes VSR-07's clause). The
section cards lose the badge alias (DV-167: the card shape has no `typeAlias`; the sample
catalogue uses none, the demo detail 16.5b's spec test pinned retires). The details header trail,
the People box and every bulk-shape caller are untouched.

## DD-617. The card's people row is flat — names without roles

- **Status:** Proposed
- **Increment:** 16.5d
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The card's people row lists the card's derived person relations as plain names
(linked, deduped by guid), under the one label "People". No role grouping, no labelled rows.
DV-167 records the gap with the note to solve it when a source exists.

**Reason.** The document's `derivedperson` pair names every person at any end (LAS-05), and the
legacy's per-role document arrays (`deriveddomainleadguid` and friends) were never filled — the
fixture suite pins that as `NEVER_FILLED`. The legacy card body carried the three labelled rows
from the entity read, not from the engine's document. The card cannot group what it cannot name,
and a wrong label is worse than none: the opened entity's People box keeps the true labelled rows
from the view's `sections` (VDR-03).

**Alternatives.**

- The card body fetches each card's ends for the roles: per-card reads return, exactly what DV-83
  retired (fails the one-read rule).
- A role-keyed relations answer from the door: the document stores no roles (LAS-05), so the door
  would walk — ADR 064 R1's refusal (fails the derivation rule).

**Consequences.** A person visible on a results card appears without their role until a source
exists (DV-167). The flat row rides `m4i_person` relations only; an entity type whose people live
under another name answers none, which is the document's honest answer.
