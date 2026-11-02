# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-012. Parity scenarios are YAML files run as parametrised pytest tests

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** A scenario is a `*.scenario.yaml` file in the stage shape of Tavern (`request`,
`response`, `save`), validated with pydantic. A project's test module turns a directory of them into
one parametrised test, `load_scenarios(directory)`, whose body is `await run_scenario(scenario, client)`;
the project's fixture decides whether `client` talks to the application in-process (`httpx.ASGITransport`)
or over HTTP to a running server.

**Reason.** ADR 045's ladder: the request/response/save stage is the community's shape for declarative
API tests, so reviewers who know Tavern read our scenarios at once. Running scenarios as ordinary pytest
parameters puts them in JUnit, in the trace file and under `covers` (SCN-04) with public pytest API only.

**Alternatives.** Tavern itself: speaks HTTP through `requests` only, so the in-process unit level is
lost, and the exact comparison, volatile paths and deviations (DD-013) would be hooks around it. A
custom collector for `*.scenario.yaml`: shorter test modules, but it needs pytest's private fixture
API to give the items a client. Schemathesis: generates requests from an OpenAPI document, which
Atlas 2.4.0 does not ship and which states types, not Atlas's answers.

**Consequences.** Every project with scenarios has one small test module and a `client` fixture. The
scenario format is ours to keep stable; it is versioned by its rules SCN-01 to SCN-03.

### DD-013. A scenario response is compared exactly, except at declared paths

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** The expected body must equal the actual body: the same keys, arrays in the same order,
booleans and null distinct from numbers. Only `volatile` paths (generated GUIDs, timestamps) skip the
value, and only `deviations` entries change the expectation, each naming its `DV-NN`.

**Reason.** The dashboard and existing clients read fields the scenarios might not think of; an extra,
missing or `null` field is a visible difference ([ADR 046](../../../../../docs/architecture/adr/046-the-catalogue-keeps-its-public-contract.md)).
Atlas serialises its models with Jackson `NON_NULL` inclusion, so "absent" and `null` differ there and
must differ here.

**Alternatives.** Subset matching: short scenarios, but an extra or misnamed field passes. Snapshot
files written from our own responses: exact, but the expectation would come from the implementation,
not from Atlas (ADR 052 R1).

**Consequences.** Expectations for large responses are long; scenarios borrow Atlas's own test fixtures
for request bodies to keep writing them cheap. Arrays whose order Atlas does not define get an explicit
order-insensitive option when the first increment needs one.
