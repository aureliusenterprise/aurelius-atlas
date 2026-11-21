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
six loops in `classification_tasks`, `entity_business_metadata`, `entity_classifications`, `entity_labels`,
and the
two in `entity_writer` call it instead of writing the loop each.

**Reason.** The six loops share a body: run, catch the version conflict, rerun, and on the last attempt raise
the
mapped error. They differ only in which error each maps to and how many attempts it allows. Copying the shape
six
times means a fix to the retry (for example a backoff, or a fix to the last-attempt error) is six edits, and
the
audit found two copies already differ on the error path.

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

**Reason.** The five `ATTEMPTS = 2` loops and `model_loader`'s `RACE_ATTEMPTS = 10` are different races with
different budgets, and each caller maps a persistent conflict to a different `AtlasError`. Forcing one count
would
change a retry budget, which is a behaviour change this increment promises not to make (PAR-03). Passing the
mapping keeps each caller's answer identical.

**Alternatives.**

- **One shared attempt count for all callers.** Smaller helper, and it changes how many times a conflict is
  retried, which is observable and out of scope.

### DD-811. The governance fields group into one nested record

- **Status:** Proposed
- **Increment:** 19.7
- **Date:** 2026-11-21
- **Relates to:** PAR-03.

**Decision.** The flat `governed`, `governed_by`, and `governed_source` fields on `StoredEntity` group into
one
nested record, the way `app_search` (a `StoredAppSearch`) and `quality_result` (a `StoredQualityResult`)
already
are. The stored values do not change.

**Reason.** `StoredEntity` carries a wide flat set, and a reader of a governance question must scan the whole
record to gather the three governance fields, while the App Search and quality questions already have their
own
nested blocks. Grouping the three gives the governance reader a narrow type without changing what is stored or
sent, because the record serialises to the same shape. This is the small half of the plan's finding 18: the
narrowing the wide record needs, limited to the block that already has a pattern to follow.

**Alternatives.**

- **Rewrite `StoredEntity` into nested blocks for everything.** Larger, touches storage and every reader, and
  the audit's finding is the duplication of a shape, not a request to rebuild the record.
