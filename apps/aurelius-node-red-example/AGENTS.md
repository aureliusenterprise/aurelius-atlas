# aurelius-node-red-example

Example Node-RED Kafka producer flow. This file covers wiring specific to this
app; workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `flows.json` — the exported flow ("Events" tab: inject → uuid → change → Kafka
  producer). Edit through the Node-RED editor and re-export; don't hand-edit in
  production-like changes unless reviewing node IDs.
- `settings.js` / `settings.prod.js` — runtime settings; prod disables the editor
  and serves on 1880.
- `e2e/` — pytest suite producing/consuming against a real broker
- `package.json` — palette nodes (`@oriolrius/node-red-contrib-kafka`,
  `node-red-contrib-uuid`) are npm deps here, installed into the image/dev dir

## Configuration

- Kafka/Schema Registry connection values are read from environment variables by
  the Kafka nodes, all under the `AURELIUS_NODE_RED_` prefix (the `${...}`
  lookups in `flows.json`): `..._KAFKA_BOOTSTRAP_SERVERS`, `..._KAFKA_TOPIC_NAME`,
  `..._SCHEMA_REGISTRY_URL`, `..._SCHEMA_SUBJECT_NAME`, `..._SCHEMA_SUBJECT_VERSION`.
- Both connections use TLS verified against the local dev CA: `AURELIUS_NODE_RED_KAFKA_CA_FILE`
  (Kafka node) and `NODE_EXTRA_CA_CERTS` (Schema Registry HTTPS client) point at
  `certs/ca.pem` (`nx certgen` generates this project's `certs/`).
- The broker's SSL listeners enforce mTLS (`ssl.client.auth` required): the
  flow's broker node presents `AURELIUS_NODE_RED_KAFKA_CLIENT_CERT_FILE`/`_KEY_FILE`
  (`certs/node-red{,-key}.pem`, provisioned by this project's `tls.json`).
  The e2e compose sets them to the in-container `/certs/...` copies; `.env`
  carries repo-relative paths for the host `serve` path. Node-RED core
  expands `${VAR}` in node properties (same mechanism as `..._KAFKA_CA_FILE`).
- `.env` holds dev defaults; `.env.enc` holds real values (SOPS).

## Wiring Checklist

- `project.json` — `implicitDependencies: ["aurelius-dev-kafka"]`; the `serve`
  target runs `node-red -u {projectRoot}` and starts Kafka first.
- `Dockerfile` — the `e2e` target depends on `docker-build`; new palette nodes
  must be added to `package.json` so they exist in the image.
- The Avro subject (`com.aureliusenterprise.example.Entity`) must match the schema
  registered by the Python/Java producers.

## Commands

```bash
nx serve aurelius-node-red-example    # editor on http://localhost:1880
nx e2e aurelius-node-red-example      # pytest E2E
nx lint aurelius-node-red-example
```

Offline-safe: `nx lint`. Needs Docker: `serve` (Kafka), `e2e`.

## Conventions

- Flow changes go through the editor and get committed as `flows.json` diffs —
  review them like code.
- Keep dev (`settings.js`) and prod (`settings.prod.js`) settings aligned when
  adding environment-driven values.

## Removal

Part of the optional Kafka streaming slice. Removing this app also removes its
`mkdocs.yaml` nav entry, CI references, and the slice row in the root `AGENTS.md`
module map.
