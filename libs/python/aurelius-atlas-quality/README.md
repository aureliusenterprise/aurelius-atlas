# aurelius-atlas-quality

The data quality engine of Aurelius Atlas (increment 12.1). A rule is data: one
of ten check kinds from a closed vocabulary, a dimension, parameters, and a
threshold. The library turns a rule into a row mask over a
[polars](https://pola.rs) `DataFrame`, scores it, rolls the scores up per
dimension, and converts to and from the shapes the store holds. It runs no code
the vocabulary cannot name (DD-451), and it has no I/O: the scanner that reads
data and writes scores is 12.2, and the REST surface that serves the scores is
7.25.

## What it holds

| Module     | Holds                                                                                              |
| ---------- | -------------------------------------------------------------------------------------------------- |
| `rule`     | the five dimensions, the ten check kinds, the rule and its parse-time validation (DQ-01, DQ-02)    |
| `checks`   | the row mask each kind asks for, over a polars frame (DQ-03)                                       |
| `evaluate` | a rule over a frame into a score, a verdict, and the rejected rows (DQ-04, DQ-05)                  |
| `score`    | the rollup: rule scores to dimension scores to the overall score (DQ-06)                           |
| `atlas`    | the glue: a stored rule entity to a rule, results to score documents (DQ-07, DQ-08, GQ-07, ASG-02) |

The semantics live in [`specs/12-1-quality-engine/spec.md`](./specs/12-1-quality-engine/spec.md)
and its design records in `design.md` beside it.

## Using it

```python
import polars as pl
from aurelius_atlas_quality import CheckKind, Dimension, DqRule, evaluate_rules, summarise

rule = DqRule.from_json(
    {
        "name": "email completeness",
        "checkKind": CheckKind.COLUMN_NOT_NULL_RATIO,
        "params": {"column": "email"},
        "threshold": 0.9,
    }
)
frame = pl.DataFrame({"email": ["a@b.c", None, "d@e.f"]})
summary = summarise(evaluate_rules([rule], frame))
assert summary.score == 2 / 3
```

A stored rule reads through `rule_from_atlas_attributes`, and a run writes
through `result_documents`, which renders one `m4i_dq_score` document per
scoring rule plus one overall document. An empty frame has no score — nothing
was measured — and stores nothing (DQ-04, DQ-08, DD-369's posture).

A rule outside the vocabulary, or a rule whose parameters disagree with its
kind, raises `QualityRuleError` at parse time. A parameter that names a column
the frame lacks raises `polars.exceptions.ColumnNotFoundError`; the caller
decides what that means — the scanner (12.2) records the rule as ERROR, an API
answers 400.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-quality/tests
npx nx lint aurelius-atlas-quality
npx nx typecheck aurelius-atlas-quality
```
