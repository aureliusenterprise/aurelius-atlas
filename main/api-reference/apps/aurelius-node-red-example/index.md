# aurelius-node-red-example

This is an example Node-RED application that demonstrates how to set up a simple Kafka producer.

The app produces a new message every 10 seconds. The content of the message is static with a randomly generated `guid` field. The message is encoded using Avro and sent to a Kafka topic.

## Key Schema

Keys should be string representations of the entity's `guid` field.

## Value Schema

Values are Avro-encoded records that conform to the `Entity` schema. The schema is registered in the schema registry as `com.aureliusenterprise.example.Entity`.

## Deployment

Deploy using the provided Dockerfile. By default, the app listens on port `1880`.

## Configuration

Every setting is read from the environment with the `AURELIUS_NODE_RED_` prefix (the `${...}` lookups in `flows.json`), so other projects' environment variables can never populate this app.

| Name | Description |
| --- | --- |
| `AURELIUS_NODE_RED_KAFKA_BOOTSTRAP_SERVERS` | A comma-separated list of Kafka bootstrap servers. |
| `AURELIUS_NODE_RED_KAFKA_TOPIC_NAME` | The name of the Kafka topic to write to. |
| `AURELIUS_NODE_RED_SCHEMA_REGISTRY_URL` | The URL of the schema registry. |
| `AURELIUS_NODE_RED_SCHEMA_SUBJECT_NAME` | The name of the schema subject to use for encoding messages. |
| `AURELIUS_NODE_RED_SCHEMA_SUBJECT_VERSION` | The version of the schema subject to use for encoding messages. |
