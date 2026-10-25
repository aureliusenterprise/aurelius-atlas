# 0.3 Test report and traceability

- **Status:** in progress
- **Pull request:** –
- **Records:** ADR 049 (becomes Accepted), DD-009, DD-010, DD-011

## Scope

Make [ADR 049](<https://aureliusenterprise.github.io/fix-tls-stacks-own-mounted-certs/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>) executable: every public function of the Atlas code and every rule of a specification is named by a test, the pipeline refuses a change that leaves either uncovered, and every change publishes one test report.

- **`libs/python/aurelius-atlas-trace`** (`aurelius_atlas_trace`), loaded into every pytest run of the workspace as a plugin:

  - the `covers` marker, `@pytest.mark.covers("<dotted.path>", ..., rules=["XXX-NN", ...])`;
  - `aurelius-atlas-trace check`, which collects the markers of all Atlas projects without running them and compares them with the public functions of those projects and the rules of the specifications;
  - `aurelius-atlas-trace report`, which builds one HTML page from the JUnit, coverage and trace files of a test run.
- **CI**: the check runs in the `validate` job on every change. The `test` job writes JUnit and trace files next to the coverage it already writes, builds the report, uploads it as the `test-report` artifact, and puts its summary on the run page.
- **Increment 0.2 under the check**: the store library's tests carry `covers` markers instead of rule ids in docstrings. ESD-01 to ESD-06, checked by hand in 0.2, become end-to-end tests in `libs/python/aurelius-atlas-store-es/e2e/` that run against `nx up aurelius-atlas-dev-elasticsearch`.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Parity results in the report | 0.4 |
| Traceability for TypeScript code | not planned |
| Publishing the report on the documentation site | not planned |
| Markers on the template projects (examples, SDK) | not planned |
| A minimum line-coverage gate in the check | not planned |

## Semantics

### The `covers` marker

| Id | Rule |
| --- | --- |
| TRC-01 | A test names what it checks with `@pytest.mark.covers(*targets, rules=[...])`; a marker with neither a target nor a rule stops the run before any test runs |
| TRC-02 | A target is the dotted import path of a function, method or property; a path that does not import, or names anything else, stops the run before any test runs, naming the test and the path |
| TRC-03 | A rule id has the form `XXX-NN` (2–5 capital letters, a hyphen, 2–3 digits); anything else stops the run before any test runs |
| TRC-04 | Targets are matched by the object they import, so a name re-exported by a package and the path of its defining module name the same function |
| TRC-05 | Markers apply at every level pytest allows (test, class, module); a test is covered by all markers that apply to it |

### The check

| Id | Rule |
| --- | --- |
| TRC-06 | The public functions are the functions, methods and properties defined in the packages of the Atlas projects, except names starting with `_` (in any part of the path) and the `testing` subpackages |
| TRC-07 | The Atlas projects are the uv workspace members, except those the configuration excludes; a new project is checked unless it is excluded on purpose |
| TRC-08 | The rules are the ids in the first column of the tables of every specification from increment 0.2 on; an id defined twice is an error |
| TRC-09 | `check` exits non-zero and lists every public function no test names, every rule no test names, and every test that names a rule no specification defines; otherwise it exits zero |
| TRC-10 | `check` reads the markers by collecting the tests of every Atlas project, including end-to-end tests, without running them, so its answer does not depend on which projects a change affects |

### The report

| Id | Rule |
| --- | --- |
| TRC-11 | With `--trace-json <file>`, a pytest run writes every test's node id, targets, rules and outcome to the file; without it, a run writes nothing |
| TRC-12 | `report` builds one self-contained HTML page from JUnit XML, Cobertura coverage XML and trace files; it reads no other format, and writes only inside the workspace |
| TRC-13 | The page lists, per rule, its increment and the tests naming it with their outcomes, and per public function, the tests naming it, their outcomes and the function's line coverage |
| TRC-14 | A rule or function whose tests did not run in this change is shown as *not run*, not as failed or uncovered |
| TRC-15 | `report` also writes a Markdown summary (counts, failed tests, uncovered items) that CI appends to the run page |

Rule TRC-10 is why the check collects instead of reading the results of a run: CI runs only the affected projects' tests, so a run's results never contain every marker ([DD-009](<https://aureliusenterprise.github.io/fix-tls-stacks-own-mounted-certs/architecture/conversion/design-log/#dd-009-traceability-is-checked-from-collected-markers-not-from-a-test-run>)). TRC-06 to TRC-08 draw the boundary of what must be covered ([DD-010](<https://aureliusenterprise.github.io/fix-tls-stacks-own-mounted-certs/architecture/conversion/design-log/#dd-010-the-traceability-check-covers-atlas-code-from-increment-02-on>)). The report is a small generator of our own over standard formats ([DD-011](<https://aureliusenterprise.github.io/fix-tls-stacks-own-mounted-certs/architecture/conversion/design-log/#dd-011-the-test-report-is-generated-from-junit-coverage-and-trace-files>)).

## Java origin

None: this is conversion tooling, not Atlas behaviour.

## Deviations

None: nothing in this increment is visible through the Atlas REST API.

## Acceptance

- `libs/python/aurelius-atlas-trace/tests/` — the marker (TRC-01 to TRC-05, TRC-11) with `pytester`, the inventory and spec parsing (TRC-06 to TRC-08), the check (TRC-09, TRC-10) on small sample workspaces, and the report (TRC-12 to TRC-15) on sample result files.
- `libs/python/aurelius-atlas-store-es/tests/` — STO-01 to STO-08 and every public function of the store library named by `covers` markers.
- `libs/python/aurelius-atlas-store-es/e2e/` — ESD-01 to ESD-06 against the running dev store (`nx e2e aurelius-atlas-store-es`).
- `uv run aurelius-atlas-trace check` exits zero on this branch; the CI run of this pull request uploads a `test-report` artifact.
