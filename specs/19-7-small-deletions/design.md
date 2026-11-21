# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-809. One helper runs the version-conflict retry

- **Status:** Proposed
- **Increment:** 19.7
- **Date:** 2026-11-21
- **Relates to:** PAR-01.

**Decision.** A retry helper in core runs a callable until it succeeds or the caller's stop condition fires.
The
seven loops in `classification_tasks`, `entity_business_metadata`, `entity_classifications`, `entity_labels`,
`relationship_store`, and the two in `entity_writer` call it instead of writing the loop each.

**Reason.** The seven loops share a body: run, catch the version conflict, rerun, and on the last attempt
raise the mapped error. They differ only in which error each maps to and how many attempts it allows. Copying
the shape seven times means a fix to the retry (for example a backoff, or a fix to the last-attempt error) is
seven edits, and the audit found two copies already differ on the error path. The spec first counted six; the
count is seven because `relationship_store` writes the same loop, and the acceptance grep names its shape.

**Alternatives.**

- **Keep the loops and share only the conflict check.** The loop body is the duplication, not the check, so
  sharing only the check removes little.

### DD-810. The helper keeps a per-caller stop condition and error mapping

- **Status:** Proposed
- **Increment:** 19.7
- **Date:** 2026-11-21
- **Relates to:** PAR-02.

**Decision.** The helper takes the attempt count, the conflict predicate, and the last-attempt error mapping
as
arguments. It does not hard-code one attempt count or one error.

**Reason.** The six `ATTEMPTS = 2` loops and `model_loader`'s `RACE_ATTEMPTS = 10` are different races with
different budgets, and each caller maps a persistent conflict to a different error. Forcing one count would
change a retry budget, which is a behaviour change this increment promises not to make (PAR-03). Passing the
mapping keeps each caller's answer identical.

**Alternatives.**

- **One shared attempt count for all callers.** Smaller helper, and it changes how many times a conflict is
  retried, which is observable and out of scope.

### DD-811. The governance fields stay where they are

- **Status:** Proposed
- **Increment:** 19.7
- **Date:** 2026-11-21
- **Relates to:** PAR-03.

**Decision.** This increment does not group `governed`, `governed_by`, and `governed_source` into one nested
record on `StoredEntity`. It keeps them as they are: `governed` flat on the entity, and `governed_by` and
`governed_source` inside the entity's `app_search` document.

**Reason.** The plan assumed all three sit flat on `StoredEntity`, beside two nested records. They do not.
Only `governed` is flat. `governed_by` and `governed_source` are already nested, inside `StoredAppSearch`
(DD-535), and the indexer and the governance round read them there. The flat one cannot join them without
moving its stored value. `governed` is the search field read from the top of the document
(`EngineField(path="governed")` in `view_search.py`), so nesting it changes the Elasticsearch path that every
governed filter reads. A document written before the change would then no longer match one written after it.
Moving a stored value is what PAR-03 forbids, and the parity scenarios and the frozen 14.6 corpus are the
rule that proves it. The two fields already in a nested record give the governance reader the narrow type the
plan wanted, and the flat one is a single boolean the record answers directly.

**Alternatives.**

- **Group the three under one nested record anyway.** Smaller to read, but it moves `governed` off the
  top-level path the search engine names. That changes both the stored document and how an old document
  reads. It is a migration, not a deletion, and this increment is neither.
- **Rewrite `StoredEntity` into nested blocks for everything.** Larger still, touches storage and every
  reader, and the audit's finding was a duplicated shape, not a request to rebuild the record.
