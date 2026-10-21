# 0.4 Parity harness

- **Status:** in progress
- **Pull request:** –
- **Records:** ADR 052 (supersedes ADR 048, becomes Accepted), DD-012, DD-013, DD-014

## Scope

Make [ADR 052](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>) executable: an endpoint's behaviour is written down as scenarios — requests and the responses Apache Atlas 2.4.0 gives, read from its source and its own tests — and every scenario runs as a test against Aurelius Atlas, with its result in the test report.

- **`libs/python/aurelius-atlas-parity`** (`aurelius_atlas_parity`):

  - the scenario format, `*.scenario.yaml`;
  - `load_scenarios`, which turns a directory of scenarios into pytest parameters, one test per scenario, and `run_scenario`, which sends its requests through an `httpx.AsyncClient` and compares the responses;
  - a pytest plugin that records each scenario's endpoints and deviations as test properties.
- **`aurelius-atlas-trace`**: the trace file carries test properties; `check` refuses a scenario that names an unknown deviation; `report` gets a section per endpoint.
- **Proof**: the harness's own tests run scenarios against a small sample ASGI application.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Scenarios for real Atlas endpoints | 0.5 (admin endpoints) and each increment |
| A running Apache Atlas, or recording from one | not planned (ADR 052) |
| Order-insensitive comparison of arrays | the first increment that needs it |
| Multipart and form request bodies | 6.3 (import and export) |

## Semantics

### The scenario format

| Id | Rule |
| --- | --- |
| SCN-01 | A scenario is one YAML file named `*.scenario.yaml` with a `name`, a non-empty `source` list citing where in Atlas 2.4.0 the expectation was read, optional `rules` and `covers`, and one or more `stages` |
| SCN-02 | A stage has an optional `name`, a `request` (`method`, `url`, optional `params`, `headers` and a `json` or `text` body) and a `response` (`status`, optional `headers`, a `json` or `text` body, and, with a `json` body, `volatile` paths, `save` names and `deviations`) |
| SCN-03 | A file that does not parse or does not match the format fails the collection of the test module that loads it, naming the file and the problem; unknown keys, keys given twice and unquoted dates are problems |
| SCN-04 | Each scenario becomes one test whose id is its path below the scenario directory without the suffix; its `rules` and `covers` become a `covers` marker of that test |

### Running and comparing

| Id | Rule |
| --- | --- |
| SCN-05 | Stages run in order through the `httpx.AsyncClient` the test gives; the first stage whose response differs fails the scenario, and later stages do not run |
| SCN-06 | `save` stores the value at a path of the response under a name; `{name}` in a later stage's request or expected response is replaced by it, a string that is exactly `{name}` takes the value with its JSON type |
| SCN-07 | A path is a JSONPath subset: `$`, `.name`, `['name']`, `[n]` and `[*]`; a `save` path must match exactly one value, and an unknown name in `{name}` fails the stage |
| SCN-08 | The status is compared exactly; each listed header is compared by exact value under a case-insensitive name; headers that are not listed are not compared |
| SCN-09 | A `json` body is compared exactly: the same keys, arrays of the same length in the same order, equal numbers, and booleans and null only equal themselves; a `text` body must be identical; no body means an empty body |
| SCN-10 | At a `volatile` path, the value is not compared, but the field must be present in the response exactly where the expectation has it |
| SCN-11 | A failing stage reports every difference of its response, each with its path, the expected and the actual value |

### Deviations

| Id | Rule |
| --- | --- |
| SCN-12 | The expectation in a scenario is the Atlas response; a deliberate difference is a `deviations` entry of the stage's response with a `DV-NN` id, a path, and the Aurelius `value` or `absent: true`, applied to the expectation before comparing; a deviation that changes nothing fails the stage |
| SCN-13 | `aurelius-atlas-trace check` lists every scenario that names a deviation id the [deviations](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/conversion/deviations/index.md>) table does not define |

### The report

| Id | Rule |
| --- | --- |
| SCN-14 | The trace file records every test's `user_properties` after collection; each scenario test carries one `parity.endpoint` property per endpoint its stages call (method and URL before substitution, without the query) and one `parity.deviation` property per deviation id |
| SCN-15 | The report has a section with one row per endpoint: its scenarios with their outcomes and deviations, with the same statuses as rules; the Markdown summary counts endpoints |

Rule SCN-01 is ADR 052 R1: a scenario without a citation is not a scenario. The format borrows the stage shape of Tavern, and scenarios run as ordinary parametrised pytest tests ([DD-012](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/conversion/design-log/#dd-012-parity-scenarios-are-yaml-files-run-as-parametrised-pytest-tests>)). Rules SCN-09 and SCN-10 make the comparison exact ([DD-013](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/conversion/design-log/#dd-013-a-scenario-response-is-compared-exactly-except-at-declared-paths>)), and SCN-14 carries scenario facts to the report through the trace file ([DD-014](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/conversion/design-log/#dd-014-scenario-facts-reach-the-report-as-test-properties>)).

## Java origin

None: this is conversion tooling, not Atlas behaviour. The scenarios of later increments cite the `release-2.4.0` tag of `github.com/apache/atlas`, for example `webapp/src/main/java/org/apache/atlas/web/resources/AdminResource.java#getVersion` or `webapp/src/test/resources/json/search-parameters/entity-filters.json`.

## Deviations

None: nothing in this increment is visible through the Atlas REST API.

## Acceptance

- `libs/python/aurelius-atlas-parity/tests/` — the format and its errors (SCN-01 to SCN-04), the comparison (SCN-05 to SCN-12) against a sample ASGI application, and the properties (SCN-14) with `pytester`.
- `libs/python/aurelius-atlas-trace/tests/` — properties in the trace file (SCN-14), unknown deviations in the check (SCN-13), and the endpoint section of the report (SCN-15).
- `uv run aurelius-atlas-trace check` exits zero on this branch.
