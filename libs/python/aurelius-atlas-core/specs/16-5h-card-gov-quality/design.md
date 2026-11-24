# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an
accepted entry is never edited except its status line, and a changed decision is a new entry that
supersedes the old one.

## DD-838. The card carries its refused verdicts, and the doors join them

- **Status:** Proposed
- **Increment:** 16.5h
- **Date:** 2026-11-23
- **Supersedes:** 16.1's not-delivered row for the card's per-rule verdicts (amends AVS-01)

**Decision.** The card shape gains `verdicts`: the entity's non-compliant
governance verdicts as `{rule, name, message}` rows (AVS-01 amended, AVS-11).
The store's documents contract gains one read, `verdicts_by_entity(guids)`,
which pages the verdicts index with a `terms` filter on `entity_guid` and groups
the documents by entity (ASG-08). The derivation takes a `verdicts` argument
beside `ends` and `propagated`, and the two read doors supply it: the search
door with one read for the whole page, the read door with one read of its entity
(VDR-13). `read_page_verdicts` mirrors `read_page_propagations` (DD-836).

**Reason.** The legacy card fetched its own verdicts, one App Search request per
visible card (DV-198). A card on the view family cannot fetch anything (ADR 064
R1: one door round per screen), and 16.5b already set the pattern for a derived
field the document does not hold: the door reads the join once per page and
threads it into `view_of` (DD-836). The verdicts index already holds the
documents and the worker already keeps them current (ASG-03, ASG-06), so the
join costs one paged search per page and no new derivation. The legacy engine
returned a document per rule per entity; the card needs only the refused ones
(AVS-11).

**Alternatives.**

- Per-card fetches through the App Search wire (the legacy path): a results page
  of twenty cards costs twenty extra requests, the wire retires in 16.6, and the
  card's "dumb" contract (DD-616) forbids a fetch of its own.
- Store the refused verdicts on the App Search document, filled by the
  governance worker (ASD-06's path for the role ends): every verdict becomes a
  document edit and a hash change, the documents grow by the verdicts of every
  rule, and the card's rows still need a join to name the rules. The verdicts
  index already answers this in one read.
- The webapp reads the verdicts through the aux validate API, as the details box
  does (DET-42, DD-520): that answers the verdicts of one opened record
  recomputed live, not a page's worth, and it asks the aux service on every card
  (DV-155's reasoning kept it there for exactly that reason).

**Consequences.** `EntityCard` grows one field and both the Python and Angular
mirrors gain it (AVS-07). The store's narrow contract gains one read (EDS-03),
so the in-memory store answers it too. Every card answer gains the empty
`verdicts` list, as `propagatedClassifications` gained its in 16.5b (AVS-05
keeps null keys out, not list fields); the OpenAPI shape moves with it. A card's
verdicts are as fresh as the worker's last round, exactly like `stale` already
says (AVS-06) — the same freshness DD-524 and DD-628 accepted for the other
derived fields.

## DD-839. The rows are the refusals, sorted by name and capped at 100

- **Status:** Proposed
- **Increment:** 16.5h
- **Date:** 2026-11-23
- **Supersedes:** none

**Decision.** A card's `verdicts` hold the entity's non-compliant verdicts only,
each as `{rule, name, message}` (the rule GUID, the rule name, and
`noncompliant_message`), sorted by rule name then rule GUID and stopped at 100
rows (AVS-11).

**Reason.** The legacy card fetched `compliant: ['0']` with `size: 100` and
sorted nothing (its dropdown listed the engine's order). Sorting makes the
dropdown stable between pages and reloads, which the legacy's engine order was
not, and 100 keeps the card's cap and the legacy page size in one number. The
rows carry the rule name the card itself does not print: the legacy row showed
`result` under the message, and no Aurelius verdict document ever filled that
field (ASG-03's field table). The card prints the message alone, the one line
that ever had text (VCF-19), and the name on the wire orders the rows and lets
the caller label them.

**Alternatives.**

- Compliant verdicts too: the card's mark counts refusals (the legacy trigger),
  the count input is the refused list, and doubling the rows doubles the answer
  for a column that shows nothing of them.
- The legacy's engine order: a dropdown that reshuffles on every page reload is
  a defect the legacy shipped, not a rule to port.
- No cap: the demo's corpus judges a handful of rules per record, and the cap
  costs one slice; an unbounded list would let one rule storm flood a dropdown.

**Consequences.** The count the mark shows is the row count, so a capped card
shows "100x" for more (the legacy did the same, page 100 was all it asked). The
details box stays the place that lists every rule of a type with its verdict
(DET-42).

## DD-840. An unjudged card shows no mark

- **Status:** Proposed
- **Increment:** 16.5h
- **Date:** 2026-11-23
- **Supersedes:** none

**Decision.** The card draws the governance mark only when the store marks the
entity judged (`governed` true, AVS-01). A judged entity with no refusals draws
the green check, and an unjudged one draws nothing at all (VCF-20).

**Reason.** The legacy card asked one question of its own fetch — did any
document name a refusal — and drew the green check whenever the answer was none,
whether because the record passes its rules or because no rule exists for its
type. The store already knows the difference: the governance worker marks every
entity it judges (ASG-06, DD-535), and `governed` carries that mark onto the
card today (AVS-02). A card that drew the check for every unjudged record would
print a verdict the store never made, the same false claim DD-583 and DD-524
avoid for the other derived fields.

**Alternatives.**

- The legacy posture (green check whenever nothing is refused): a type with no
  governance rules at all looks certified compliant on every card.
- A neutral dot for unjudged: a third state the legacy never had, for a column
  the user reads as good-or-bad.
- `governed` alone with no rows: kept, and the rows answer the "which rules" on
  hover, which is what the dropdown is for.

**Consequences.** VCF-20 replaces the legacy's blanket check, recorded as the
second difference in DV-198. The ui part stays dumb (DD-154): the card passes
`verdicts` and the judged mark, and the mount decides.
