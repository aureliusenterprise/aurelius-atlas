# 040\. The system raises its hand when it is broken

- **Status:** Proposed
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Acceptance trigger (swept 2026-10-19): increment 6.4 names the conditions, the destinations, and the silence trigger as alert rules in the observability stack; accepted in that pull request, recorded in the observability tree as it fills.

A condition that matters to the business has a named trigger and a named destination: the system notices and tells someone, without that person watching a screen. Collected signals nobody examines are a blind spot with extra steps.

## Decision

**Noticing is an arrangement, not a habit.** A condition that matters to the business has a named trigger and a named destination: the system notices it and tells someone, without that person watching a screen. **Signals collected but never examined are treated as a blind spot with extra steps**, and a condition nobody is told about is a defect of the arrangement, not bad luck.

## Context

The system already produces its own picture and gathers it in one place: traces, metrics, and logs from every part meet at a collection point the system runs itself ([016](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/016-the-system-observes-itself-internally/index.md>), [034](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/034-signals-meet-at-one-replaceable-collection-point/index.md>)). That arrangement made the picture available wherever the system runs. **It says nothing about anyone looking.**

Today nobody is told anything. The collection point holds the signals and a person reads them when they already suspect something — so the system's failures are discovered by whoever notices a symptom, usually a person outside the system, after the fact. The collection point's own storage can fill, a part can stop emitting and the picture simply goes quiet, **and neither event announces itself.**

The tension is between noticing and noise: **a trigger for everything trains people to ignore triggers, and an ignored trigger is worse than none because it carries a false promise.**

The tension is sharper here than in a typical deployment because the boundary rule ([016](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/016-the-system-observes-itself-internally/index.md>)) keeps the whole picture inside: there is no hosted service with alerting switched on by default, so noticing a failure is either a mechanism the organisation builds itself, or nobody does it.

And the availability posture ([037](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/037-the-system-itself-promises-nothing-about-staying-up/index.md>)) makes this record the system's only honest answer to "how would you know?" — **the system promises no prevention, so detection is what remains.**

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Conditions are named, not improvised.** The conditions worth announcing are written where a reviewer can see them; a trigger exists because someone chose it. |
| **R2** | **Every trigger has a destination.** Who is told and how; a trigger that reaches nobody is a log line with a siren on. |
| **R3** | **Silence is itself a condition.** A part that stops emitting, or a collection point that stops receiving, is a named trigger — the picture going quiet is an event. |
| **R4** | **Triggers stay worth reading.** A condition that fires without action is revised or removed; the arrangement is graded by whether its announcements still mean something. |
| **R5** | **The mechanism lives inside the boundary.** Noticing uses the signals the collection point already holds; nothing outside that the boundary forbids. |
| **R6** | **The path is exercised where validation runs.** A trigger can be demonstrated to fire locally or in the pipeline; a trigger nobody has seen fire is decoration. |
| **R7** | **Cheap to keep true.** A new part inherits the basic triggers — it is emitting, it is reachable — rather than arriving mute. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Dashboards only (status quo) | The picture exists for whoever looks. R2 and R3 by definition: nothing is announced, and the picture going quiet is precisely what a dashboard cannot show you. |
| Alert on everything measurable | R4: a stream nobody triages becomes wallpaper, and the wallpaper hides the one announcement that mattered. |
| Watch the platform, not the conditions | R1 for the business: a service can be healthy on every gauge and wrong in every answer — the conditions the business cares about are answers, not gauges. |
| Rely on users to report | The cheapest detector ever built. R2's purpose: the first informed person is the affected customer. R3: a system quiet enough to be broken quietly produces no complaints worth trusting. |
| A hosted alerting service | Mature and low-upkeep; R5: the raw material of noticing is the operational picture, and the boundary keeps that inside ([016](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/016-the-system-observes-itself-internally/index.md>)) — a hosted alert would ship the evidence out to announce it. |
| Do nothing | Free today; fails every requirement the way the status quo does, and leaves the availability posture ([037](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/037-the-system-itself-promises-nothing-about-staying-up/index.md>)) with no detection to stand on. |

## Tradeoffs

### What it buys

- Failures announce themselves instead of being excavated (R1, R2).
- The blind spot of a quiet part or a full store closes (R3).
- The boundary holds — noticing happens on the picture the system already keeps (R5).
- The incident path has something to start from, which the incident-response question needs before it can be answered at all.

### What it costs

- Triggers are upkeep: each one a condition to tune, a destination to keep current, a false alarm to learn from.
- The first honest set of triggers is wrong in both directions until it is exercised.
- Naming a destination for every trigger forces a question the organisation has not answered — who is told at what hour — which belongs to the incident record but cannot be dodged here.

### Watch

- This record is Proposed because the decision has not been made: the collection point holds the signals and no trigger reads them. The alerting placeholder page stays a heading until acceptance writes it from this answer.
- What a person does after the hand is raised is the incident record's question ([041](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/041-a-failure-of-the-running-system-has-an-owner-and-a-rehearsed-path/index.md>)), and that record leans on this one for the moment the incident begins.
- The thresholds and numbers belong to whoever accepts this record and **must be named at acceptance, not deferred.**
- A part that emits nothing is a deviation the observability record already names ([016](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/016-the-system-observes-itself-internally/index.md>)): an uninstrumented part cannot raise its hand, and this record inherits that blind spot until each part is instrumented or excused in writing.

> [!NOTE]
>
> **Why is silence a trigger — isn't quiet normal?**
>
> Quiet is normal; *unexplained* quiet is the failure. A part that stops emitting and a collection point that stops receiving make the picture look healthy-by-absence (R3) — the one failure mode where "nothing to report" is indistinguishable from "no way to report." A heartbeat turns that ambiguity into an event.
