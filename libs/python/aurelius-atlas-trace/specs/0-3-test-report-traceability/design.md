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

### DD-701. The check collects each test directory in its own pytest run

- **Status:** Proposed
- **Increment:** 0.3 (a fix, 2026-11-19)
- **Date:** 2026-11-19

**Decision.** `collect_project` runs pytest once per test directory of a project. One run collects
`tests`, the next collects `e2e`.

**Reason.** pytest imports a `conftest.py` as the bare module `conftest`. One run over both
directories imports both files under the same name, and Python keeps only the first. A test module
that reads `from conftest import BASE_URL` then fails to import, so collection dies and the check
reports nothing for any project after the first broken one. The workspace hit this in October 2026:
the whole report was empty, and nobody saw a gap because an empty report looks green until a rule
table trips the check first. Running one directory per process keeps each `conftest.py` the one
pytest loads for its own tests, which is how `nx test` runs them anyway.

**Alternatives.** Import conftests under unique module names (a pytest plugin of our own): the fix
lives below pytest's own import rules and breaks on its next change. Rename every conftest import
to a package import: it changes dozens of test files to work around a tool detail, and the next
`from conftest import` added by habit brings the bug back.

**Consequences.** A project with both test directories costs two pytest collection runs. The
existing test names its regression by that shape: two conftests, one shared bare import, and both
node ids collected.

### DD-702. The rule reader skips a table that lists rules against their proofs

- **Status:** Proposed
- **Increment:** 0.3 (a fix, 2026-11-19)
- **Date:** 2026-11-19

**Decision.** `read_rules` walks each spec as tables. A table whose second header cell names a
proof (`Proven by`, `Unit proof`, `File`, `Area`) is a reference table, and its rows are skipped.
Every other table contributes the rule rows its first column defines.

**Reason.** A specification's Acceptance section repeats each rule id next to the test that proves
it. Reading those rows as definitions reports the id a second time, and TRC-08 rightly refuses a
doubly defined id. Before this decision the reader survived only because collection died first.
The strict alternative (a table counts only when its header is exactly `Id | Rule`) drops 54 real
rules from multi-column rule tables such as the AUX, DTM, LM and VE tables.

**Alternatives.** Treat a repeated identical row as one definition: it would hide a real duplicate
where two increments mean different things. Parse only `## Semantics` sections: several
specifications state rules outside that heading, and the reader would silently drop them.

**Consequences.** A new proof table shape needs its column name added to the skip list. The three
true duplicate ids the first complete run found (EDT-17 and SPL-03 across webapp increments, ASU-07
inside 14.3) were fixed in the specifications in the same change, so an id still means one rule.

### DD-703. The workspace root counts as a test-only project

- **Status:** Proposed
- **Increment:** 0.3 (a fix, 2026-11-19)
- **Date:** 2026-11-19

**Decision.** The check collects the workspace root's `tests` and `e2e` like a project's. The root
declares no package, so it contributes markers and no public functions.

**Reason.** The workspace-level increments (the charts, the compose stacks, 10.x and 17.x) state
rules that live in `tests/` at the repository root, because no uv member owns the charts. Projects
come from the uv members (TRC-07), so the check never saw those markers. CHT alone lost 102 of its
113 rules, and the report blamed the specifications instead of the gap.

**Alternatives.** Move the root tests into a new uv member: it churns every chart test path and the
CI wiring for a reporting detail. Exclude the workspace-level rule prefixes from the check: the
rules then have no gate at all, which is where they were.

**Consequences.** `config.projects` gains the root when it holds a test directory. TRC-10 now names
the root beside the projects. A rule proven only at the root counts as proven, and the report
counts 102 CHT rules green that it wrongly listed before.
