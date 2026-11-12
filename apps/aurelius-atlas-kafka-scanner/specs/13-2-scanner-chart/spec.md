# 13.2 The Kafka scanner chart and schedule

- **Status:** in review
- **Pull request:** #326
- **Records:** adds CHT-121 and CHT-122 (here) and DD-514 and DD-515 (here);
  relies on 13.1 (KSC-01..10, DD-466..473), 12.3 (the shared CronJob contract,
  CHT-114..120 plus CHT-125 and DD-508..513), and 12.2/DD-458 (the
  service-client pattern)

## Scope

This increment delivers `apps/aurelius-atlas-kafka-scanner/helm`: a standalone
Helm chart that runs the Kafka scanner as a Kubernetes `CronJob`, on the shared
shape 12.3's spec states (CHT-114..117, CHT-125) with the broker rules below.
Its client registration, credential, and audience join are the ones 12.3 states
whole (CHT-118..120).

This increment does not deliver: the broker's own machine-identity credential
as a first-class values block (DD-514's decision: `secretRefs` reaches it), or
a Kafka broker in any umbrella install (the suite's broker stays
compose-only, in the app's `e2e/` stack — DD-538). The broker's transport TLS and the telemetry leg are both
optional like every other trust leg (CHT-121's `securityProtocol`, CHT-125): a
deployment turns each on with its own values.

## Rules

The shared rules (CHT-114..117, CHT-125) apply verbatim; only the
scanner-specific ones are stated here.

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CHT-121 | The broker address is a first-class join: `<PREFIX>BOOTSTRAP_SERVERS` arrives from the required `broker.bootstrapServers` value (no default — pointing the job at `localhost:29092` in a cluster is a silent no-scan, the KSC-01 failure this guard exists to fail early). The remaining scan knobs (`broker.securityProtocol`, `broker.topicPattern`, `broker.systemName`, `broker.sniffMessages`, the three timeouts, and `schemaRegistry.url` when it exists) are values that render into their `<PREFIX>`-prefixed environment keys only when set; unset settings keep the app's own defaults (KSC-03's System name, KSC-02's `*` filter). SASL credentials are never values: the operator supplies an existing Secret and `secretRefs` maps its keys to `<PREFIX>SASL_*` and `<PREFIX>SASL_OAUTH_*` names (DD-514). |
| CHT-122 | The broker's OAUTHBEARER leg reuses the catalogue client: with `brokerOauth.enabled` true, `<PREFIX>SASL_MECHANISM` renders `OAUTHBEARER`, `<PREFIX>SASL_OAUTH_TOKEN_URL` joins the same issuer+realm token URL as CHT-116's `TOKEN_URL`, and `<PREFIX>SASL_OAUTH_CLIENT_ID` takes the catalogue client id — the broker accepts the same Keycloak the catalogue trusts, so one credential serves both doors (DD-514). The four `SASL_OAUTH_*`/`SASL_*` secret names stay `secretRefs` joins. `securityProtocol` stays an explicit value: the flag pair never guesses `SASL_SSL` over `SSL`.                                                                                                                                                                                                                              |

## Deviations

From 13.1's dev run: the compose drives the scanner against a PLAINTEXT loopback
broker with a dev secret; the chart never renders PLAINTEXT as a default —
in-cluster the address is required and the transport is the operator's choice.
From Java Atlas: none (the legacy Kafka scanner's static JAAS file has no
chart-side twin; `secretRefs` is the portable shape).

## Acceptance

- `uv run pytest tests/test__charts_kafka_scanner.py` — the CronJob shape on the
  shared contract (CHT-114..117, CHT-125, re-proven for this chart), the
  broker joins and guard (CHT-121), and the OAUTHBEARER leg (CHT-122).
- `npx nx run aurelius-atlas-kafka-scanner:helm-lint` / `:helm-template` /
  `:helm-config-scan` — the chart's share of the gates (CHT-06, DD-282).
- The realm half rides 12.3's acceptance: this chart's client id is the
  deployment's registration name (absent from the shipped realm asset and the
  umbrella's Secrets, CHT-118/119) and is in the server audience default
  (CHT-120).
