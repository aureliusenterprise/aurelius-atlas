# aurelius-atlas-dev-elasticsearch

Local development Elasticsearch (increment 0.2, rules ESD-01 to ESD-06). This file covers wiring
specific to this project; workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — `elasticsearch`, the one-shot `volume-init`, and the `metrics-puller` sidecar
- `config/elasticsearch.yml` — every node setting (mounted over the image's file)
- `config/metrics-puller.yaml` — OTel Collector config for the puller (scrapes this cluster, pushes
  OTLP to dev/observability)
- `tls.json` — certificate for the `elasticsearch` service (`certgen` writes `certs/`)
- `.env` / `.env.enc` — SOPS-encrypted dev settings (`ELASTICSEARCH_PASSWORD`, `_PORT`, `_HEAP`)

## Wiring Checklist

- Exposes the Docker network `aurelius-atlas-dev-elasticsearch-network`.
- `implicitDependencies` on `aurelius-atlas-dev-observability`, as for dev/postgres: the
  `metrics-puller` joins the external `aurelius-atlas-dev-observability-network`. Prometheus series carry
  `exported_job="dev-elasticsearch"`.
- The image tag is shared with `aurelius_atlas_store_es.testing.container`; change both together.

## Hardened-image quirks (dhi.io/elasticsearch)

- **Dotted environment variables are ignored**, unlike the official image — settings go in
  `config/elasticsearch.yml`. `ELASTIC_PASSWORD` still works (the entrypoint writes it to the keystore).
- **No `curl`/`wget`** — the healthcheck speaks HTTPS through `openssl s_client`.
- **No data directory in the image** — `volume-init` chowns the named volume to uid 1000.
- **Certificates live in `config/tls`**, not `config/certs`: security auto-configuration owns that
  directory and fails to start when it is a mount. Auto-configuration is also switched off.
- **`node.store.allow_mmap: false`** removes the `vm.max_map_count >= 262144` bootstrap check, which
  dev machines and CI runners (65530 by default) do not meet.

## Commands

```bash
nx serve aurelius-atlas-dev-elasticsearch   # compose up (foreground)
nx up aurelius-atlas-dev-elasticsearch      # detached, waits for healthy
docker compose -f dev/elasticsearch/docker-compose.yaml down -v   # reset all data
```

## Conventions

- Keep it an empty cluster: index templates and mappings belong to the application (1.3, 2.2).
- `ELASTICSEARCH_PORT` (default 9200) is part of the workspace contract — coordinate before changing.

## Removal

Part of the spine; not removable (ADR 047).
