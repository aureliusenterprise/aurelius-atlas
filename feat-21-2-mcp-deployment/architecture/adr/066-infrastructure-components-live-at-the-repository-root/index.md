# 066\. Infrastructure components live at the repository root

- **Status:** Proposed
- **Date:** 2026-11-17
- **Deciders:** Aurelius Enterprise

## Decision

**A component whose Helm chart the umbrella installs is not development material, and does not live under a folder named for development.** The Elasticsearch, Keycloak and observability slices — each of which carries a production chart and a compose stack — live at `infra/<name>/` at the repository root, beside the umbrella chart in `helm/` and the system's compose stack in `docker/` ([ADR 057](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/architecture/adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs/index.md>), [ADR 065](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/architecture/adr/065-compose-stacks-that-deploy-the-whole-system-live-at-the-root/index.md>)). Each carries both ways to run it beside its code: the chart, and a compose file that is the component's own piece — runnable on its own for development, and `extends`-able by a stack that runs the component as the deployment's. Its Nx project, compose project and Docker network carry the same name, `aurelius-atlas-infra-<name>`.

The standalone stack stops owning its own Elasticsearch and Keycloak. Its fragments extend the infra services and state only their differences — the stack's volumes, the stack's realm, the address through the stack's proxy. The stack's Keycloak keeps the production topology: Postgres-backed, theme mounted, no telemetry leg. A try-me that hides what an operator installs is worth nothing.

## Context

The folder `dev/` came from the template as the home of development infrastructure ([ADR 005](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/architecture/adr/005-dev-infra-starts-with-the-app/index.md>)), and the conversion grew it in place. What grew was not development-only: the Elasticsearch chart in `dev/elasticsearch/helm` and the Keycloak chart in `dev/keycloak/helm` are dependencies of the umbrella — the artifacts a customer installs (ADR 057). The specs that produced them say so: "Elasticsearch infrastructure" (0.2), "the prod realm" (10.7). The folder's name describes the biggest consumer of its compose files, not the content.

Two costs of the name are on record. A reader who learns that a chart lives under `dev/` predicts wrongly about every other deployable, which is the same misreading ADR 065 removed for the compose stack. And the standalone stack, placed first inside the server's project and then at the root, grew its own second definitions of the store and the identity provider: the suite pinned the duplication by comparing the two Elasticsearch healthchecks as written copies. One component, described twice, drifting twice.

The naming rule this repo already follows is "a deployable sits where its scope sits" (ADR 065). For the three slices, the scope has long been the system: their charts are installed by the umbrella, their certificates and themes are shared assets, and their compose files run the same components development and demonstration both need.

## Requirements

- R1 — The folder says what the components are, at every layer: path, Nx project name, compose project name, network name. No layer keeps a name that contradicts another.
- R2 — Each component's way of running is stated once. A deployment that needs a variant states its differences; it does not copy the definition.
- R3 — The development workflow keeps its commands: serving an app starts its infrastructure, and the e2e suites reach the shared services as before (DD-223's rule against restarting shared services holds unchanged).
- R4 — The move is followable: history is not rewritten; one record states the old name and the new.
- R5 — The standalone stack runs the components as the charts run them, so a visit to the stack exercises the deployment shape rather than a cheaper imitation.

## Alternatives

**Keep the folder name and rename nothing.** It keeps R1 false. The chart under `dev/` is the one artifact the umbrella releases, and the stack's copies keep their reason to exist.

**Move only the charts to the root and leave the compose in `dev/`.** It splits each component in two, and makes the compose's owner ambiguous — the drift the placement rule exists to prevent (DD-290). A component is a folder, not a file-type.

**Name the folder `components/` or `platform/`.** Either names the same set. `infra/` is the word the repository already uses for the same idea in prose and in `infra/arc/`, so it adds no new vocabulary. It loses nothing but preference.

**Keep the Nx project names (`aurelius-atlas-dev-*`) and move only the folder.** It halves the diff and re-creates the contradiction in writing: the command a contributor types would say `dev` for a folder that says `infra`. Two changes would each prove half of the sweep; one change proves it with one grep.

## Tradeoffs

- **Positive:** one name for one component at every layer; each component's compose joins its chart as the component's own piece, which is the chart-beside-the-project rule extended rather than a new rule; the stack's duplicated store and identity provider are deleted, and their pin-tests become inheritance proofs; the stack's Keycloak gains the database-backed topology the charts install, so the demo shows what production runs.
- **Negative:** the rename touches about 130 live references, the umbrella's lock file, and the names the e2e suites and consumer guides cite; the historical records keep the old path and need ADR 066 as the pointer (the pattern ADR 065 set). The stack's cold start grows by the Postgres and Keycloak boot it now runs. Compose's `extends` interpolates the base with the consuming project's environment, so the stack must carry the infra files' variables even where it replaces them — a sharp edge stated in the stack's README rather than hidden.
