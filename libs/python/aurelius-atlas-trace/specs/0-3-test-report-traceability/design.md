# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-009. Traceability is checked from collected markers, not from a test run

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-trace check` runs `pytest --collect-only` over the unit and end-to-end
tests of every Atlas project and reads the `covers` markers from the collected items. Whether the
naming tests pass is the test job's concern, not the check's.

**Reason.** CI runs `nx affected -t test e2e`, so the results of one run contain only the affected
projects' tests; a check over them would report every unaffected function as uncovered (TRC-10).
Collection imports the tests but starts no containers, so it is cheap enough to run on every change.

**Alternatives.** Merge the trace files of the run with those of the last run on `main`: needs
artifact plumbing between workflows and still goes stale when a run on `main` fails. Run every test
on every change: correct, but turns a one-minute check into the full end-to-end suite. Parse the test
sources with `ast`: misses markers applied through `pytestmark`, classes and parametrisation.

**Consequences.** A test module that fails to import fails the check, which is the right answer: its
markers are unknown. A test that names a function but is skipped still counts as naming it; the
report shows it as skipped.

### DD-010. The traceability check covers Atlas code from increment 0.2 on

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** R1 applies to the public functions, methods and properties of every uv workspace
member that the configuration does not exclude; the template projects (examples, SDK, reports) are
excluded, and so are `testing` subpackages, which are test infrastructure. R2 applies to the rules of
every specification from increment 0.2 on. The configuration is the `[tool.aurelius-atlas-trace]`
table of the root `pyproject.toml`.

**Reason.** Template code is removed or replaced by the conversion (0.5 removes the examples), so
markers on it would be written to be deleted. Excluding instead of listing makes a new Atlas project
checked by default. Increment 0.1's rules (ADO-01 to ADO-03) describe the adoption of the template and
were verified when it merged; 0.2 is the first increment with code, and its manual checks of ESD-01 to
ESD-06 are replaced by tests in this increment.

**Alternatives.** Check every workspace member: retrofits markers onto code about to be deleted.
List the Atlas projects explicitly: a new project is silently unchecked until someone adds it.

**Consequences.** A project that leaves the template set (the SDK, if it is kept) is removed from the
exclusion list and gets its markers in the same change.

### DD-011. The test report is generated from JUnit, coverage and trace files

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-trace report` turns JUnit XML (`pytest --junitxml`), Cobertura XML
(`pytest-cov`) and the plugin's trace JSON into one static HTML page and a Markdown summary. CI uploads
the page as the `test-report` artifact and appends the summary to the run page.

**Reason.** ADR 045's ladder: the input formats are the ecosystem's own, and no framework or community
tool joins test results to specification rules and to a function inventory, which is the view ADR 049
R3 asks for. The generator is a few hundred lines with the standard library only.

**Alternatives.** Allure Report: a polished viewer, but it needs its Java CLI, and the per-rule and
per-function gap view would still be ours to build as labels and post-processing. `pytest-html`: one
page of test results, nothing about rules or functions. SonarCloud: shows coverage, not traceability.

**Consequences.** The page is an artifact of the CI run, not a published site; 0.4 adds the parity
results to it. If a later need (history, trends) outgrows a static page, a viewer is chosen then.
