# 039\. Data is protected where it travels and where it rests

- **Status:** Accepted
- **Date:** 2026-10-10
- **Deciders:** Aurelius Enterprise

## Decision

Data is protected in two places the system does not control by default: on the wire between parts, and at rest in the stores it keeps. Both protections are declared arrangements — named, configured, and checkable — not properties assumed from the environment. The mechanisms named below exist in the development arrangement and in CI/E2E: a local certificate authority issues per-service certificates (`nx certgen`, each project's `certs/`), every store and service-to-service path verifies them, and the one named relaxation is the plaintext Keycloak browser listener of the local development arrangement.

## Context

The system moves data between parts — a browser to a service, a service to a database, a producer through the event platform into storage — and keeps data in stores: the database, the event log, the operational signals. Today every one of those paths and stores is unprotected: traffic between parts travels in the clear, and data at rest sits exactly as written.

For the development arrangement this is deliberate and cheap: everything runs on one machine, the paths never leave it, and adding certificates to every connection would tax every run to protect a wire nobody can read. The development record ([006](<https://aureliusenterprise.github.io/chore-add-thijs-laptop-key/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)) is right to keep the local arrangement simple.

The problem is what the arrangement teaches and what it ships. The examples are the taught path: a part wired without protection in an example is wired without protection in the next system built from it. And the system is meant to be deployed into environments that keep business data, where both protections are usually not optional — carried between machines someone else operates, stored on media someone else owns. The secret-handling record ([008](<https://aureliusenterprise.github.io/chore-add-thijs-laptop-key/architecture/adr/008-secrets-never-in-plaintext/index.md>)) already decided that the credentials themselves never exist in the clear; the data those credentials protect has no equivalent decision.

The forces are asymmetric, and the record must hold both: protection has a real cost per run — certificates, trust, rotation, local tooling — and its absence has a cost that arrives all at once, in an environment where it was assumed. The decision to make is what the system guarantees about protection, where the guarantee may be relaxed, and how a relaxation stays visible.

## Requirements

Any acceptable arrangement must deliver:

- **R1 — The posture is stated per place.** For data in transit and data at rest, the record says what is protected, where protection is required, and where it is deliberately relaxed — a reader does not infer it from a localhost URL.
- **R2 — Protection is configured, not assumed.** Where protection is required, a mechanism enforces it and a reviewer can see the configuration; "the network is trusted" is not an arrangement.
- **R3 — The taught path matches the required path.** An example wired for a protected path shows the protected shape; where an example runs unprotected because it runs on one machine, the deviation is visible in the example, not folklore.
- **R4 — Relaxation is local and named.** The development arrangement may run unprotected, and says so; an unprotected path outside the development arrangement is a defect, not a default.
- **R5 — The check is cheap.** Whether a given path or store is protected can be answered from configuration, not by probing a running system.
- **R6 — New parts inherit the posture.** A new connection or store starts inside the declared arrangement rather than outside it.

## Alternatives

- **Protect everything, always, including local runs.** Honest and uniform. It fails the arrangement the whole-system record requires ([006](<https://aureliusenterprise.github.io/chore-add-thijs-laptop-key/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)) in its cheapest form: every run pays certificate setup to protect a wire that never leaves the machine, and the friction teaches people to disable the protection everywhere it matters.
- **Protect nothing; make the deployment add it.** It fails R3 and R6: the taught path stays unprotected, so the deployment inherits an unprotected shape and discovers the gap in production; it fails R2 because the deployment's protection is then nobody's configuration in this system.
- **Protect only the browser-facing edge.** Familiar, since browsers insist on it. It fails R1: the paths inside the system — service to store, part through the event platform — are exactly the ones a deployed environment crosses machine boundaries on, and they stay declared by silence.
- **Defer entirely (the status quo).** It fails R1 by leaving the posture to be guessed from localhost URLs, and R3 by teaching the unprotected shape as the normal one.
- **Do nothing.** Costs nothing today; every requirement above is failed by the same silence, which is the current state described as a choice.

## Tradeoffs

- **Positive:** the development arrangement keeps its cheap local paths with the relaxation written down instead of implied (R4); the taught path can show the protected shape without dragging certificates into every run (R3); and a deployment gets a declared starting point — which paths must be protected and where the switches live (R2, R5).
- **Negative:** two postures (required, deliberately relaxed) are more to state and review than one absolute rule, and the line is a standing review question; protection has upkeep the system does not have today — trust, rotation, expiry — and an expired certificate fails loudly at the worst moment; and declaring the development arrangement unprotected is itself an exposure a reader may copy if R4's visibility is not kept.
- **Neutral / follow-ups:** the credential rule it complements is already accepted ([008](<https://aureliusenterprise.github.io/chore-add-thijs-laptop-key/architecture/adr/008-secrets-never-in-plaintext/index.md>)) — that record protects the keys to the data; this one protects the data itself — and the identity of the parts on those paths is owned by the boundary-identity record ([013](<https://aureliusenterprise.github.io/chore-add-thijs-laptop-key/architecture/adr/013-services-prove-who-they-are-at-every-boundary/index.md>)), which decides who may speak, not whether the words are private. The placeholder page on data encryption under the architecture section is written from this record's answer; the operational signals' lifetime inside the protected stores is owned by the data-lifetime record ([025](<https://aureliusenterprise.github.io/chore-add-thijs-laptop-key/architecture/adr/025-data-has-a-stated-lifetime/index.md>)).

## Implementation

The mechanisms that make the posture checkable (R2, R5), all part of the spine:

- **Issuance.** Each project that serves or consumes TLS owns a `tls.json` listing the certificates it needs; `nx certgen` (custom plugin, `tools/plugins/tls.ts`) issues them from a local `mkcert` certificate authority into the project's own gitignored `certs/` directory — leaf keypairs, PKCS12 keystores, a JVM truststore where needed, and a `ca.pem` copy for pure clients. Generation is on demand: every `serve` or `e2e` target that mounts `certs/` declares a `certgen` dependency, so no prewarm step exists in the devcontainer or CI. Each project's `certgen` bootstraps the CA itself — mkcert owns it in its own store (outside the workspace) and `certgen` installs it into the system trust stores under an exclusive lock — and copies it into the project's `certs/`; `mkcert -uninstall` drops the CA again. Certificates are development material only — deployments bring their own.
- **Stores.** PostgreSQL runs with `ssl=on` and a TLS-only client authentication file; clients connect with `sslmode=verify-full` against the CA — and the unit-test database containers enforce the same posture with an ephemeral per-run CA, so TLS regressions fail the test suite. Kafka speaks TLS listeners only (SSL for infrastructure links, SASL\_SSL for application clients — the OAuth credentials on those sessions belong to the boundary-identity record ([013](<https://aureliusenterprise.github.io/chore-add-thijs-laptop-key/architecture/adr/013-services-prove-who-they-are-at-every-boundary/index.md>))), and Schema Registry and Kafka Connect serve and consume over HTTPS.
- **Services.** The FastAPI example serves HTTPS and verifies Keycloak and the database against the CA; the event-platform examples (Java producer, Node-RED, Lambda, JDBC sink connector) all speak TLS to broker, registry, and store. The OpenTelemetry collector's OTLP receivers are TLS, and every exporter in the arrangement trusts the CA.
- **The named relaxation (R4).** In the local development arrangement, Keycloak additionally serves a plaintext HTTP listener so the developer browser opens a familiar URL, and the browser-facing developer surfaces (SPA dev-server, Grafana, Kafka UI, Node-RED) stay plaintext. CI and E2E run every one of those paths over TLS and verify it — the deviation exists only on a developer machine, and each occurrence carries a comment naming this record.
