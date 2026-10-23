# 029\. What ships is signed, and its origin can be proven

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Every released part is signed at publication, carries its build provenance and contents inventory, and the release event ends by verifying the signature against a pinned identity. Anyone can prove who built an artifact, without trusting a copy.

## Decision

**Sign, attest, verify — at publication.** Every deployable part of a release is signed, its build origin recorded alongside it, and its inventory of contents attached — and **the release is not delivered until the signature has been verified against the identity that was supposed to produce it.** Anyone holding a released artifact can prove which pipeline run produced it and what it contains, without trusting a copy of the artifact or the word of whoever delivered it.

This decision was in force before it was written down: publication signs each artifact **without holding a secret of its own**, attaches provenance and contents as attestations, and ends with a verification step pinned to the exact identity allowed to have produced the release. This record exists because a mechanism this load-bearing should not be folklore.

## Context

A released artifact travels: pushed to a registry, pulled by environments, copied by pipelines, sometimes mirrored to places the organisation does not operate. At every hop the receiving side asks — *is this the thing we published, a copy, or something wearing its name?* — and an artifact with no answer is trusted only as far as the last person who touched it.

The system releases as one versioned whole ([019](<https://aureliusenterprise.github.io/phase3-3.3a-direct-classifications/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)), and the unit that ships is the unit that was validated ([010](<https://aureliusenterprise.github.io/phase3-3.3a-direct-classifications/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>)). Both properties depend on the artifact a consumer runs being the artifact the pipeline produced. **Without signatures and provenance, that identity is an assumption renewed at every pull; with them, it is a check.**

> [!NOTE]
>
> **An assumption renewed at every pull**
>
> Each hop — registry, mirror, cache, laptop — is a place an artifact can be swapped or mislabelled, and the puller has no memory of the pipeline. Without a signature the consumer re-trusts from scratch every time, silently; a verified signature and provenance statement turn that trust into a check the puller runs and records.

The supply chain the artifacts are built *from* is scanned and reported elsewhere ([015](<https://aureliusenterprise.github.io/phase3-3.3a-direct-classifications/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>) — the scanning half); this record covers the other half: the trustworthiness of what the organisation itself publishes. There is also a teaching obligation: the examples are how the organisation teaches ([009](<https://aureliusenterprise.github.io/phase3-3.3a-direct-classifications/architecture/adr/009-examples-must-run-and-be-tested/index.md>)), and publication without proof would teach that shipping ends at uploading bytes.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Every released part is covered.** Signing and origin proof apply to every deployable part automatically — triggered by being a part. |
| **R2** | **No secret to steal.** The proof of who published does not depend on a custodyed signing key that, leaked, lets anyone publish a trusted forgery. |
| **R3** | **Contents travel with the artifact.** What a part is built from is attached: "what is in what we ran?" is a lookup, not a reconstruction. |
| **R4** | **Verification is part of delivery.** The release event checks the signature against a pinned identity; delivery without verification is incomplete. |
| **R5** | **The check needs no insider.** A consumer with no special access can verify the signature and read the provenance and inventory. |
| **R6** | **Cheap to keep true.** A new deployable part gets the whole chain by convention, no per-part ceremony. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Publish unsigned | Simplest, and the norm for internal systems. R1's purpose: consumers cannot tell the published artifact from a forgery. R3: contents knowledge exists only in build logs that expire. R4 becomes impossible — there is nothing to verify. |
| A long-lived signing key | Classical and portable; R2 fails — the key becomes a crown jewel with a custody problem attached (the class of problem [028](<https://aureliusenterprise.github.io/phase3-3.3a-direct-classifications/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>) handles), and a leaked key forges trust retroactively, since old verification still accepts it. Keyless publication removes the asset instead of guarding it. |
| Sign only, no provenance | A signature answers "who" but not "how" or "what." R3, and R5 weakened: the consumer can confirm the publisher yet cannot say what the artifact contains without re-running the build. |
| Verify at the deployment site only | R4's spirit, not its letter: the release event would complete unverified. R5 in practice: verification rules known only to deployers are not usable by other consumers. |
| Do nothing (keep the mechanism undocumented) | Fails no requirement of the mechanism, and fails the organisation's: an unrecorded load-bearing decision is silently dropped by the next person who rewrites the pipeline, and its absence would not fail any check. |

## Tradeoffs

### What it buys

- Artifact identity survives every copy and mirror (R1, R5).
- There is no signing key to guard, leak, or rotate (R2).
- Incident response can ask what a running part contains and get an attached answer (R3).
- The release is self-certifying — delivery includes its own proof (R4).

### What it costs

- The proof depends on external parties — the identity issuer and the public record — so a release cannot be signed where they are unreachable: **a network dependency on the one step that must never be improvised.**
- Keyless signatures age differently from keys: long-term verification of old releases relies on those parties' history staying intact.
- Signature and provenance say *who* and *how*, not *whether it is safe* — a signed artifact is a truthful one, not a clean one, and the scanning question stays separate ([015](<https://aureliusenterprise.github.io/phase3-3.3a-direct-classifications/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)).

### Watch

- Signing runs only at release: an artifact built outside a release event is unsigned by design and must not be confused with a release.
- The verification identity is pinned to the release workflow itself — a change to that workflow's path or name is a change to the trust anchor and deserves the review weight of a security boundary.
- Promotion of a verified artifact into environments is where this record stops and [024](<https://aureliusenterprise.github.io/phase3-3.3a-direct-classifications/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>) begins.
- The contents inventory is assembled from two sources — the runtime image and the built application, merged into one document — for the one part whose build produces an application inventory; every other part's inventory comes from its image alone, and **a new kind of deployable part must name how its inventory is produced.**
- R5's no-insider check assumes the registry serves signatures, provenance, and inventories to anyone — a registry setting not yet declared anywhere beside it.

> [!NOTE]
>
> **Why keyless signing instead of an organisation key?**
>
> Because an organisation key is an asset that, leaked, forges trust retroactively — and guarding it is a custody problem ([028](<https://aureliusenterprise.github.io/phase3-3.3a-direct-classifications/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>)) that never ends. Keyless signing ties each signature to the pipeline identity that made it, so there is no key to steal and the forgery scenario has no object (R2).
