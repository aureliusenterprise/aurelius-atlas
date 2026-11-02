# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-059. The delete type and its override are server settings

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** `AURELIUS_ATLAS_SERVER_DELETE_TYPE` (`soft` by default, or `hard`) stands for
`atlas.DeleteHandlerV1.impl`; `AURELIUS_ATLAS_SERVER_DELETE_TYPE_OVERRIDE` (`false` by default) for
`atlas.rest.enable.delete.type.override`, which lets a request's `deleteType` choose.

**Reason.** Atlas configures both in `atlas-application.properties`; the server's settings are its equivalent.

**Alternatives.** Soft deletes only: deployments that configure Atlas for hard deletes could not move.

**Consequences.** None beyond two settings with Atlas's defaults.
