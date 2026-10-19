# 005\. Development infrastructure starts with the app that needs it

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

An application's development infrastructure starts when the application runs and stops with the run. No always-on shared environment; no app depends on infrastructure someone else started. One command, from fresh checkout to working system.

## Decision

**The run brings its own infrastructure.** An application's database, identity provider, event platform, and observability backends start when the application is run and stop with that run. No application depends on infrastructure somebody else started.

**The run command is the entry point:** it brings up the services the application declares, then the application. From a fresh checkout, one command per application is enough to see the system work.

This record settles who owns development infrastructure and when it exists; which machine the whole system runs on is decided separately ([006](<https://aureliusenterprise.github.io/phase1-1.6-types-rest/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)).

> [!NOTE]
>
> **Two apps need the same Keycloak — do I start it twice?**
>
> Per run, yes. The isolation is the point: a shared always-on provider is the named alternative, and it fails on shared state — one person's sign-in changes another's results. The cost is real (the provider starts per run) and bought deliberately; a run's infrastructure is declared by the app that uses it and dies with the run.

## Context

The system is several small applications, each depending on services — a database, an identity provider, metrics — so every developer faces the same question before feature work: how do I get a running system in front of me? Two conventional answers, both with costs:

- **A shared always-on environment:** front-loads the work with access requests and setup instructions, and shares state — what one person changes is visible in everyone else's results.
- **A documented manual setup:** puts the system in front of the developer only as reliably as the list is current, and lists go stale without anyone noticing.

Both share a slower cost: the cost of trying the system decides how often it is run, and a system that is rarely run is rarely observed. Where the codebase's examples are its demonstration, an example nobody runs is an example nobody can vouch for.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **One command to a running system.** From a fresh checkout; no manual prerequisite steps. |
| **R2** | **Runs do not interfere.** Two apps, or two developers, at once — one run cannot change another's results. |
| **R3** | **Dependencies declared where used.** In the application's own definition, so the list travels with it. |
| **R4** | **Reproducible everywhere.** New developer, fresh machine, CI — same command, no knowledge held by whoever set up last. |
| **R5** | **Nothing accumulates.** The run ends, its infrastructure ends; no state between runs. |
| **R6** | **Cheap to keep true.** Changing dependencies is a local edit by the person making the change. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Shared always-on development environment | R2 structurally: shared state, one person's run changes everyone's results, debugging becomes "who else is connected?" R5: outlives every run, accumulates state nobody owns. R1 at the front door: access provisioning is a prerequisite. |
| One root compose file that starts the whole world | R3: what starts is the full list, not what one app uses, so list and reality drift. R6: adding an app is an edit to a global file. |
| A documented manual setup | R1: the list is the prerequisite. R4: works on the machine of whoever last wrote it down, nowhere else. |
| Do nothing (each developer wires their own stack) | R1 by default: every run is bespoke. R2 by default: every stack differs slightly, every mismatch debugged as an app bug. |

## Tradeoffs

### What it buys

- Clone-to-running is one command, no prerequisites (R1).
- Runs are isolated: a broken run is the developer's own to fix (R2).
- The dependency list lives with the application — removing a module removes its infrastructure (R3).
- New developer, colleague, and CI all take the same path (R4).
- Changing what an app needs is a local edit (R6).

### What it costs

- Startup cost is paid per run, not amortised over a shared environment: bring-up must stay fast — images kept current, services started in parallel.
- Several applications running at once means several stacks whose ports and resource use must be coordinated.

### Watch

- Every application needs a run command that brings up its declared infrastructure; an app whose run target is a build tool or emulator deviates from this record until it has one.
- The convention keeping parallel stacks from colliding on ports is a convention, not a check — and remains so until a collision has happened once.
