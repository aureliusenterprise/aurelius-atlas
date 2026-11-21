# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-782. One function owns the own-versus-propagated classification test

- **Status:** Proposed
- **Increment:** 19.3
- **Date:** 2026-11-21
- **Relates to:** RUL-01.

**Decision.** A function `own_classifications` in core decides which classifications on an entity the acting
user set, as against the ones propagation added. The four places that ask this question call it.

**Reason.** Four modules decide it today: `_direct` in `entity_classifications.py`, `_own_classifications` in
`entity_writer.py`, `_tags` in `view_mutation.py`, and `_classification_names` in `view_derivation.py`. Each
reads
the stored entity a little differently, so 18.2, 18.3, and 18.5 each changed one copy of a neighbouring rule
and
left three. One owner makes the rule a single edit.

**Alternatives.**

- **Keep four copies and add a cross-check test.** A test that the four agree still needs four edits when the
  rule changes, which is the cost the increment removes.
- **Fold the rule into each module's view of the entity.** That is the current shape, and it is why the copies
  drift.

### DD-783. The owner reads the stored entity, not a view

- **Status:** Proposed
- **Increment:** 19.3
- **Date:** 2026-11-21
- **Relates to:** RUL-01, RUL-02.

**Decision.** `own_classifications` takes the stored entity and reads its own-classification field directly.
It
does not take a derived view, a header, or a tag map.

**Reason.** The four copies differ because three of them start from a view built for another purpose, and each
re-derives the own set from that view. Reading the stored field once gives every caller the same source, which
is RUL-02.

**Alternatives.**

- **Take whatever each caller already has.** That lets a caller pass a view that already lost the propagation
  marker, and the owner silently returns the wrong set.

### DD-784. One function owns the parent-end test

- **Status:** Proposed
- **Increment:** 19.3
- **Date:** 2026-11-21
- **Relates to:** RUL-03.

**Decision.** A function in `graph_helper` decides which end of a relationship attribute is the parent end,
from
the attribute's edge label and direction. The classic write path and the view door both call it.

**Reason.** The parent-end decision is read in the classic path through `entity_discovery` (the RPS-01 and
RPS-02
checks) and again in the view door's write path. The two grow apart because nothing names the shared question,
and
18.3 changed the classic copy alone.

**Alternatives.**

- **Leave the door to re-derive the end from the edge it already holds.** That keeps a second copy of the
  rule, which is the finding.

### DD-785. Every copy is replaced in the same pull request

- **Status:** Proposed
- **Increment:** 19.3
- **Date:** 2026-11-21
- **Relates to:** RUL-01, RUL-03, RUL-06.

**Decision.** The increment replaces all four classification copies and both parent-end copies in one pull
request. No copy is left behind for a later increment.

**Reason.** A half-migrated rule is the worst state: a reviewer cannot tell which copy is authoritative, and a
later increment inherits the drift. Replacing all copies at once keeps the rule equal on both sides in every
commit on the branch, which keeps RUL-06 provable commit by commit.

**Alternatives.**

- **Migrate one path first.** The parity gate then compares two shapes, and a green run proves less.

### DD-786. The RPS-02 difference is written up before any copy is replaced

- **Status:** Proposed
- **Increment:** 19.3
- **Date:** 2026-11-21
- **Relates to:** RUL-04, RUL-05.

**Decision.** Before the parent-end copies are replaced, the increment states the RPS-02 difference: the
classic
path lets a request drop a child from one parent and add it to another in the same call, and the view door
does
not have that release. The write-up decides whether the door gains the release or the difference becomes a
deviation row.

**Reason.** The difference is a behaviour change, not a refactor, and folding it into the copy replacement
hides
it. Written up first, it gets its own test and, if kept, its own deviation row. The plan's risk table names
this
as the way to keep a real bug from riding along in a refactor.

**Alternatives.**

- **Make the door match the classic path silently.** That is the cheapest fix and the most likely to be wrong,
  because it changes a wire answer with no record. Rejected for hiding the change.
- **Ignore the difference.** It is the reason the audit read the two paths side by side.

### DD-787. The RPS-02 outcome is one commit with its own record

- **Status:** Proposed
- **Increment:** 19.3
- **Date:** 2026-11-21
- **Relates to:** RUL-04, RUL-05, RUL-06.

**Decision.** If RUL-05 closes the gap, the door gains the release in one commit with a test that names
RUL-04.
If it keeps the gap, the same pull request adds one row to `deviations.md`, and DD-787 is the entry that row
cites.

**Reason.** Either way the change is visible at the seam the 18.x series touches. One commit keeps the parity
diff small enough to read, and a deviation row makes the kept difference a recorded answer rather than a
future
bug report.

**Alternatives.**

- **Defer the decision to a later increment.** The refactor ships with an open question, and the next person
  to touch the parent rule inherits it unrecorded.
