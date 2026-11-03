# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) apply:
an accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-312. The glossary sort parameter is its own vocabulary

- **Status:** Proposed
- **Increment:** 8.10
- **Date:** 2026-11-03

**Decision.** `aurelius-atlas-server-client` defines `GlossarySort` as
`Literal["ASC", "DESC"]` for the glossary reads' `sort` parameter (CLG-02). It
is exported from `__init__.py` and used in every paged glossary signature.

**Reason.** The server's glossary `_page` helper parses `sort` with
`aurelius_atlas_core.glossary_service.SortOrder.of`, which reads anything that
is not `DESC` as ascending — the wire words are `ASC` and `DESC`. The client
cannot reuse either existing enum. The core `SortOrder` sits behind
`aurelius-atlas-core`, which DD-203 keeps off the client's dependency list (the
same floor DD-311 holds for `DeleteType`). `aurelius-atlas-model`'s
`discovery.SortOrder` is importable but is a different vocabulary —
`ASCENDING`/`DESCENDING`, the search parameter — and sending `DESCENDING` to a
glossary read would not even error: the server would read it as ascending and
silently return the wrong order.

**Alternatives.** (a) Reuse `discovery.SortOrder` (refused — the wire mismatch
fails quietly, the worst failure mode a paging parameter can have). (b) Import
core's `SortOrder` (refused — DD-203's dependency floor). (c) Type the
parameter bare `str` (refused — CLG-02 names the two values, and a bare string
invites the discovery vocabulary into the wrong parameter).

**Consequences.** A third small client-side vocabulary leaves `client.py`,
exported with the rest. The paging tests pin both words: `sort="DESC"` travels
as `sort=DESC`, and the default `ASC` travels as absence (CLG-02), so a reader
sees the wire form next to the type. If a glossary-shaped sort ever appears in
`aurelius-atlas-model`, this entry is the one to supersede.
