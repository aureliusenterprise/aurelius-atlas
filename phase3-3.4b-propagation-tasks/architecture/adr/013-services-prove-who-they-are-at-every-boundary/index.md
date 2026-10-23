# 013\. Services prove who they are at every boundary

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Every call between two parts is authenticated in both directions: the credential says which service is calling, and an unauthenticated boundary is a defect, not a default. Machine identity is separate from human identity.

## Decision

**Every boundary carries a verdict.** Each call between two parts — a service to a database, one service to another — presents a credential the other side verifies; a rejected caller is turned away at the boundary, not trusted inside it.

**Machine identity is separate from human identity.** People are admitted by the shared identity provider ([007](<https://aureliusenterprise.github.io/phase3-3.4b-propagation-tasks/architecture/adr/007-one-shared-identity-provider/index.md>)); services by credentials issued to services. The rule is the same everywhere: the receiving side acts on **what the credential says**, not on which network the call arrived from.

**Credentials are part of the system, not a service beside it.** Issued, stored, and rotated by the arrangements the system already runs locally and in the pipeline, so the authenticated path is exercised wherever the system is validated.

## Context

The system is parts talking to parts, and each conversation crosses a boundary where one side decides whether to trust the other. When that decision is skipped, trust defaults to **location**: anything on the inside network is a colleague. That breaks in the ways that cost most:

- **Blast radius:** a compromised part reaches everything its neighbours trusted.
- **Misconfiguration:** a deployment joins a conversation it never belonged to.
- **Attribution:** the audit trail says "something inside" acted, not which service — and for regulated data, "who moved this record" must name a service the way it names a person.

Services are not people: no password to remember, no interactive sign-in, created and destroyed by automation, credential arriving by the same path as configuration. Bolting human admission onto services ends with service credentials in people's hands or people's credentials embedded in services — one failure with two faces: the audit trail can no longer say who acted.

> [!NOTE]
>
> **Machine identity and human identity — which is which?**
>
> Two questions with two answers: *who is this person* belongs to the shared provider ([007](<https://aureliusenterprise.github.io/phase3-3.4b-propagation-tasks/architecture/adr/007-one-shared-identity-provider/index.md>)), *which service is calling* belongs to credentials issued to services, verified at the boundary they arrive at. The line is what keeps a person's token out of a service and a service's key out of a laptop — and keeps "who acted" answerable in both registers.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Every boundary has a verdict.** Both directions authenticated; a rejected caller is turned away at the boundary. |
| **R2** | **The audit trail names the caller.** A record says which service acted, not which network it came from. |
| **R3** | **Machine identity is not human identity.** Service credentials belong to services; revoking one touches no person. |
| **R4** | **Credentials travel with delivery.** Same configuration path as everything else; a fresh deployment is authenticated without a person. |
| **R5** | **The authenticated path runs where validation runs.** Local and unattended runs exercise it, not a more trusting variant. |
| **R6** | **Revocation is an edit.** Retiring a service changes a stated set, not a hunt for copies of a shared value. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Network location as identity | R1: there is no verdict to make. R2: the trail records an address. R6: "revoking" means re-wiring reachability, and any second path revokes nothing. |
| One shared secret for everything | R1 thinly, R2 not at all — every caller looks identical. R6: revoking one caller means replacing the secret everywhere at once, which is never done. |
| Human identity for services | R3 by construction: the credential belongs to a person, so their departure revokes the service, and machine actions are attributed to them. |
| Authenticate production only | R5: the authenticated path exists only where identity failures are least affordable and least exercised — the same argument that puts human identity in every local run ([007](<https://aureliusenterprise.github.io/phase3-3.4b-propagation-tasks/architecture/adr/007-one-shared-identity-provider/index.md>)). |
| Do nothing (boundaries close when remembered) | R1 by default: every boundary is open and nobody knows which. R2 by default: unauthenticated conversations leave nothing to audit. |

## Tradeoffs

### What it buys

- A compromised part reaches only what its own credential allows (R1).
- The trail names the calling service for machine actions as it names the person for human ones (R2).
- Retiring a service is an edit to a stated set (R6); deployments are authenticated with no person in the loop (R4).

### What it costs

- Every boundary gains a credential to issue, deliver, and rotate — real upkeep the open arrangement never paid.
- Local and pipeline environments run the authenticated path too, so bring-up carries credential setup an open cluster avoids.
- A wrong credential breaks a deployment loudly, where the open arrangement failed with no signal at all.

### Watch

- The credential format per boundary (identity provider, platform, or deployment) is a follow-up per service, not settled here.
- A service credential is a secret and rests where the secrets record says ([008](<https://aureliusenterprise.github.io/phase3-3.4b-propagation-tasks/architecture/adr/008-secrets-never-in-plaintext/index.md>)); who owns its rotation is the question a proposed record takes up ([028](<https://aureliusenterprise.github.io/phase3-3.4b-propagation-tasks/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>)).

## Implementation

**Demonstrated, then removed with the slice.** The rule was proven end-to-end on the development event platform, which at acceptance ran unauthenticated — a defect by this record's definition. The proof, before the slice left ([050](<https://aureliusenterprise.github.io/phase3-3.4b-propagation-tasks/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)):

- The local Kafka cluster was closed to anonymous callers: token callers arrive with OAuth 2.0 bearer tokens (SASL/OAUTHBEARER over TLS) from a dedicated `kafka` realm, each a distinct confidential client so the broker's session log names the caller (R1, R2, R3, R6).
- Library exceptions arrive with per-service client certificates under mutual TLS.
- Every E2E suite authenticates over TLS (R5).

**The rule stands** and now governs the boundaries the catalogue keeps: the server to its search store, its identity provider, and its HTTP API. Transport protection belongs to the data-protection record ([039](<https://aureliusenterprise.github.io/phase3-3.4b-propagation-tasks/architecture/adr/039-data-is-protected-where-it-travels-and-where-it-rests/index.md>)); this record covers the credential presented once the channel is open.
