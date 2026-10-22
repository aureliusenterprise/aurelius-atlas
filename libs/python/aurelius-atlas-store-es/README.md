# aurelius-atlas-store-es

Elasticsearch access for Aurelius Atlas, the only store of the catalogue
([ADR 047](../../../docs/architecture/adr/047-one-search-store-is-the-system-of-record.md)).

Introduced by increment 0.2 as a skeleton: settings, the lifecycle of one async client, a version
check and a health check. The client reads floats as decimals and sends bodies given as bytes unchanged
(`serializer`, DD-039, DD-043); index layouts belong to the stores that use them, in `aurelius-atlas-core`.

## Usage

```python
from aurelius_atlas_store_es import ElasticsearchStore, StoreSettings

settings = StoreSettings(
    hosts=["https://localhost:9200"],
    password="…",
    ca_certs="dev/elasticsearch/certs/ca.pem",
)

async with ElasticsearchStore(settings) as store:  # fails fast unless the server is Elasticsearch 9
    report = await store.health()  # never raises; up for green or yellow
```

The application owns configuration: the library reads no environment variables, and connections
are always HTTPS with certificate verification.

## Extras

| Extra     | Enables                                                                |
| --------- | ---------------------------------------------------------------------- |
| `testing` | `testing.container` (TLS-enabled Elasticsearch through testcontainers) |

`testing.fake` (a stand-in client for unit tests) needs no extra.
