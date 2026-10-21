# 018\. Settings arrive at startup through one channel and fail loudly

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Every setting a part needs arrives through the environment it starts in and is validated once, at startup. A missing setting stops the start; nothing environment-specific is compiled into a part.

## Decision

**One channel: the start-up environment.** Addresses, ports, feature switches, credentials a part reads rather than owns — all arrive through the environment the part starts in, read and validated once, at startup. A part that has started has been told everything it needs and found it usable; **a missing or malformed setting stops the start** rather than surfacing at first use.

**Nothing environment-specific is compiled in.** The validated unit is reconfigured per environment by changing what it is told, never by rebuilding — which is what makes [010](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>) possible at all.

The channel is defined by **who supplies the settings** — the deployment — not by the delivery mechanism: a part rendered in a browser cannot read a server's environment, so its deployment places the settings beside it for pickup at run start, the same channel one step removed. Where a setting is a secret, this record governs how it arrives, not where it rests ([008](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/008-secrets-never-in-plaintext/index.md>)).

## Context

Parts are configured by different forces: an engineer changes a port to avoid a collision, the pipeline points a part at a throwaway service, a deployment points it at the real one. The settings belong to the part; **the values belong to the environment.** Every stack in the repository has its own historical habit for how a value reaches code — a compiled-in file per environment, a settings document, a value read deep in a request path — and each habit carries the same two costs.

- **The rebuild trap.** A setting fixed at build time makes a new environment a new build, quietly breaking the rule that the validated unit is the deployed unit: the deployment then carries a build no validation ever saw.
- **Late failure.** A setting read when first used fails at an ordinary-looking moment, far from the start that omitted it. A part that starts broken and fails at first use is worse to operate than one that refuses to start: the second is obvious, the first is a support ticket.

The team is small, multi-disciplinary, and moves between stacks — a different configuration habit per stack is a different habit to remember per stack, and the person debugging a misconfigured part at two in the afternoon does not care which ecosystem the part was written in.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One channel for every stack.** A setting reaches a part the same way in every technology — one mental model. |
| **R2** | **Reconfiguring never rebuilds.** A new environment changes only what the part is told; the validated unit is untouched. |
| **R3** | **Bad settings fail at startup.** A missing or malformed setting stops the start, naming the setting. |
| **R4** | **The running configuration is knowable.** What a part was told can be enumerated from outside — a fact, not a hypothesis. |
| **R5** | **Configuration and secrets stay distinct.** Ordinary settings may be committed dev defaults; secrets follow [008](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/008-secrets-never-in-plaintext/index.md>). |
| **R6** | **Cheap to keep true.** Adding a setting is a local edit to the part and its environment description. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Compile settings in per environment | R2 outright: every environment becomes its own build, taking the confidence transfer [010](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>) with it. R1 in spirit: the environment's values live in the build system, not with the environment. |
| A central configuration service | R1 and R4 elegantly; the arrangement the system runs under, no: every start waits on a service and a network ([006](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), so offline and unattended runs need a fallback — a local file — and the organisation now has two channels and has decided nothing. |
| Settings files beside the code, read at will | R2: the file travels inside the unit, so environment values ship inside the artifact. R3: a value read at first use fails at first use. R1: the mechanism is whatever each stack's library offers. |
| Framework defaults with silent fallbacks | R3 by design: a missing setting is indistinguishable from an intentional default, so a part pointed at the wrong place by omission looks healthy until it writes somewhere wrong. |
| Do nothing (each stack keeps its habit) | The current state, costs nothing. R1 by default: every stack answers the same question differently. R3 unevenly — some habits fail loudly and some don't, which is worse than all failing loudly. |

## Tradeoffs

### What it buys

- One question — "what was this part told at startup?" — answers configuration for every stack (R1, R4).
- Environments differ by values, never by builds, so the deployment rule holds (R2).
- A misconfigured part is loud at start instead of quiet at first use (R3); adding a setting is local work (R6).

### What it costs

- The environment description joins every run path, so **a typo in an environment file becomes the commonest incident** — the correct trade, but the incidents are real.
- Startup validation must be written deliberately for each part: a part that merely reads strings discovers its problems late.

### Watch

- The browser-rendered part fetches its settings at run start, which is the same channel one step removed — it needs the same startup-validation habit to be worth anything. The example now validates the fetched document at bootstrap and fails loudly (`apps/aurelius-atlas-frontend-example/src/app/config.ts`) — the deviation this record named is closed.
- The Node-RED example that baked its production settings into its unit left with its slice ([050](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)).
- The setting/secret line is enforced by the check [008](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/008-secrets-never-in-plaintext/index.md>) already owes. The startup message's quality is a standing obligation: the enumerated startup configuration is where an operational review looks first.

> [!NOTE]
>
> **Why not a configuration service — live settings, one source?**
>
> Because every start would then wait on it. The offline laptop and the unattended pipeline run need the part to start with what it was given ([006](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), so the service would need a local fallback — and a fallback file plus a service is two channels, which is the state this record exists to end.
