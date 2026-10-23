# 039\. Data is protected where it travels and where it rests

- **Status:** Accepted
- **Date:** 2026-10-10
- **Deciders:** Aurelius Enterprise

Data is protected on the wire between parts and at rest in the stores — both declared, configured, checkable arrangements. Protection is the default, and every relaxation of it is named.

## Decision

**Protection is a declared posture, in two places.** Data is protected on the wire between parts and at rest in the stores it keeps. Both are declared arrangements — named, configured, and checkable — **not properties assumed from the environment.**

The mechanisms below exist in the development arrangement and in CI/E2E: a local certificate authority issues per-service certificates (`nx certgen`, each project's `certs/`), every store and service-to-service path verifies them, and the one named relaxation is the plaintext Keycloak browser listener of the local development arrangement.

## Context

The system moves data between parts — a browser to a service, a service to its store — and keeps data in stores: the search store, the operational signals. **Protection has two costs, and they are asymmetric:** it costs real work per run — certificates, trust, rotation, local tooling — and its absence costs a lump sum that arrives all at once, in an environment where it was assumed.

For the development arrangement, unprotected local paths are deliberate and cheap: everything runs on one machine, the paths never leave it, and certificate tax on every run protects a wire nobody can read ([006](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>) is right to keep the local arrangement simple).

**The problem is what the arrangement teaches and what it ships.** The examples are the taught path ([009](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/009-examples-must-run-and-be-tested/index.md>)) — a part wired without protection in an example is wired without protection in the next system built from it. And the system is meant to be deployed into environments that keep business data, where both protections are usually not optional: carried between machines someone else operates, stored on media someone else owns.

The secrets record ([008](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/008-secrets-never-in-plaintext/index.md>)) already decided the credentials never exist in the clear; **the data those credentials protect had no equivalent decision.**

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The posture is stated per place.** What is protected, where required, where deliberately relaxed — never inferred from a localhost URL. |
| **R2** | **Protection is configured, not assumed.** Where required, a mechanism enforces it and a reviewer sees the configuration; "the network is trusted" is not an arrangement. |
| **R3** | **The taught path matches the required path.** An example shows the protected shape; an example running unprotected because it runs on one machine says so visibly. |
| **R4** | **Relaxation is local and named.** Development may run unprotected and says so; an unprotected path outside development is a defect, not a default. |
| **R5** | **The check is cheap.** Whether a path or store is protected is answered from configuration, not by probing a running system. |
| **R6** | **New parts inherit the posture.** A new connection or store starts inside the declared arrangement. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Protect everything, always, including local runs | The arrangement the whole-system record requires ([006](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)) in its cheapest form: every run pays certificate setup to protect a wire that never leaves the machine — and the friction teaches people to disable the protection everywhere it matters. |
| Protect nothing, let the deployment add it | R3 and R6: the taught path stays unprotected, so the deployment inherits an unprotected shape and discovers the gap in production. R2: the deployment's protection is then nobody's configuration in this system. |
| Protect only the browser-facing edge | Familiar, since browsers insist. R1: the paths inside the system — service to store — are exactly the ones a deployed environment crosses machine boundaries on, and they stay declared by silence. |
| Defer entirely (status quo) | R1: the posture is guessed from localhost URLs. R3: the unprotected shape is taught as the normal one. |
| Do nothing | Free today; every requirement failed by the same silence — the current state described as a choice. |

## Tradeoffs

### What it buys

- The development arrangement keeps its cheap local paths with the relaxation written down instead of implied (R4).
- The taught path shows the protected shape without dragging certificates into every run (R3).
- A deployment gets a declared starting point: which paths must be protected and where the switches live (R2, R5).

### What it costs

- Two postures (required, deliberately relaxed) are more to state and review than one absolute rule, and the line is a standing review question.
- Protection has upkeep the system did not have — trust, rotation, expiry — and **an expired certificate fails loudly at the worst moment.**
- Declaring development unprotected is itself an exposure a reader may copy if R4's visibility is not kept.

### Watch

- The credential rule it complements is accepted ([008](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/008-secrets-never-in-plaintext/index.md>)) — that record protects the keys to the data; this one protects the data itself. The identity of the parts on those paths is [013](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/013-services-prove-who-they-are-at-every-boundary/index.md>)'s: who may speak, not whether the words are private.
- The operational signals' lifetime inside the protected stores is owned by [025](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/025-data-has-a-stated-lifetime/index.md>).
- The event-platform paths this record's first implementation listed (broker, registry, connectors) left with the streaming slice ([050](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)). The posture and its mechanisms stand for the paths the catalogue keeps, below.

## Implementation

The mechanisms that make the posture checkable (R2, R5), all part of the spine:

- **Issuance.** Each project that serves or consumes TLS owns a `tls.json` listing the certificates it needs. `nx certgen` (custom plugin, `tools/plugins/tls.ts`) issues them from a local `mkcert` certificate authority into the project's gitignored `certs/` — leaf keypairs, PKCS12 keystores, a JVM truststore where needed, a `ca.pem` copy for pure clients. Generation is on demand: every `serve`/`e2e` target that mounts `certs/` declares a `certgen` dependency. `mkcert -uninstall` drops the CA. **Certificates are development material only — deployments bring their own.**
- **Stores.** PostgreSQL runs with `ssl=on` and a TLS-only client authentication file; clients connect `sslmode=verify-full` against the CA — and unit-test database containers enforce the same posture with an ephemeral per-run CA, so TLS regressions fail the test suite. Elasticsearch — the system of record ([047](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)) — serves its REST layer over TLS with certificate verification against the CA.
- **Services.** The FastAPI example serves HTTPS and verifies Keycloak and the store against the CA. The OpenTelemetry collector's OTLP receivers are TLS, and every exporter in the arrangement trusts the CA.
- **The named relaxation (R4).** In the local development arrangement, Keycloak additionally serves a plaintext HTTP listener so the developer browser opens a familiar URL, and browser-facing developer surfaces (the SPA dev-server, Grafana) stay plaintext. **CI and E2E run every one of those paths over TLS and verify it** — the deviation exists only on a developer machine, and each occurrence carries a comment naming this record.

> [!NOTE]
>
> **Why is a plaintext listener a named exception and not a defect?**
>
> Because it is a developer convenience on a wire that never leaves the machine (R4), and R1's rule is that such relaxations are written down, not implied. The line R4 guards: the same plaintext path outside the development arrangement — the localhost URL copied into a deployment — is a defect, which is why each occurrence carries a comment naming this record.
