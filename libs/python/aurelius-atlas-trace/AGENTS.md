# aurelius-atlas-trace

The traceability check and test report (ADR 049, DD-009 to DD-011) — local tools since DD-215,
run by choice, not CI steps. This file covers wiring specific
to this lib; workspace-wide rules live in the root `AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_trace/marker.py` — the `covers` marker: validation and target resolution
- `aurelius_atlas_trace/plugin.py` — the pytest plugin (`pytest11` entry point), `--trace-json`
- `aurelius_atlas_trace/inventory.py` — public functions of a package; `rules.py` — rule ids of the specs
- `aurelius_atlas_trace/config.py` — reads `[tool.aurelius-atlas-trace]` and the uv workspace members
- `aurelius_atlas_trace/check.py` — collects every Atlas project's markers in a subprocess and finds gaps
- `aurelius_atlas_trace/report.py` — HTML page and Markdown summary; `cli.py` — `aurelius-atlas-trace`
- `aurelius_atlas_trace/parity.py` — the `parity.*` test property names and the deviations table reader
- `aurelius_atlas_trace/testing.py` — a sample workspace for this lib's own tests
- `tests/` — `pytester` tests for the plugin; sample workspaces for the check and the report

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`) — the dev group is
  what loads the plugin into every project's pytest run.
- `[tool.aurelius-atlas-trace]` in the root `pyproject.toml`: `specs`, `enforce-from`,
  `exclude-projects` (template projects), `exclude-subpackages` (`testing`), `deviations` (the table
  that scenario deviation ids are checked against).
- `tools/plugins/python.ts`: the `ci` configuration of `test` and `e2e` passes `--junitxml` and
  `--trace-json` next to the coverage options.
- `.github/workflows/ci.yaml`: nothing — CI dropped `check` and `report` in DD-215; the commands
  are local only.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-trace/tests
uv run aurelius-atlas-trace check
```

## Conventions

- Rule ids are `XXX-NN` (TRC-03); specs are `N-M-slug.md` (TRC-08). Changing either format means
  changing `marker.RULE_ID_PATTERN` or `rules.SPEC_FILE_PATTERN` and their tests together.
- Standard library only beyond pytest: the report reads JUnit and Cobertura XML, nothing else (TRC-12).
- Parity scenarios reach the check and the report only as test properties (DD-014); the property names in
  `parity.py` and in `aurelius-atlas-parity` change together.
- A new Atlas project needs no change here; a project that should not be checked goes into
  `exclude-projects` with a reason in the design log.

## Removal

Removable as a slice: CI no longer calls it (DD-215, ADR 056). What keeps it today is the
`covers` marker convention — removing the lib means stripping the marker from every test and the
`--trace-json` flag from the `ci` test configuration in `tools/plugins/python.ts`.
