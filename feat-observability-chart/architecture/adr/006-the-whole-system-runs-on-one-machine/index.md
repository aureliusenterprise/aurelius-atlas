# 006\. The whole system runs on one machine

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

Every application, service, and dependency runs on the machine of the person doing the work — brought up by automation, the same arrangement the pipeline validates on every change. The rule constrains what may enter: a dependency that exists only as a hosted service needs a local equivalent first.

## Decision

**One machine holds the whole system.** The machine of the person doing the work runs every application, every service, and the infrastructure between them, brought up by automation rather than by procedure.

**The pipeline validates the same arrangement.** What the pipeline proves on every change is what a person can bring up on demand — a green pipeline and a working local run are claims about the same thing.

**The rule constrains what may enter, not just where it runs.** A dependency that exists only as a service elsewhere needs a local equivalent before the system may depend on it.

## Context

The system's behaviour lives in the interactions between parts, not inside any one part, so defects surface wherever the whole system runs. Two candidates: infrastructure the organisation operates (scale, realism) and the engineer's machine (the whole system in front of the person who must understand it).

What either place is worth depends on how often the system runs there, and frequency follows cost. Validation that is expensive to run happens rarely; validation that happens rarely lags the code it should validate — the gap is found later, by someone else, at higher cost.

> [!NOTE]
>
> **One machine sounds like a toy — why is it a requirement?**
>
> It is not a claim about scale; production runs where the deployment puts it. The requirement is about frequency: the whole system must run in front of the person changing it, on every change, so the pipeline's green and the laptop's run are claims about the same arrangement. The rule spends its force on admission: a hosted-only dependency needs a local equivalent first.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The investigator reproduces the defect.** Whole, quickly, repeatably — no operated infrastructure to keep available. |
| **R2** | **Validation covers the parts working together.** Every change, unattended — not part by part, not waiting for a person. |
| **R3** | **Work needs no operated infrastructure.** No reachable services, no network, no provisioned accounts. |
| **R4** | **Running it is an everyday act.** Bring-up, work, teardown in minutes. Hours means the premise has failed. |
| **R5** | **Cheap to keep true.** Adding a service is a local edit to the environment definition, not a change request. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Organisation-operated development environment | R1: reproducing means investigating through the platform — its state, availability, access. R4: the everyday loop queues behind shared infrastructure. |
| Apps local, infrastructure cloud-hosted | R3 outright: every loop reaches services its owner doesn't control, needs network and accounts. R1: reproduce against someone else's services. |
| One orchestration everywhere | R3: the organisation now operates a platform beside the system. R4: the loop waits on a cluster one app doesn't need. R5: adding a service changes cluster definitions. |
| Validation in the pipeline only | R1: a failure nobody can reproduce off-platform is a second-class defect, debuggable only by platform-access holders. |
| Do nothing (parts run wherever they happen to) | R2 by default: the system runs as a whole nowhere until someone assembles it by hand. R4: every run is a planned assembly; every machine accumulates its own environment. |

## Tradeoffs

### What it buys

- A production incident reproduces on a laptop, no access provisioning.
- Everyday work runs offline, with no accounts and no access requests.
- The pipeline and the local run prove the same arrangement — no translation gap.

### What it costs

- The rule constrains what may enter: every part must be startable by automation on one machine, so a hosted-only dependency needs a local stand-in — and every stand-in is a maintained artifact ([012](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/012-validation-runs-against-real-services/index.md>)).
- Validating the full stack unattended costs real minutes and real money per run.
- Confidence stops at the environment boundary; [010](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>) names its exceptions.

### Watch

- Every application needs a run target that brings up what a run needs — the obligation [005](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/005-dev-infra-starts-with-the-app/index.md>) places on each app.
- The cost of validating on every change is bounded by validating the parts a change can reach, with the full arrangement reserved for unbounded reach — where that line sits is a pipeline decision this record does not make.
