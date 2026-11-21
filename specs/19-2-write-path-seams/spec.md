# 19.2 A store the write path can be tested against

- **Status:** in review
- **Pull request:** TBD
- **Records:** DD-773 to DD-781, plan in [plan.md](./plan.md), design in [design.md](./design.md)

## Scope

This increment gives the write path a store contract it is typed against, so a test can drive `EntityWriter`
and
`ViewMutationDoor` without a running server. It rebuilds the view door's rewind wrapper on the documents
contract instead of subclassing the concrete store, and it moves the writer's per-attempt state onto a
transaction object that each retry builds fresh. Import semantics leave the shared writer for their own
orchestrator.

This increment changes no answer that leaves the server. No endpoint changes its body, its status, or its
headers, and a successful or refused write answers as it does today. The parity scenarios and the frozen 14.6
corpus must answer byte-identical, and that is an acceptance rule below.

This increment does not deliver:

| Not delivered                                                | It lands in |
| ------------------------------------------------------------ | ----------- |
| The one owner for the shared classification and parent rules | 19.3        |
| The `entity_documents.py` module split                       | 19.4        |
| The store-lookup error and route providers                   | 19.5        |

## Semantics

The store is the thing the write path is hard to test against, because the write path reaches into its
internals
and depends on the order a caller sets them. The rules below make that dependency visible in the types.

| Id     | Rule                                                                                                                                                                                                                                    |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| WRS-01 | One store contract names every store member the write path calls: the eight `EntityWriter` calls and the seven the view door makes. `EntityWriter` and `ViewMutationDoor` are typed against it, not against the concrete `EntityStore`. |
| WRS-02 | `EntityStore` stays the only production implementation of that contract. This increment adds no new production store, and the in-memory and fake stores already satisfy it.                                                             |
| WRS-03 | The rewind wrapper is built on the documents contract and holds the real store as a collaborator. It does not subclass `EntityStore`, so it cannot read the real store's private documents, clock, or id source.                        |
| WRS-04 | The rewind wrapper shares the real store's write listeners and task listeners by name, because the real store owns them. It reaches no private field to do so.                                                                          |
| WRS-05 | One per-attempt transaction object holds the write's mutable state: the import flag, the deferred deletions, the import guid map, the task hold, and the request record. `EntityWriter` builds it at the top of each attempt.           |
| WRS-06 | A write step reads the output of an earlier step from the transaction object. `EntityWriter` holds no mutable attribute of one write across an attempt boundary, so a retry starts clean.                                               |
| WRS-07 | Import semantics live in an `ImportWriter` that shares the transaction object. `EntityWriter` answers the non-import paths and carries no import-only flag.                                                                             |
| WRS-08 | A write that rolls back wakes no write listener and wakes no task listener. The documents it had prepared are discarded, and the index and task workers see nothing of them.                                                            |
| WRS-09 | No wire answer changes. A created, updated, or refused entity answers identical, and the parity scenarios and the 14.6 governance corpus answer identical to the base commit.                                                           |

## Java origin

This ports nothing. Apache Atlas 2.4.0 writes through `AtlasEntityStore` and `EntityGraphDao` against
JanusGraph,
and it has no view door and no rewind path, so the classes the increment touches (`view_mutation.py`,
`entity_writer.py`, `transaction_view.py`) are Aurelius-native. This increment reorganises Aurelius code
around
the seams 16.x and 18.x already lean on.

## Deviations

None from Apache Atlas. The increment changes no observable behaviour, so it adds no row to
[Deviations](../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                          | Command                                                                                    | Level |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------ | ----- |
| Every WRS rule has a test that names it        | `uv run aurelius-atlas-trace check` scoped to this increment                               | 0     |
| The write path is driven without a server      | `nx test aurelius-atlas-core -c ci`, and `test__view_mutation.py` drives the door directly | 0     |
| The core and server write suites pass          | `nx test aurelius-atlas-core aurelius-atlas-server -c ci`                                  | 1     |
| No wire answer moved                           | The parity scenarios and `test__app_search_governance.py` answer identical                 | 1     |
| A rolled-back write wakes no worker            | WRS-08 test on the door's write listeners, replacing the pinned rollback test              | 1     |
| Lint and types                                 | `nx lint aurelius-atlas-core` and `nx typecheck aurelius-atlas-core`                       | 0     |
| One live proof that the write doors still work | `nx e2e aurelius-atlas-server -c ci`                                                       | 2     |

## Design decisions

The reasoning for each rule above lives in [design.md](./design.md) as DD-773 to DD-781. The two worth reading
before the rest are DD-775, which records why the rewind wrapper composes the store rather than subclassing
it,
and DD-780, which records why import semantics move to their own orchestrator.
