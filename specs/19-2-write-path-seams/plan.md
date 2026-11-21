# Plan: 19.2 A store the write path can be tested against

The rules are WRS-01 to WRS-09 of [the spec](./spec.md), the design DD-773 to DD-781.

## Analysis

- **The store is concrete.** `EntityStore` is a class, not a protocol. `EntityWriter` calls eight of its
  members, `ViewMutationDoor` calls six plus `undo`, and a test drives either only through a server or through
  a subclass.
- **The wrapper subclasses it.** `view_mutation.py` `RewindStore(EntityStore)` calls
  `super().__init__(real._documents, clock=real._clock, new_id=real._new_id)` and then aliases
  `real.write_listeners` and `real.task_listeners`, with a `# noqa: SLF001`. It reaches three private fields.
- **The writer carries order-dependent state.** `_create_or_update` sets `self._record`, `self._importing`,
  `self._import_deletions`, and `self._import_guids` in order, and the `ATTEMPTS = 2` retry reruns the method.
  Five fields are import-only, which is the source of the coupling.
- **Rollback wakes workers.** A rewound write fires the real store's listeners, and a 26-line test pins the
  wrong behaviour in `test__view_mutation.py`.

## Steps

1. `WriteStore` protocol with the write path's members. `EntityStore` satisfies it, no behaviour change
   (DD-773, DD-774). Commit one.
2. `WriteTransaction` value object with typed step fields. Move the five mutable writer fields onto it and
   thread it through `_create_or_update` (DD-776, DD-779). Commit two, behaviour-preserving.
3. `RewindStore` composes `WriteStore` and the documents contract. Name the shared listeners. Delete the
   `# noqa: SLF001` (DD-775). Commit three.
4. Suppress the listener emit on a rewind, and replace the pinned rollback test with the WRS-08 test (DD-777).
   Commit four.
5. `ImportWriter` sharing `WriteTransaction`. Drop the import-only fields from `EntityWriter` (DD-778,
   DD-780). Commit five.

Commit 1 and 2 are behaviour-preserving and reviewable by diff. Commit 4 changes one behaviour (WRS-08) that
no
endpoint exposes, so parity stays green. Commit 5 is the only step that moves code between modules, so it gets
its own review.

## Verification

Level 0: `uv run pytest libs/python/aurelius-atlas-core/tests`, ruff, pyright. Prove the door drives on
`WriteStore` by shrinking `test__view_mutation.py`. Level 1: `nx test aurelius-atlas-core
aurelius-atlas-server
-c ci` and the parity scenarios. WRS-09 is the gate: the scenarios and `test__app_search_governance.py` answer
identical to the base, byte for byte. Level 2: `nx e2e aurelius-atlas-server -c ci` after commit 2 and again
at
the end, the plan's risk mitigation for the write path. Trace check scoped to WRS, compared against the base.
