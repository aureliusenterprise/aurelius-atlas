# aurelius-atlas-dev-elasticsearch

Local development Elasticsearch, the only store of Aurelius Atlas
([ADR 047](../../docs/architecture/adr/047-one-search-store-is-the-system-of-record.md)).

Part of the **spine**.

## Services

| Service        | Image                                               | Host port                             |
| -------------- | --------------------------------------------------- | ------------------------------------- |
| elasticsearch  | `dhi.io/elasticsearch:9.5-debian13`                 | `${ELASTICSEARCH_PORT}` (9200, HTTPS) |
| metrics-puller | `dhi.io/opentelemetry-collector:0-debian13-contrib` | –                                     |
| volume-init    | same as `elasticsearch` (one-shot, runs as root)    | –                                     |

- Single node, cluster name `aurelius-atlas`, heap `${ELASTICSEARCH_HEAP}` (1 GiB)
- Security on (DD-006): HTTPS only with a certificate from the workspace CA, basic authentication as
  `elastic` with the password from `.env`
- Data in the named volume `data`; it survives restarts until removed with `docker compose down -v`
- Attached to the `aurelius-atlas-dev-elasticsearch-network` Docker network

## Running

```bash
nx serve aurelius-atlas-dev-elasticsearch   # docker compose up (foreground)
nx up aurelius-atlas-dev-elasticsearch      # detached, waits for healthy
```

```bash
# from dev/elasticsearch, after nx up (which decrypts .env)
curl --cacert certs/ca.pem -u "elastic:$(grep ELASTICSEARCH_PASSWORD .env | cut -d= -f2)" \
    https://localhost:9200/_cluster/health
```
