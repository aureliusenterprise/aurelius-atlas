# aurelius-atlas-parity

The parity scenario harness (ADR 052, DD-012 to DD-014). This file covers wiring specific to this lib;
workspace-wide rules live in the root `AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_parity/scenario.py` — the format: pydantic models, the strict YAML loader, `read_scenario`
- `aurelius_atlas_parity/run.py` — `load_scenarios` (pytest parameters), `run_scenario`, substitution
- `aurelius_atlas_parity/compare.py` — the exact comparison, volatile masking, deviations
- `aurelius_atlas_parity/path.py` — the JSONPath subset
- `aurelius_atlas_parity/plugin.py` — the pytest plugin (`pytest11` entry point): `parity.*` test properties
- `aurelius_atlas_parity/testing.py` — the sample ASGI application for this lib's own tests
- `tests/` — format errors, comparison and runs against the sample application, the plugin with `pytester`

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`) — the dev group is
  what loads the plugin into every project's pytest run.
- `aurelius-atlas-trace` reads the `parity.endpoint` and `parity.deviation` properties: the property
  names in `scenario.py` and in the trace lib change together.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-parity/tests
```

## Conventions

- Writing a scenario: read the Atlas 2.4.0 code (`github.com/apache/atlas`, tag `release-2.4.0`) and
  cite it in `source`; borrow request bodies from Atlas's own test fixtures where they exist
  (`webapp/src/test/resources/json/`, `repository/src/test/resources/json/`). Never record from, or run,
  an Apache Atlas (ADR 052).
- An expectation is the Atlas response. A difference Aurelius makes on purpose is a `deviations` entry
  with a `DV-NN` from `docs/architecture/conversion/deviations.md`, never an edited expectation.
- Changing the format means changing its rules SCN-01 to SCN-03 in the 0.4 spec and the tests together.

## Removal

Not removable while ADR 052 stands: the server's scenarios depend on it.
