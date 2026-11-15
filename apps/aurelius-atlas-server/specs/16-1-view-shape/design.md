# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-580. The shape lives in the shared model library

- **Status:** Proposed
- **Increment:** 16.1
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The card and the view are Pydantic models in `aurelius_atlas_model.views`, built on
`AtlasModel` like every other wire model. The server, the Python client and the hand-mirrored
Angular models treat that file as the one definition of the fields.

**Reason.** The conversion's drift problem is the hand-mirrored Angular twin (7.3): each shape
that lives twice drifts. The model library is where a wire shape belongs (ADR 004), and 16.2 and
16.3 answer through it, so one definition serves the doors.

**Alternatives.**

- Models in the server: the Python client and any second consumer cannot import them, as 8.4
  learned and fixed for the aux APIs (CL-01..50).
- A generated Angular client from OpenAPI: the generator decision is bigger than this increment
  and belongs to its own record.

**Consequences.** The Angular models of 16.5 mirror `views.py` by hand until a generator replaces
the mirroring; a field change names both files in its PR.

### DD-581. One derivation, shared by the doors

- **Status:** Proposed
- **Increment:** 16.1
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `aurelius_atlas_core` holds one `view_of(stored entity)` function and its card
projection. The read door, the write door's answer and the search door's results all call it. A
door adds nothing to the shape on its own.

**Reason.** ADR 064's rule is that the three doors answer one shape. A shared function is that
rule made executable: a field added once reaches every door at once, and the parity of a card
with a view's card fields is structural, not tested against drift.

**Alternatives.**

- Each route composing its own answer: three definitions of "the same shape", which is the
  today's-client problem moved to the server.

**Consequences.** The derivation is tested once (AVS-02, AVS-08); the door tests prove routing,
authorization and freshness, not the fields.

### DD-582. A relation end is a name and a GUID, never a body

- **Status:** Proposed
- **Increment:** 16.1
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The `relations` of a card and the seeded part of a view's `sections` hold
`{guid, name}` pairs read from the stored document. A view never carries the full entity of a
related end, and no door resolves pairs into bodies.

**Reason.** The stored document pairs names with GUIDs (LAS-05), so pairs cost nothing and bodies
cost a read per page. The webapp's screens navigate to a related entity rather than embedding it
(7.21a's cards open a route), and a screen that needs a body opens the read door for its GUID,
which is one call it would make anyway. Resolving bodies in the view re-creates the fan-out ADR
064 exists to remove.

**Alternatives.**

- Resolving the pairs server-side: a per-section read storm moved from the client to the server,
  with no saved round trip when the person does not open the section.
- Bodies for the first K ends: a second contract nobody asked for (ponytail: no door before it
  is knocked).

**Consequences.** If a future card design needs more of a related end (its badge, say), the pair
model or a batch door is a decision for that increment, recorded here as the open seam.

### DD-583. The shape carries its freshness, not a promise

- **Status:** Proposed
- **Increment:** 16.1
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** A card and a view carry `stale` (the stored document's flag, ASU-01) and
`updateTime`. They carry no freshness enum and no ETag, and they do not hide a stale document.

**Reason.** ADR 064's R7 states freshness per endpoint, and DD-524 already chose to answer a
stale document rather than hide it. The fields tell the client what the worker knew when it
derived; a hidden stale document would make a renamed entity vanish for a round, the same
failure DD-524 rejected for the engine.

**Alternatives.**

- Omitting `stale`: the webapp cannot tell "old" from "absent", and 16.3's mutation answer needs
  the distinction to mark its own write fresh.
- ETags: an HTTP cache layer is the client-cache decision of its own record, not this shape's.

**Consequences.** The write door (16.3) answers a view it derived live, so it marks `stale`
false. The results list may show a name a round old, as DD-524 accepted.
