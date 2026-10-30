# 009\. Every example runs and is tested, or it is removed

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

Every example is a working implementation, verified by tests the pipeline runs against real services. An example that can't hold that bar is removed, not annotated.

## Decision

**An example is a small implementation, held to the system's bar** — it runs the way the rest of the system runs, and its behaviour is verified by tests in the pipeline. An example that cannot hold that standard is removed, not annotated.

Because the system runs everywhere it is validated ([006](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), examples run there too: on an engineer's machine and in the pipeline, against real services, with their real behaviour tested.

## Context

The codebase carries examples — a service wired to the database, a flow wired to the stream, a screen wired to the API. People read them and copy them, and a copied example becomes the standard for whatever is built next. The examples are how the codebase teaches, intended or not.

An example, unlike ordinary code, has **no callers**. Ordinary code that breaks breaks loudly: its dependents fail. An example depends on nothing, so when it stops working, nothing notices. Its health is whoever last ran it by hand — and the first person to discover the breakage is a reader who has already trusted it, often a new person, who cannot tell a deliberate simplification from rot.

The two errors cost differently:

- **Removing a good example** costs a directory and a lost teaching artifact.
- **A broken example left in place** teaches its mistake with the authority of the codebase, and the mistake can be copied before it is noticed.

> [!NOTE]
>
> **Why remove a broken example, not fix it later?**
>
> "Later" is where the asymmetry above lives: every day in place, the broken example teaches with the codebase's authority, and the first reader to trust it is usually the newest. A fix-later promise has the same shape as the health the example already lost — someone ran it by hand, once. Removal is loud and dated; annotation is silent decay.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **The claim is tested, not remembered.** A pipeline test, not "someone ran it once," backs the claim that it works. |
| **R2** | **Breakage fails a build, not a reader.** Detected the day it breaks — not discovered by whoever trusts it. |
| **R3** | **The taught path is the shipped path.** Real mechanisms, real services: a passing example means the path works. |
| **R4** | **Examples run like the rest.** The same bring-up as the system ([005](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/005-dev-infra-starts-with-the-app/index.md>), [006](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)) — no special harness. |
| **R5** | **Removal is cheap.** A local deletion that leaves nothing dangling. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Keep broken examples, annotated "for illustration" | R1: the annotation is a claim no test runs, and rots like the code it labels. R2: nothing fails as the example drifts; a reader cannot tell illustration from rot. |
| Documentation snippets instead of implementations | R1: a snippet is never executed, so its correctness is a claim about the day it was written. R3: a quotation of the path, and quotations drift in silence. |
| Examples tested against substitutes | R3: the example demonstrates agreement with stubs, not the path that ships — and the integration failures the example exists to catch are exactly what stubs hide. |
| Do nothing (examples live until someone complains) | R1 by default: health is whoever last ran it by hand. R2 by default: breakage is discovered by readers — the one audience the arrangement exists to protect. |

## Tradeoffs

### What it buys

- What people copy is verified, against the real path, before they copy it (R1, R3).
- An example that breaks fails a build the same day, and is never discovered by a reader months later (R2).
- Examples double as the system's integration tests: teaching artifact and safety net are one code, maintained once.

### What it costs

- Every example is a maintained implementation — code, tests, services — so the honest response to an example falling behind is deletion. Cheap (R5), still a loss, and the honest consequence is that **the set of examples stays small on purpose**.
- Real-service testing costs real pipeline minutes and money per run, more than substitutes ([012](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/012-validation-runs-against-real-services/index.md>)).

### Watch

- The full chain — producer, stream, sink, service, screen — is proven segment by segment; a single test spanning all five is the test this record's own standard most wants.
- [005](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/005-dev-infra-starts-with-the-app/index.md>) requires every application to have a run target; an example in an application that lacks one cannot yet be reached by the one-command path.
