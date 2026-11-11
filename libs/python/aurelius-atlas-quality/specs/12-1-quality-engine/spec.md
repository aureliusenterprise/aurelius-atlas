# 12.1 The data quality engine

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** adds DQ-01..08 and DD-450..454 (here), and DV-146 to
  [deviations](../../../../docs/architecture/conversion/deviations.md) in the implementation PR;
  relies on DD-002 (the lib-per-layer split), DD-369 (sourceless quality renders nothing, not zero),
  DET-35/DD-444 (the rules box seeds from the relationship end), DD-447 (the dumb quality components),
  DV-67 (the validate-entity mock is the current backend), and ADR 051/052/056.

## Scope

The webapp shows quality rules and their verdicts (7.24), and its score box, pies, badges, and
per-record verdicts wait on an evaluator (the 7.25 row, DD-369). The legacy evaluator was a Flink job
whose rules were custom Python expressions; Aurelius Atlas runs no rule engine, and the deployed
validate-entity app is still the fixed mock (DV-67).

This increment builds the engine as a library, `libs/python/aurelius-atlas-quality`. A rule is data: a
check kind from a closed vocabulary, a dimension, and parameters. The library turns a rule into a row
mask over a polars DataFrame, scores it, rolls the scores up per dimension, and converts to and from
the shapes the store holds. It has no I/O: the scanner that reads data and writes scores is 12.2, and
the REST surface that serves the scores is 7.25.

Delivered here:

| Module                            | Holds                                                                                                  |
| --------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `aurelius_atlas_quality.rule`     | the five dimensions, the ten check kinds, the rule, its parameter shape, and its parse-time validation |
| `aurelius_atlas_quality.checks`   | the row mask each kind asks for, over a polars frame                                                   |
| `aurelius_atlas_quality.evaluate` | a rule over a frame into a score, a verdict, and the rejected rows                                     |
| `aurelius_atlas_quality.score`    | the rollup: per-rule scores to per-dimension scores to the overall score                               |
| `aurelius_atlas_quality.atlas`    | the glue: a stored `m4i_data_quality` entity to a rule, results to score documents                     |

Explicitly not delivered, with the increment that will:

| Not delivered                                     | Lands with     | Why                                                                        |
| ------------------------------------------------- | -------------- | -------------------------------------------------------------------------- |
| Reading a dataset's rows from a source system     | 12.2           | The scanner owns I/O; the engine takes a frame the caller hands it         |
| Writing scores to the store, and the schedule     | 12.2           | The scanner owns the store; the engine only renders documents              |
| The score REST surface and the webapp's score box | 7.25           | The server and webapp read what the scanner stores                         |
| Real validate-entity verdicts over content        | 12.2/7.25      | DV-67 stands: the mock answers until the engine is wired                   |
| Custom rules beyond the closed vocabulary         | a later record | A custom rule needs its own decision (ADR); this port ships the closed set |

## Semantics

Python tests name the ids, the `aurelius-atlas-dsl` convention. The rule JSON and the score document
are this increment's own contract; the stored rule's legacy attribute names are cited from the sample
corpus and 7.24, not restated.

| Id    | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DQ-01 | A rule is data: a `checkKind` from the closed vocabulary, a `dimension` (one of the five), a `params` map, a `threshold` (a ratio, default 1.0), and the store `guid` of the entity that carries it. Each kind names the parameters it requires and its own dimension; `dimension` may be omitted, and then the kind's own is used.                                                                                                      |
| DQ-02 | Parsing a rule validates it. An unknown kind, a dimension that disagrees with the kind, a missing or unknown parameter, a castable type outside the named set, or a threshold outside 0..1 raises `QualityRuleError` (a `ValueError`). Nothing outside the vocabulary is ever executed.                                                                                                                                                  |
| DQ-03 | Each kind maps to a row mask over a polars frame: `True` on the rows the rule accepts. A null value is accepted — a null holds no violation — except for `ROW_FRESHNESS_MAX_AGE`, where a filled column that holds no time fails. A parameter that names a column the frame lacks raises `polars.exceptions.ColumnNotFoundError`.                                                                                                        |
| DQ-04 | `evaluate` runs one rule over a frame and answers the share of accepted rows as the `score`, the verdict `passed` (`score >= threshold`), the rows checked, the rows rejected, and the rejected rows capped at `max_failed_rows`. An empty frame has `score=None`: nothing was measured, so no score is invented (DD-369).                                                                                                               |
| DQ-05 | `evaluate_rules` runs each rule over the same frame, in order. A column error from any rule still raises for the caller to record.                                                                                                                                                                                                                                                                                                       |
| DQ-06 | `summarise` rolls results up: each dimension's score is the mean of its scoring rules' scores, and the overall score the mean of the dimensions, each weighed once. A dimension with no scoring rule is absent, never present at zero; a set with no scoring rule has `score=None`.                                                                                                                                                      |
| DQ-07 | `rule_from_atlas_attributes` reads a stored rule's attributes as a rule. A new rule names `dqcheckkind` and the `dq`-prefixed parameters; a legacy rule's `dataqualitytype`/`dataqualityoperator` pair maps through the known pairs, and its parameters arrive from the legacy attributes. A pair outside the map — the legacy free-text expression — raises `QualityRuleError`. Values read bare or as the webapp's `{raw: …}` wrapper. |
| DQ-08 | `result_documents` renders a run as one score document per scoring rule, plus one overall document with the per-dimension scores. Each carries the rule guid, dataset guid, run id, run time, dimension, kind, score, verdict, and row counts. A rule with no score produces no document (DD-369).                                                                                                                                       |

## Aurelius origin

This is not a port of a Java class; Apache Atlas has no rule engine. Its origin is the Aurelius
product's quality concepts, cited so a reviewer can compare the shapes:

- `apps/atlas/.../details/field/data-quality-cards`, the `m4i_data_quality` corpus, and the
  `dqscore_*` dimensions (7.24's "Aurelius origin") — the five dimensions and the stored rule this
  engine reads. The legacy's custom Python rule expressions are **not** ported (DV-146): the closed
  vocabulary replaces them.
- The legacy Flink `dqscore_*` writer — the score-per-rule-per-dataset document this engine renders
  through `result_documents`, without Flink.

## Deviations

Against Apache Atlas: none, the engine adds a product surface Atlas does not have. Against the
Aurelius product, added to [deviations](../../../../docs/architecture/conversion/deviations.md) in
the implementation PR:

- **DV-146**: the legacy measures a field with a custom Python expression stored on the rule; Aurelius
  Atlas stores a check kind from a closed vocabulary and its parameters, and never executes a stored
  expression. Legacy rules whose shape the vocabulary holds read through the pair map; the rest raise
  and need re-authoring.

## Acceptance

Unit tests, one per public function and per rule id, `uv run pytest libs/python/aurelius-atlas-quality`:

| Proves              | File                      |
| ------------------- | ------------------------- |
| DQ-01, DQ-02        | `tests/test__rule.py`     |
| DQ-03, DQ-04, DQ-05 | `tests/test__evaluate.py` |
| DQ-06               | `tests/test__score.py`    |
| DQ-07, DQ-08        | `tests/test__atlas.py`    |

The engine has no I/O, so it has no e2e here; the scanner (12.2) and the REST surface (7.25) carry
the integration proof.
