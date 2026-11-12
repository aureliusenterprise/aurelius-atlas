# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-514. The broker's machine identity reuses the catalogue client

- **Status:** Proposed
- **Increment:** 13.2
- **Date:** 2026-11-12

**Decision.** When the broker speaks OAUTHBEARER, the chart points the broker
leg at the same confidential client the job uses for the catalogue:
`SASL_OAUTH_TOKEN_URL` and `SASL_OAUTH_CLIENT_ID` join the issuer and the
catalogue client id, and `SASL_MECHANISM` renders `OAUTHBEARER` under the
`broker.oauth.enabled` value (CHT-122). A broker that wants a different
identity (a broker-local `SASL_USER`/`SASL_PASSWORD` pair, or a second Keycloak
client) gets it through `secretRefs` and `config`, not a bespoke block. The
13.1 spec's open question — "the broker's machine identity decision" — is
answered: the chart assumes the broker trusts the deployment's own issuer.

**Reason.** A Kafka broker inside an Aurelius deployment validates JWTs against
the same Keycloak the catalogue does (DD-113's one-issuer rule for the system),
so the scanner's existing client credentials are already a broker-accepted
token — KSC-10's door accepts them with no second credential. Minting a second
client per scanner-per-broker would triple the realm roster for one issuer.
The credential itself stays `secretRefs`-supplied for every mechanism except
the OAUTHBEARER leg, which reuses the join CHT-116 already renders.

**Alternatives.** A dedicated `otel`-style roster entry per broker: 13.1
shipped one broker in dev with `PLAINTEXT` and no credential (DD-469), and no
Atlas-side rule needs a second identity; a roster for a need nobody has named
is the abstraction DD-290 rejects. A first-class `broker.sasl.*` values tree:
the mechanism/username/password space is the broker's, not the chart's, and
`config` plus `secretRefs` covers it verbatim (CHT-117) without the chart
learning Kafka.

**Consequences.** `securityProtocol` stays an explicit value (CHT-121) — the
chart never infers `SASL_SSL` from the presence of the oauth flag pair, because
SSL-only brokers exist too. The oauth join renders `OAUTHBEARER` and the two
oauth settings and nothing else; the operator's SASL secret stays outside the
chart. A broker on a foreign issuer is served by turning `broker.oauth.enabled`
off and spelling the settings through `config`/`secretRefs` directly.

### DD-515. The required `broker.bootstrapServers` guard, and nothing else required

- **Status:** Proposed
- **Increment:** 13.2
- **Date:** 2026-11-12

**Decision.** Besides the shared guards (`schedule`, `catalogue.serverUrl`,
CHT-115), the Kafka chart requires exactly one more value:
`broker.bootstrapServers` (CHT-121). Every other Kafka setting keeps the app
default and renders only when a value names it.

**Reason.** The app default is the dev broker (`localhost:29092`, DD-469's
loopback pin) — inside a cluster that address is either nothing or the wrong
thing, and the KSC-01 failure it produces ("no bootstrap server answered
metadata") costs the broker's own timeout to surface. The render-time guard
fails an install before the first cron tick, which is CHT-02's rule for the one
setting whose default is a lie outside dev. The scan knobs' defaults (`*`,
`Kafka Broker`, 100 messages, five seconds) are honest in every environment,
so the chart passes them through untouched when set and stays silent otherwise
— the aux charts' `config` pattern, not a re-list of the settings module.

**Alternatives.** No guard (trust the operator): the KSC-01 error names the
bootstrap servers it tried, but by then the job has already minted a token and
burned a run; the guard costs one `required:` line. A required
`securityProtocol`: `PLAINTEXT` is a legitimate cluster-internal choice (the
dev broker itself runs it), and forcing an answer would push operators to
write `SSL` to satisfy the render, which is worse than the default.

**Consequences.** `tests/values.test.yaml` names a broker address
(`broker.test.svc:9092`), so CI's bare render carries the honest shape, and the
bare-render guard test pins the failure text. The 13.1 AGENTS.md removal notes
gain the chart directory, and the roadmap's 13.2 row closes with the broker
identity decision named here (DD-514).
