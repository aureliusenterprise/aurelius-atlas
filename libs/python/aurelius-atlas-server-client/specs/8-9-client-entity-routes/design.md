# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) apply:
an accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-311. The client states its own DeleteType

- **Status:** Proposed
- **Increment:** 8.9
- **Date:** 2026-11-03

**Decision.** `aurelius-atlas-server-client` defines `DeleteType` (the three
values `DEFAULT`, `SOFT`, `HARD`) in its own `models.py`, rather than importing
the server's `aurelius_atlas_core.delete_type.DeleteType`. CLE-04's parameter is
typed with it.

**Reason.** The enum the entity deletes carry lives in `aurelius-atlas-core`,
the server's store-and-services library — Elasticsearch, openpyxl and the type
system ride in behind it. DD-203 built the client on `aurelius-atlas-model` and
`httpx2` alone so any consumer can depend on it cheaply; pulling `core` in for
one three-value enum would undo that. The wire vocabulary is the three values
themselves — the server parses them with its own `DeleteType.of`, which accepts
any case — so a client-side copy states the contract, not an implementation.

**Alternatives.** (a) Depend on `aurelius-atlas-core` (refused — the client's
dependency floor is the point of 8.4). (b) Type the parameter `str` (refused —
CLE-04 is a rule about the parameter and a bare string invites values the server
silently reads as `DEFAULT`). (c) Move `DeleteType` to `aurelius-atlas-model`
(refused for now — the model library is the Java `org.apache.atlas.model` port,
and Java's `DeleteType` is a server class, not a model class; moving it there
would drift from the port's rule. If a second client-side need appears, that
move becomes its own entry.)

**Consequences.** `models.py` gains the enum and `__init__.py` exports it. The
`models.py` comment names the server-side twin so a reader finds it. The test
for CLE-04 sends `DeleteType.HARD` and asserts the wire value `HARD`.
