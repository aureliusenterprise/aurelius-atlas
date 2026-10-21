# 007\. One shared identity provider serves every authenticated surface

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

People exist in exactly one place: a shared identity provider. Every surface that authenticates a human delegates to it — no surface holds accounts, credentials, or a sign-in flow. The provider runs wherever the system runs, so the authenticated path is exercised everywhere the system is validated.

## Decision

**The provider is the only place people exist.** Every surface that authenticates a human — screens, the APIs behind them, operational tooling — delegates: the provider decides who a person is and whether they are admitted now; surfaces act only on what the provider has issued.

**Surfaces stay thin:** no user accounts, no stored credentials, no sign-in flow — they verify tokens against the provider.

**The provider is part of the system,** not a service beside it: it runs on an engineer's machine and in the pipeline, so the authenticated path is exercised everywhere the system is validated ([006](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)).

## Context

People touch the system in several places — the screens where work is entered, the APIs behind them, the tooling that operates it. Each must know who is acting, and left to itself each keeps its own list of people.

- **People join, change roles, and leave.** When a person leaves, the business must stop recognising them everywhere at once. With identity per surface, revocation is a checklist whose completeness depends on whoever carries it out.
- **Access is audited.** The auditor asks who could reach what, and when. One place answers directly; several places require reconciling records by hand.
- **Admission is code that has to run to be trusted.** A sign-in path that only exists in production is a path no earlier run has exercised — and identity code carries the least tolerance for unexercised paths.

> [!NOTE]
>
> **Why not per-app auth?**
>
> Each bullet above is the answer: leaving a person is a checklist across surfaces, an audit becomes reconciliation by hand, and every app's sign-in flow is identity code that runs only in production. One provider exercised everywhere the system is validated replaces all three with one path that is never unexercised.

The decision is where "who is this person, and are they in?" lives, and who may answer it.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One answer about people.** One authoritative statement of who is admitted; no surface keeps its own list. |
| **R2** | **Revocation is one action.** Ending access at the provider ends it everywhere, on the next request — not the next release. |
| **R3** | **Surfaces stay thin.** No credentials stored, no tokens issued, no sign-in flow. Security code is written, reviewed, patched once. |
| **R4** | **Identity runs where validation runs.** The provider runs locally and in CI ([006](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), so authenticated paths are exercised in every validation. |
| **R5** | **The provider is replaceable.** Surfaces integrate through a standard interface. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Per-surface identity | R1: as many answers about people as surfaces. R2: revocation is a tour of every surface, complete when someone remembers every stop. R3: every surface writes its own password and session handling — every one a breach site. |
| The cloud platform's identity service | R4: the everyday loop and every unattended run reach a service behind a cloud account and a network — the authenticated path can't run offline ([006](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)). |
| A home-grown auth service | R5: the interface is whatever the first surface needed, so replacing it is a rewrite; the credential code is permanently the organisation's own audit surface. |
| Do nothing (surfaces unauthenticated until needed) | R1 by default: the first surface needing auth invents what the next inherits. R4: admission is exercised for the first time in production — where identity bugs are least affordable. |

## Tradeoffs

### What it buys

- Revocation is one action with immediate effect (R2).
- Credential and session code exists once, reviewed once, patched once (R3).
- The authenticated path runs on every machine and pipeline: auth regressions fail a build, not a user (R4).
- Surfaces speak a standard interface — the provider is replaceable (R5).

### What it costs

- The provider is critical infrastructure: while it is down, every authenticated surface is down — it is the business system's front door.
- The local environment carries one more service to start, version, and keep current.
- Identity is where compliance looks hardest: where the provider stores user data, and who administers it, is constrained by policy, not preference.

### Watch

- The current implementation is a self-hosted provider speaking OIDC, with the application registered as a public client in a realm of its own.
- This record covers people only. Services that move data and calls between surfaces — streaming paths, service-to-service calls — are not people: their identity is a separate decision ([013](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/adr/013-services-prove-who-they-are-at-every-boundary/index.md>)).
