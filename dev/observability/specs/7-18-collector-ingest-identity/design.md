# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-202. One issuer world: producers mint on the TLS listener, the collector validates both

- **Status:** Accepted
- **Increment:** 7.18
- **Date:** 2026-10-23

**Decision.** The per-service ingest leg standardizes on the Keycloak **TLS
listener**: every per-service producer — the three slice `metrics-puller`
sidecars, the Atlas server, and the 8.x aux APIs — mints its client-credentials
JWT from `https://keycloak.localhost:8443`, written as a **literal** in each
compose/`.env` (no `${VAR:-default}` indirection), with the mint leg pinned to
the slice's copy of the shared mkcert CA. The collector's `oidc` extension
drops its env-injected issuer (`OTEL_COLLECTOR_OIDC_ISSUER`/`_CA_FILE` are
removed from `dev/observability/docker-compose.yaml`) and lists **both**
listeners as `providers` in `config/otel-collector.yaml`: the TLS `:8443`
(CA-pinned via the existing `/dev-ca` mount) and the plaintext `:8080`, the
audience enforced per provider. The e2e suites' issuer-flip convention (the
conftest fixtures that set the four ingest env vars and re-run `up` on the
shared stacks) is deleted.

**Reason.** Keycloak stamps `iss` from the listener that served the mint, and
the collector's go-oidc verifier matches `iss` exactly. Each producer's mint
URL is baked into its container at creation, so the mint issuer is fixed per
container while the validator issuer was a per-`up` env: the dev defaults
(:8080) and the e2e flip (:8443) are two self-consistent worlds, and any mix
401s the per-service leg — OTLP is dropped silently and Prometheus starves.
ESD-06 was the first test to _observe_ it: the webapp e2e suite recreates the
shared collector with the :8443 issuer, and the store-es suite — started by
its own `up` chain with the dev-default puller — polled `count(exported_job=
"dev-elasticsearch")` against a collector rejecting the puller's :8080 tokens.
The failure is suite-order-dependent because the flip is a side effect of
execution order on shared stacks. Accepting both issuers makes the mixed
world unrepresentable (one realm, one signing key, two listener URLs — not
two trust domains); standardizing the mint on :8443 keeps every automated
producer in a single world, so the plaintext listener remains only what ADR
039 always meant it for: the human dev browser, which cannot enroll the
mkcert CA.

**Alternatives.** (a) Per-suite isolated telemetry stacks (unique compose
project/ports/network per suite): the honest isolation, but the shared-stack
design is deliberate (the `nx up` chain, fixed `:9090`, ESD/CIA probes that
query the machine's Prometheus) and the change is architectural, not
incremental. (b) A shared pytest plugin owning the flip: removes the
triplication, not the race — global env mutation stays load-bearing.
(c) The store-es conftest flipping the pair itself (the first fix tried):
order-independent, but it made the suite a third writer of shared
infrastructure state — the same disease with a bigger dose.

**Consequences.** The issuer story is one sentence: _mint at :8443, the
collector accepts both listeners._ No e2e suite can starve another's
telemetry; the CIA-07 mint fixtures, the slice pullers, and `nx serve` all
present the :8443 `iss`. The dev browser (plaintext :8080 tokens) keeps its
DD-194 attribution through the second provider. The collector trusts the
dev-only plaintext issuer's tokens by design — bounded: dev stacks, loopback
listeners, audience-gated, and the legacy leg is unchanged. The
`OTEL_INGEST_TOKEN_URL`/`OTEL_INGEST_CA_FILE` quartet retires from the slice
composes; the pullers' `restart: on-failure:15` (DD-195, issuer-shaped)
stays. `dev/observability` remains slice-agnostic.
