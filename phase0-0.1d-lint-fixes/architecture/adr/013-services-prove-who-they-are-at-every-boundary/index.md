# 013\. Services prove who they are at every boundary

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

## Decision

Every call between two parts of the system — a service to a database, a consumer to the event platform, one service to another — is authenticated: each side presents a credential the other can verify, and an unauthenticated boundary is a defect, not a default.

Machine identity is separate from human identity. People are admitted by the shared identity provider ([007](<https://aureliusenterprise.github.io/phase0-0.1d-lint-fixes/architecture/adr/007-one-shared-identity-provider/index.md>)); services are admitted by credentials issued to services, with the same rule applied everywhere: the credential says which service is calling, and the receiving side acts on what the credential says rather than on which network it arrived from.

The credentials are part of the system, not a service beside it: they are issued, stored, and rotated by the same arrangements the system already runs locally and in the pipeline, so the authenticated path is exercised wherever the system is validated.

## Context

The system is assembled from parts that talk to each other: services read and write storage, consumers produce and consume on a shared event platform, tooling reaches the same places people do. Each conversation crosses a boundary at which one side decides whether to trust the other.

When that decision is skipped, trust defaults to location: anything on the inside network, or inside the same container cluster, is treated as a colleague. That assumption breaks in the ways that cost the business most — a compromised part reaches everything its neighbours trusted, a misconfigured deployment joins a conversation it never belonged to, and the audit trail cannot say which service acted, only that "something inside" did. For regulated data, "who moved this record" has to name a service the way it has to name a person.

Services are not people, and the arrangement for admitting them differs: a service has no password to remember and no interactive sign-in, it is created and destroyed by automation, and its credential must reach it through the same delivery path as its configuration. Bolting human admission onto services tends to end with service credentials in the hands of people, or people's credentials embedded in services — both are the same failure: the audit trail can no longer say who acted.

The decision to make is how a part proves which service it is, and what an unauthenticated boundary means.

## Requirements

Any acceptable arrangement must deliver:

- **R1 — Every boundary has a verdict.** Each conversation between parts is authenticated in both directions, and a rejected caller is turned away at the boundary rather than trusted inside it.
- **R2 — The audit trail names the caller.** A record of an action says which service performed it, not merely which network it came from.
- **R3 — Machine identity is not human identity.** Service credentials are issued to services, are not shared with or derived from people's accounts, and revoking one service does not touch any person's access.
- **R4 — Credentials travel with delivery.** A service receives its credential through the same configuration path as everything else it needs, so a fresh deployment is authenticated without a person intervening.
- **R5 — The authenticated path runs where validation runs.** Local runs and unattended runs exercise the authenticated path, not a more trusting variant of it.
- **R6 — Revocation is an edit.** Retiring a service or responding to a leaked credential is a deliberate change to a stated set, not a hunt for copies of a shared value.

## Alternatives

- **Network location as identity.** Anything reachable on the inside is a colleague; boundaries carry no credentials. It fails R1 outright — there is no verdict to make — and R2: the trail records an address, not a caller. It also fails R6: "revoking" a service means re-wiring reachability, and any second path to the network revokes nothing.
- **One shared secret for everything.** All parts present the same credential. It passes R1 thinly but fails R2 — every caller looks identical — and R6: revoking one caller means replacing the secret everywhere at once, which is operationally impossible, so it is never done.
- **Human identity for services.** Services sign in as people, or carry a person's credential. It fails R3 by construction: the credential belongs to a person, so their departure revokes the service, and the audit trail attributes machine actions to whoever's credential was embedded.
- **Authenticate production paths only.** Leave development and pipeline runs unauthenticated because "nothing real is there." It fails R5: the authenticated path then exists only in production, which is where identity failures are least affordable and least exercised — the same argument that puts human identity in every local run ([007](<https://aureliusenterprise.github.io/phase0-0.1d-lint-fixes/architecture/adr/007-one-shared-identity-provider/index.md>)).
- **Do nothing (each boundary authenticates when someone remembers).** Zero cost today. It fails R1 by default — every boundary is open until someone closes it, and nobody knows which ones are — and R2 by default, because unauthenticated conversations leave nothing to audit.

## Tradeoffs

- **Positive:** a compromised part reaches only what its own credential allows, not everything its neighbours trusted (R1); the audit trail names the calling service for machine actions as it names the person for human ones (R2); retiring a service is an edit to a stated set (R6); deployments are authenticated without a person in the loop (R4).
- **Negative:** every boundary gains a credential to issue, deliver, and rotate, which is real upkeep the open arrangement never paid; local and pipeline environments must run the authenticated path too, so bring-up carries credential setup that a shared open cluster avoids; and a wrong credential turns a working deployment into a broken one loudly, where the open arrangement failed quietly.
- **Neutral / follow-ups:** the development event platform currently runs unauthenticated, which this record defines as a defect (closed in 2026-10: the event platform now authenticates every client — see Implementation); the credential format per boundary (issued by the identity provider, by the platform itself, or by the deployment) is a follow-up per service, not settled here; and the line between a service credential and a secret follows the secrets record — a credential is a secret and rests where that record says secrets rest, while who owns its rotation is the question a proposed record takes up ([028](<https://aureliusenterprise.github.io/phase0-0.1d-lint-fixes/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>)).

## Implementation

The boundary this record left open — the development event platform — is now closed. The local Kafka cluster admits no anonymous producer or consumer. Callers that can present a service token arrive with OAuth 2.0 bearer tokens (SASL/OAUTHBEARER over TLS) issued by the shared identity provider ([007](<https://aureliusenterprise.github.io/phase0-0.1d-lint-fixes/architecture/adr/007-one-shared-identity-provider/index.md>)) from a dedicated `kafka` realm; the exception clients whose Kafka libraries cannot do OAUTHBEARER — Node-RED first among them — arrive instead with a per-service client certificate under mutual TLS:

- **The broker holds a verdict.** `dev/kafka` serves SASL\_SSL listeners whose validation points at the realm's JWKS endpoint and refuses tokens from any other issuer or audience — a caller without a valid service token is turned away at the boundary (R1).
- **Credentials name the service.** Each token caller — the Java producer, the Lambda, the JDBC sink connector, the E2E suites — is a distinct confidential client of the realm with its own secret, so the broker's session log names the calling service (R2, R3); retiring one is an edit to the realm definition (R6). Secrets rest encrypted with the project ([008](<https://aureliusenterprise.github.io/phase0-0.1d-lint-fixes/architecture/adr/008-secrets-never-in-plaintext/index.md>)) and reach the service through the same configuration path as its other settings (R4).
- **The authenticated path runs where validation runs.** Every E2E suite that touches Kafka over the token listeners authenticates against the running realm over TLS (R5), the certificate-path suites present their own client certificate, and unit tests cover the OAuth configuration branches beside the certificate ones.

Transport protection on those paths (certificates, trust) belongs to the data-protection record ([039](<https://aureliusenterprise.github.io/phase0-0.1d-lint-fixes/architecture/adr/039-data-is-protected-where-it-travels-and-where-it-rests/index.md>)); this record covers the credential presented once the channel is open. The platform's own infrastructure links that carry no service identity of their own (controller quorum, Schema Registry backing store) also stay on mutual TLS; there the certificate is the transport arrangement, while for the exception clients above it doubles as the service identity.
