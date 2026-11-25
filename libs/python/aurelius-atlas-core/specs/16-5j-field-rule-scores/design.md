# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-862. The field's results read rides the entity index, not a new index

- **Status:** Proposed
- **Increment:** 16.5j
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `results_by_field(field_guid)` (ASQ-09) pages the **entity** index,
not a new one: a filter on `typeName = m4i_dq_score` and `state = ACTIVE` —
`scores()`'s filter — plus a terms filter on `qualityResult.fieldguid`, sorted
by `guid` with `search_after`, and the answer is each hit's stored
`qualityResult`. The in-memory store answers the same predicate over the
entities it holds, in GUID order.

**Why.** The quality worker already stores what the box needs on the score
entity itself (ASQ-02, DD-528) and already maps `qualityResult.fieldguid` as a
keyword (ASQ-03), so the read is one filter the index can answer with no new
index, no new mapping, and no worker change. The alternative store shape —
reading the scores and filtering in Python — is `scores()` plus a full scan: the
demo ships 42 scores, the legacy deployment's own quality index ships one
document per rule per field, and a scan prices that per read rather than per
round. The sort is the read's own (`guid`), which makes the answer stable across
pages; sorting in Python would make `search_after` meaningless.

**Considered and rejected.** _A materialised list on the field's document_ — the
worker would rewrite every field document a rule touches whenever a score
changes, where the totals roll-up already pays its own careful price (ASQ-05);
_as a search-door field_ — 16.6's hold stands, and the box's condition is a
stored `fieldguid`, which `SearchParameters` has no form for (DD-444's argument,
unchanged).

## DD-863. The rows ride the view as `ruleScores`, not the cards

- **Status:** Proposed
- **Increment:** 16.5j
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** The score rows join the `EntityView` as `ruleScores: [{rule, name,
dimension, score}]` (AVS-13), not the `EntityCard`. `card_of` drops the field the
way it already drops `sections` and `attributes`, and the search door answers it
empty.

**Why.** A score is a fact about a **pair** — one rule over one field — while a
card is a fact about one entity. The box's cards resolve through the search
door's `guid` chunks, which serve every screen at once: a rule card shown on the
results page, on a dataset's box, and on three field pages cannot carry one
field's score. Putting it on the card would either answer a wrong number on the
other screens or force the search door to know which field asked. The field view
is the one place the pair is named, and the screen already holds it (DET-08's
read), so the join costs the box nothing — the same shape 7.25b's verdict boxes
use, where the screen holds the rows and the shared chrome draws them (DD-848).
The four fields are exactly the legacy ask's `result_fields` (DD-864); the rule
name rides because a box card whose rule the store lost still names itself.

**Considered and rejected.** _A card field the search door fills_ — the pair
argument above; _a fifth door_ — the verdicts door has one because the rule page
needs a per-rule read of an index keyed by the judged entity (ADR 071); here the
field's own read is the door, and a second call would break DET-62's one-read
rule for a box that shares the screen's view.

## DD-864. The read door joins the rows only for a field

- **Status:** Proposed
- **Increment:** 16.5j
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `_live_view` calls `results_by_field` only when the entity's type
name is `m4i_field` (VDR-16), beside the verdicts read it already runs. Every
other type answers `ruleScores` empty without a store round trip.

**Why.** ASQ-02 stores only field GUIDs in `qualityResult.fieldguid`, so a
result of another type is always empty — and 14.5's own worker proves the shape
holds: the totals roll-up reads the results' `fieldguid` and their fields' data
attributes, never any other end (ASQ-04/05). Gating on the type therefore costs
nothing in truth and saves a search on the six other layouts that ride the same
door — the gate the 7.25a box list applies to the governance box for the same
reason (DD-841). It also keeps the mutation door thin: the field's post-save
re-read (DD-679) rides the same helper and pays the one read, which is what the
screen shows after a save of the field's rule ends.

**Considered and rejected.** _Join for every type_ — an empty answer per open
dataset, collection, system, attribute, entity and domain page (the corpus's 25
scored fields sit under one dataset), paid for a set 14.5 can never fill; _read
lazily in the derivation_ — `view_of` reads nothing by design (AVS-08, DD-581),
and a derivation that queries would make the search door pay it too.
