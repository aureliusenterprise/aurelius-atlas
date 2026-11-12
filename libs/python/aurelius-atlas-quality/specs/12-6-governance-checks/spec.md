# 12.6 The governance quality checks

- **Status:** in progress
- **Pull request:** –
- **Records:** adds GQ-01..08 and DD-487..490 (here); relies on DQ-01/DQ-02 (the vocabulary
  discipline), DD-450 (polars masks, the shape this half deliberately drops), DD-457 (patch 001, the
  precedent for GQ-08), and DV-146 (a stored expression is never executed). The records that change
  the product surface — ADR 061 and DV-153 (supersedes DV-67, the validate-entity mock retires) —
  join at 12.7, the increment this one unblocks. The roadmap row 12.6 joins
  [the ledger](../../../../docs/architecture/conversion/index.md) in the implementation PR.

## Scope

A governance-quality rule (`m4i_gov_data_quality`) answers one question about one catalogue record:
does this record hold the value its rule asks for? The legacy answered it with a Python expression
stored on the rule and evaluated by a Flink job (`length('dataDomain', 1) | length('parentEntity', 1)`);
nothing in Aurelius Atlas interprets those expressions (DD-369), and the deployed
validate-entity app still answers its fixed mock (DV-67).

12.1 built the engine for the other subject: a score over the rows of a dataset, as a polars row
mask. This increment builds the entity-subject half of the same engine. A governance rule is data
from a second closed vocabulary — two presence kinds over an entity attribute — and the evaluation is
one boolean verdict over the attributes of one record, in memory, no frame. The engine stays what
12.1 made it: no I/O, no store, no schedule. 12.7 (validate-entity's real backend) and 7.28 (the
webapp's banner and gov rule form) consume it.

Delivered here:

| Module                                                             | Holds                                                          |
| ------------------------------------------------------------------ | -------------------------------------------------------------- |
| `aurelius_atlas_quality.governance`                                | the two governance kinds, the gov rule, the one-record verdict |
| `aurelius_atlas_quality.atlas`                                     | grows: `rule_from_gov_attributes`, `GOV_RULE_TYPE_NAME`        |
| `aurelius-atlas-core` patch `002-gov_data_quality_vocabulary.json` | the vocabulary attributes on `m4i_gov_data_quality`            |

Explicitly not delivered, with the increment that will:

| Not delivered                                        | Lands with        | Why                                                                   |
| ---------------------------------------------------- | ----------------- | --------------------------------------------------------------------- |
| Fetching the active gov rules and evaluating a draft | 12.7              | validate-entity owns that call path; the engine takes data            |
| The verdict REST shape and the editor banner switch  | 12.7 / 7.28       | DV-67 retires there, by ADR 061 and DV-153                            |
| The gov rule editor form and the kinds endpoint rows | 7.28 / 12.7       | The vocabulary needs its consumers, not a server change here          |
| Storing each entity's verdicts when the entity saves | 12.8 (planned)    | The server's write path evaluates and stamps; this lib stays I/O-free |
| Re-validating stored entities in bulk                | a later increment | The scanner scores dataset files; gov rules do not join it            |
| A migration of the stored expression rules           | a data PR         | Sample-corpus rules re-author through the editor, not a script        |

## Semantics

Python tests name the ids, the `aurelius-atlas-dsl` convention. The legacy origin is the Aurelius
source (below), not Apache Atlas: Atlas has no governance rules.

| Id    | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GQ-01 | A governance rule is data: a `GovCheckKind` from the governance vocabulary, the `attribute` it measures, an optional `anyOf` list of further attributes, the rule's own `compliantMessage` and `nonCompliantMessage`, and the store `guid` of the entity that carries it. It has no threshold and no score: a verdict over one record is boolean.                                                                                             |
| GQ-02 | Parsing a governance rule validates it through the same door as DQ-02: an unknown kind, a missing or unknown parameter, or an `anyOf` that is not a list raises `QualityRuleError`. Nothing outside the vocabulary is executed.                                                                                                                                                                                                               |
| GQ-03 | The governance vocabulary is `GOV_KINDS`, two rows of the same `KindSpec` shape `KINDS` uses (dimension, required, optional, reason), so one resource can serve both vocabularies: `ATTRIBUTE_PRESENT` (required `attribute`, optional `anyOf`) and `ATTRIBUTE_NOT_EMPTY` (same parameters), both in dimension COMPLETENESS — the dimension every stored governance rule names.                                                               |
| GQ-04 | `evaluate_gov_entity(rule, attributes)` answers one record: `compliant=True` when the check passes. `ATTRIBUTE_PRESENT` passes when the attribute holds a value that is not null — an empty string or an empty collection counts as a value. `ATTRIBUTE_NOT_EMPTY` passes when the value holds content: a string of at least one character, a collection of at least one value, or any present non-collection value.                          |
| GQ-05 | An attribute the record does not carry fails the check; it never raises. The legacy scored a missing column zero for both of its governance functions, and an editor draft is always missing something. A rule that names a malformed attribute raises at parse (GQ-02), never at evaluate.                                                                                                                                                   |
| GQ-06 | `anyOf` restates the legacy \| bar: the kind's check applies to the rule's attribute and to each listed attribute, and one pass makes the verdict compliant. The verdict's message is the rule's own message for its verdict (`compliantMessage` or `nonCompliantMessage`, read also under the corpus's lowercase `noncompliantMessage` spelling), or the kind's reason line when the rule stores none.                                       |
| GQ-07 | `rule_from_gov_attributes` reads a stored `m4i_gov_data_quality` entity's attributes as a gov rule: `guid`, `name`, `dqcheckkind`, `dqattribute`, `dqanyOf`, and the two messages, each bare or as the webapp's `{raw: …}` wrapper. A rule with no `dqcheckkind` — a stored expression rule — raises `QualityRuleError`, the DV-146 case: the caller records it, nothing executes it.                                                         |
| GQ-08 | Patch `002-gov_data_quality_vocabulary.json` (`TYPEDEF_PATCH_M4I_0011_002`, `ADD_ATTRIBUTE`, `m4i_gov_data_quality` 1.0 → 1.1) adds `dqcheckkind` (string), `dqattribute` (string), and `dqanyOf` (`array<string>`, SET) to the type, through the loader path that applies patch 001 at server start (DD-457). The type's legacy `expression`, `ruleType`, and `qualityDimension` attributes stay: a stored value is never dropped (ADR 046). |

## Aurelius origin

Not a Java port — Apache Atlas has no governance quality. The origin is the Aurelius source, cited
so a reviewer can compare:

- `libs/m4i-data-management/.../core/quality/utils/run_quality_rule_expression/` — the legacy
  evaluator: `eval` over a whitelisted function set, `|` split into parts combined with `any`. The
  execution is **not** ported (DV-146's posture, extended to this half).
- `.../core/quality/rules/completeness/` and `.../rules/length/` — the two functions the governance
  corpus uses: not-null, and "at least n elements/characters, zero for a missing column". GQ-04 and
  GQ-05 restate them as data.
- `libs/m4i-governance-data-quality/.../rules/definitions/*.json` — the shipped rule corpus: 15
  `length('…', 1)`, 11 `completeness('…')`, one OR pair, every rule dimension `completeness`. This
  fixes the two-kind vocabulary (DD-488).
- `backend/m4i-atlas-post-install/data/atlas-dev-gov-quality.json` — the origin of the mock cards
  (VE-02): the same presence verdicts, frozen. 12.7 replaces them with these verdicts, live.

## Deviations

Against Apache Atlas: none, this surface exists in no Apache product. Against the Aurelius product:
the no-expression posture is [DV-146](../../../../docs/architecture/conversion/deviations.md)'s, and
this increment states its governance case inside that row's meaning rather than adding a row. The
the mock-retirement deviation (DV-153) and its ADR (061) join the 12.7 PR, where the user-visible change
lands. The legacy `compliantMessage`/`nonCompliantMessage` fields survive — the verdict lines are
their job (DV-148's "carry over where a field survives").

## Acceptance

Unit tests, one per public function and per rule id — the engine has no I/O, so no e2e here; 12.7
carries the integration proof:

| Proves    | File                                                                                            |
| --------- | ----------------------------------------------------------------------------------------------- |
| GQ-01..06 | `libs/python/aurelius-atlas-quality/tests/test__governance.py`                                  |
| GQ-07     | `libs/python/aurelius-atlas-quality/tests/test__atlas.py` (gov cases join)                      |
| GQ-08     | `libs/python/aurelius-atlas-core/tests/test__m4i_models.py` (the patch applies to the gov type) |

GQ-08 joins the loader count that `libs/python/aurelius-atlas-core/tests/test__m4i_models.py`
asserts (three model changes become four). Run:

```bash
uv run pytest libs/python/aurelius-atlas-quality/tests libs/python/aurelius-atlas-core/tests/test__model_loader.py libs/python/aurelius-atlas-core/tests/test__m4i_models.py
npx nx lint aurelius-atlas-quality && npx nx typecheck aurelius-atlas-quality
```

Markers validate per project (`--collect-only --trace-json`), not with the whole-repo trace check.
