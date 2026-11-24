# 065\. Compose stacks that deploy the whole system live at the repository root

- **Status:** Proposed
- **Date:** 2026-11-17
- **Deciders:** Aurelius Enterprise

## Decision

**A deployment target sits where its scope sits.** A docker-compose stack that brings up the whole system lives in `docker/` at the repository root, beside the umbrella chart in `helm/` ([ADR 057](<https://aureliusenterprise.github.io/feat-7-25c-quality-scores/architecture/adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs/index.md>)); a stack that deploys one component lives beside that component, as its chart does. A system-wide deployable never lives inside one of the projects it deploys.

The standalone stack — the server, the webapp, the embedder, a Keycloak and an Elasticsearch of their own, behind one proxy — is such a stack: it is the compose counterpart of the umbrella, a way to run and try the whole system by hand. It moves from `apps/aurelius-atlas-server/standalone/` to `docker/`. What is shared rather than stack-owned moves with its owner: the Keycloak `aurelius` theme becomes `infra/keycloak/themes/aurelius`, so the chart's realm and the infra Keycloak can wear the same look (DD-414) without a copy.

The same rule splits the stack's compose file: each project's services live in a fragment beside that project (`apps/<project>/docker/compose.yaml`) and the root file `include`s them, as the umbrella chart includes the component charts. The fragments exist for ownership, not delivery — they name the stack's project and are not runnable on their own, and only the root file is the stack. Publishing a compose stack as a deployable artifact (e.g. an OCI artifact, the way the charts ship) is deliberately out of scope here: the fragments bind-mount files from the checkout, so the stack is run from the repository, not distributed.

## Context

The repository already answers "where does a deployable live?" for Kubernetes: component charts live next to the project they deploy, and the umbrella — the deployable that spans every project — sits at the root, because it belongs to the system and not to any one project (DD-290, DD-292). Docker Compose arrived later with the standalone demo stack (series 9.5), and it was placed inside the server's project, because the server was the piece a visitor came to try. The stack has since grown past that: it now runs five projects' images, mounts `infra/`'s configuration and certificates, and pins Keycloak and webapp behaviour its own way. Two targets for the same system now answer the same question two ways, and the reader who learned one is misled about the other.

The forces are the ones that decided the chart question: a placement rule a contributor can apply without asking (scope decides the folder), ownership of shared assets by the project that owns them rather than by whichever stack borrowed them first, and each deployment target removable as a whole slice ([ADR 002](<https://aureliusenterprise.github.io/feat-7-25c-quality-scores/architecture/adr/002-modules-are-removable-slices/index.md>)).

## Requirements

- R1 — One placement rule covers both deployment technologies: a reader who knows one target's home predicts the other's.
- R2 — A system-wide deployable is found at the root, not inside a project it merely includes.
- R3 — An asset two deployables may wear has one home, owned by the project that owns the asset.
- R4 — A deployment target is removable by deleting its folder and unwiring its references.
- R5 — The move keeps the stack's tests, user-guide pages, and history (a rename git can follow), and changes no runtime behaviour.

## Alternatives

**Leave the stack inside the server's project.** It fails R1 and R2: the folder says "this is the server's", while the compose file says otherwise. It also fails R3 on the theme, which would stay owned by a demo stack.

**Give every compose stack its own named subfolder (`docker/standalone/`).** It meets the rules and leaves room for a second stack. It loses on simplicity while there is exactly one stack and the umbrella precedent puts the system-wide artifact at the folder's root; a second stack can add its folder when it arrives.

**Put every deployment target under one parent (`deployments/helm`, `deployments/docker`).** It is the same rule expressed one level up, but it moves the accepted, release-wired Helm tree ([ADR 057](<https://aureliusenterprise.github.io/feat-7-25c-quality-scores/architecture/adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs/index.md>), its chart plugin, and the umbrella's path in CI) for a placement question compose alone raised. The root `helm/` is cited across the ledger; moving it would rewrite more history than the question is worth.

**Do nothing and document the split.** A written exception decays: the next compose artifact lands by whichever precedent the author saw first.

## Tradeoffs

- **Positive:** one rule for both targets; the server's project again contains only the server; the theme gains an owner and a second consumer becomes a mount, not a copy; `docker/` deletes cleanly (R4).
- **Negative:** the accepted specs of series 9.5b–9.5e and of 11.2 name the old path as written history — they stay as written, and this record is the pointer forward. The DDs that placed the stack (DD-363, DD-366, DD-367, DD-369) keep their decisions apart from placement, which this record supersedes for them.
- **Neutral / follow-ups:** the root `AGENTS.md` module map gains `docker/` on the spine; if a second compose stack (for one component) appears, its home is beside that component, per this record.
