# 0.2 Elasticsearch infrastructure

- **Status:** done
- **Pull request:** [\#78](<https://github.com/aureliusenterprise/aurelius-atlas/pull/78>)
- **Records:** ADR 047 (becomes Accepted), DD-005, DD-006, DD-007, DD-008

## Scope

Give the spine its search store ([ADR 047](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)) without adding Atlas behaviour:

- **`dev/elasticsearch`** (`aurelius-atlas-dev-elasticsearch`): a single-node Elasticsearch 9.5 for development and end-to-end tests, wired like `dev/postgres` — hardened `dhi.io/elasticsearch:9.5-debian13` image, TLS from the workspace CA (`tls.json` → `certgen`), credentials in `.env.enc`, a named data volume, and a `metrics-puller` sidecar that pushes cluster metrics to `dev/observability`.
- **`libs/python/aurelius-atlas-store-es`** (`aurelius_atlas_store_es`), the store library skeleton named in [DD-002](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>): a settings model, the lifecycle of one asynchronous client, a version check, and a health check.
- **A test fixture** in the library's `testing` extra that starts a TLS-enabled Elasticsearch with testcontainers, for this library's tests and for every later project that needs a store.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Index names, mappings and templates | 1.3, 2.2 |
| The `covers` marker and the traceability check | 0.3 |
| An HTTP endpoint that exposes the health check | 0.5 |
| Removing Postgres and the template examples | 0.5 |
| Production deployment, snapshots and index tuning | 6.4 |

## Semantics

### Development store

| Id | Rule |
| --- | --- |
| ESD-01 | `nx up aurelius-atlas-dev-elasticsearch` starts a single-node Elasticsearch 9 that reports healthy, reachable at `https://localhost:9200` |
| ESD-02 | Security is on: HTTP is TLS-only with a certificate from the workspace CA, and every request needs basic authentication |
| ESD-03 | Credentials exist only in the project's SOPS-encrypted `.env.enc`; the plaintext `.env` holds dev defaults, as for every other project |
| ESD-04 | Data survives `docker compose down` / `nx up`; only removing the named volume (`down -v`) resets it |
| ESD-05 | The JVM heap is fixed (1 GiB by default) so the whole system still runs on one machine ([ADR 006](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)) |
| ESD-06 | Cluster metrics reach `dev/observability` through a sidecar collector; `dev/observability` stays unaware of this project |

### Store library

| Id | Rule |
| --- | --- |
| STO-01 | The library is configured only by an explicit settings object (hosts, user name, password, CA certificate, request timeout); it reads no environment variables |
| STO-02 | Connections are HTTPS and verify the server certificate against the configured CA; there is no setting that turns verification off |
| STO-03 | One client is opened per store instance and closed exactly once when the store is closed, also when the body of `async with` raises |
| STO-04 | Opening a store fails with `UnsupportedVersionError` when the server's major version is not 9, and with `StoreUnavailableError` when the server cannot be reached |
| STO-05 | The health check reports **up** when the cluster status is green or yellow, and **down** when it is red |
| STO-06 | The health check never raises: an unreachable server, a rejected credential or a timeout is reported as **down** with the reason |
| STO-07 | A health report carries the cluster name, the server version and the cluster status whenever the server answered |
| STO-08 | The password is never part of the settings' `repr`, a log record or a health report |

Rule STO-05 counts yellow as up because a single-node cluster is yellow as soon as an index has a replica it cannot place ([DD-008](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/conversion/design-log/#dd-008-a-yellow-cluster-is-healthy>)).

## Java origin

None ported. The JanusGraph and Solr wiring this replaces (`graphdb/*`, `AtlasJanusGraphDatabase`, `Solr6Index`) is already mapped as *replaced* in the [Java to Python Map](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/conversion/java-map/index.md>). Atlas's own health answer, `GET /api/atlas/admin/status` (`AdminResource.getStatus`), is ported in 0.5 on top of STO-05.

## Deviations

None: nothing in this increment is visible through the Atlas REST API.

## Acceptance

- `libs/python/aurelius-atlas-store-es/tests/` — unit tests for STO-01, STO-02, STO-03, STO-08 without a server, and integration tests for STO-03 to STO-07 against the `testing` fixture (testcontainers, TLS on). Until the `covers` marker exists (0.3), each test names its rule ids in its docstring; 0.3 turns them into markers.
- `dev/elasticsearch` — ESD-01 to ESD-06 are checked by hand for this increment (`nx up`, `curl --cacert … -u …`, `docker compose down`/`nx up` with a test document, the Grafana Elasticsearch metrics); the first project that depends on the dev store in an end-to-end test (0.5) turns them into automated checks.
- `nx affected -t lint typecheck test -c ci` and `zensical build` are green.
