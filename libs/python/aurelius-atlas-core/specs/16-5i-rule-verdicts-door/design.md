# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-845. The verdicts index gains a read by rule, next to the read by entity

- **Status:** Proposed
- **Increment:** 16.5i
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** The documents contract gains `verdicts_by_rule(rule_guid)`,
implemented the way ASG-08's `verdicts_by_entity` is: one paged terms filter over
the verdicts index (`guid` this time), `sort` on `id` with `search_after`, the
sources validated into `StoredVerdict` (ASG-09). The Elasticsearch store pages it
like `_verdict_ids` does; the in-memory store answers it by filtering its held
verdicts in sorted-id order.

**Why.** The legacy page asked the engine the same question twice
(`compliant: '1'` and `compliant: '0'`, both on `guid`), and ADR 071 gives the
new webapp one call that answers both. A read by rule is the only store shape
that fits: an entity-keyed read (`verdicts_by_entity`) would need every GUID of
the type up front, and a scan of the entities index cannot say which are judged.
Keeping the read on the narrow `EntityDocuments` contract (19.4) leaves the
route thin and the fake store honest (EDS-03).

**Considered and rejected.** _A join in the search door_ — verdicts are not
entities and the door's field table (AVR-03) has no verdict fields; adding them
would let any query sort or facet over them, which the frozen oracle never
offered (ASG-05). _A materialised per-rule list on the rule's document_ — the
worker would re-derive a rule's whole entity set on every entity write, and
14.6's digest rule (ASG-06) deliberately keeps verdicts keyed by the judged
entity.

## DD-846. The door answers verdict rows, not cards

- **Status:** Proposed
- **Increment:** 16.5i
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `POST /api/aurelius/v1/rule/verdicts` answers
`{verdicts: [{entity, compliant, name, message}]}` (AVS-12): one row per stored
verdict, `entity` the judged entity's GUID and `compliant` the document's `"1"`
or `"0"` as a boolean. The shape lives in `aurelius_atlas_model/views.py` beside
the family's other DTOs, and its Angular twin rides `atlas-view.ts` (AVS-07).

**Why.** A verdict is not an entity, so the door cannot answer cards (ADR 064's
"one shape" covers the entity shapes; ADR 071 says so plainly). The four fields
are exactly what the legacy's two asks read (`entity_guid`, `compliant`, and the
message the card list's rows show). Returning the rule name and message costs
nothing — the verdict documents copy them from the rule when they are written
(ASG-03) — and saves the screen a second read of the rule.

**Considered and rejected.** _Two endpoints, compliant and non-compliant_ — the
page wants both counts from one round (DD-847's single read); _a boolean filter
in the body_ — the page always asks both sets, so the filter would only fork the
contract.

## DD-847. The door never reads the rule, and the screen splits the rows

- **Status:** Proposed
- **Increment:** 16.5i
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** The door's body names a GUID and the door reads only the verdicts
index (VDR-14): it never checks that the GUID is a rule, and any GUID without
verdicts answers the empty list. The screen (part-0) splits AVS-12's rows into
the two sets the legacy drew, on the row's `compliant`, and resolves the judged
entities through the search door's `guid` filter like every other details box
resolves its rows.

**Why.** The verdicts index is the whole truth of what the worker judged
(ASG-06), and a rule's identity adds nothing the page uses — the page is already
opened on the rule, and its view carries the rule's own fields. A door that
read the rule would need the entity store, a second privilege story for deleted
rules, and a round-trip on every page open, for no answer the screen needs. The
split by `compliant` is the legacy's own split (its two `filters.all` asks) and
the counts fall out of the row arrays the page already holds, so the page costs
two requests total: this door plus one card resolve per page of nine (DET-22).

**Considered and rejected.** _Counting server-side_ — the legacy counts came
from the engine's page metadata, but the browser holds every row of both sets
after one read, and a server count that could disagree with the rows the page
renders would be a new bug, not a saved query.
