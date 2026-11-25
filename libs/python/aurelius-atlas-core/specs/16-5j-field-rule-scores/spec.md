# 16.5j A field's rule scores through the view family: the store read and the door join

- **Status:** in review
- **Pull request:** #463
- **Records:** ASQ-09, AVS-13, VDR-16 new; DD-862 to DD-864 (here); relies on
  14.5 (ASQ-01..ASQ-08, DD-528..DD-532), 16.5h (ASG-08, AVS-11, VDR-13, DD-838),
  16.5i (AVS-12, VDR-14, DD-845..DD-847, ADR 071), 16.2 (AVR-01/AVR-10, DD-586)
  and 16.1 (AVS-02/AVS-04, DD-581)

This page is the `aurelius-atlas-core` part of increment 16.5j; its rule table is
the increment's shared set. The other part is with
[`aurelius-atlas-webapp`](../../../../../apps/aurelius-atlas-webapp/specs/7-25e-rules-box-rule-scores/spec.md),
which draws the box.

The legacy field page drew its Data Quality Rules box from the App Search
`data_quality` index: the query filtered `fieldguid: [entityId]` and its
`result_fields` carried `dqscore` beside the rule's name and dimension
(`apps/atlas/src/app/search/details/field/data-quality-cards/`), so every card
in that box was a rule **with its score on this field**. The Aurelius box seeds
from the field's own `dataQuality` end instead (7.24's DET-35, DD-444), and
DD-444 kept the score column out because at the time "the score has no source
(DD-369)". That premise expired: the 12.2 scanner writes `m4i_dq_score`
entities, 14.5's `QualityIndexer` derives each score's `qualityResult` — rule
GUID, rule name, dimension, and `dqscore`, over the fields it scored (ASQ-02) —
and 12.9 ships 42 of them over 25 fields in the demo corpus. The rows exist;
they just reach no screen.

The App Search wire answers them today for the original webapp, and
[ADR 064](../../../../../docs/architecture/adr/064-the-webapp-reads-rich-catalogue-data-through-one-aurelius-view-family.md)
forbids giving that wire a new consumer, while
[ADR 054](../../../../../docs/architecture/adr/054-the-server-api-is-the-webapps-one-data-plane.md)
keeps the server the webapp's one data plane. [ADR 071](../../../../../docs/architecture/adr/071-a-rule-s-verdicts-come-through-the-view-family.md)'s
answer generalises: the data joins the view family instead. This increment is
the store read and the read door's join; the box is
[part-0](../../../../../apps/aurelius-atlas-webapp/specs/7-25e-rules-box-rule-scores/spec.md).

## Scope

- the read of one field's stored quality results (ASQ-09);
- the view's `ruleScores` field: one row per rule that scored the field
  (AVS-13);
- the join in the read door, beside the verdicts join (VDR-16).

Not in scope:

| Not delivered                                                                                                                   | Lands with |
| ------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| The box: the score row on the rule cards, the legacy sorts (DET-65, DET-66, DV-207)                                             | [part-0]   |
| The score rows on search-door cards (the rows belong to one field's screen, like the verdict-seeded boxes' rows are one rule's) | –          |
| A `dqscore` or dimension facet or door query field (16.5i's hold, unchanged)                                                    | – (16.6)   |
| A score for a rule that never scored the field: the scanner produces none and the door joins none, as 14.5 stores none (ASQ-02) | –          |
| A live re-score on read: the door answers what the quality worker last wrote (AVS-06's freshness rule, ASQ-07)                  | –          |

[part-0]: ../../../../../apps/aurelius-atlas-webapp/specs/7-25e-rules-box-rule-scores/spec.md

## Semantics

The ids continue 14.5's `ASQ` and 16.x's `AVS`/`VDR` namespaces; the box's DET
ids live with [part-0](../../../../../apps/aurelius-atlas-webapp/specs/7-25e-rules-box-rule-scores/spec.md).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASQ-09 | The documents contract answers `results_by_field(field_guid)` with the quality results of the active score entities whose stored result names that field, in score GUID order (DD-862). The read pages the entity index the way `scores()` does — a filter on `typeName` and `state`, a terms filter on `qualityResult.fieldguid`, sorted by `guid` with `search_after`, sources kept (ASQ-03) — and answers the `qualityResult` of each hit; an entity of another kind, or a score holding no result, answers no row. A field no score names answers the empty list. The Elasticsearch store and the in-memory store both answer it (EDS-03's narrow contract) |
| AVS-13 | The view's `ruleScores` hold one row per quality result that reaches the entity — `{rule, name, dimension, score}`: the result's rule GUID, rule name, rule dimension, and `dqscore` (ASQ-02, DD-863). The rows are ASQ-09's order, unchanged and uncapped: a field's rules are its end, and DET-22's page is the screen's. A view of an entity the read door did not join answers the empty list, as the other derived fields do (AVS-02). The field is the view's own (AVS-04): a card never carries it (`card_of` leaves it out, as it leaves `sections` out), and the search door's cards answer none                                                       |
| VDR-16 | The read door joins `results_by_field(guid)` into the view it answers for an `m4i_field`, beside the verdicts read (VDR-13's pattern, DD-864). No other entity type pays the read: ASQ-02 stores field GUIDs in `fieldguid`, so a result never reaches another type, and the door's answer for one carries the empty list without a store round trip. The door answers what the store holds now (AVS-06); the mutation door's answer carries the rows only when its re-read runs the read door's join (VDR-13's posture). A store without the score entities answers the empty list like the verdicts join does                                                 |

## Aurelius origin

From `aureliusenterprise/aurelius` at commit b057389:

- `apps/atlas/src/app/search/details/field/data-quality-cards/data-quality-cards.component.ts`:
  the box's ask — the `data_quality` engine, `filters.all` `[{fieldguid: [entityId]}]`,
  `result_fields` `guid, name, dataqualityruledescription, dataqualityruledimension, dqscore`,
  page size 9. ASQ-09 answers the field's whole result set in one store read;
  the door (VDR-16, DD-864) hands it to the screen with the field's own view, so
  the box costs no request of its own (VDR-13's economy, DV-198's posture).
- `apps/atlas/src/app/search/components/cards/data-quality/data-quality-card.component.html`:
  the card the legacy drew from each result — the UIC-36 pie at
  `dqscore.raw * 100`, the percent, the dimension lowercased. Its rows are
  [part-0](../../../../../apps/aurelius-atlas-webapp/specs/7-25e-rules-box-rule-scores/spec.md)'s
  DET-65; AVS-13's row carries exactly the four fields the ask's `result_fields`
  named (the rule's GUID and name, the dimension, the score).
- The `qualityResult` documents (ASQ-02, `StoredQualityResult`) already hold all
  four under the engine's names, mapped for the terms filter the read uses
  (ASQ-03: `fieldguid` and `qualityguid` are keywords).
- 7.24's [DD-444](../../../../../apps/aurelius-atlas-webapp/specs/7-24-dq-rules-governance-banner/design.md#dd-444-the-rules-box-seeds-from-the-relationship-end-not-a-quality-index)
  named this return: "When 7.25 brings the scores back, the score stat, the sort
  list, and the card badge column arrive through their own entries, and this box
  does not change." The box's seed does not change here: the rules end stays the
  box's set (DET-35), and the score rows join it by rule GUID.

## Deviations

Against Apache Atlas: none — the data-quality scores have no Atlas twin (ASQ-08
stands, and the App Search wire keeps answering exactly as 14.5 fixed it).

Against the legacy ask: none new. The wire's `fieldguid` ask becoming a door
join is ADR 064's and ADR 071's existing rule (the wire gains no consumer), not
a new deviation — the same shape DV-198 and DV-201 record for the verdicts, and
those records stay the citation.

## Acceptance

Unit (offline, `uv run pytest libs/python/aurelius-atlas-core/tests`):

- `tests/test__entity_documents.py` (beside the ASG-08/09 reads): ASQ-09 — a
  field's results in score GUID order over both stores, the empty list for a
  field none names, a score whose result names a different field left out, an
  inactive score left out, a score entity holding no result left out, two
  fields' rows never mixed, and the read's paging proven on a page size of 1.
- `tests/test__view_derivation.py`: `view_of` with results answers AVS-13's rows
  in store order; a door that passes none answers the empty list; `card_of`
  leaves `ruleScores` out.

Route (offline, `uv run pytest apps/aurelius-atlas-server/tests`):

- `tests/test__view_family.py` (beside the family's other door tests): VDR-16 —
  the read of a field answers its rows, the read of a dataset answers none
  without a documents read (the door's type gate), `VIEW_FORBIDDEN` stands
  unchanged, and the mutation door's re-read answer carries the field's rows.

No e2e scenario of its own (DD-839's posture): the rows exist only after the
quality worker's round, and [part-0]'s e2e drives the field page over the demo
corpus (12.9), which proves the whole chain once.

Run with `nx test aurelius-atlas-core -c ci` and `nx test aurelius-atlas-model -c ci`.
