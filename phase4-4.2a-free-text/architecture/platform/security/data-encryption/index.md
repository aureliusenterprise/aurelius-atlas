# Data Encryption

This page answers where data is encrypted, from the data-protection record ([ADR 039](<https://aureliusenterprise.github.io/phase4-4.2a-free-text/architecture/adr/039-data-is-protected-where-it-travels-and-where-it-rests/index.md>)). Whether a path is protected is answered from configuration, not by probing a running system (that record's R5) — this page names the rule per path; where each knob lives is in the component's design documentation.

## In transit (production)

Every path data travels on inside the system is TLS with certificate verification, by role:

| Path | Rule |
| --- | --- |
| Browser → catalogue service | TLS with the deployment's own certificate; the E2E suite proves the served image over TLS |
| Service → search store | TLS only — plain endpoints are rejected by settings validation, before connecting |
| Service → relational store (examples only) | TLS with full verification; the catalogue spine has no relational store (ADR 047) |
| Service → signal collector | TLS; exporters trust the deployment's CA |
| Service → identity provider (token verify) | TLS issuer with CA trust in CI/E2E; the local browser path is the named relaxation below |

The knobs that make each row true — the setting names, verification flags, and trust material per component — live in the components' design documentation ([server](<https://aureliusenterprise.github.io/phase4-4.2a-free-text/api-reference/apps/aurelius-atlas-server/index.md>), [store](<https://aureliusenterprise.github.io/phase4-4.2a-free-text/api-reference/libs/python/aurelius-atlas-store-es/index.md>)).

## Proven in development and CI

The posture is tested, not just configured: the store library rejects plain endpoints; the dev store serves TLS only and is health-checked over it; the server's e2e runs the built image over HTTPS against that store; the template examples' relational-store containers start with TLS-only client authentication and connect with full verification. The per-command proofs are in the slice READMEs under `dev/` and each project's `e2e/`.

## At rest

Encryption at rest is owned by the stores and is not configured in this repository; deployments choose store-level encryption (disk or volume encryption). Development data is throwaway and carries no at-rest guarantee — the arrangement states this rather than implying it.

## Named relaxation (development arrangement only)

Plaintext exists only in the development arrangement, each occurrence deliberate: a browser-facing dev convenience listener on the identity provider, plaintext developer-only surfaces on a developer machine, and the E2E browser navigating with certificate verification skipped — every one of them recorded, with its reason, its out-of-band verification, and the commands around it, in [TLS Certificates](<https://aureliusenterprise.github.io/phase4-4.2a-free-text/contributor-guide/tls-certificates/#named-development-relaxations>).

> [!IMPORTANT]
>
> **A deployment replicates the posture, not the conveniences**
>
> Every production path is verified TLS. The plaintext listeners are development material with named reasons, commented in the repository at each occurrence, citing ADR 039 — they never travel to a deployment.
