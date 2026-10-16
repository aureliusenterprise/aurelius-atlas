# aurelius-aws-lambda-example

Example AWS Lambda function demonstrating the Aurelius serverless pattern: a
container-image Lambda triggered by MSK/Kafka records, deserialising Avro `Entity`
messages and re-producing them to the same topic.

Part of the optional **AWS Lambda slice** — remove this project together with
the rest of that slice.

## How it works

- `handler.py` — `main(event, context)` decorated with the `kafka_consumer` event
  handler (AWS Lambda Powertools). An `initialize()` warm-start hook builds the
  settings, Avro deserializer/serializer (header schema-id framing,
  `RecordNameStrategy` naming), and the Confluent producer.
- `processor.py` — base64-decodes MSK event payloads and round-trips each record.
- The image extends `docker/aurelius-aws-lambda-base` (resolved via
  `--build-arg VERSION`, `local` by default); the
  entrypoint resolves the handler as `aurelius_aws_lambda_example.main`.

## Workspace dependencies

- `aurelius-aws-lambda` — pydantic models for Kafka Lambda events
- `aurelius-kafka` — producer/Schema Registry helpers
- `aurelius-example` — the shared `Entity` model

## Configuration

Settings read environment variables with the `AURELIUS_LAMBDA_` prefix
(`Settings.env_prefix`) — other projects' configuration can never populate
this app. `AWS_REGION` is the one exemption: the boto3/AWS SDK chain and the
MSK IAM signer read the standard name too.

| Variable                                         | Default          | Purpose                                       |
| ------------------------------------------------ | ---------------- | --------------------------------------------- |
| `AURELIUS_LAMBDA_KAFKA_TOPIC_NAME`               | `example.entity` | Consumed and produced topic                   |
| `AURELIUS_LAMBDA_KAFKA_BOOTSTRAP_SERVERS`        | (per-env)        | Broker address (set in e2e)                   |
| `AURELIUS_LAMBDA_SCHEMA_REGISTRY_URL`            | (per-env)        | Schema Registry (set in e2e)                  |
| `AURELIUS_LAMBDA_KAFKA_OAUTH_TOKEN_ENDPOINT_URL` | (set in `.env`)  | When set, the producer uses OAuth (ADR 013)   |
| `AURELIUS_LAMBDA_KAFKA_OAUTH_CLIENT_ID`          | `kafka-lambda`   | Keycloak client (required with the token URL) |
| `AURELIUS_LAMBDA_KAFKA_OAUTH_CLIENT_SECRET`      | (in `.env.enc`)  | Keycloak client secret (required with it)     |

With the OAuth settings, `initialize()` configures the producer via
`aurelius_kafka.oauth_client_config` (SASL_SSL + OAUTHBEARER, OIDC client
credentials). In Docker networks the token URL must use the plain `keycloak`
service name — librdkafka resolves `*.localhost` to loopback — see
`dev/kafka/AGENTS.md` for why the e2e compose overrides it.

## Testing

```bash
nx test aurelius-aws-lambda-example -c ci   # unit tests
nx e2e aurelius-aws-lambda-example          # Lambda RIE container + real Kafka
nx docker-build aurelius-aws-lambda-example # build the deployment image
```

The E2E suite runs the function in the AWS Lambda Runtime Interface Emulator
(port 8080) with a local Kafka broker and Schema Registry.
