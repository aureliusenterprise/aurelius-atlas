# 9.5c The standalone stack's own store

- **Status:** in review
- **Pull request:** to be opened
- **Records:** DD-367; relies on DD-363 (the standalone stack behind nginx), DD-366 (its demo realm) and
  DD-223 (the e2e suites share the dev stores)

The standalone stack keeps its catalogue in an Elasticsearch of its own. It shows what was imported into it,
and none of the types and entities the e2e suites and `nx serve` leave in the dev store.

## Scope

The standalone stack in `apps/aurelius-atlas-server/standalone/`: the services `elasticsearch-volume-init` and
`elasticsearch`, the volumes `elasticsearch-data` and `elasticsearch-snapshots`, the server's store address.
The node takes `dev/elasticsearch`'s configuration, certificate and coredump agent as they are.

Not in scope: the dev store, the e2e suites and what they leave there.

## Semantics

| Id     | Rule                                                                                                                                                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SST-01 | The stack runs its own Elasticsearch, `elasticsearch`, with the volumes `elasticsearch-data` and `elasticsearch-snapshots`, `dev/elasticsearch`'s configuration and certificate, and no published port     |
| SST-02 | The server reaches that store alone, as `https://elasticsearch:9200`, with its password as the store's `elastic` password; the stack joins no dev network, and the server starts once the store is healthy |
| SST-03 | The store lasts across `down` and `up`; `down -v` empties it, and the next start creates the types again and imports `SAMPLE_ZIP`                                                                          |

## Java origin

None: Atlas's stores are its own deployment's; the stack is Aurelius's.

## Deviations

None.

## Acceptance

- `tests/test__standalone_store.py`: SST-01 and SST-02, read from the stack's compose file.
- By hand, the standalone stack with `SAMPLE_ZIP=sample_data.zip` on a new store: the import's 688 entities in
  13 entity types, Atlas's `AtlasServer` and the m4i types, and no type of an e2e suite (SST-03).
