# Plan: 19.7 Small deletions

The rules are PAR-01 to PAR-03 of [the spec](./spec.md), the design DD-809 to DD-811.

## Analysis

- **Six retry loops.** `classification_tasks`, `entity_business_metadata`, `entity_classifications`,
  `entity_labels`, and two in `entity_writer` each run `for number in range(1, ATTEMPTS + 1)` with a
  last-attempt raise. They share a body and differ in count and error mapping.
- **A different race.** `model_loader` uses `RACE_ATTEMPTS = 10` for a type-update lock, which is not the same
  budget and does not call the helper.
- **The governance fields are flat.** `StoredEntity` holds `governed`, `governed_by`, and `governed_source`
  flat, while `app_search` and `quality_result` are already nested records.

## Steps

1. `retry.py`: the helper with an attempt count, a conflict predicate, and an error mapping (DD-809, DD-810).
2. Rewrite the six loops to call it, keeping each one's count and mapping (DD-809). Prove each owner's suite
   green as it converts, so a change in one owner's error answer cannot hide behind another's.
3. `StoredGovernance` nested record; the three flat fields become it. Wire shape unchanged (DD-811).

Commits 1 and 2 are the deletion; commit 3 is the grouping. Both keep the stored and wire values identical, so
the
whole increment sits outside the parity surface except as the byte-equality proof.

## Verification

Level 0: `uv run pytest libs/python/aurelius-atlas-core/tests`, ruff, pyright, and a grep proving no second
retry
loop remains. Level 1: `nx test aurelius-atlas-core -c ci` and the parity scenarios. PAR-03 is the gate: the
scenarios and `test__app_search_governance.py` answer identical to the base, byte for byte. Trace check scoped
to
PAR, compared against the base.
