# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-074. `bulk/headers` moves to 3.5

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** `GET bulk/headers?tagUpdateStartTime` (`ClassificationAssociator.Retriever`) is ported with the
entity audit in 3.5 rather than in 3.3b.

**Reason.** It lists the entities whose classifications changed in a time window by asking the audit
repository (`getEntitiesWithTagChanges`); without audit events it could only answer an empty list, or keep a
second record of classification changes that 3.5 would replace.

**Alternatives.** An index of classification change times now: a record 3.5's audit events supersede.

**Consequences.** Until 3.5 the endpoint answers `404`. 3.3b ports `bulk/setClassifications` alone.
