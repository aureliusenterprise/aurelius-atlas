# Plan: 19.3 One owner for the shared classification and parent rules

The rules are RUL-01 to RUL-06 of [the spec](./spec.md), the design DD-782 to DD-787.

## Analysis

- **The own-classification rule has four reads.** `entity_classifications._direct`,
  `entity_writer._own_classifications`, `view_mutation._tags`, and `view_derivation._classification_names`
  each answer it from a different view of the stored entity.
- **The parent-end rule has two write reads.** The classic path answers it in `entity_discovery` (RPS-01,
  RPS-02), and the view door answers it in `view_mutation`. The two differ on a child released in the same
  request.
- **The primitives live in core.** `graph_helper` already hosts the edge-label and direction helpers, so both
  new owners belong beside them.
- **The client copy is out of scope.** The webapp re-implements the parent rule in `form-fields.ts`; 19.6's
  guard finds that drift.

## Steps

1. State the RPS-02 difference (DD-786). Decide it, and open the deviation row or the door-release test the
   same branch. Commit one.
2. `own_classifications(stored)` in core, reading the stored field (DD-782, DD-783). Replace all four reads in
   one commit.
3. `parent_end(attribute)` in `graph_helper` (DD-784). Replace the classic read. Commit three.
4. The view door calls `parent_end`, and carries the RPS-02 outcome from commit one. Commit four.
5. Trace check scoped to RUL, compared against the base.

Commit one isolates the only behaviour change. Commits two to four are copy replacements proven by parity, so
the
reviewer can read them as a file-existence check plus one moved function each.

## Verification

Level 0: `uv run pytest libs/python/aurelius-atlas-core/tests`, ruff, pyright. Level 1: `nx test
aurelius-atlas-core aurelius-atlas-server -c ci` and the parity scenarios. RUL-06 is the gate: the scenarios
and
`test__app_search_governance.py` answer identical to the base, except for the chosen RPS-02 outcome, which is
its
own commit and its own test.
