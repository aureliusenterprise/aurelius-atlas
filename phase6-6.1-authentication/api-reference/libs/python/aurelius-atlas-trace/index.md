# aurelius-atlas-trace

Traceability for Aurelius Atlas: the `covers` marker, the coverage check and the test report.

## Installation

Part of the workspace dev group, which loads the pytest plugin into every test run.

```
[dependency-groups]
dev = ["aurelius-atlas-trace"]

[tool.uv.sources.aurelius-atlas-trace]
workspace = true
```

## Documentation

## aurelius\_atlas\_trace

Modules:

- **`check`** –

  The check: every public function and every rule is named by a test (ADR 049 R1, R2).
- **`cli`** –

  The `aurelius-atlas-trace` command: `check` and `report`.
- **`config`** –

  Which projects, packages and specifications the check covers (TRC-07), read from the root `pyproject.toml`.
- **`inventory`** –

  The public functions of a package: what R1 of ADR 049 says must be named by a test (TRC-06).
- **`marker`** –

  The `covers` marker: what a test names, validated against the code it names.
- **`parity`** –

  What the check and the report know of parity scenarios: their test properties and the deviations table.
- **`plugin`** –

  The pytest plugin: registers `covers`, validates it at collection and writes the trace file.
- **`report`** –

  The test report: results, coverage and traceability of one run on one page (ADR 049 R3).
- **`rules`** –

  The rules of the increment specifications: what R2 of ADR 049 says must be named by a test (TRC-08).
- **`testing`** –

  A sample workspace on disk, for tests of the check and the report.
- **`trace`** –

  The trace file: each test's markers and outcome, as the plugin writes it (TRC-11).

Classes:

- **`Covers`** –

  What a test names: canonical function names and rule ids.
- **`MarkerError`** –

  A `covers` marker names something that is not a function or not a rule id.

Functions:

- **`canonical_name`** –

  Return the defining `module.qualname` of a function, method or property, or None for anything else.
- **`resolve_target`** –

  Import a dotted path and return the canonical name of the function it names.

Attributes:

- **`MARKER_NAME`** –

### MARKER\_NAME

```
MARKER_NAME = 'covers'
```

### \_\_all\_\_

```
__all__ = ['MARKER_NAME', 'Covers', 'MarkerError', 'canonical_name', 'resolve_target']
```

### Covers

```
Covers(targets: tuple[str, ...] = (), rules: tuple[str, ...] = ())
```

What a test names: canonical function names and rule ids.

Attributes:

- **`rules`** (`tuple[str, ...]`) –
- **`targets`** (`tuple[str, ...]`) –

#### rules

```
rules: tuple[str, ...] = ()
```

#### targets

```
targets: tuple[str, ...] = ()
```

### MarkerError

Bases: `ValueError`

A `covers` marker names something that is not a function or not a rule id.

### canonical\_name

```
canonical_name(obj: object) -> str | None
```

Return the defining `module.qualname` of a function, method or property, or None for anything else.

Properties are named by their getter, so `Store.is_open` names the same function whether it is reached through the class or a re-exporting package (TRC-04).

### resolve\_target

```
resolve_target(path: str) -> str
```

Import a dotted path and return the canonical name of the function it names.

Parameters:

- #### **`path`**

  (`str`) –

  A dotted import path such as `package.module.Class.method`.

Returns:

- `str` –

  The `module.qualname` where the function is defined.

Raises:

- `MarkerError` –

  The path does not import, or names something other than a function, method or property.

## aurelius\_atlas\_trace.check

The check: every public function and every rule is named by a test (ADR 049 R1, R2).

Classes:

- **`CollectionError`** –

  pytest could not collect a project's tests, so its markers are unknown.
- **`Findings`** –

  What the check found missing (TRC-09).
- **`ProjectTests`** –

  The collected tests of one project.

Functions:

- **`collect_project`** –

  Collect a project's tests, without running them, and read their markers (TRC-10).
- **`find_gaps`** –

  Compare what the tests name with the functions and rules that must be named (TRC-09).
- **`format_findings`** –

  Describe the findings for a terminal, one item per line.
- **`inventory`** –

  List the public functions of every Atlas project (TRC-06, TRC-07).
- **`run_check`** –

  Collect every Atlas project's tests and compare them with its functions and the specified rules.

Attributes:

- **`COLLECTION_FAILED_ERROR`** –

### COLLECTION\_FAILED\_ERROR

```
COLLECTION_FAILED_ERROR = 'collecting the tests of {project} failed (exit code {code}):\n{output}'
```

### CollectionError

Bases: `RuntimeError`

pytest could not collect a project's tests, so its markers are unknown.

### Findings

```
Findings(
    uncovered_functions: tuple[PublicFunction, ...],
    unchecked_rules: tuple[Rule, ...],
    unknown_rules: tuple[tuple[str, str], ...],
    unknown_deviations: tuple[tuple[str, str], ...] = (),
)
```

What the check found missing (TRC-09).

Attributes:

- **`ok`** (`bool`) –

  Whether nothing is missing.
- **`unchecked_rules`** (`tuple[Rule, ...]`) –
- **`uncovered_functions`** (`tuple[PublicFunction, ...]`) –
- **`unknown_deviations`** (`tuple[tuple[str, str], ...]`) –

  Pairs of (test node id, deviation id) for deviations the deviations table does not define (SCN-13).
- **`unknown_rules`** (`tuple[tuple[str, str], ...]`) –

  Pairs of (test node id, rule id) for rules that no specification defines.

#### ok

```
ok: bool
```

Whether nothing is missing.

#### unchecked\_rules

```
unchecked_rules: tuple[Rule, ...]
```

#### uncovered\_functions

```
uncovered_functions: tuple[PublicFunction, ...]
```

#### unknown\_deviations

```
unknown_deviations: tuple[tuple[str, str], ...] = ()
```

Pairs of (test node id, deviation id) for deviations the deviations table does not define (SCN-13).

#### unknown\_rules

```
unknown_rules: tuple[tuple[str, str], ...]
```

Pairs of (test node id, rule id) for rules that no specification defines.

### ProjectTests

```
ProjectTests(project: Project, tests: tuple[TracedTest, ...])
```

The collected tests of one project.

Attributes:

- **`project`** (`Project`) –
- **`tests`** (`tuple[TracedTest, ...]`) –

#### project

```
project: Project
```

#### tests

```
tests: tuple[TracedTest, ...]
```

### collect\_project

```
collect_project(project: Project) -> ProjectTests
```

Collect a project's tests, without running them, and read their markers (TRC-10).

Raises:

- `CollectionError` –

  pytest failed to collect, for example because a test module does not import.

### find\_gaps

```
find_gaps(
    functions: Iterable[PublicFunction],
    rules: dict[str, Rule],
    tests: Iterable[TracedTest],
    deviations: set[str] | None = None,
) -> Findings
```

Compare what the tests name with the functions and rules that must be named (TRC-09).

Parameters:

- #### **`functions`**

  (`Iterable[PublicFunction]`) –

  The public functions that must be named.
- #### **`rules`**

  (`dict[str, Rule]`) –

  The rules that must be named, by id.
- #### **`tests`**

  (`Iterable[TracedTest]`) –

  The collected tests.
- #### **`deviations`**

  (`set[str] | None`, default: `None` ) –

  The deviation ids scenarios may name (SCN-13); None skips that comparison.

### format\_findings

```
format_findings(findings: Findings, workspace: Path) -> str
```

Describe the findings for a terminal, one item per line.

### inventory

```
inventory(config: TraceConfig) -> list[PublicFunction]
```

List the public functions of every Atlas project (TRC-06, TRC-07).

### run\_check

```
run_check(config: TraceConfig) -> Findings
```

Collect every Atlas project's tests and compare them with its functions and the specified rules.

## aurelius\_atlas\_trace.config

Which projects, packages and specifications the check covers (TRC-07), read from the root `pyproject.toml`.

Classes:

- **`ConfigError`** –

  The workspace configuration is missing or incomplete.
- **`Project`** –

  An Atlas project: its directory, its importable packages and its test directories.
- **`TraceConfig`** –

  The check's view of the workspace.

Functions:

- **`load_config`** –

  Read `[tool.aurelius-atlas-trace]` and the uv workspace members of the root `pyproject.toml`.

Attributes:

- **`BAD_SETTING_ERROR`** –
- **`CONFIG_TABLE`** –
- **`MISSING_TABLE_ERROR`** –
- **`NO_DEVIATIONS_ERROR`** –
- **`NO_PACKAGE_ERROR`** –
- **`PYPROJECT`** –
- **`TEST_DIRECTORIES`** –

  The test directories of a project, as the Nx Python plugin knows them.

### BAD\_SETTING\_ERROR

```
BAD_SETTING_ERROR = "{path}: [tool.{table}] needs 'specs' and 'enforce-from' (N.M): {error}"
```

### CONFIG\_TABLE

```
CONFIG_TABLE = 'aurelius-atlas-trace'
```

### MISSING\_TABLE\_ERROR

```
MISSING_TABLE_ERROR = '{path} has no [tool.{table}] table'
```

### NO\_DEVIATIONS\_ERROR

```
NO_DEVIATIONS_ERROR = '{path}: [tool.{table}] deviations: {file} does not exist'
```

### NO\_PACKAGE\_ERROR

```
NO_PACKAGE_ERROR = '{project} declares no package in [tool.hatch.build.targets.wheel] packages'
```

### PYPROJECT

```
PYPROJECT = 'pyproject.toml'
```

### TEST\_DIRECTORIES

```
TEST_DIRECTORIES = ('tests', 'e2e')
```

The test directories of a project, as the Nx Python plugin knows them.

### ConfigError

Bases: `ValueError`

The workspace configuration is missing or incomplete.

### Project

```
Project(root: Path, packages: tuple[str, ...], test_dirs: tuple[Path, ...])
```

An Atlas project: its directory, its importable packages and its test directories.

Attributes:

- **`packages`** (`tuple[str, ...]`) –
- **`root`** (`Path`) –
- **`test_dirs`** (`tuple[Path, ...]`) –

#### packages

```
packages: tuple[str, ...]
```

#### root

```
root: Path
```

#### test\_dirs

```
test_dirs: tuple[Path, ...]
```

### TraceConfig

```
TraceConfig(
    workspace: Path,
    spec_dir: Path,
    enforce_from: Increment,
    projects: tuple[Project, ...],
    excluded_subpackages: tuple[str, ...],
    members: tuple[Path, ...],
    deviations: Path | None = None,
)
```

The check's view of the workspace.

Attributes:

- **`deviations`** (`Path | None`) –

  The deviations table that parity scenarios name their deviations from (SCN-13), if configured.
- **`enforce_from`** (`Increment`) –
- **`excluded_subpackages`** (`tuple[str, ...]`) –
- **`members`** (`tuple[Path, ...]`) –

  Every uv workspace member, excluded or not: where the report looks for test results.
- **`projects`** (`tuple[Project, ...]`) –
- **`spec_dir`** (`Path`) –
- **`workspace`** (`Path`) –

#### deviations

```
deviations: Path | None = None
```

The deviations table that parity scenarios name their deviations from (SCN-13), if configured.

#### enforce\_from

```
enforce_from: Increment
```

#### excluded\_subpackages

```
excluded_subpackages: tuple[str, ...]
```

#### members

```
members: tuple[Path, ...]
```

Every uv workspace member, excluded or not: where the report looks for test results.

#### projects

```
projects: tuple[Project, ...]
```

#### spec\_dir

```
spec_dir: Path
```

#### workspace

```
workspace: Path
```

### load\_config

```
load_config(workspace: Path) -> TraceConfig
```

Read `[tool.aurelius-atlas-trace]` and the uv workspace members of the root `pyproject.toml`.

The table holds `specs` (directory of the specifications), `enforce-from` (first increment whose rules count), `exclude-projects` (workspace members left out, as listed in `members`) and `exclude-subpackages` (subpackage names left out of every package, default `["testing"]`) and `deviations` (the deviations table, optional).

Raises:

- `ConfigError` –

  The table or one of its settings is missing, or a project declares no package.

## aurelius\_atlas\_trace.inventory

The public functions of a package: what R1 of ADR 049 says must be named by a test (TRC-06).

Classes:

- **`PublicFunction`** –

  A public function, method or property getter, and where its source lives.

Functions:

- **`public_functions`** –

  List the public functions, methods and properties defined in a package (TRC-06).

### PublicFunction

```
PublicFunction(name: str, file: Path, first_line: int, last_line: int)
```

A public function, method or property getter, and where its source lives.

Attributes:

- **`file`** (`Path`) –
- **`first_line`** (`int`) –
- **`last_line`** (`int`) –
- **`name`** (`str`) –

#### file

```
file: Path
```

#### first\_line

```
first_line: int
```

#### last\_line

```
last_line: int
```

#### name

```
name: str
```

### public\_functions

```
public_functions(package: str, excluded_subpackages: Collection[str] = ('testing',)) -> list[PublicFunction]
```

List the public functions, methods and properties defined in a package (TRC-06).

A name is public when no part of its path starts with `_`. Functions imported into a module are listed where they are defined, and inherited methods are not listed again.

Parameters:

- #### **`package`**

  (`str`) –

  The importable package name.
- #### **`excluded_subpackages`**

  (`Collection[str]`, default: `('testing',)` ) –

  Subpackage names left out at any depth, such as test helpers.

Returns:

- `list[PublicFunction]` –

  The functions, sorted by name.

## aurelius\_atlas\_trace.report

The test report: results, coverage and traceability of one run on one page (ADR 049 R3).

Classes:

- **`JUnitFailure`** –

  A failed or erroring test case from a JUnit file.
- **`JUnitTotals`** –

  Test counts over every JUnit file of the run.
- **`Report`** –

  Everything the page and the summary show.
- **`Row`** –

  One rule or function with its tests.
- **`Status`** –

  The state of a rule or function in this run (TRC-13, TRC-14).
- **`TestRef`** –

  A test that names a rule or function, and its outcome in this run.

Functions:

- **`build_report`** –

  Collect every Atlas project's tests and join them with the results the run left in the workspace.
- **`function_coverage`** –

  Return the share of a function's measured body lines that ran, or None when coverage did not measure it.
- **`read_coverage`** –

  Read Cobertura XML files into hits per line per absolute source file.
- **`read_junit`** –

  Add up JUnit XML files and list their failed and erroring test cases.
- **`render_html`** –

  Render the report as one self-contained HTML page (TRC-12 to TRC-14).
- **`render_summary`** –

  Render the Markdown summary CI appends to the run page (TRC-15).
- **`status_of`** –

  Summarise the outcomes of the tests naming one rule or function; None is a test that did not run.

Attributes:

- **`COVERAGE_GLOB`** –
- **`JUNIT_GLOB`** –
- **`TRACE_GLOB`** –

  File names the report reads from each workspace member's directory, where the Nx test targets write them.

### COVERAGE\_GLOB

```
COVERAGE_GLOB = 'coverage.xml'
```

### JUNIT\_GLOB

```
JUNIT_GLOB = 'junit*.xml'
```

### TRACE\_GLOB

```
TRACE_GLOB = 'trace*.json'
```

File names the report reads from each workspace member's directory, where the Nx test targets write them.

### JUnitFailure

```
JUnitFailure(name: str, message: str)
```

A failed or erroring test case from a JUnit file.

Attributes:

- **`message`** (`str`) –
- **`name`** (`str`) –

#### message

```
message: str
```

#### name

```
name: str
```

### JUnitTotals

```
JUnitTotals(
    tests: int = 0, failures: int = 0, errors: int = 0, skipped: int = 0, failed_cases: list[JUnitFailure] = list()
)
```

Test counts over every JUnit file of the run.

Attributes:

- **`errors`** (`int`) –
- **`failed_cases`** (`list[JUnitFailure]`) –
- **`failures`** (`int`) –
- **`skipped`** (`int`) –
- **`tests`** (`int`) –

#### errors

```
errors: int = 0
```

#### failed\_cases

```
failed_cases: list[JUnitFailure] = field(default_factory=list)
```

#### failures

```
failures: int = 0
```

#### skipped

```
skipped: int = 0
```

#### tests

```
tests: int = 0
```

### Report

```
Report(totals: JUnitTotals, rules: tuple[Row, ...], functions: tuple[Row, ...], endpoints: tuple[Row, ...] = ())
```

Everything the page and the summary show.

Attributes:

- **`endpoints`** (`tuple[Row, ...]`) –

  One row per endpoint that parity scenarios call (SCN-15).
- **`functions`** (`tuple[Row, ...]`) –
- **`rules`** (`tuple[Row, ...]`) –
- **`totals`** (`JUnitTotals`) –

#### endpoints

```
endpoints: tuple[Row, ...] = ()
```

One row per endpoint that parity scenarios call (SCN-15).

#### functions

```
functions: tuple[Row, ...]
```

#### rules

```
rules: tuple[Row, ...]
```

#### totals

```
totals: JUnitTotals
```

### Row

```
Row(name: str, detail: str, tests: tuple[TestRef, ...], coverage: float | None = None)
```

One rule or function with its tests.

Attributes:

- **`coverage`** (`float | None`) –
- **`detail`** (`str`) –
- **`name`** (`str`) –
- **`status`** (`Status`) –

  The row's status over its tests.
- **`tests`** (`tuple[TestRef, ...]`) –

#### coverage

```
coverage: float | None = None
```

#### detail

```
detail: str
```

#### name

```
name: str
```

#### status

```
status: Status
```

The row's status over its tests.

#### tests

```
tests: tuple[TestRef, ...]
```

### Status

Bases: `StrEnum`

The state of a rule or function in this run (TRC-13, TRC-14).

Attributes:

- **`FAILED`** –
- **`NOT_RUN`** –
- **`PASSED`** –
- **`SKIPPED`** –
- **`UNCOVERED`** –

#### FAILED

```
FAILED = 'failed'
```

#### NOT\_RUN

```
NOT_RUN = 'not run'
```

#### PASSED

```
PASSED = 'passed'
```

#### SKIPPED

```
SKIPPED = 'skipped'
```

#### UNCOVERED

```
UNCOVERED = 'uncovered'
```

### TestRef

```
TestRef(project: str, nodeid: str, outcome: Outcome | None)
```

A test that names a rule or function, and its outcome in this run.

Attributes:

- **`__test__`** –
- **`nodeid`** (`str`) –
- **`outcome`** (`Outcome | None`) –
- **`project`** (`str`) –

#### \_\_test\_\_

```
__test__ = False
```

#### nodeid

```
nodeid: str
```

#### outcome

```
outcome: Outcome | None
```

#### project

```
project: str
```

### build\_report

```
build_report(config: TraceConfig) -> Report
```

Collect every Atlas project's tests and join them with the results the run left in the workspace.

### function\_coverage

```
function_coverage(function: PublicFunction, coverage: dict[Path, dict[int, int]]) -> float | None
```

Return the share of a function's measured body lines that ran, or None when coverage did not measure it.

The first measured line is the `def` statement (with its decorators), which runs when the module is imported, so it is left out: a function no test calls has 0%, not a share for its signature.

### read\_coverage

```
read_coverage(paths: Iterable[Path]) -> dict[Path, dict[int, int]]
```

Read Cobertura XML files into hits per line per absolute source file.

### read\_junit

```
read_junit(paths: Iterable[Path]) -> JUnitTotals
```

Add up JUnit XML files and list their failed and erroring test cases.

### render\_html

```
render_html(report: Report, title: str = 'Test report') -> str
```

Render the report as one self-contained HTML page (TRC-12 to TRC-14).

### render\_summary

```
render_summary(report: Report) -> str
```

Render the Markdown summary CI appends to the run page (TRC-15).

### status\_of

```
status_of(outcomes: Sequence[Outcome | None]) -> Status
```

Summarise the outcomes of the tests naming one rule or function; None is a test that did not run.

## aurelius\_atlas\_trace.rules

The rules of the increment specifications: what R2 of ADR 049 says must be named by a test (TRC-08).

Classes:

- **`DuplicateRuleError`** –

  Two specifications, or two rows of one, define the same rule id.
- **`Increment`** –

  An increment number such as 0.2, ordered numerically.
- **`Rule`** –

  A rule id and the specification that defines it.

Functions:

- **`read_rules`** –

  Read the rule ids of every specification from increment `enforce_from` on (TRC-08).

Attributes:

- **`DUPLICATE_RULE_ERROR`** –
- **`SPEC_FILE_PATTERN`** –

  A specification file: `N-M-slug.md` for increment N.M.

### DUPLICATE\_RULE\_ERROR

```
DUPLICATE_RULE_ERROR = 'rule {rule} is defined in both {first} and {second}'
```

### SPEC\_FILE\_PATTERN

```
SPEC_FILE_PATTERN = re.compile('(\\d+)-(\\d+)-[a-z0-9-]+\\.md')
```

A specification file: `N-M-slug.md` for increment N.M.

### DuplicateRuleError

Bases: `ValueError`

Two specifications, or two rows of one, define the same rule id.

### Increment

```
Increment(major: int, minor: int)
```

An increment number such as 0.2, ordered numerically.

Methods:

- **`__str__`** –
- **`parse`** –

  Read `N.M`.

Attributes:

- **`major`** (`int`) –
- **`minor`** (`int`) –

#### major

```
major: int
```

#### minor

```
minor: int
```

#### \_\_str\_\_

```
__str__() -> str
```

#### parse

```
parse(text: str) -> Increment
```

Read `N.M`.

Raises:

- `ValueError` –

  The text is not two dot-separated numbers.

### Rule

```
Rule(id: str, increment: Increment, spec: Path)
```

A rule id and the specification that defines it.

Attributes:

- **`id`** (`str`) –
- **`increment`** (`Increment`) –
- **`spec`** (`Path`) –

#### id

```
id: str
```

#### increment

```
increment: Increment
```

#### spec

```
spec: Path
```

### read\_rules

```
read_rules(spec_dir: Path, enforce_from: Increment) -> dict[str, Rule]
```

Read the rule ids of every specification from increment `enforce_from` on (TRC-08).

A rule is a table row whose first cell is a rule id. Files that are not named `N-M-slug.md` (the template, the index) are ignored.

Parameters:

- #### **`spec_dir`**

  (`Path`) –

  The directory of the increment specifications.
- #### **`enforce_from`**

  (`Increment`) –

  The first increment whose rules count.

Returns:

- `dict[str, Rule]` –

  The rules by id.

Raises:

- `DuplicateRuleError` –

  A rule id is defined twice.

## aurelius\_atlas\_trace.trace

The trace file: each test's markers and outcome, as the plugin writes it (TRC-11).

Classes:

- **`Outcome`** –

  The outcome of one test, over its setup, call and teardown.
- **`TraceFile`** –

  The content of one trace file: the pytest root directory and its tests.
- **`TracedTest`** –

  One collected test: its node id, what it names, how it ended (None when it did not run), and its properties.

Functions:

- **`read_trace_file`** –

  Read a trace file written by `--trace-json`.

Attributes:

- **`TRACE_FORMAT_VERSION`** –
- **`UNSUPPORTED_VERSION_ERROR`** –

### TRACE\_FORMAT\_VERSION

```
TRACE_FORMAT_VERSION = 1
```

### UNSUPPORTED\_VERSION\_ERROR

```
UNSUPPORTED_VERSION_ERROR = '{path}: trace format version {version} is not supported'
```

### Outcome

Bases: `StrEnum`

The outcome of one test, over its setup, call and teardown.

Methods:

- **`combine`** –

  Fold a phase into the outcome so far: any failure fails the test, a skip outranks a pass.
- **`of`** –

  Return the outcome of one phase report.

Attributes:

- **`FAILED`** –
- **`PASSED`** –
- **`SKIPPED`** –

#### FAILED

```
FAILED = 'failed'
```

#### PASSED

```
PASSED = 'passed'
```

#### SKIPPED

```
SKIPPED = 'skipped'
```

#### combine

```
combine(current: Outcome | None, phase: Outcome) -> Outcome
```

Fold a phase into the outcome so far: any failure fails the test, a skip outranks a pass.

#### of

```
of(report: TestReport) -> Outcome
```

Return the outcome of one phase report.

### TraceFile

```
TraceFile(rootdir: Path, tests: tuple[TracedTest, ...])
```

The content of one trace file: the pytest root directory and its tests.

Attributes:

- **`rootdir`** (`Path`) –
- **`tests`** (`tuple[TracedTest, ...]`) –

#### rootdir

```
rootdir: Path
```

#### tests

```
tests: tuple[TracedTest, ...]
```

### TracedTest

```
TracedTest(
    nodeid: str,
    targets: tuple[str, ...],
    rules: tuple[str, ...],
    outcome: Outcome | None = None,
    properties: tuple[tuple[str, str], ...] = (),
)
```

One collected test: its node id, what it names, how it ended (None when it did not run), and its properties.

The properties are the test's `user_properties` at collection, as name and value pairs (SCN-14).

Methods:

- **`from_json`** –

  Read a test from its JSON form.
- **`property_values`** –

  Return the values of every property with this name, in order.
- **`to_json`** –

  Return the JSON form of this test.

Attributes:

- **`nodeid`** (`str`) –
- **`outcome`** (`Outcome | None`) –
- **`properties`** (`tuple[tuple[str, str], ...]`) –
- **`rules`** (`tuple[str, ...]`) –
- **`targets`** (`tuple[str, ...]`) –

#### nodeid

```
nodeid: str
```

#### outcome

```
outcome: Outcome | None = None
```

#### properties

```
properties: tuple[tuple[str, str], ...] = ()
```

#### rules

```
rules: tuple[str, ...]
```

#### targets

```
targets: tuple[str, ...]
```

#### from\_json

```
from_json(data: dict[str, Any]) -> TracedTest
```

Read a test from its JSON form.

#### property\_values

```
property_values(name: str) -> tuple[str, ...]
```

Return the values of every property with this name, in order.

#### to\_json

```
to_json() -> dict[str, Any]
```

Return the JSON form of this test.

### read\_trace\_file

```
read_trace_file(path: Path) -> TraceFile
```

Read a trace file written by `--trace-json`.

Raises:

- `ValueError` –

  The file has a format version this reader does not know.
