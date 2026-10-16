# aurelius-kafka-connect-jdbc-sink-example

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aurelius-kafka-connect-jdbc-sink-example)

This is an example Kafka Connect JDBC Sink application.

## Workflow

```mermaid
graph LR
    subgraph A["Kafka"]
        a[("example.entity")]
    end

    subgraph B["Connector"]
        b["JDBC Sink"]
    end

    subgraph C["Postgres"]
        c[("Entity")]
    end

    subgraph D["Kafka"]
        d[("example.entity-dlq")]
    end

    a -->|"Messages"| b
    b -->|"Records"| c
    b -->|"Errors"| d
```

The connector reads messages from the `example.entity` Kafka topic, processes each message, and writes the resulting
data to the `Entity` table in Postgres.

??? QUESTION "What happens if the database is unavailable?"

    If the database is unavailable, the connector will retry processing the messages at a later time.

??? QUESTION "What happens if processing fails?"

    If processing fails, the connector forwards the problematic message to the dead-letter queue topic `example.entity-dlq`.

## Key Schema

Keys should be string representations of the entity's [`guid`][aurelius_example.models.Entity.guid]
field.

## Value Schema

Values are expected to be Avro-encoded records that conform to the [`Entity`][aurelius_example.models.Entity]
schema.

??? INFO "Entity Schema"

    ::: aurelius_example.models.Entity

The schema is registered in the schema registry as `com.aureliusenterprise.example.Entity`.

## Tombstone Messages

The connector also supports tombstone messages, which are used to delete records from the database. Tombstone
messages should have a key that matches the entity's [`guid`][aurelius_example.models.Entity.guid] field and a
value that is `null`.

## Configuration

This example runs Kafka Connect in standalone mode and uses two properties files:

- `workers/worker.properties` for worker runtime settings
- `workers/connector.properties` for this JDBC sink connector instance

### Standalone startup in Docker Compose

Set the service entrypoint to `connect-standalone.sh` and pass the worker file first, then the connector file:

```yaml
services:
    kafka-connect:
        image: ghcr.io/aureliusenterprise/aurelius-kafka-connect-jdbc-sink-example:local
        entrypoint: ["/opt/kafka/bin/connect-standalone.sh"]
        command: ["/connect-worker", "/connect-connector"]
        configs:
            - connect-worker
            - connect-connector

configs:
    connect-worker:
        file: ./workers/worker.properties
    connect-connector:
        file: ./workers/connector.properties
```

### Worker configuration environment variables

These environment variables are referenced by `workers/worker.properties`:

All app settings carry the `AURELIUS_CONNECTOR_` prefix, so other projects'
environment variables can never populate this app.

| Name                                           | Description                                           |
| ---------------------------------------------- | ----------------------------------------------------- |
| `AURELIUS_CONNECTOR_KAFKA_BOOTSTRAP_SERVERS`   | Kafka bootstrap servers.                              |
| `AURELIUS_CONNECTOR_CONFIG_STORAGE_TOPIC`      | Connect config storage topic name.                    |
| `AURELIUS_CONNECTOR_GROUP_ID`                  | Connect worker group ID.                              |
| `AURELIUS_CONNECTOR_OFFSET_STORAGE_TOPIC`      | Connect offset storage topic name.                    |
| `AURELIUS_CONNECTOR_STATUS_STORAGE_TOPIC`      | Connect status storage topic name.                    |
| `AURELIUS_CONNECTOR_REST_ADVERTISED_HOST_NAME` | Hostname advertised by the Connect REST API.          |
| `AURELIUS_CONNECTOR_REST_PORT`                 | Connect REST API port.                                |
| `AURELIUS_CONNECTOR_SCHEMA_REGISTRY_URL`       | Schema Registry URL used by the Avro value converter. |

`worker.properties` also sets `offset.storage.file.filename`, which is required for standalone mode.

### Connector configuration environment variables

These environment variables are referenced by `workers/connector.properties`:

| Name                                   | Description                                               |
| -------------------------------------- | --------------------------------------------------------- |
| `AURELIUS_CONNECTOR_DATABASE_URL`      | JDBC URL for the target Postgres database.                |
| `AURELIUS_CONNECTOR_DATABASE_USERNAME` | Database username.                                        |
| `AURELIUS_CONNECTOR_DATABASE_PASSWORD` | Database password.                                        |
| `AURELIUS_CONNECTOR_KAFKA_TOPIC_NAME`  | Source topic consumed by the sink connector.              |
| `AURELIUS_CONNECTOR_DLQ_TOPIC_NAME`    | Dead-letter queue topic for records that fail processing. |
| `AURELIUS_CONNECTOR_TABLE_NAME`        | Destination table name used by the JDBC sink connector.   |
