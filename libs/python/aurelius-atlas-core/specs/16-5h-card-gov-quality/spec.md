# 16.5h Governance verdicts on the rich cards: the store read and the door join

- **Status:** in review
- **Pull request:** #458
- **Records:** DD-838 to DD-840 (here); DV-198 new; AVS-01 amended in place; 16.1's
  "per-rule governance verdicts" not-delivered row closed for the card; relies on
  14.6 (ASG-01..07, DD-533..537), 16.1 (AVS-02/05, DD-581), 16.2 (AVR-08), 16.5b
  (VDR-12, DD-836), 16.5d (VCF-01, DD-616)

This page is the `aurelius-atlas-core` part of increment 16.5h; its rule table is
the increment's shared set. The other part is with
[`aurelius-atlas-webapp`][part-0], which renders the mark.

The legacy results card carried a governance mark in its quality column: a
warning icon with the count of the rules the entity fails, and a hover dropdown
of the failed rules. The legacy card fetched its own verdicts, one App Search
request per visible card, size 100 (`GovernanceQualityListSearchService` in the
legacy `search/components/governance-quality-list`). Aurelius already stores the
same verdicts: 14.6's worker writes one document per rule and entity into the
verdicts index and marks the entity `governed` (ASG-03, ASG-06). This increment
reads those documents through the store contract and joins them into the
view-family cards, one read per page, the way 16.5b joined the propagated tags
(VDR-12, DD-836).

## Scope

- the batched verdicts read on the documents contract (ASG-08);
- the card's `verdicts` field: the entity's non-compliant verdicts, carried by
  every door that reads them (AVS-11);
- the join in the search door (one read for the page) and the read door (the
  entity's own read), beside the propagations read (VDR-13).

Not in scope:

| Not delivered                                                                                         | Lands with |
| ----------------------------------------------------------------------------------------------------- | ---------- |
| The mark itself (VCF-19/VCF-20, the ui part)                                                          | [part-0]   |
| The details box, which keeps its live aux read (DET-42, DV-155)                                       | –          |
| A verdicts read in the mutation door's answer (the worker re-judges after the save, AVS-06's posture) | –          |
| Verdicts as door query fields or facets (the legacy card fetched by `entity_guid` only)               | – (16.6)   |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASG-08 | The documents contract answers `verdicts_by_entity(guids)` with the stored verdicts of these entities grouped by entity GUID, each group in document id order (DD-838). An entity with no verdicts answers no key, and an empty request costs no store request. The read pages the verdicts index the way `_verdict_ids` does, one terms filter over `entity_guid` sorted by `id` with `search_after`, and keeps the sources (ASG-03). The Elasticsearch store and the in-memory store both answer it (EDS-03's narrow contract)                                                                                                  |
| AVS-11 | The card's `verdicts` hold the entity's non-compliant governance verdicts, each `{rule, name, message}`: the verdict's rule GUID, rule name, and `noncompliant_message` (AVS-01 amended, DD-838). The rows sort by rule name then rule GUID and stop at the legacy card's 100 (DD-839). A judged entity with nothing refused answers the empty list, as do the other derived fields of an entity without a document (AVS-02), and `governed` stays the card's judged mark (AVS-01, ASG-06). The compliant verdicts stay in the index: the card's mark counts refusals, and the quality roll-ups carry the scores (AVS-01, LAS-12) |
| VDR-13 | The search door answers each card's `verdicts` from one `verdicts_by_entity` read of the page's GUIDs, beside the page's propagations read (VDR-12's pattern, DD-836). The read door answers its entity's `verdicts` from the same contract with the entity's own GUID. Both doors answer the verdicts the store holds now; a door without a store answers the empty list, as it does for the propagated tags (VDR-12, DD-835). The mutation door's answer keeps awaiting the worker's next round (AVS-06): its view carries the verdicts only when the read door re-reads it                                                     |

## Aurelius origin

- `search/components/governance-quality-list/governance-quality-list-search.service.ts`
  (legacy, Aurelius `atlas` app): one App Search request per card against the
  `atlas-dev-gov-quality` engine, `filters.all` `[{entity_guid: [entityId]}, {compliant: ["0"]}]`,
  `result_fields` `entity_guid, guid, name, compliant, noncompliant_message, result`,
  page size 100. ASG-08 replaces that N+1 with one terms read per page, and the
  door join (VDR-13) replaces the per-card fetch.
- The verdict documents (ASG-03, `StoredVerdict`) already hold the card's every
  field. The legacy dropdown showed `noncompliant_message` as the heading and
  `result` as the line, and no Aurelius document ever filled `result` (ASG-03's
  field table). The card's rows therefore carry the message alone, the one line
  the legacy ever had text in, and the rule name rides on the wire for the
  details box (DD-839).
- The legacy card mounted the mark under the `SHOW_GOV_QUALITY` injection token,
  in the card's quality column. The column's CSS aligned the mark to the card's
  bottom-right edge (`.quality` flex column, `align-items: flex-end` in the
  legacy details-card SCSS). The webapp part keeps that position (VCF-19).

## Deviations

Against Apache Atlas: none (the governance verdicts are m4i/Aurelius demo
furniture, DV-155).

Against the demo: DV-198 new. The demo fetched each card's verdicts itself, one
request per visible card. Aurelius joins the verdicts into the cards on the
server, one store read per page, so the card stays dumb (DD-616) and a page
costs one read instead of twenty.

## Acceptance

- `tests/test__entity_documents.py`: `verdicts_by_entity` groups the stored
  verdicts by entity, in id order, leaves an unjudged entity out, and answers an
  empty request without a search (ASG-08).
- `tests/test__view_derivation.py`: `view_of` with verdicts answers the
  non-compliant rows sorted by rule name then guid, capped at 100 (AVS-11);
  `read_page_verdicts` answers a whole page in one documents read (VDR-13).
- `tests/test__view_search.py`: a seeded verdict round answers the door's cards
  with `verdicts` (VDR-13, AVS-11), and a door without a store answers none.
- `libs/python/aurelius-atlas-model/tests/test__views.py`: the card serializes
  `verdicts` with camelCase aliases and no null keys (AVS-11, AVS-05).

No e2e scenario (DD-839's note): a card's verdicts exist only after the
App Search worker's round, so an e2e pin would race the worker. The states are
pinned in unit tests, and the worker's own round is 14.6's (ASG-06).

Run with `nx test aurelius-atlas-core -c ci` and `nx test aurelius-atlas-model -c ci`.

[part-0]: ../../../../../apps/aurelius-atlas-webapp/specs/16-5h-card-gov-quality/spec.md
