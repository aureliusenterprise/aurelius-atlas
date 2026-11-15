# 12.7c The field and data-entity rules answer as hierarchy pairs

- **Status:** in review
- **Pull request:** #372
- **Records:** adds DD-637 (here) and DV-172; amends nothing on the wire. Relies on
  DD-635 (12.7b, the pairs as data), VEV-09 (12.7b, the alternatives travel), and
  GQ-06/ASG-02 (the `|` pair parses and passes on any name).

## Scope

12.7b paired the two dataset rules. An audit of the other 91 sample-corpus rules
against the metamodel's hierarchy edges found the same contention twice more,
and one already-paired case.

A rule over a hierarchy asks a node for an edge. A one-sided rule penalizes a
node that holds its content or its placement through the other side of the same
edge. The metamodel carries both sides — every `parentX` end has its `childX` —
so the honest rule is a pair.

| Rule                          | Type             | Contention                                                                | Treatment                                          |
| ----------------------------- | ---------------- | ------------------------------------------------------------------------- | -------------------------------------------------- |
| `m4i_field--datasets`         | 264 fields       | 16 nested struct fields hang off a `parentField`, never their own dataset | paired here: `\| length('parentField', 1)`         |
| `m4i_data_entity--attributes` | 16 data entities | 1 entity carries its attributes on its child entities                     | paired here: `\| length('childEntity', 1)`         |
| `m4i_data_entity--dataDomain` | —                | a sub-entity hangs off a parent entity                                    | already a pair in the corpus (the 12.7b precedent) |
| `m4i_dataset--fields`         | —                | a dataset holds a child dataset                                           | paired by 12.7b (DV-171)                           |
| `m4i_dataset--collections`    | —                | a dataset holds a parent dataset                                          | paired by 12.7b (DV-171)                           |

The audit left eight one-sided rules alone: `m4i_collection--datasets`,
`m4i_data_domain--dataEntity`, `m4i_data_attribute--dataEntity`,
`m4i_data_attribute--businessOwner`, `m4i_data_entity--businessOwner`,
`m4i_data_entity--steward`, `m4i_data_domain--domainLead`, and
`m4i_system--collections`. None has an honest hierarchy alternative: a leaf
(attribute, owner-less domain) has no parent to borrow from, an owner or steward
edge is not a hierarchy, and the two sample systems that miss `collections` hold
no `parentSystem` either, so a pair would hide a real gap.

## Semantics

No new rule id. VEV-09, GQ-06, and ASG-02 already carry a pair end to end; this
increment changes two records as data, as DD-635 did. Python tests name the ids
with `@pytest.mark.covers(..., rules=[...])` (ADR 056).

The two records change in both shipped bundles:

- `m4i_field--datasets` (`cad0a3bf-9f7f-464f-aeb5-9ce97eb993b3`): expression
  `length('datasets', 1) | length('parentField', 1)`, name
  "Field belongs to a dataset or a field", pair sentences for
  `ruleDescription`/`compliantMessage`/`nonCompliantMessage`.
- `m4i_data_entity--attributes` (`c4d10911-7661-4058-a2df-a25fbed0e093`):
  expression `length('attributes', 1) | length('childEntity', 1)`, name
  "Data entity has a data attribute or a child", pair sentences.

No rule is retired; both halves stay active. Each pair keeps its one-sided
demand for the node that has neither edge: a struct field's parent rides a
dataset, and a data entity with neither attributes nor children still answers
its refusal line (the sample's `test` entity, empty on both sides, proves it).

## Aurelius origin

- `data/atlas-sample/sample_data.zip` — the two records; the metamodel's
  `m4i_field_parent_assignment` and the `parentField`/`childField` and
  `parentEntity`/`childEntity` ends of
  `0010-m4i_data_dictionary_model.json` are the hierarchy the pairs read.
- The corpus's own `m4i_data_entity--dataDomain` pair
  (`length('dataDomain', 1) | length('parentEntity', 1)`) is the in-repo
  precedent, unchanged here.

## Deviations

[DV-172](../../../../docs/architecture/conversion/deviations.md): the sample
corpus's field and data-entity rules are pairs, where the frozen `atlas-dev`
oracle judged one-name rules. The oracle falsifies for exactly those two rules:
280 of its verdict documents carry a description the records no longer hold
(264 field + 16 data entity), 17 of its verdicts pass through the alternative,
and the two renamed records join DV-171's name-difference list (3 → 5).
Every other document answers as it was. The edit was accepted with the damage
named (the user's decision, DD-637).

## Acceptance

The pair reads and travels through 12.7b's legs; no new unit leg is needed for
the wire. The proof is the re-baselined 14.6 gates, on the fake client
(`uv run pytest libs/python/aurelius-atlas-core/tests`):

- `test__app_search_governance.py`: 45 of 95 read (unchanged — both pairs stay
  readable, no rule retires); 2,558 verdicts, 1,767 met and 791 missed; 1,583 of
  the 1,612 legacy verdicts kept, and the 29 that moved all belong to a pair rule
  (DV-160's 16 `conditional_value` verdicts stay absent).
- `test__legacy_app_search_fixtures.py`: 324 stale descriptions, all four pair
  rules'; 5 name differences; the `usedattributes`/first-name disagreement still
  199 (the oracle is unchanged).
- `test__app_search_indexer.py`: 5 name differences.
- 14.6's reading code is untouched (ASG-02/ASG-04) — only the corpus's rules and
  the counts moved.

Both bundles verified byte-surgical: integrity OK, 690/98 entries, and only the
two rule entries differ from HEAD.
