# 16.5i A rule's verdicts through the view family: the store read and the door

- **Status:** in progress
- **Pull request:** –
- **Records:** ASG-09, VDR-14, AVS-12 new; DD-845 to DD-847; ADR 071 new; relies
  on 14.6 (ASG-01..07, DD-533..537, DV-160), 16.5h (ASG-08, AVS-11, VDR-13,
  DD-838), 16.2 (AVR-01/AVR-08, DD-586) and 16.1 (AVS-02, DD-581)

This page is the `aurelius-atlas-core` part of increment 16.5i; its rule table
is the increment's shared set. The other part is with
[`aurelius-atlas-webapp`][part-0], which draws the rule's page.

The legacy details screen of a governance rule asked the `atlas-dev-gov-quality`
engine for the rule's own verdicts — twice, once for `compliant: '1'` and once
for `compliant: '0'`, each on the rule's GUID — and drew the two counts, the
compliance chart and the two card lists from the answers
(`apps/atlas/src/app/search/details/gov-quality/`). Aurelius already stores
those documents: 14.6's worker judges every active governance rule over every
entity of its type and keeps the verdicts current (ASG-03, ASG-06). 16.5h
opened the index per entity for the cards (ASG-08, VDR-13). What no door answers
is the same index read by rule, which is what the rule page needs.

[ADR 071](../../../../../docs/architecture/adr/071-a-rule-s-verdicts-come-through-the-view-family.md)
decides the shape: a fourth door of the view family answers a rule's verdicts,
because the App Search wire is on its exit path and gains no new consumer
([ADR 064](../../../../../docs/architecture/adr/064-the-webapp-reads-rich-catalogue-data-through-one-aurelius-view-family.md)).
This increment is the store read and the door. The screen that reads them is
[part-0].

[part-0]: ../../../../../apps/aurelius-atlas-webapp/specs/7-25b-rule-verdicts-page/spec.md

## Scope

- the batched verdicts read by rule on the documents contract (ASG-09);
- the door's answer shape: one row per judged entity (AVS-12);
- the door itself: its route, its privilege, its refusals and its answer
  (VDR-14).

Not in scope:

| Not delivered                                                                                                | Lands with |
| ------------------------------------------------------------------------------------------------------------ | ---------- |
| The rule page: counts, chart, the two card lists (DET-50..DET-54, DV-201)                                    | [part-0]   |
| The App Search wire's `/gov_quality` engine: unchanged, still answering the original webapp (ASG-07, ASG-01) | –          |
| A verdict as a door query field or facet (the page filters by rule, which the door's body names)             | – (16.6)   |
| A live re-judge on read: the door answers what the worker last wrote (ASG-06, ADR 071 R2)                    | –          |

## Semantics

The ids continue 14.6's `ASG` and 16.x's `VDR`/`AVS` namespaces; the rule ids
name the read and the door, and the screen's DET ids live with
[part-0](../../../../../apps/aurelius-atlas-webapp/specs/7-25b-rule-verdicts-page/spec.md).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASG-09 | The documents contract answers `verdicts_by_rule(rule_guid)` with the stored verdicts of that rule in document id order (DD-845). The read pages the verdicts index the way ASG-08's read does — one terms filter, now over `guid`, sorted by `id` with `search_after`, sources kept (ASG-03). A rule with no verdict documents answers the empty list. The Elasticsearch store and the in-memory store both answer it (EDS-03's narrow contract)                                                                                                                                                                                     |
| AVS-12 | The door answers one row per verdict: `entity` the judged entity's GUID, `compliant` the verdict's `compliant` as a boolean (`"1"` true, `"0"` false, any other value `null`), `name` the rule name the document holds, and `message` its `noncompliant_message` (DD-846). The rows are ASG-09's order, and the door caps nothing: the page grows by the search door's paging of the rows [part-0] resolves, as every details box does (DET-22)                                                                                                                                                                                       |
| VDR-14 | `POST /api/aurelius/v1/rule/verdicts` answers AVS-12's rows for the body's `rule` GUID (ADR 071). The door needs `ENTITY_READ` and answers `VIEW_FORBIDDEN` without it, as the search and read doors do (AVR-01). Its refusals are `VIEW_REFUSED` in the door's shape, one message per problem (AVR-13): a body that is not an object, a missing `rule`, and a `rule` that is not a GUID. The door reads only the verdicts index: it never reads the rule's entity, judges nothing, and starts no task, so a GUID of anything at all — a rule that is inactive or deleted, an entity, no entity — answers the empty list (R2, ASG-06) |

## Aurelius origin

From `aureliusenterprise/aurelius` at commit b057389:

- `apps/atlas/src/app/search/details/gov-quality/compliant-cards/compliant-cards.component.ts`
  and `non-compliant-cards/`: the two asks — `{ compliant: ['1'], guid: [entityId] }`
  and `{ compliant: ['0'], guid: [entityId] }` on the `atlas-dev-gov-quality`
  engine, `result_fields` `entity_guid`, page size 250, then the entity page of
  9 by the `guid` facet. ASG-09 answers both asks with one read (DD-845); the
  split into the two sets is the screen's, not the store's (DD-847).
- `libs/atlas/api/src/lib/elastic/engines/gov-quality-search.service.ts`: the
  engine client the legacy asks ride. ADR 071 keeps it answering the original
  webapp and gives it no new consumer.
- The verdict documents (ASG-03, `StoredVerdict`) already hold every field the
  rule page shows: `entity_guid`, `compliant`, `name`, `noncompliant_message`.

## Deviations

Against Apache Atlas: none — this surface has no Atlas twin (ASG-07 holds, and
the App Search wire answers exactly as 14.6 fixed it). Against the legacy ask,
[DV-201](../../../../../docs/architecture/conversion/deviations.md): the page's two
engine queries become one Aurelius door call that answers both verdicts sets.

## Acceptance

Unit (offline, `uv run pytest libs/python/aurelius-atlas-core/tests`):

- `tests/test__entity_documents.py` (beside the ASG-08 read): ASG-09 — a rule's
  verdicts in id order over both stores, the empty list for a rule none of, the
  rows of two rules never mixed, and the read's paging proven on a page size of 1.
- `tests/test__view_rule.py` (the family's door tests): VDR-14's refusals — a
  non-object body, a missing `rule`, and a `rule` that is no GUID — and AVS-12's
  rows, including a `compliant` the store holds as neither `"1"` nor `"0"`
  answering `null`, and a GUID that is a GUID but names nothing answering empty.

Route (offline, `uv run pytest apps/aurelius-atlas-server/tests`):

- `tests/test__view_family.py` (beside the family's other door tests): VDR-14's route — the answer
  shape, `VIEW_FORBIDDEN` without `ENTITY_READ` (the family's fixture),
  `VIEW_REFUSED` bodies, and the empty list for a GUID with no verdicts.

E2E (Level 2, on the dev Elasticsearch):

- `libs/python/aurelius-atlas-core/e2e/test__rule_verdicts_e2e.py`: seed a
  dataset, seed an ACTIVE readable rule over its type, wait for the worker's
  round (ASG-06), read the door, and state the judged dataset's row and the
  count of the rule's verdicts (ASG-09, VDR-14). The names ride the run and
  self-clean (DD-223, 9.6).
