# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-773. One store contract names the write path's store calls

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-01.

**Decision.** A `WriteStore` protocol names the store members `EntityWriter` and `ViewMutationDoor` call. The
two are typed on it instead of on `EntityStore`. `EntityStore` satisfies it unchanged.

**Reason.** `EntityStore` is a concrete class, so a test that wants to drive the write path either runs a
server
or subclasses it. `apps/aurelius-atlas-server/tests/test__view_mutation.py` is 680 lines of HTTP fixtures for
that reason. The write path calls eight members on `EntityWriter` and seven on the door, so a protocol of that
size is a day's work and it names the seam. `search_query.py` and the 19.1 `SearchDocuments` protocol set the
precedent: a narrow protocol at the seam, not the concrete type.

**Alternatives.**

- **Keep `EntityStore` concrete and pass a `Mock`.** A mock built per test drifts from the real store and
  proves only that the mock agrees with itself. `test__view_mutation.py` already shows the cost.
- **Widen the protocol to all 34 `EntityDocuments` methods.** The write path uses a handful, and a wide
  protocol forces every fake to carry the rest, which is the finding 19.4 works on.

### DD-774. The contract gains no second production store

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-02.

**Decision.** `EntityStore` stays the only production implementation of `WriteStore`. This increment adds no
store class, and it adds no behaviour. It is a type and its two consumers.

**Reason.** A contract with one implementation and no fake is a seam, not a feature. Naming it is the value.
If
the increment also shipped a second store, a reviewer could not tell a type change from a behaviour change,
and
the parity gate would have more to hold.

**Alternatives.**

- **Add a recording store for tests in the same commit.** The in-memory store in `testing/memory.py` already
  satisfies the contract and is reviewed. A third store duplicates it.

### DD-775. The rewind wrapper composes the store instead of subclassing it

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-03, WRS-04.

**Decision.** `RewindStore` stops inheriting from `EntityStore`. It holds a `WriteStore` collaborator and the
documents contract, and it forwards the calls it must forward. It names the two listener lists it shares, and
the real store keeps owning them.

**Reason.** Today `RewindStore.__init__` (DD-590) calls `super().__init__(real._documents, clock=real._clock,
new_id=real._new_id)` and then sets `self.write_listeners = real.write_listeners` and
`self.task_listeners = real.task_listeners`, with a `# noqa: SLF001` to pass the lint. It reaches three
private
fields of the class it subclasses. Any change to `EntityStore.__init__` breaks the wrapper silently, and a
listener added to the real store does not reach the door unless someone remembers the alias. Composition names
what it shares and fails loudly when the store changes.

**Alternatives.**

- **Keep subclassing and move the private reads behind accessors.** That removes the lint suppression and
  nothing else. The wrapper still inherits a concrete constructor whose signature it must track.
- **Fold rewind into the door.** Rewind is a store concern because it undoes writes at the document level. The
  door would then know about documents, which the 19.4 split keeps apart.

### DD-776. A per-attempt transaction object replaces the writer's mutable fields

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-05, WRS-06.

**Decision.** A `WriteTransaction` value object holds the state one attempt carries between its steps: the
import flag, the deferred deletions, the import guid map, the task hold, and the request record.
`_create_or_update` builds it at the top of an attempt and passes it to each step in turn.

**Reason.** `_create_or_update` (DD-052, the 12-step path) sets `self._record`, `self._importing`,
`self._import_deletions`, and `self._import_guids` in order, and a later step reads the field an earlier step
wrote. The retry at `ATTEMPTS = 2` runs the method again, and correctness depends on the first attempt's
fields
being fully reset by the second's first steps. That coupling is invisible: nothing stops a step reading a
field
a later step writes, and a wrong order is a silent wrong write rather than a type error.

**Alternatives.**

- **Pass the fields as parameters.** There are five of them and each step takes a subset, so the signature
  grows past readable. One object keeps the steps' signatures small and names the bundle.
- **Leave the fields and add an assert.** An assert at the top does not stop a step reading a field out of
  order inside the attempt.

### DD-777. A rolled-back write wakes no listener

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-08.

**Decision.** A write that is discarded by the rewind path must not fire a write listener or a task listener.
The rewind wrapper builds the rollback so it reverts documents without emitting the events the real write had
prepared.

**Reason.** A rolled-back write today wakes the index workers, so the App Search index and the task queue see
a
write that did not happen. `apps/aurelius-atlas-server/tests/test__view_mutation.py` pins that behaviour with
a
26-line test rather than fixing it, because the fix needs the seam this increment builds. Once the wrapper
owns
the listeners by name (DD-775), it can suppress the emit on a rewind, and the pinned test becomes a direct
WRS-08
test.

**Alternatives.**

- **Keep the pinned behaviour.** The index then holds a document no reader may see, and a later read
  reconciles it. That is a correctness cost paid to avoid a small fix.

### DD-778. Import semantics move to their own orchestrator

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-07.

**Decision.** An `ImportWriter` shares the `WriteTransaction` object and owns the import-only behaviour: the
import flag's effect on discovery, the deferred deletions, and the import guid map. `EntityWriter` keeps the
create, update, and delete paths and drops the import-only fields.

**Reason.** Five of the writer's mutable fields exist only for the import path (DD-776), so the shared writer
carries order-dependent state that most writes never set. Splitting them lets the common writer hold no import
flag, and it lets the import path grow without touching the hot write path. This settles the plan's second
open
decision (D2).

**Alternatives.**

- **Keep import in `EntityWriter` behind a flag.** That keeps the import-only mutable fields on the shared
  writer, which is the source of the order-dependency DD-776 removes. The flag is the cheaper edit, and the
  cheaper edit leaves the finding.

### DD-779. The transaction object makes a wrong step order a type error

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-05, WRS-06.

**Decision.** Each step of `_create_or_update` declares the part of `WriteTransaction` it reads and the part
it
writes, as typed fields a caller fills in order. A step that needs a value not yet set does not type-check.

**Reason.** Naming the order in types is the reason for the object. DD-776 groups the state, and DD-779 makes
the grouping enforce the sequence the 12 steps already assume. A wrong order is then a build failure rather
than
a wrong write that a parity scenario catches late.

**Alternatives.**

- **Document the order in a comment.** The order is already documented, and it still breaks. The finding is
  that the order is not checked.

### DD-780. The ImportWriter shares the transaction, not the writer

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-07.

**Decision.** `ImportWriter` holds a `WriteTransaction` and the store contract, and calls the same prepare,
map,
and commit helpers `EntityWriter` uses. It does not subclass `EntityWriter`.

**Reason.** Subclassing the writer would re-inherit the shared mutable state the split removes, the same
mistake
DD-775 fixes for the rewind wrapper. Sharing helpers and the transaction object gives both writers the same
mechanism without one owning the other's fields.

**Alternatives.**

- **`ImportWriter(EntityWriter)`.** Re-adds the import-only fields to a shared base. Rejected for the DD-775
  reason.

### DD-781. The write contract is additive and reversible

- **Status:** Proposed
- **Increment:** 19.2
- **Date:** 2026-11-21
- **Relates to:** WRS-01, WRS-02.

**Decision.** The increment ships `WriteStore`, the rewired `RewindStore`, and the `WriteTransaction` in one
pull request, in that commit order, and adds no behaviour between the contract and the rewiring.

**Reason.** A write-path change is the riskiest in this plan: a mistake loses writes. Landing the contract
with
no behaviour change first means the level-2 write suites prove equality before any step moves, so a revert of
one SHA leaves no orphaned files. The rollback path is a `git revert` of the increment's merge.

**Alternatives.**

- **One big commit.** Cheaper to write and impossible to bisect when a write regresses. The plan's risk table
  names the split as the mitigation, so the increment's own commit order follows it.
