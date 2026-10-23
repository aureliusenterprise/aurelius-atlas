# 024\. A validated release is promoted by a declared path

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

A release is validated once and then moves by promotion: an environment receives the identical artifact, never a rebuilt one. The record's sharp edge is its scope. The system names and operates two environments, development and test, and hands every further environment a complete artifact rather than operating the promotion into it.

## Decision

**The system names the environments it operates:** **development**, one person's machine, and **test**, the pipeline. A change becomes a release candidate by passing test. What happens to a released version after that is the adopting deployment's decision: acceptance and production exist only as customer- or project-specific arrangements, stated here rather than left to oral tradition.

**The obligation to the rest is a complete hand-over:** an artifact ready to promote — signed, versioned, and configured only by the settings an environment supplies. Where a deployment wants promotion to be a declared, repeatable path with a one-move rollback, it writes that path against the released artifact; the system neither operates it nor invents one on the deployment's behalf.

**Both named environments run today.** Development is the versioned container the whole system runs in; test is the pipeline that validates every change against real services. The decision is the boundary between what the system operates and what it hands over — and the mechanisms for the named environments already exist, which is why this record is Accepted rather than Proposed.

## Context

The system releases as one versioned whole, and a release produces a complete set of deployable artifacts, validated together and signed so their origin is provable ([029](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>)). Two environments are the system's own: development, where the whole system runs on one machine, and test, where the pipeline validates every change before it can become a release. Beyond test the picture changes shape — acceptance and production are where a customer's or project's requirements live, and they are not the same arrangement twice. The one part whose runtime is a cloud provider's reaches neither named environment today: it runs only in a local emulator, so its first real deployment will be unexercised.

This is not an accident of laziness; it is the honest shape of a system meant to be adopted rather than operated by the people who build it.

The boundary still has to be drawn. A reader who finds no statement will assume the missing environments are an oversight and build on them; a reader who finds a promotion path in the documentation will assume the system operates one. The cost of the ambiguity is paid at the worst moment: the first deployment that matters, by the person with the least room for error.

The question this record answers is what happens to a released version after it is published: which environments exist, what moving a version into one means, and who or what performs the move.

## Requirements

Any acceptable arrangement must deliver:

- **R1 — The set of environments is stated.** Where the system runs is written down, including which environments the system operates and which it hands over; "where does version N run?" has an answer that is not a question back.
- **R2 — Promotion is repeatable where the system operates.** Moving a version into an environment the system runs is one declared action that produces the same result every time, performable by whoever is allowed to perform it, not only by whoever invented it.
- **R3 — The artifact does not change.** What is promoted is the released, signed artifact itself; an environment contributes settings, never a rebuild.
- **R4 — Position is knowable.** Any environment can state which version it runs, and the statement is trustworthy because promotion is what updates it.
- **R5 — Rollback is one move where the system operates.** Returning an environment the system runs to a previous version is the same kind of action as promotion, not a reconstruction.
- **R6 — The operated path is exercised.** Promotion in the environments the system runs happens routinely enough that its first use in anger is not its first use.
- **R7 — The hand-over is complete.** What the system gives an environment it does not operate is enough to promote from without the system's help: the artifact, its provenance, and the settings channel — no oral tradition about extra steps only the builders know.

## Alternatives

The chosen shape is the Decision: name the operated environments, delegate the rest. It satisfies every requirement — R2, R5, and R6 speak only of the environments the system runs, and R7 is the contract it keeps toward the ones it does not. The rejected shapes:

| Alternative | Why it fails |
| --- | --- |
| Hand deployment (the status quo) | R1: the set of environments is never written down. R7: the hand-over is oral tradition — the extra steps live in the heads of whoever built them. |
| Per-environment build pipelines | R3: the artifact in the environment was never the artifact that was validated, quietly undoing the confidence the release was built to carry. R5 as a side effect: rollback means waiting on a rebuild. |
| Declare every environment out of scope | R1 even for the environments the system does operate: development and test exist and are exercised daily, and leaving them unnamed makes the taught path a secret. The Decision takes this alternative's honest half — the further environments are not the spine's to operate — and refuses its dishonest half, which is silence about the two that are. |
| A platform's native deployment model, wholesale | R2 and R4 for one environment shape; fails R3's neutrality by binding promotion to that platform, which narrows where the system may run at all. |
| Do nothing | The current state described as a choice: every requirement left to oral tradition. This record exists to prevent that. |

## Tradeoffs

### What it buys

- The boundary between what the system operates and what it hands over is written down, so neither a reader nor a reviewer has to guess (R1, R4).
- The two operated environments are exercised daily rather than hoped for (R6).
- The hand-over contract is small and checkable: a signed, versioned artifact configured only by settings (R3).

### What it costs

- The system cannot promise a deployment how its release will be promoted; a customer who expects one must be told the answer is theirs to build.
- Naming the operated environments constrains future flexibility — the point, but it will be felt as a cost.
- The delegation is honest only while the handed-over artifact is truly complete: any property a deployment needs that the artifact lacks silently pulls the environment back into the spine (the system's kept core, [002](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/002-modules-are-removable-slices/index.md>))'s scope.

### Watch

- Promotion of a *released* artifact beyond test has no mechanism here by design: a deployment that wants one writes it against the signed artifact, and the first such deployment is this record's first real test.
- The image the pipeline validates and the image the release publishes are built by different steps, so R3 does not yet hold even for the named environments; closing that gap is a standing obligation of this record.
- The cloud-provider runtime reaches neither named environment and runs today only in a local emulator, so its first real deployment will be unexercised.
- Rollback beyond test is the deployment's move, named as a deploy-time act by the release record ([019](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)).
- Settings are what an environment contributes to an artifact, and the channel that delivers them is already decided elsewhere ([018](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)).
- Every environment must be reachable by the same identity rules that govern every other boundary ([013](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-nxlv-python-23.3.0/architecture/adr/013-services-prove-who-they-are-at-every-boundary/index.md>)).
