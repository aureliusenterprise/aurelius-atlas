# aurelius-atlas-quality

The data quality engine (increment 12.1, DD-450..454): a closed vocabulary of
ten check kinds, each one a row mask over a polars frame, with its score,
rollup, and the store glue. This file covers wiring specific to this lib;
workspace-wide rules live in the root `AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_quality/rule.py` — the leaf: dimensions, kinds, the `KINDS`
  registry (each kind's dimension, parameters, reason), `DqRule` and its
  parse-time validation. Imports nothing else from the lib.
- `aurelius_atlas_quality/checks.py` — the builders: one expression per kind,
  `mask_for` as the single door. Only `rule.py` data crosses in.
- `aurelius_atlas_quality/evaluate.py` — `evaluate`, `evaluate_rules`,
  `RuleResult`.
- `aurelius_atlas_quality/score.py` — `summarise`, `QualitySummary`.
- `aurelius_atlas_quality/atlas.py` — the store shapes: `m4i_data_quality`
  attributes in (`rule_from_atlas_attributes`), `m4i_gov_data_quality`
  attributes in (`rule_from_gov_attributes`, a legacy expression of the two
  forms read by `gov_expression_params`, ASG-02), `m4i_dq_score` documents out
  (`result_documents`).

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group,
  `uv.sources`).
- The specs live here: `specs/12-1-quality-engine/spec.md` with its `DD-450..454`
  entries in `design.md` beside it (the per-project layout new increments use).
- `docs/api-reference/libs/python/aurelius-atlas-quality.md` and its
  `mkdocs.yaml` nav entry.
- Readers of the scores arrive later: the scanner (12.2) and the server's
  score surface (7.25) depend on this lib; nothing depends on them here.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-quality/tests
npx nx lint aurelius-atlas-quality     # ruff
npx nx typecheck aurelius-atlas-quality  # pyright
```

## Conventions

- polars only: no pandas, no validation library (DD-450). The engine's whole
  dependency surface is `polars`; a second frame library forks every mask
  builder.
- A new check kind is one `KINDS` row in `rule.py` plus one builder in
  `checks.py` plus its `_BUILDERS` entry, and the vocabulary test in
  `tests/test__rule.py` covers the row. polars 2.x dropped string-to-date
  casts, so time parsing goes through `str.to_date`/`str.to_datetime` with
  `strict=False` — never a bare `.cast` of text.
- Null semantics: a null value is accepted (a null holds no violation, DQ-03);
  the freshness kind is the named exception. Uniqueness masks guard
  `cum_count().over(...)` with `is_not_null()` — polars counts nulls too.
- Errors: module-level message constants and `raise QualityRuleError(...)`
  (the house ruff style); a `ValueError` subclass, so callers catch one type.
- `mask_for` normalises `as_of` to naive UTC; zoned timestamps convert. Tests
  pin this with Berlin-zone instants (`AS_OF`, `_BERLIN` in `test__evaluate.py`).

## Removal

Removable as a slice: drop the three root `pyproject.toml` entries, the mkdocs
page and nav row, the roadmap row in `docs/architecture/conversion/index.md`,
and the projects that depend on it (12.2's scanner, 7.25's score surface) lose
their evaluator. `deviations.md` keeps DV-146 as history.
