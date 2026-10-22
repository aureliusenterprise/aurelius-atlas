# 033\. Shipped artifacts carry a contents inventory

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Every deployable part carries a machine-readable inventory of its contents, attached at publication. "What is in what we ran?" is a lookup against the artifact, not a reconstruction from build logs.

## Decision

**The inventory ships with the part.** Every deployable part of a release carries a machine-readable inventory of what it contains, attached at publication in the same attestation step that carries its provenance ([029](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>)). Answering "what is in what we ran?" — at an incident, during a recall of a flawed dependency, for a customer question — is a lookup, not a reconstruction.

This decision was in force before it was written down: publication assembles each part's inventory and attaches it to the signed artifact, and the advisory scans over released parts ([015](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)) consume it. This record exists because **the inventory is what makes those scans answerable for a specific release**, and that role should not be implicit.

## Context

A release is a set of artifacts that travel ([019](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)), and the unit that ships is the unit that was validated ([010](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>)).

When a running part goes wrong, the first question is not who built it — that is provenance ([029](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>)) — **but what is inside it**: which dependencies, which versions, which layers. A part whose contents can only be re-derived by re-running an old build — if the build inputs still exist at all — turns an urgent question into slow reconstruction work.

The organisation already answers dependency questions continuously for the codebase ([015](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)); the inventory makes the same answer **specific to a released artifact** rather than to the current branch. Origin and contents stay separate decisions, each checkable on its own: an artifact can have perfect provenance and no inventory, and the gap should be visible as exactly that.

> [!NOTE]
>
> **Provenance and inventory: two answers, one attestation**
>
> Provenance ([029](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>)) answers *where this came from*; the inventory answers *what is inside it*. They ship attached together, at the same signing step, and are checked apart — a CVE sweep reads the inventory, a trust decision reads the signature. Conflating them is how a scanned branch gets mistaken for an answered release.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Every released part is covered.** An inventory is produced and attached for every deployable part, automatically. |
| **R2** | **The inventory travels with the artifact.** Attached at publication, so it survives every copy and mirror the artifact survives. |
| **R3** | **Machines can read it.** A standard machine-readable form: scanners, report builders, a customer's tooling — no cooperation needed. |
| **R4** | **Incident-time lookup.** Contents readable the moment the question is asked, however old the release, without re-running its build. |
| **R5** | **Cheap to keep true.** A new deployable part gets the inventory by convention, no ceremony. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Contents live only in build logs | R2 and R4: logs expire, are not attached, are written for humans. R3: no standard form. The arrangement this record replaces. |
| Reconstruct contents on demand | R4 under pressure: the worst moment to discover the old build inputs are gone — and it answers about today's toolchain, not what the release contained. |
| Ship the inventory as a side document | R2 in substance: a document beside the artifact is copied at some hops and not others, and nothing binds it to the artifact it describes. |
| Rely on the registry's metadata | The registry knows storage-level facts, not application contents, readable only through that registry. R3; the answer strands where the artifact was mirrored from. |
| Do nothing (keep the inventory implicit) | The state this record corrects. Fails the organisation's requirement: the next person to wire a new part would not know the inventory is required, and its absence would not fail any check. |

## Tradeoffs

### What it buys

- An incident question about a running part is answered by reading the artifact (R2, R4).
- Dependency advisories are answered per release, not per branch — what [015](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>) needs to be precise.
- Consumers can run their own tooling over what they received (R3).

### What it costs

- Assembling an inventory adds real time to every publication, and for the one part whose build already produces its own application inventory the two sources must be merged into one document — a maintained mechanism.
- An inventory is a claim about contents, not about safety: the judgement of whether any of it is a problem stays with the scanning record ([015](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)).

### Watch

- The two-source merge (runtime image plus built application) exists for the one part whose build produces an application inventory; **every other part's inventory comes from its image alone, and a new kind of deployable part must name how its inventory is produced** rather than assume the image covers it.
- Reading an inventory with no special access depends on the registry serving attached attestations to anyone — the same undeclared registry setting [029](<https://aureliusenterprise.github.io/feat-webapp-entity-details-spec/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>) waits on; confirm it before R2's no-insider reading is called met.
- A publication-time inventory is silent about contents added later at run time — configuration, downloads, mounted code — outside what any inventory can claim.
