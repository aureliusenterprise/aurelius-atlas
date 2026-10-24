# aurelius-atlas-trace

Traceability for Aurelius Atlas
([ADR 056](../../../docs/architecture/adr/056-behaviour-is-proven-by-executed-tests-not-by-a-trace-gate.md)):
the `covers` marker names, for every test, the public functions and increment rules it proves — a
review convention. `check` and `report` are local tools; the CI pipeline runs neither and blocks
merges on executed tests alone.

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
# Local tools by choice — CI runs neither (ADR 056).
uv run aurelius-atlas-trace check     # exit 1 when a public function or rule is named by no test
uv run aurelius-atlas-trace report --output dist/test-report/index.html --summary dist/test-report/summary.md
```

`check` collects the tests of every Atlas project without running them, so its answer does not depend
on which projects a change touches. `report` joins the files the `ci` configuration of the Nx `test`
and `e2e` targets writes (`junit*.xml`, `coverage.xml`, `trace*.json`) into one page; rules and
functions whose tests did not run in this change show as _not run_. Parity scenarios
([aurelius-atlas-parity](../aurelius-atlas-parity/README.md)) get one row per endpoint, and `check`
refuses a scenario whose deviation id is not in the deviations table.

What counts as an Atlas project, and from which increment rules are enforced, is configured in the
`[tool.aurelius-atlas-trace]` table of the root `pyproject.toml`.
