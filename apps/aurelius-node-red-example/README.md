# aurelius-node-red-example

Example Node-RED application demonstrating the Aurelius Kafka producer pattern with
a low-code flow: every 10 seconds it generates an `Entity` message and produces it
to Kafka with Avro serialisation.

Part of the optional **Kafka streaming slice** — remove this project together
with the rest of that slice.

## How it works

- `flows.json` — the exported flow ("Events" tab): inject → UUID generation →
  field population → Kafka producer node (plus a debug node).
- `settings.js` / `settings.prod.js` — Node-RED runtime settings; the production
  variant disables the editor and serves on port 1880.
- Kafka/Avro support comes from the `@oriolrius/node-red-contrib-kafka` and
  `node-red-contrib-uuid` palette nodes.

## Configuration

Every flow setting is read from the environment with the
`AURELIUS_NODE_RED_` prefix (the `${...}` lookups in `flows.json`), so other
projects' environment variables can never populate this app.

| Variable                                    | Default                                 | Purpose                                                              |
| ------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------- |
| `AURELIUS_NODE_RED_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092`                        | Broker address                                                       |
| `AURELIUS_NODE_RED_KAFKA_TOPIC_NAME`        | `example.entity`                        | Target topic                                                         |
| `AURELIUS_NODE_RED_SCHEMA_REGISTRY_URL`     | `https://localhost:8081`                | Schema Registry                                                      |
| `AURELIUS_NODE_RED_SCHEMA_SUBJECT_NAME`     | `com.aureliusenterprise.example.Entity` | Avro subject                                                         |
| `AURELIUS_NODE_RED_SCHEMA_SUBJECT_VERSION`  | `latest`                                | Avro subject version                                                 |
| `AURELIUS_NODE_RED_KAFKA_CA_FILE`           | `certs/ca.pem`                          | TLS CA for the Kafka connection                                      |
| `AURELIUS_NODE_RED_KAFKA_CLIENT_CERT_FILE`  | `certs/node-red.pem`                    | Client certificate for the broker (mTLS)                             |
| `AURELIUS_NODE_RED_KAFKA_CLIENT_KEY_FILE`   | `certs/node-red-key.pem`                | Private key for the client certificate                               |
| `NODE_EXTRA_CA_CERTS`                       | `certs/ca.pem`                          | TLS CA for the Schema Registry (third-party Node.js name, kept bare) |

Kafka and Schema Registry connections use TLS verified against the local
development CA (`nx certgen` generates this project's `certs/`). The broker's
SSL listeners require a client certificate (mTLS), so the flow presents this
project's own leaf and key when connecting.

## Running

```bash
nx serve aurelius-node-red-example
```

Starts `node-red` with this directory as the user directory (the `serve` target
also starts `aurelius-dev-kafka` first). The editor is available on port 1880.

## Testing

```bash
nx e2e aurelius-node-red-example   # pytest E2E against a real broker
```
