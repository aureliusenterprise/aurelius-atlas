# aurelius-atlas-typesystem

The Atlas type system (DD-002, DD-024, DD-025). This file covers wiring specific to this lib;
workspace-wide rules — including the scaffold recipe for Python libs — live in the root `AGENTS.md` and
`libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_typesystem/atlas_type.py` — `AtlasType`: name, category and the value contract (VAL-02)
- `aurelius_atlas_typesystem/builtin/` — one module per nested class of `AtlasBuiltInTypes` (DD-041), with
  `integral_type` and `floating_type` for what the number types share
- `aurelius_atlas_typesystem/enum_type.py`, `array_type.py`, `map_type.py` — `AtlasEnumType`, `AtlasArrayType`,
  `AtlasMapType`, definition and value side
- `aurelius_atlas_typesystem/types.py` — the struct, classification, entity, relationship and business metadata
  types, definition side only until 2.1c (DD-025, DD-041)
- `aurelius_atlas_typesystem/java.py` — Java's number conversions on Java values held as Python values
  (DD-040); `values.py` — JSON strings and Java `equals` for arrays and maps
- `aurelius_atlas_typesystem/registry.py` — `TypeRegistry` and `TransientTypeRegistry`
- `tests/` — TRG-01 to TRG-16 (1.2) and THY-01 to THY-12 (1.3); `tests/values/` — VAL-02 to VAL-15 (2.1b),
  one `test__values_<module>.py` per module, Atlas's `TestAtlas*Type` values translated by DD-040;
  `tests/fixtures/` holds Atlas's `0010-base_model.json` and `0011-glossary_model.json`, unchanged and skipped
  by the hooks

## Conventions

- A type resolves in three phases, `_resolve_references`, `_resolve_references_phase2` and
  `_resolve_references_phase3`, called only by the registry; keep Java's phase for each step.
- The registry changes only through a `TransientTypeRegistry` (`with registry.update()`); never mutate a
  committed registry's types (TRG-05).
- Raise `AtlasError` with codes from `aurelius_atlas_model.errors`, copied from `AtlasErrorCode` with
  their parameters in Java's order (DD-023).
- Value methods keep Java's names in snake_case (`is_valid_value`, `get_normalized_value`, …) and take Java
  values as DD-040 holds them: `int`, `Decimal`, `float`, `bool`, `str`, `datetime`, lists and maps. Use the
  conversions in `java.py`, never Python's own (`int("1 2")`, `float("inf")`), which accept what Java rejects.
- A new type class gets its own module (DD-041). JanusGraph names are not ported.

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`); depends on
  `aurelius-atlas-model` (`implicitDependencies` too).
- `sonar-project.properties` and `.env.enc` (`SONAR_TOKEN`) for the CI Sonar job.
- `docs/api-reference/libs/python/aurelius-atlas-typesystem.md` and its `mkdocs.yaml` nav entry.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-typesystem/tests
npx nx test aurelius-atlas-typesystem -c ci
uv run pyright libs/python/aurelius-atlas-typesystem
```

## Removal

Not removable: the stores and the server resolve every type through it.
