# 20.1 Client view routes

- **Status:** in progress
- **Pull request:** —
- **Records:** CLV-01..CLV-04 and CLW-13 (minted in the workspace-root increment
  [`20-1-e2e-through-client`](../../../../../specs/20-1-e2e-through-client/spec.md)),
  DD-812 to DD-815; cites 8.4 (CL-01..CL-13), 8.8 (DD-307)

The view family's doors (16.2, 16.3) answer the Aurelius-native `/api/aurelius/v1`
routes. At the 2026-08-01 review the client covered none of them, and the server's
e2e suite called those three routes with hand-built requests. Increment 20.1 moves
the suite onto the client and gives the client the doors it needs.

## Scope

In scope, in this increment:

- `AtlasClient.view` — the search door of `routes/view_search.py` and the read and
  mutation doors of `routes/view_entity.py` (CLV-01..CLV-04).
- `AtlasSessionInfo`'s two entity permission flags (CLW-13).

Out of scope:

- The form-slice door of `routes/view_types.py` — no caller needs it today; its row
  stays open below.
- Any Angular twin — the webapp has its own data-access service (8.13).

## Semantics

The 8.4 rules (CL-01..CL-08, CL-10..CL-13) apply to every new method and are not
restated. CLV-01..CLV-04 and CLW-13 state the behaviour; the table of every route
is the matrix (DD-307): a change to one of these two route modules updates this
matrix in the same PR.

## Route matrix

| Server route                                 | Covered by                   |
| -------------------------------------------- | ---------------------------- |
| `POST /api/aurelius/v1/search`               | `view.search` (CLV-04)       |
| `GET /api/aurelius/v1/entity/guid/{guid}`    | `view.read` (CLV-01)         |
| `POST /api/aurelius/v1/entity`               | `view.save` (CLV-02, CLV-03) |
| `GET /api/aurelius/v1/types/for-type/{name}` | open — no caller (AVW-11)    |

## Acceptance

| Check                                  | Command                                                        | Level |
| -------------------------------------- | -------------------------------------------------------------- | ----- |
| Each CLV rule has a test that names it | `uv run pytest libs/python/aurelius-atlas-server-client/tests` | 0     |
| The whole library still passes         | `nx test aurelius-atlas-server-client -c ci`                   | 1     |
| The doors answer the real routes       | `nx e2e aurelius-atlas-server` (the view suites)               | 2     |
