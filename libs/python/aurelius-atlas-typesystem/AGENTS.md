# aurelius-atlas-typesystem

The Atlas type system (DD-002, DD-024, DD-025). This file covers wiring specific to this lib;
workspace-wide rules — including the scaffold recipe for Python libs — live in the root `AGENTS.md` and
`libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_typesystem/types.py` — `AtlasType` and its subclasses (`org.apache.atlas.type`), the
  definition side only (DD-025)
- `aurelius_atlas_typesystem/registry.py` — `TypeRegistry` and `TransientTypeRegistry`
- `tests/` — TRG-01 to TRG-16

## Conventions

- A type resolves in three phases, `_resolve_references`, `_resolve_references_phase2` and
  `_resolve_references_phase3`, called only by the registry; keep Java's phase for each step.
- The registry changes only through a `TransientTypeRegistry` (`with registry.update()`); never mutate a
  committed registry's types (TRG-05).
- Raise `AtlasError` with codes from `aurelius_atlas_model.errors`, copied from `AtlasErrorCode` with
  their parameters in Java's order (DD-023).
- The value side (`isValidValue`, `getNormalizedValue`, …) is 2.1's; JanusGraph names are not ported.

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
