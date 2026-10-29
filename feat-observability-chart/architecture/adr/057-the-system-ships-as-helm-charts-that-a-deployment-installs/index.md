# 057\. The system ships as Helm charts that a deployment installs

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Aurelius Enterprise

The system is delivered for Kubernetes as a set of Helm charts — one per component, plus an umbrella chart that joins them — published as signed artifacts beside the images. The repository owns the charts; it does not own a cluster, a domain, or an operated environment.

## Decision

**The chart is the deployment artifact.** A release publishes, beside every image, one chart per component and one umbrella chart that composes them, all under the release's one version ([ADR 019](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)). A deployment installs the umbrella and passes environment values; nothing is hand-written per environment.

**Ownership is split at the component boundary.** Each component's chart lives beside it and is maintained by the increment that changes the component: the ports it listens on, the settings it requires, the probes that answer for it, and the identity it needs. The umbrella owns what no component can own — how the pieces are joined, exposed, trusted, and supplied with secrets.

**The charts are cloud-agnostic by construction.** Every chart takes the environment as values: domain, issuer, storage, edge class, registry. Nothing in a chart names a cloud provider. The tested target is a stock cluster; a provider-specific arrangement is a values file, not a chart variant.

**The repository names a promotion path; it does not operate one.** What ships is the release plus the chart; installing, upgrading, and running a production environment belongs to the deployment ([ADR 024](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>), [ADR 037](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/037-the-system-itself-promises-nothing-about-staying-up/index.md>)).

The sharp edges are named, not hidden: the stateful parts (the search store, the identity provider, its database) are run by these charts as self-managed workloads, so operational duties the plan until now assigned to a managed service — backups, upgrades, quorum — have the charts as their named home, and each duty is a decision to be written before it is performed ([ADR 026](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>)).

## Context

The conversion's plan closes with the hardening increment: metrics, load, tuning. What it has never answered is how a customer runs the result. The system's whole life so far is one machine — development infrastructure starts with the app ([ADR 005](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/005-dev-infra-starts-with-the-app/index.md>)), the whole system runs on a laptop ([ADR 006](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)) — and that is a deliberate property of development, not a shape of production. A catalogue that is expensive to operate governs nothing; the operating model is a first-class constraint on a product whose promise is a low total cost of running.

Three forces are in tension:

- **Portability.** The organisation's own target is a Google Kubernetes cluster, while the product is sold to customers with other preferences, including sovereign ones. A delivery that assumes one provider's services narrows the market the product can enter.
- **Coherence.** The system is proven and released as one versioned whole. A delivery mechanism that versions its parts independently (a chart per component with independent release cycles) lets the shipped combination drift from the tested one.
- **Ownership.** The people who change a component know its ports, its settings, and its probes. A single chart maintained in one place goes stale the first week a component moves, and staleness in a deployment manifest is discovered by a customer, not by a test.

The repository has, until now, shipped containers and declared the rest the deployment's business. That is honest, and it is not enough: an installation instruction that no one has executed is a claim, and the plan is judged by whether an organisation can stand the catalogue up.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Portability.** The same artifact installs on a stock cluster and on a provider's cluster. |
| **R2** | **One version.** The charts ship under the release's number; the tested combination is shippable. |
| **R3** | **Component ownership.** The increment that changes a component changes its deployment piece. |
| **R4** | **Composition.** One install brings the whole system up, in dependency order, with one command. |
| **R5** | **No secrets in the artifact.** Settings and credentials arrive at install time. |
| **R6** | **Proven, not promised.** An installation is executed and checked as part of the system's gate. |
| **R7** | **Fits the existing delivery.** Same registry, same tags, same signing, same release event. |

## Alternatives

- **Ship containers and write installation instructions.** Fails R6: an instruction is unexecuted, and every deviation from it is discovered at a customer site. It also leaves the composition (ordering, trust, secrets) as prose, which is the least verifiable form a specification has.
- **GitOps with an operated cluster (Argo CD or Flux).** Satisfies R1–R7 for one environment and fails the boundary: the repository would name a cluster it does not operate, and a customer with their own promotion path cannot use it. GitOps is an answer to *how a deployment promotes*, which is the deployment's half of [ADR 024](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>).
- **Kustomize.** The bases-overlays shape meets R1, and its resource-file ownership is close to the component boundary. It fails R7 twice over: the deployment plane has no Helm today, and its parameterisation is env-var text substitution rather than typed values, so it has no native answer to publishing a versioned artifact to a registry.
- **One monolithic chart.** Meets R2, R4, R7, fails R3: a single file for nine components is the place where component knowledge goes stale.
- **Managed cloud services for the stateful parts.** Not an alternative at this layer: it is a deployment's choice, and the chart keeps the door open by treating the stateful parts as values (an external store URL replaces the in-cluster one) rather than by mandating one answer.

## Tradeoffs

- **Positive:** one install command to a running system; component knowledge stays with the component; the chart is validated by the pipeline (lint, render, install, smoke), so an installation is a tested artifact; cloud independence is a property of the artifact, not of a customer's patience.
- **Negative:** the repository inherits the operational shape of the stateful parts — Elasticsearch and Keycloak are run here, so their backup, restore, and upgrade duties are open decisions with this as their home; a new toolchain joins the delivery plane (charts are linted, packaged, published, and versioned alongside images); self-managed state means self-managed recovery until [ADR 026](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>) is built.
- **Neutral / follow-ups:** GitOps promotion remains a deployment's option on top of the charts; admission-time signature verification ([ADR 029](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>)) is a follow-up this makes possible; a high-availability store (quorum, transport trust) is a values change this chart is built to accept, not a rewrite.
