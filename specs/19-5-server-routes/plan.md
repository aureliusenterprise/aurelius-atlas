# Plan: 19.5 A server whose routes state their dependencies

The rules are SVC-01 to SVC-08 of [the spec](./spec.md), the design DD-793 to DD-801.

## Analysis

- **One bare 500.** A closed tenant store set raises `LookupError`, which has no handler, so FastAPI answers a
  500 with no body. Only `AtlasError` has a handler (`app.py:257`).
- **Hidden dependencies.** Routes read `request.app.state` and call factories inline, so five test files
  change behaviour by writing `app.state.settings`.
- **The entity hub.** `routes/entity.py` (909 lines) holds handlers, ten service factories, and the Java
  coercion, and eight sibling route files import from it.
- **Copied rules.** Four body-validation blocks and two export-lock sequences drift on error paths, and the
  OpenAPI model list (`openapi.py:26`) is a module global appended at import.

## Steps

1. Resolve the store set to raise `AtlasError` for a closed set, plus its test. Commit one, ships alone
   (DD-793, DD-801).
2. The store-set and authorizer as cached dependencies; settings as a dependency. Bodies read them unchanged
   (DD-794, DD-799). Commit two.
3. `services.py` with the ten factories, and the coercion to its owner module. `routes/entity.py` to handlers
   only. One commit per route family (DD-795, DD-800). Commit three onward.
4. `bodies.py` for the four validation blocks, and one owner for the export lock (DD-796, DD-797).
5. Per-app OpenAPI model list (DD-798).

Commit one is the only behaviour change and it is provable alone. Commits two to five move how a body gets a
value
without changing the value, so the parity scenarios stay green across all of them.

## Verification

Level 0: `uv run pytest apps/aurelius-atlas-server/tests`, ruff, pyright, and a check that no test writes
`app.state.settings` after commit two. Level 1: `nx test aurelius-atlas-server -c ci` and the parity
scenarios.
SVC-08 is the gate: the scenarios and `test__app_search_governance.py` answer identical to the base, and
SVC-01 is
its own new test rather than a parity change. Level 2: `nx e2e aurelius-atlas-server -c ci` after commit
three.
Trace check scoped to SVC, compared against the base.
