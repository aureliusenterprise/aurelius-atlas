# aurelius-atlas-trace

Traceability for Aurelius Atlas
([ADR 049](../../../docs/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test.md)):
every public function of the Atlas code and every rule of an increment specification is named by a
test, and every CI run publishes one test report.

Introduced by increment 0.3.

## Naming what a test checks

The pytest plugin is loaded into every test run of the workspace. A test names the functions (dotted
import paths) and the specification rules it checks:

```python
@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.open", rules=["STO-04"])
async def test__elasticsearch_store_open_rejects_unsupported_versions(...): ...
```

Markers on a module (`pytestmark`) or class apply to every test in it. A path that does not import, a
target that is not a function, method or property, or a malformed rule id stops the run before any
test runs.

## Commands

```bash
uv run aurelius-atlas-trace check     # exit 1 when a public function or rule is named by no test
uv run aurelius-atlas-trace report --output dist/test-report/index.html --summary dist/test-report/summary.md
```

`check` collects the tests of every Atlas project without running them, so its answer does not depend
on which projects a change touches. `report` joins the files the `ci` configuration of the Nx `test`
and `e2e` targets writes (`junit*.xml`, `coverage.xml`, `trace*.json`) into one page; rules and
functions whose tests did not run in this change show as _not run_. Parity scenarios
([aurelius-atlas-parity](../aurelius-atlas-parity/README.md)) get one row per endpoint, and `check`
refuses a scenario whose deviation id is not in the deviations table.

An Atlas project is an Nx project: any directory with a `project.json`, so a project that ships no
Python — a container image, a dashboard — is checked for its rules too (DD-035). `exclude-projects`
in the `[tool.aurelius-atlas-trace]` table of the root `pyproject.toml` leaves projects out on
purpose, and `enforce-from` sets the first increment whose rules count.
