# 028\. Operational secret handling has a named owner and a rehearsed path

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Accepted 2026-10-19: the owner of secret handling is the maintainers team (the role that signs changes under [044](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)). The urgent-rotation, key-loss, and break-glass paths are written in [Operations Ownership](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/contributor-guide/operations-ownership/index.md>), with the first rehearsal scheduled there (R3). Membership on the accepted side already works: adding a person is a reviewed change to `.sops.yaml` plus automated re-encryption ([008](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/008-secrets-never-in-plaintext/index.md>)).

The bad cases of secret handling — urgent rotation, key loss, break-glass, removal — have a named owner and written, rehearsed paths. No secret is in a state where nobody knows who could rotate or recover it.

## Decision

**Handling is owned, written, rehearsed.** Rotating a secret, replacing a key, recovering a lost one, granting temporary access, removing a person: each is owned by a named role and follows a written path walked before it is needed.

The storage mechanism ([008](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/008-secrets-never-in-plaintext/index.md>)) decides how secrets are stored; this record decides **who operates it, on what rhythm, and what happens in the bad cases.** No secret, and no key, may be in a state where nobody knows who could rotate or recover it.

## Context

Secrets are encrypted to a named set of people and travel with the code as ciphertext. Membership is already a working process — adding a person is a reviewed change, the re-encryption that follows is automated. That is the easy direction: planned, reviewed, rehearsed by frequency.

**The hard cases had no owner:**

- A credential must be rotated *today* — suspected leak, departing person, vendor's forced expiry. Who acts, how fast, and how does the new value travel without a group chat?
- A person loses their key. Is the data recoverable, by whom, under whose judgement — or is the honest answer that it is not?
- An incident needs an outsider to read one secret right now. Is there a path, and does anyone find out afterwards?
- Do the keys themselves, and the automation's shared secret, ever get replaced — or only added to?

None of these are storage problems — the ciphertext is fine. They are organisational problems, and the record that drew the storage line named them as undecided. **The risk of leaving them undecided is specific: when the bad case arrives, the path gets invented under pressure, and an invented path around a security mechanism is how that mechanism gets bypassed for good.**

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **An owner exists.** One named role answers for rotation, keys, membership, and the bad cases — a written answer to "who would do this?" |
| **R2** | **Urgent rotation is a rehearsed path.** Replaced and redistributed quickly, by the owner, walked at least once before it was needed. |
| **R3** | **Loss has a declared answer.** Recovery with named custodians, or declared unrecoverable with the consequence owned. Silence is not a third option. |
| **R4** | **Temporary access is possible and visible.** A break-glass grant for a stated reason and period, leaving a trace the owner reviews. |
| **R5** | **Removal is effective, not cosmetic.** Future access stops; the record says what removal does *not* fix — what that person already copied. |
| **R6** | **Keys and automation secrets are themselves rotated.** A stated replacement cadence, or a stated reason not. |
| **R7** | **Cheap enough to survive.** Routine handling stays one reviewed change with automated follow-through; a path heavier than the mechanism it governs will be bypassed — that counts as this record failing. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Leave it undecided (status quo) | R1 by construction; everything else by postponement: the path will be invented during the incident that needed an owner. The current arrangement, and the reason this record exists. |
| A dedicated secrets platform | Answers R2, R4, R6 well as product features. Fails R7 for a system of this size today — a second platform to operate, with its own custody question about *its* root — and does not answer R3 or R5 by itself: custody and offboarding remain organisational decisions wearing new software. A legitimate destination, not an automatic one. |
| Ad-hoc handling by senior people | What happens today: whoever built the mechanism gets paged. R1: the role is a person, and people leave. R2: an unpractised path is slower and less safe. R4: informal access leaves no trace. |
| Strictest-possible policy | No break-glass, no escrow, no exceptions. R4: an incident that cannot grant access does not stop needing the secret — it stops using the mechanism. R3: declaring data unrecoverable is only honest if the business agreed to lose it. |
| Do nothing, recorded honestly | "Lost keys mean lost data; urgent rotation means whoever is available" is legitimate at this size — written with R1–R3 answered in the negative and the risk named, not left as silence. |

## Tradeoffs

### What it buys

- The bad cases stop being improvisations: rotation, loss, and break-glass have owners and paths before they are needed (R1–R4).
- Offboarding means something honest, including about what removal cannot undo (R5).
- The storage rule finally has its operational half: the two records together describe a usable mechanism, not a vault nobody can open in an emergency.

### What it costs

- A named owner is a single point unless the path is documented well enough to hand over: the record trades silence for a dependency on a role.
- Rehearsing urgent rotation is time spent pretending to have an incident.
- Every added control — trails, cadences, grants — is friction that, per R7, must stay lighter than the risk it manages, or people route around it.

### Watch

- The storage rule names this exact gap as its open end ([008](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/008-secrets-never-in-plaintext/index.md>)) — acceptance closes it here.
- Service identity assumes credentials are "issued, stored, and rotated by the arrangements the system runs" ([013](<https://aureliusenterprise.github.io/phase5-5.2b-glossary-terms/architecture/adr/013-services-prove-who-they-are-at-every-boundary/index.md>)) — this record is where those arrangements get their owner.
- The cadence numbers, custodian counts, and grant durations are named in the Operations Ownership guide, not deferred.
- The automation's own shared secret sits in R6 explicitly so it cannot stay in the unexamined category.

> [!NOTE]
>
> **Why rehearse paths for incidents that may never happen?**
>
> Because the first real run is the worst day to learn the procedure: a suspected leak is a Tuesday afternoon, not a project. A path walked once in calm conditions is minutes; an invented path under pressure is the mechanism getting bypassed for good (R2, R3).
