# 031\. Language and runtime versions have a declared support window

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Accepted 2026-10-19: the window is declared in [Runtime Windows](<https://aureliusenterprise.github.io/phase4-4.1b-classification-search/contributor-guide/development-environment/#runtime-windows>) — one answer per runtime, the pin files named, major bumps by reviewed change of the maintainers team. R2 was closed in the same sweep: the dev container pinned Node to the moving `lts` tag while the dashboard build pinned 24; both now pin 24.

For every runtime the system runs on, the organisation declares a support window, and every place a version is written agrees with it. A major-version move is a planned, recorded act — never something that happens by accident because one machine upgraded first.

## Decision

**A window per runtime, written down.** For every language and runtime, the organisation declares the versions it undertakes to build, test, and keep working — a floor, a ceiling, an owner for bumps. **Every place a version is written agrees with that declaration**, and a disagreement is caught, not discovered.

**A major move is planned work.** Moving a runtime's major version is a scheduled, recorded act with an owner and an end date for the old version — never a surprise delivered by an upgrade or an image refresh.

## Context

The system spans several languages, and **each version is a business fact, not a technicality**: it determines which libraries can be used, which security fixes arrive, what a joiner installs, and how long before the organisation runs something the ecosystem stopped maintaining. A runtime past end of support is a compliance conversation and an emergency upgrade, in that order.

Because the whole system releases as one versioned whole ([019](<https://aureliusenterprise.github.io/phase4-4.1b-classification-search/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)), a runtime version is a property of the system, not of a part — which means it needs one answer.

It had several: the same runtime's version appears in the build definition, the development environment, the shipped image, and the compiler configuration, **kept by nobody in step** — the development environment asked for the Node "lts" release while the build and image pinned a major, tools were pinned to "latest", and two compiler targets disagreed. Nothing caught the disagreement, because nothing stated what the answer was supposed to be.

Two neighbouring records bound this one: keeping dependencies up to date ([020](<https://aureliusenterprise.github.io/phase4-4.1b-classification-search/architecture/adr/020-dependencies-stay-current-by-default/index.md>)) covers the libraries *inside* a runtime; this record speaks to the runtime itself, which that record does not — **a language major version is not a dependency bump, because it can change what correct code is.** Where they meet — a runtime minor release is arguably a dependency update — the owner of that bump is named in the window.

The development environment is a versioned artifact ([011](<https://aureliusenterprise.github.io/phase4-4.1b-classification-search/architecture/adr/011-the-development-environment-is-a-versioned-artifact/index.md>)) — that record decides the environment is reproducible; this one decides what version it is allowed to contain, and who says so.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The window is written.** The supported range per runtime, readable without inspecting five configuration files. |
| **R2** | **One answer everywhere.** Every place a version is declared agrees with the window; a disagreement is caught by a check, not an incident. |
| **R3** | **Nothing floats.** No runtime, tool, or compiler target unpinned — an unpinned thing changes without a decision. |
| **R4** | **Bumps are planned.** Scheduled work with an owner and an end date for the old version. |
| **R5** | **Support status is visible.** How close each runtime is to losing upstream maintenance, without research. |
| **R6** | **Cheap for the routine case.** A patch or minor inside the window is automatic; only a window change costs a decision. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Pins without a window (status quo) | R1: the window exists only as an archaeology result. R2: the disagreement observed today. R3 wherever a tool is pinned to "latest". |
| Track the newest of everything | R4: "always newest" is a policy of never planning, and every major becomes an emergency when it lands. It quietly narrows where the system can run — consumers and hosts on older supported versions excluded by choice nobody made. |
| Freeze with long windows | R5's purpose: a long window with no plan for its end is how an organisation ends up two majors behind with a deadline. It collides with dependency currency ([020](<https://aureliusenterprise.github.io/phase4-4.1b-classification-search/architecture/adr/020-dependencies-stay-current-by-default/index.md>)), which commits to staying near the front. |
| Let each part choose its version | R1 and R2 at the level that matters: as many answers as parts, and a release that can no longer be described in one version number. |
| Do nothing | Free today; the observed drift continues, and the first end-of-support date arrives as news. It fails every requirement by leaving the window unwritten — which describes today's drift as if it were a choice. |

## Tradeoffs

### What it buys

- "What version do we support?" has one written answer (R1), and every configuration file is accountable to it (R2).
- Runtime upgrades become scheduled work with a visible deadline (R4).
- End-of-support risk stops being discovered by an auditor (R5).

### What it costs

- A declared window is a commitment that costs effort at its edges: supporting the floor of a window is real work a single pinned version would dodge.
- Reconciling the places versions are written touches build, environment, image, and compiler configuration together — exactly the cross-stack coordination this system keeps minimal.
- A window written but not reviewed is worse than none, because people trust it.

### Watch

- The remaining pin drifts are the first items the window check must catch: the base TypeScript target (`es2015` in `tsconfig.base.json`) against the per-project targets (`es2022`), and the dev container's SOPS feature pinned to `latest` (R3).
- The window is revisited in the cadence review ([015](<https://aureliusenterprise.github.io/phase4-4.1b-classification-search/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>)) — no separate review is invented for it.
- The window's numbers — floor, ceiling, and how long an old major stays alive — are named in [Runtime Windows](<https://aureliusenterprise.github.io/phase4-4.1b-classification-search/contributor-guide/development-environment/#runtime-windows>), not deferred.

> [!NOTE]
>
> **Why a window instead of one pinned version?**
>
> One pin answers "what do we run," not "what do we support" (R1). Consumers, hosts, and onboarding need the range; a lone pin gives them a single point and hides the edges. The window also turns the floor into a commitment with a plan (R4) — a lone pin quietly ages into an end-of-support surprise.
