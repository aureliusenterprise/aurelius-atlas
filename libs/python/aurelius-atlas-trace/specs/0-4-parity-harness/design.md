# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-014. Scenario facts reach the report as test properties

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** The parity plugin adds each scenario's endpoints and deviation ids to the test item's
`user_properties` at collection. The trace plugin writes every test's properties to the trace file, so
`check` (unknown deviations) and `report` (one row per endpoint) read them from the collection they
already do.

**Reason.** `user_properties` is pytest's own channel for facts about a test, and JUnit carries it too.
Reading it at collection keeps the report's rule of DD-009: an endpoint whose scenarios did not run in
this change is _not run_, not missing.

**Alternatives.** A separate `--parity-json` file: a second format next to the trace file for the same
tests. Make the trace library know scenarios: couples the traceability tool to one kind of test.

**Consequences.** The trace file format gains a `properties` field per test; readers of version 1 files
without it see no properties. Property names are prefixed with the plugin that sets them (`parity.`).
