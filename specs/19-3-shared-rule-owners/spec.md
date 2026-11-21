# 19.3 One owner for the shared classification and parent rules

- **Status:** in review
- **Pull request:** TBD
- **Records:** DD-782 to DD-787, plan in [plan.md](./plan.md), design in [design.md](./design.md)

## Scope

This increment gives the two rules that the 18.x series keeps changing one owner each. The first is "which
classifications did the acting user set on this entity, as against the ones propagation put there". The second
is
"which end of this relationship is the parent end". Each rule is written several times today, and the 18.2,
18.3,
and 18.5 increments each edited one copy and left the others.

This increment changes no answer that leaves the server for the paths that already agree. The one path where
the
two write paths disagree today is written up first (RUL-04 and RUL-05), and its outcome decides whether one
answer moves. That outcome is its own commit and its own test.

This increment does not deliver:

| Not delivered                                    | It lands in |
| ------------------------------------------------ | ----------- |
| The store contract the write path is typed on    | 19.2        |
| The `entity_documents.py` module split           | 19.4        |
| The webapp copy of the parent rule and its guard | 19.6        |

## Semantics

Both rules read one stored shape today and reach the same answer in the paths that agree. The rules below give
each answer one function and replace every copy with a call to it.

| Id     | Rule                                                                                                                                                                                                                   |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RUL-01 | One function decides which classifications on an entity the acting user set, as against the ones propagation added. Every place that asks this question calls it.                                                      |
| RUL-02 | That function reads the stored entity's own classifications field and nothing else, so every caller reads the same source and cannot drift by reading a different view of the entity.                                  |
| RUL-03 | One function decides which end of a relationship attribute is the parent end, from the attribute's edge label and direction. Both write paths call it.                                                                 |
| RUL-04 | A parent end released in the same request that takes it (the RPS-02 move) is one rule. The classic path and the view door both apply it, or the difference is recorded as a deviation.                                 |
| RUL-05 | Before the copies are replaced, the RPS-02 difference between the two write paths is written up. It is then closed in this increment or given a row in [Deviations](../../docs/architecture/conversion/deviations.md). |
| RUL-06 | The parity scenarios and the 14.6 governance corpus answer identical, except for the RPS-02 outcome chosen by RUL-05, which is one commit with its own test.                                                           |

## Java origin

Apache Atlas 2.4.0 spreads both rules over its graph layer. The own-versus-propagated classification test sits
in
`AtlasClassificationHelper` and the propagation path, and the parent-end test sits in `EntityGraphDao` and
`AtlasRelationshipHelper`. Aurelius Atlas already ports each rule once in `entity_classifications.py` and
`graph_helper.py`, and the copies this increment removes are Aurelius code that grew beside those ports. This
increment does not change the Java comparison, so it adds no row to [Java
map](../../docs/architecture/conversion/java-map.md).

## Deviations

The own-classification owner and the parent-end owner match Apache Atlas, so they add no row. RUL-05 may add
one
row, and only if the RPS-02 difference between the two write paths is kept rather than closed. That row is
named
in [design.md](./design.md) at DD-787 and lands in
[Deviations](../../docs/architecture/conversion/deviations.md)
with the increment if it is chosen.

## Acceptance

| Check                                               | Command                                                                                                                                            | Level |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| Every RUL rule has a test that names it             | `uv run aurelius-atlas-trace check` scoped to this increment                                                                                       | 0     |
| The four classification reads call one owner        | `uv run pytest libs/python/aurelius-atlas-core/tests/test__entity_classifications.py libs/python/aurelius-atlas-core/tests/test__view_mutation.py` | 0     |
| The two parent-end reads call one owner             | `uv run pytest libs/python/aurelius-atlas-core/tests/test__entity_discovery.py`                                                                    | 0     |
| The core and server suites pass                     | `nx test aurelius-atlas-core aurelius-atlas-server -c ci`                                                                                          | 1     |
| No wire answer moved except a chosen RPS-02 outcome | The parity scenarios and `test__app_search_governance.py` answer identical                                                                         | 1     |
| Lint and types                                      | `nx lint aurelius-atlas-core` and `nx typecheck aurelius-atlas-core`                                                                               | 0     |

## Design decisions

The reasoning for each rule above lives in [design.md](./design.md) as DD-782 to DD-787. The one worth reading
before the rest is DD-786, which records why the RPS-02 difference is written up before any copy is replaced.
