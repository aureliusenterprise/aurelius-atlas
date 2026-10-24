# 016\. The system observes itself; its operational data never leaves it

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

Traces, metrics, and logs are produced and consumed inside the system, at one collection point the system runs itself. No operational data ships to a vendor: understanding the system requires nothing outside it.

## Decision

**The running picture lives inside.** Every part exports the same three signals — traces, metrics, logs — to one collection point that is part of the system, and the tools that read the picture run beside it. Nothing is shipped to a hosted service.

**The rule follows the data to its source.** A part running in a user's browser sends its signals to the collection point its deployment names, so a customer's deployment keeps the picture inside the same boundary. **A part that emits nothing is a blind spot, treated as a defect, not a simplification.**

The collection seam itself — one protocol, replaceable tools — is a separate decision ([034](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/034-signals-meet-at-one-replaceable-collection-point/index.md>)); this record covers where the picture lives.

## Context

The behaviour of the business system lives in the conversations between its parts, so when something misbehaves, the evidence is spread across them: which request entered where, how long each hop took, what each part decided. The question is where the picture is assembled and who may hold its raw material.

**The conventional answer moves the raw material outside.** A hosted observability service is cheap to operate, and operational data is not neutral: traces carry request data, logs carry identifiers, and what they reveal about customers grows as the system grows. Once the data flows to a vendor, every environment needs an account, a network path, and a data-processing agreement — and an environment that cannot grant them (an offline machine, a restricted site, a demonstration) runs blind.

**The system is meant to be legible wherever it runs**: a person's machine, the pipeline, a customer's environment ([006](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)). And because the examples are how the organisation teaches ([009](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/009-examples-must-run-and-be-tested/index.md>)), the debugging path is part of what is taught — if observing required an external account, the taught path would be one the learner cannot walk.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The picture is assembled inside.** Signals from every part meet where the system runs; reading them needs nothing external. |
| **R2** | **The system runs where data may not leave.** Running it can never depend on a third-party data agreement. |
| **R3** | **Observing needs no accounts or network.** A person on their machine and an unattended run get the same picture. |
| **R4** | **The path is exercised where validation runs.** The debugging path is live in local and pipeline runs, not discovered under pressure. |
| **R5** | **Cheap to keep true.** Instrumenting a part, or adding the stack to an environment, is a local change. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| A hosted observability service | R2: the raw material leaves the boundary; R3: every environment needs an account and a network path, so an offline run loses the picture — contradicting [006](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>). R4: the debugging path exists only where the vendor is reachable, so the taught path and the shipped path diverge. |
| Self-hosted stack, outside the system | R2 yes; R1 and R3 no: the picture is assembled where the system does not run, so every environment provisions the stack beside it — the account-and-network dependency with a different owner. R5: every new environment installs two things. |
| The cloud platform's monitoring | R2: the data leaves the boundary, to the platform's owner. R3 for every environment not on that platform. |
| Logs only, no traces or metrics | R2 and R3 pass, R1 fails: the picture of a request crossing several parts cannot be reassembled from uncorrelated text — precisely the failure mode the system's shape makes common. |
| Each part exports to its own backend | R1 in practice: a picture spread over unlinked backends is not one picture — and the seam those backends would sit behind is what [034](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/034-signals-meet-at-one-replaceable-collection-point/index.md>) decides. |
| Do nothing (prints and local reproduction) | R1 by default: the evidence of an incident is whatever the logs happened to catch. R4: the debugging path is invented per incident, not exercised daily. |

## Tradeoffs

### What it buys

- The system is legible wherever it runs — offline, in a customer's environment — with no account to provision (R1, R3).
- No operational data crosses the boundary, so running the system never requires a data-processing agreement (R2).
- The debugging path is live in every validation run: trusted before it is needed (R4).

### What it costs

- The organisation operates its own observation stack — availability, retention, dashboards are its problem; a hosted service's polish is paid for in upkeep.
- The picture is bounded by what a self-hosted stack at the scale of the run can hold: long retention and fleet-wide aggregation are not on offer.
- Every part that ships uninstrumented is a blind spot its owner must close — the picture is only as complete as its least-instrumented part.

### Watch

- Parts that currently emit nothing are deviations this record **names rather than tolerates**: each needs instrumentation or a stated reason not to have it. A part emitting only some of the three signals is a partial blind spot, treated the same way.
- The collection point speaks a standard protocol ([034](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/034-signals-meet-at-one-replaceable-collection-point/index.md>)) so a future production arrangement may export elsewhere — **no export may begin without a new record superseding this one.**
- Sampling rates are a tuning decision per part; how long signals are kept is a lifetime question owned by [025](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/025-data-has-a-stated-lifetime/index.md>).

> [!NOTE]
>
> **Why not a hosted service for production only?**
>
> Because the rule is about the system, not the environment. A production export splits the debugging path in two — the legible arrangement taught locally, an opaque one where it matters most — and the split is exactly what [006](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-prettier-plugin-toml-4.1.0/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>) removes elsewhere. Export requires superseding this record first.
