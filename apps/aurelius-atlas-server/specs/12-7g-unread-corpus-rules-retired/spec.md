# 12.7g The unread corpus rules retire

- **Status:** in review
- **Pull request:** #458
- **Records:** adds DD-844 (here) and DV-200; amends nothing on the wire. Relies
  on VEV-03 (12.2, a rule is ACTIVE unless its `active` attribute is false),
  ASG-02/ASG-03 (14.6, an unread or inactive rule judges nothing), and DD-635
  (12.7b, the retirement as data).

## Scope

The sample corpus ships 34 governance rules the vocabulary cannot read. 33 of
them carry a
`conditional_value('target_relationship_type', 'source_typename' | 'target_typename', {…})`
expression. Each one asks what type a relationship is, or what type the entity
on its other end is. The 34th is `m4i_field--qualifiedName`
(`5a96a80f-acde-4856-8466-9ac5386d7af1`), a `uniqueness('qualifiedName')`
expression of the `uniqueness` dimension. The vocabulary has two kinds —
`ATTRIBUTE_PRESENT` and `ATTRIBUTE_NOT_EMPTY` — and neither reads a type or a
value another entity holds (GQ-01, GQ-07). The rules are therefore unread on
every read path (VEV-03, ASG-02) and paint an iconless row on the details box
(DV-155): the four `m4i_dataset--…--source`/`--target` rows the product owner
saw first, then the field's `qualifiedName` row the owner found next.

The ask behind this increment was whether the verdicts are calculated. They are:
the readable rules of the opened type each carry a live verdict. The rows with
no icon are the unread ones, shown iconless by design (DV-155). The owner's
decision is to retire the unjudgeable rules rather than leave iconless rows on
every page, and the corpus audit that followed named the `qualifiedName` rule as
the last one in the same posture. It is the only active rule of either bundle
that reads nothing once the 33 retire.

This increment edits those 34 records in both sample bundles. Each carries
`active: false`. No code changes: VEV-03 and ASG-03 already take an inactive
rule out of the verdicts, the editor, the rule pages and the 14.6 read set, the
12.7d precedent (DD-638).

Delivered here:

| Module                                   | Holds                                         |
| ---------------------------------------- | --------------------------------------------- |
| `data/atlas-sample/sample_data.zip`      | the 34 rule records, `active: false`          |
| `data/atlas-sample/only_gov_quality.zip` | the same 34 records, the same edit            |
| `e2e/test__aurelius_atlas_webapp.py`     | the box scenario reads its count, not pins it |

Explicitly not delivered, with the increment that will:

| Not delivered                                         | Lands with           | Why                                                                                                                                                        |
| ----------------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A check kind for a relationship's or neighbour's type | none (needs a spike) | the verdict record never carries those type names (VEV-08: a relationship reads as its end GUIDs); judging one is a new engine capability, not a rule edit |
| A check kind for a value another entity holds         | none (needs a spike) | uniqueness is a scan over the type, and a governance verdict answers over one record (DD-487); the store already reserves each unique value (ENS-05)       |
| Deleting the 34 records                               | none                 | `atlas-export-order.json` names their GUIDs; deactivation is the corpus's own removal (VEV-03 hides an inactive rule)                                      |

## Semantics

No new rule id and no code change. VEV-03 and ASG-03 already take a rule with
`active: false` out of the verdicts, the editor, the rule pages and the 14.6
read set — the 12.7d retirement (DD-638), applied to 34 records. The box's
client filter (`isActive`, the same reading) drops them from the details
section. The rules of the two expression forms the vocabulary reads (GQ-07 as
amended by ASG-02) are untouched: the corpus keeps its readable rules and judges
them.

## Aurelius origin

- `libs/m4i-governance-data-quality/.../rules/definitions/*.json` — the corpus's
  own rule definitions; the `conditional_value` form ships there and never had a
  vocabulary reading.
- `libs/m4i-data-management/.../quality/rules/conditional_value/` — the legacy
  evaluator for the form, over a DataFrame. Aurelius judges one record with the
  two presence kinds and has no DataFrame half (DD-487), so the form has no port.
- `libs/m4i-data-management/.../quality/rules/uniqueness/` — the legacy evaluator
  for `uniqueness(...)`, over the same DataFrame. It answers whether one value
  appears once among the rows of a type, which no governance verdict of one
  record can answer (DD-487), so the form has no port either.

## Deviations

[DV-200](../../../../docs/architecture/conversion/deviations.md): the corpus
ships 34 rules the vocabulary cannot read, so every page of a type that carries
them shows iconless rows. The frozen `atlas-dev` oracle judged none of them —
they were never in its read set. Retiring them moves Aurelius closer to the
oracle and takes the iconless rows off every page.

## Acceptance

- The three 14.6 gates, unchanged: `test__app_search_governance.py` (28 of 65
  rules read, 1,785 verdicts; the count line `65` counts rule entities by
  state, not by the `active` attribute, and the 34 already read nothing, so
  nothing moves), `test__legacy_app_search_fixtures.py`, `test__app_search_indexer.py`.
- Both bundles: only the 34 rule records changed, every other entry byte-identical.
- Webapp E2E (`nx e2e aurelius-atlas-webapp`): `test__the_dataset_page_turns_the_quality_rules_section`
  reads the box's count line instead of pinning it (DD-223), because the count
  is the store's and a corpus edit moves it. DET-47's nine-per-page growth rides
  the unit suite.
