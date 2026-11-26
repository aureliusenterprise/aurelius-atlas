# 067\. The standalone stack ships as one generated release bundle

- **Status:** Proposed
- **Date:** 2026-11-19
- **Deciders:** Aurelius Enterprise

## Decision

**The standalone stack is delivered as an artifact, not as a checkout.** A release publishes one bundle: a folder tree, archived, that contains the stack's compose files, the files those files mount, the sample data, and the certificate script (increment 17.2). The bundle is generated from the repository at release time and is never a committed file. The person who receives it needs Docker, `bash`, and `openssl`, and needs no source code, no repository tooling, and no developer account.

Because the bundle is generated, the repository holds one description of the stack and the bundle holds a copy of it. Nothing may state a service, a mount, or an image twice. A bundle that references a file it does not contain, or that names a build no one published, is a build failure rather than a customer's failed start.

Publishing the bundle is the compose counterpart of publishing the charts ([ADR 057](<https://aureliusenterprise.github.io/docs-user-guide-pr3-governance/architecture/adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs/index.md>)). Signing the bundle itself, and the hardening of its settings, are separate decisions and separate increments.

## Context

The standalone stack exists so a person can run the whole system on one machine and judge it. Today that person must be a contributor. The stack is a tree of compose fragments that read files from across the repository, its images carry a tag that only exists on a developer's machine, and a fresh clone must run the repository's certificate tool before anything starts. Each of those is fine inside the repository and fatal outside it.

Two delivery channels already work for the deployed system: container images on a registry and Helm charts on an OCI registry, both published and signed by the release ([ADR 029](<https://aureliusenterprise.github.io/docs-user-guide-pr3-governance/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>), [ADR 019](<https://aureliusenterprise.github.io/docs-user-guide-pr3-governance/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)). Neither answers "try it on my laptop": a chart needs a cluster, and the compose tree needs a repository. [ADR 065](<https://aureliusenterprise.github.io/docs-user-guide-pr3-governance/architecture/adr/065-compose-stacks-that-deploy-the-whole-system-live-at-the-root/index.md>) placed the stack and stated that shipping it as an artifact was out of scope for that decision. This record takes up that open question.

The force that shapes the answer is trust. A bundle that a maintainer assembled by hand, or refreshed when they remembered, is a claim about the stack that nothing checks. A bundle built from the tree a release published carries that tree's behaviour, or the build fails.

## Requirements

- R1 — A person outside the repository can start the stack and reach it in a browser, with only the tools a developer machine already has.
- R2 — The bundle carries no secret, no private key, and no credential from the repository. The recipient supplies their own, and the artifact names every value they must supply.
- R3 — The bundle describes the same stack the repository runs. One service definition, one mount list, one image list exist in the source, and the bundle holds a copy of them rather than a second account of them.
- R4 — A bundle is reproducible from a version tag, and it names the build it carries, so support can tell which version a customer is running.
- R5 — The repository's own use of the stack is unchanged: development, the end-to-end suites, and the shared infrastructure keep working as they do now.
- R6 — A broken bundle fails a check a contributor sees before merge, not a customer on first start.

## Alternatives

**Tell evaluators to clone the repository and follow the README.** It needs no new work, and it fails R1 and R2: the clone brings the source tree and the repository's secret layout, and the steps run developer tooling. It also makes the evaluation depend on repository access.

**Ship a single all-in-one container, as Apache Atlas's Quickstart does.** It is one image and one command, and the simplest thing to hand over. It gives up the shape the stack exists to show: a store, an identity provider, and telemetry that a reader can inspect and replace, each one the same component the deployment runs, which is what makes the stack the compose counterpart of the umbrella ([ADR 065](<https://aureliusenterprise.github.io/docs-user-guide-pr3-governance/architecture/adr/065-compose-stacks-that-deploy-the-whole-system-live-at-the-root/index.md>)). Building it would also mean re-implementing the proxy, the certificates, and the realm setup inside one image.

**Ask evaluators to install the Helm chart on a local cluster.** It reuses an accepted channel, and it fails R1: a cluster, an ingress, and certificate work cost more than the evaluation is worth, and the failure modes are the cluster's, not the product's.

**Commit a prepared bundle folder and refresh it in the release job.** It looks like the same artifact and fails R3 and R6: the folder is a second copy of ten compose files, drift goes unnoticed, and the release ships whatever the folder happened to hold.

**Flatten the whole stack into one generated compose file.** One file is easy to read past, and its generation freezes environment values, erases the comments that say why a setting exists, and leaves a large generated file for the customer to edit. Copying the tree and shortening its paths keeps a file a reader can diff and change.

## Tradeoffs

- **Positive:** an evaluator gets one artifact and two commands (R1); the release produces it, so it matches the version it names (R4); a broken bundle fails before merge (R6); the repository keeps its development flows untouched (R5).
- **Negative:** a new piece of build logic is needed to derive the bundle, and it must learn each new mount shape the stack grows. The check that catches an unlearned shape is a rule and a test, not a compile error.
- **Negative:** the bundle is a copy, so it is stale by the time the tree moves unless a release builds it. That is the accepted meaning of "generated": a bundle belongs to a version, not to a working tree.
- **Neutral / follow-ups:** signing the archive, pinning third-party image digests inside the bundle, and the stack's production posture (restart policy, resource caps) belong to the hardening increment. The delivery folder for published artifacts, and where the bundle sits next to the images and charts, follow the declared promotion path ([ADR 024](<https://aureliusenterprise.github.io/docs-user-guide-pr3-governance/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>)).
