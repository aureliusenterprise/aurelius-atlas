# 19.7 Small deletions

- **Status:** in review
- **Pull request:** TBD
- **Records:** DD-809 to DD-811, plan in [plan.md](./plan.md), design in [design.md](./design.md)

## Scope

This increment makes two small deletions. It replaces the six copies of the version-conflict retry loop with
one
helper, and it groups the stored entity's flat governance fields into one nested record, the way the App
Search and
quality blocks already are. Both deletions remove duplication without touching how the store writes or reads.

This increment changes no answer that leaves the server. No endpoint changes its body, its status, or its
headers,
because neither change moves a value across the wire. The parity scenarios and the frozen 14.6 corpus must
answer
byte-identical, and that is an acceptance rule below.

This increment does not deliver:

| Not delivered                                  | It lands in |
| ---------------------------------------------- | ----------- |
| The `WriteTransaction` the retry sits in       | 19.2        |
| Any change to a stored value or the wire shape | Not planned |

## Semantics

Both deletions replace a repeated shape with one shape. The retry loop is the same six times with a different
error mapping, and the governance fields are three flat fields beside two nested records that already show the
narrower shape.

| Id     | Rule                                                                                                                                                                                                                                             |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PAR-01 | One helper runs the version-conflict retry. The six loops in core call it. Each caller passes its own error mapping, so a conflict the caller must turn into a specific answer still does.                                                       |
| PAR-02 | A retry keeps its own attempt count and its own stop condition. The helper does not force every caller to the same number of attempts, because the loops today differ (five run twice, one runs ten).                                            |
| PAR-03 | No wire answer changes, and no stored value changes. The helper returns what the loop returned, and the governance fields hold the same values in a nested record. The parity scenarios and the 14.6 corpus answer identical to the base commit. |

## Java origin

This ports nothing. Apache Atlas 2.4.0 handles the version conflict in JanusGraph's transaction layer and has
no
stored-entity record of Aurelius's shape. Both the retry loops and the stored-entity record are Aurelius code,
so
this increment adds no row to [Java map](../../docs/architecture/conversion/java-map.md).

## Deviations

None from Apache Atlas. Neither deletion moves a value a parity test can see, so the increment adds no row to
[Deviations](../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                     | Command                                                                                   | Level |
| ----------------------------------------- | ----------------------------------------------------------------------------------------- | ----- |
| Every PAR rule has a test that names it   | `uv run aurelius-atlas-trace check` scoped to this increment                              | 0     |
| The retry helper is the only retry loop   | a grep shows no second `for number in range(1, ATTEMPTS` loop in core after the change    | 0     |
| Each caller's error mapping still answers | the suites of the five retry owners answer, `nx test aurelius-atlas-core -c ci`           | 1     |
| The governance block reads the same       | `nx test aurelius-atlas-core -c ci`, and the wire shape of the stored record is unchanged | 1     |
| No wire answer moved                      | the parity scenarios and `test__app_search_governance.py` answer identical                | 1     |
| Lint and types                            | `nx lint aurelius-atlas-core` and `nx typecheck aurelius-atlas-core`                      | 0     |

## Design decisions

The reasoning for each rule above lives in [design.md](./design.md) as DD-809 to DD-811. The one worth reading
before the rest is DD-810, which records why the retry helper keeps a per-caller stop condition rather than
forcing
one count.
