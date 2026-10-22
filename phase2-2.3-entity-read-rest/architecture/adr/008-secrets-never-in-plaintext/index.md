# 008\. Real secrets are encrypted; only dev defaults are committed

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

Real secrets exist in the codebase only as ciphertext, encrypted to a named recipient list; plaintext files carry dev defaults only. The recipient list is the access list — changing it is an edit, not a hunt.

## Decision

**Plaintext never carries a real secret.** A secret the system needs is encrypted to a named set of recipients and committed as ciphertext; what the codebase carries in plaintext is dev defaults — values safe to publish.

**Access is the recipient list.** Who can read the secrets is exactly that list; changing the set of readers is an edit to it.

**Reading and writing is part of running, not a side trip.** Bring-up decrypts what a run needs ([005](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/005-dev-infra-starts-with-the-app/index.md>)); the loop never waits on a secret store ([006](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)). The ciphertext travels with the code, so cloning, forking, and caching are safe acts.

## Context

The system runs on secrets — database passwords, service tokens, signing keys — and between creation and use a secret rests somewhere. Where it rests, and who can read it there, is the decision.

- **The codebase's history is permanent and endlessly copied.** A committed file reaches everyone who ever clones, every pipeline cache, every fork, and is recalled from none of them. A real secret committed in plaintext is not a mistake to correct but a breach to remediate: rotate every credential, audit the exposure.
- **The readers are a small, named set** — the people who build and operate the system. So "who can read this secret?" is answered explicitly, by encrypting to named recipients, not implicitly by whoever holds a copy.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **History never carries plaintext.** A real secret enters as ciphertext; plaintext is never the default path. |
| **R2** | **The loop never waits on a secret service.** A full local run, no live store — no dependency re-entered side doors. |
| **R3** | **Access is a list, not a trail.** One explicit set; removing a person ends future access by editing the set. |
| **R4** | **One mechanism everywhere.** Machine, pipeline, deployment — no environment invents its own handling. |
| **R5** | **Cheap to keep true.** Adding a secret or a person is a small edit, not a standing project. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Cloud secret manager, nothing in the repository | R2: every loop and unattended run reaches a service behind a cloud account — the system stops being runnable offline ([006](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)). R4: the local loop needs a fallback, and the fallback is a plaintext file. |
| A vault per environment | R2 for the same reason. R4: the loop starts and configures a vault. R5: standing up, versioning, administering vaults is a standing project. |
| Trust the ignore list | R1: an ignore list is a wish, not a wall — one forced add, one renamed file, one tool committing what it was given, and the breach is permanent. R3: "who can read this" becomes "everyone who ever held a copy." |
| Do nothing (secrets handled as they come) | R1 by default: every password pasted into config or chat is a future remediation. R3 by default: access is whatever the copies say. |

## Tradeoffs

### What it buys

- The codebase can be cloned, forked, mirrored, cached — none of those acts is a breach (R1).
- Development stays fully offline-capable (R2).
- Who can read secrets is one list; revoking a person is an edit to it (R3).
- One mechanism serves machine, pipeline, and deployment (R4).

### What it costs

- The decryption key becomes the crown jewels: losing it locks the organisation out of its own secrets, leaking it decrypts the whole history. Key custody is a business process with named owners.
- Adding or removing a person re-encrypts every secret file — rotation is cheap but never free.
- The rule protects history only from the day it starts: secrets committed before it are still exposed and still need rotation.

### Watch

> [!WARNING]
>
> **Production rides the same mechanism — don't fight it**
>
> Production secrets are encrypted to a named set of people. Rotating a production credential quickly, or granting a break-glass reader, means touching that list; treating it as friction is how the mechanism gets bypassed. Operational secret handling beyond the list is the question [028](<https://aureliusenterprise.github.io/phase2-2.3-entity-read-rest/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>) takes up.

- Any plaintext configuration found carrying a real value moves into ciphertext rather than being argued about — which means the line between a dev default and a real secret needs a check that flags likely-real values before they reach history.
