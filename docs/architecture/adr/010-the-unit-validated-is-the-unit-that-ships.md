# 010. The unit validated is the unit that ships

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

Every part ships as one packaged unit, and that same unit is what development
and the pipeline validate. Environments differ in configuration and
orchestration — never in artifact.

## Decision

**One packaged unit per part.** The unit built and validated on an engineer's
machine and in the pipeline is the unit deployed to production. Environments
may differ in configuration and in the orchestration that runs the unit —
production runs on the orchestration the organisation operates, which need not
be how the system runs in development or CI — **but not in artifact**.

**A run is evidence about a unit; a deployment is of that unit.** Where a
difference between places is unavoidable, it is expressed as configuration of
the unit, never as a differently built unit.

## Context

The system is validated in several places — an engineer's machine, the
pipeline, production — and each validation produces a claim: _the system
behaves this way_. The claims are worth acting on only if they are about the
same thing.

If the validated artifact differs from the deployed artifact, a passing run and
a healthy deployment are claims about two objects, and confidence does not
transfer. The organisation is left reasoning about the gap: which failures
belong to packaging, which to environment, which to code — a question that
exists only because two builds happened where one could have.

??? QUESTION "What does a green run _not_ prove?"

    The unit, not the environment: scale, live traffic, third-party behaviour,
    and the production orchestration itself are named exceptions this record
    refuses to claim. A passing run transfers its evidence about the artifact —
    configuration and orchestration differences are stated, not silently
    absorbed, and the gap is a list, not a fog.

## Requirements

Any acceptable arrangement must deliver:

|        | Requirement                                                                                                                              |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **R1** | **One build, everywhere used.** Packaged once per change; every consumer takes that package, never rebuilds.                             |
| **R2** | **Validation transfers to production.** A passing run is evidence about what deploys — differences are config, not artifact.             |
| **R3** | **The unit is self-contained.** Carries what it needs to run; external dependencies are declared, not assumed from the machine.          |
| **R4** | **Deploy is a selection, not a transformation.** Point the environment at a validated unit — no rebuild, repackage, or patch on the way. |
| **R5** | **Cheap to keep true.** Packaging a part is a local edit by the person making the change.                                                |

## Alternatives

| Alternative                                 | Why it fails                                                                                                                                                                                                                  |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Build per environment                       | R1 by construction — the tested unit and the serving unit come from different builds at different times, every difference unvalidated. R4: deploying runs a build, so the release path contains a step no validation covered. |
| Patch the validated unit at release         | R4 directly: the deployed unit is the validated unit plus an unvalidated edit, and the pipeline's claim ends where the edit begins.                                                                                           |
| Deploy source, build in place               | R1: each environment's toolchain assembles its own copy — two environments, two running things, one commit. R4: the running thing has no identity to roll back to.                                                            |
| Do nothing (each place takes what it takes) | R1 by default: machine, pipeline, and production each assemble a copy. R2 by default: green here and green there are claims about different things; the gap is investigated when they disagree.                               |

## Tradeoffs

### What it buys

- A passing run means the same thing on a machine, in the pipeline, and in production (R1, R2).
- Releasing is a selection, so rollback is a selection: point back at the previously validated unit (R4).
- The running unit has an identity, so an incident ties to exactly the code that runs.

### What it costs

- Every part must be packageable — arrangements that only work in place are out —
  and packaging joins every delivery path, so packaging bugs become release bugs.
- Per-environment configuration must live outside the unit: a stated place for it,
  and the habit of keeping secrets and environment values out of the package.

### Watch

- The confidence claim stops at the environment boundary: scale, live traffic,
  third-party behaviour, and the production orchestration itself are **named
  exceptions**, not proven by validating the unit.
- Parts packaged non-uniformly (an app run from source, not its package) deviate
  from this record until they ship the unit that was tested.
- The image developers and the pipeline work in is not a deliverable and not the
  unit this record governs: it is a tool for producing and validating the unit,
  and a change to it is not a release.
