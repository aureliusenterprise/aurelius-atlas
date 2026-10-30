# aurelius-atlas-dsl

The Atlas DSL (DD-002, DD-217, DD-218). This file covers wiring specific to this lib; workspace-wide rules —
including the scaffold recipe for Python libs — live in the root `AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `grammar/` — `AtlasDSLLexer.g4` and `AtlasDSLParser.g4`, byte-identical to Atlas 2.4.0 (no hook touches
  them), and `generate.sh`, which runs the ANTLR tool on them
- `aurelius_atlas_dsl/generated/` — the lexer and parser ANTLR 4.13.2 generates; never edit, regenerate. Left
  out of ruff, pyright, coverage, Sonar, the hooks and the traceability check
- `aurelius_atlas_dsl/atlas_dsl.py` — `AtlasDSL`: `parse` (`Parser#parse` with its `Validator`),
  `QueryMetadata`
- `aurelius_atlas_dsl/dsl_tree.py` — the typed syntax tree, one node per grammar rule (DD-218)
- `aurelius_atlas_dsl/tree_builder.py` — ANTLR's contexts to those nodes
- `tests/` — DSL-01 to DSL-07; `tests/fixtures/atlas_queries.json` holds the queries of Atlas's DSL tests with
  their source lines

## Conventions

- Change neither grammar file: a difference from Atlas's grammar is a deviation, recorded first.
- The ANTLR tool's version in `grammar/generate.sh` equals `antlr4-python3-runtime`'s pin in `pyproject.toml`;
  bump both and regenerate together.
- Read contexts in `tree_builder` through its typed helpers (`_child`, `_optional`, `_children`, `_tokens`),
  not the generated accessors, whose return types pyright cannot narrow.
- Raise `AtlasError` with codes from `aurelius_atlas_model.errors` (DD-023).

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`, ruff and pyright excludes,
  `exclude-subpackages` of the traceability check); depends on `aurelius-atlas-model` (`implicitDependencies`
  too).
- `.pre-commit-config.yaml` excludes `grammar/*.g4` and `generated/*.py`.
- `sonar-project.properties` (excludes `generated/`) and `.env.enc` (`SONAR_TOKEN`) for the CI Sonar job.
- `docs/api-reference/libs/python/aurelius-atlas-dsl.md` and its `mkdocs.yaml` nav entry.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-dsl/tests
npx nx test aurelius-atlas-dsl -c ci
uv run pyright libs/python/aurelius-atlas-dsl
npx nx generate-parser aurelius-atlas-dsl  # needs Java 11+; then commit generated/
```

## Removal

Remove it together with DSL search (4.4), which composes its queries from the tree.
