# 12.7b The dataset rules become pairs, and a verdict names both pickers

- **Status:** in review
- **Pull request:** #371
- **Records:** adds VEV-09 (here) and DD-635..636 (here); adds DV-171; amends
  GQ-06's reading on the wire (an OR verdict names its alternatives) and the
  sample corpus's four rule records. Relies on VEV-08 (12.7a, the picks ride the
  record) and GQ-06/ASG-02 (the `|` pair already parses; here it travels).

## Scope

The sample corpus holds four dataset rules that read one name each. Two ask a
dataset for a field (`length('fields', 1)`), two ask one for a child or a parent
(`completeness('childDataset')`, `completeness('parentDataset')`). The product's
rule is different: a dataset must hold a field or a child dataset, and it must
belong to a collection or have a parent dataset. Four one-name rules paint a
warning on a dataset that meets the rule through its other half.

This increment edits the four records in both sample bundles. The fields rule
becomes `length('fields', 1) | length('childDataset', 1)`, the collections rule
becomes `length('collections', 1) | length('parentDataset', 1)`, and the two
presence rules go inactive. The grammar already understands an OR: GQ-06 and
ASG-02 parse the whole `|` pair and the engine passes when the first name or any
alternative passes. What the wire lost was the second name: a verdict carried
only its first attribute, so the editor could paint the pair's line under only
one of the two pickers it measures. VEV-09 puts the alternatives on the verdict,
and the editor paints the line under each control the rule names.

Delivered here:

| Module                                           | Holds                                                     |
| ------------------------------------------------ | --------------------------------------------------------- |
| `data/atlas-sample/sample_data.zip`              | the four rule records, edited                             |
| `data/atlas-sample/only_gov_quality.zip`         | the same four records, the same edit                      |
| `aurelius_atlas_validate_entity_client.models`   | the verdict grows `anyOf`                                 |
| `aurelius_atlas_validate_entity.verdicts`/routes | the alternatives travel; a one-name verdict omits the key |
| `aurelius-atlas-data-access`                     | the TS twin grows `anyOf`                                 |
| `aurelius-atlas-webapp` editor                   | a verdict paints under each control it names              |
| `aurelius_atlas_core.app_search_governance`      | `usedattributes` names every attribute the rule measures  |

Explicitly not delivered, with the increment that will:

| Not delivered                                                       | Lands with              | Why                                                                                                                   |
| ------------------------------------------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Deleting the two retired rules                                      | none                    | `atlas-export-order.json` names their GUIDs; deactivation is the corpus's own removal (VEV-03 hides an inactive rule) |
| The stored path's `[]`-present reading of an empty relationship end | 14.6's DD-536 follow-up | unchanged here (DD-634's table); the pairs are `length` rules, which already missed `[]` (DD-632)                     |
| Pairs over a `completeness` alternative                             | none                    | the corpus's two pairs are both `length` halves; GQ-06 already reads a `completeness` pair too (ASG-02)               |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056).
The reference is the Aurelius source and the corpus itself (ADR 052).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VEV-09 | A verdict names every attribute its rule measures. The first is `attribute`, as VEV-02 states; the `\|` alternatives that follow it are `anyOf`, a JSON list of names, in the order the expression holds them (GQ-06's reading, ASG-02). A rule that measures one name answers with no `anyOf` key at all — the key is absent, never null or empty. The editor paints the verdict under the control each name names (EDT-24 amended, DD-636). |

The sample corpus's rules change as data, not as code. The fields record (`cfd24715-125d-46e2-854d-b0c1b16340bf`)
and the collections record (`fb2c608f-d7ff-4574-8c2d-a240c8c79e91`) carry the pair expression, the pair
name, and the pair sentences for `ruleDescription`, `compliantMessage`, and `nonCompliantMessage`. The
childDataset record (`0d3807d0-d6cc-4093-b990-6a0928504a94`) and the parentDataset record
(`7bf6b045-704c-46ff-aed2-91885ff890f7`) carry `active: false`; VEV-03's reading retires them from the
banner, the details box (DET-42), and 14.6's engine (ASG-03). The 12.7a scenario's `completeness('childDataset')`
restatement keeps answering its lines — the scenario stubs its own rules, so the retirement answers no verdict
there, and 14.6's stored-path reading of the pair halves stands as ASG-04 states it.

## Aurelius origin

- `data/atlas-sample/sample_data.zip` — the four rule records themselves; the pair sentences are the
  product's rule, stated in the records' own message fields.
- `libs/m4i-governance-data-quality/.../rules/definitions/m4i_dataset.json` — the corpus's own OR pair
  (`length('dataDomain', 1) | length('parentEntity', 1)` on `m4i_data_entity`) is the precedent for the
  shape; its 16 legacy verdict documents carry both names in `usedattributes`, which is the reading
  DD-636 copies.
- `apps/atlas/src/app/search/components/editor/components/gov-quality-display/` — the legacy card keyed
  its lines by attribute; the pair line lands under each name's card the same way.

## Deviations

[DV-171](../../../../docs/architecture/conversion/deviations.md): the sample corpus's two dataset rules
are pairs, where the frozen `atlas-dev` oracle judged one-name rules. The oracle falsifies for exactly
those two rules: 44 of its verdict documents carry a description the records no longer hold, 12 of its
verdicts now pass through the alternative the oracle's rule did not measure, and the two renamed records
join the name differences of DD-485's list. Every other document of the oracle still answers as it was.
The edit was accepted with the damage named (the user's decision, recorded in DD-635).

## Acceptance

Unit (`uv run pytest apps/aurelius-atlas-validate-entity/tests`), on the fake catalogue:

| Proves | File                                                                                                 |
| ------ | ---------------------------------------------------------------------------------------------------- |
| VEV-09 | `tests/test__verdicts.py` (the pair's verdict carries `anyOf`; a picked alternative passes)          |
| VEV-09 | `tests/test__aurelius_atlas_validate_entity_app.py` (the whole-body answer: `anyOf` present, absent) |

Scenarios: `scenarios/validation/verdicts.scenario.yaml` restates the fields record as the corpus's new
pair, in the vocabulary shape (`dqanyOf`). Every stage's fields verdict carries `anyOf: [childDataset]`
and the pair sentences, and the last stage — a draft whose picker holds a child — passes the pair
through the alternative (VEV-09).

Webapp unit: `entity-editor.component.spec.ts` (the pair's line rides both pickers once each). Run
`nx test aurelius-atlas-webapp -c ci`.

14.6 gates, re-baselined under DV-171 (`uv run pytest libs/python/aurelius-atlas-core/tests`):
`test__app_search_governance.py` (45 of 95 read, 2,558 verdicts, 12 moved to compliant — all of them a
pair rule's own, the other 1,600 kept), `test__legacy_app_search_fixtures.py` (44 stale descriptions,
all two pair rules), `test__app_search_indexer.py` (three name differences). The engine's reading is
unchanged (ASG-02/ASG-04); only the corpus's rules and the counts moved.

E2E: the app's suite seeds its own rules, and the webapp's banner suite seeds under `DataSet--`, so the
corpus edit answers nothing there. The pair's live proof is the unit and scenario legs (level 0), and
the re-baselined 14.6 gates run inside `nx affected -t test e2e -c ci`.
