# Change Management

Every change reaches production the same way: it merges into `main` only after the pipeline proves it, ships inside a signed release, and is then promoted by the deployment that receives it. This page describes the released version and what a deployment receives first, then the development flow that produces them — the order a reader of the running system needs.

The environments the system itself operates are two: **development**, which is each person's own machine, and **test**, which is the pipeline. Acceptance and production are not operated by the system; they exist per engagement, and the release hands over an artifact complete enough for a deployment to promote from. The reasoning behind that split is recorded in [ADR 024](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>).

> [!NOTE]
>
> **Where are acceptance and production, then?**
>
> Outside this system's boundary, by design. The system's obligation to them ends at the hand-over — a signed, self-contained artifact — and each engagement runs its own promotion path from there ([The hand-over obligation](<#the-hand-over-obligation>)).

## Release

A version of the system is released as one versioned whole: one number, one changelog, and one release event that publishes every deployable part together as signed, provenance-bearing artifacts. Passing the test environment is what qualifies a change to be part of a release.

## Acceptance and Production

What happens to a released version beyond the pipeline is decided per project or customer: acceptance and production are where an engagement's own requirements live — who signs off, on what environment, under what schedule.

### The hand-over obligation

The system's obligation to those environments is the hand-over. A release hands over an artifact that is:

- signed and versioned, so the deployment can prove what it received;
- configured only through the settings the environment supplies;
- promotable and rollable back without knowledge that lives only with the people who built it.

A project that wants promotion to acceptance and production to be a declared, repeatable path writes that path against the released artifacts, as part of its own deployment arrangement.

## Development and the pipeline

Where changes are made and proven before the releases above: each person's own machine, and the pipeline that gates the merge.

### Development

> [!NOTE]
>
> **The dev container**
>
> Each developer works in their own dev container — an isolated environment with the tools, dependencies, and the whole system (application and its infrastructure) running on the developer's machine, keeping experiments away from everyone else's work. The container is itself a versioned artifact ([ADR 011](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/011-the-development-environment-is-a-versioned-artifact/index.md>)); setup is in the [Development Environment guide](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/contributor-guide/development-environment/index.md>).

Developers commit to a feature branch in the version-control repository, created from `main`. The branch isolates the changes until they are ready for review and testing.

### Test

The test environment is the pipeline: every change is validated there before it merges into `main`. The pipeline runs the same checks as the local hooks, and then the full suite — the layers are listed in [Testing](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/platform/delivery/testing/index.md>):

- **Code quality** — formatting, linting, typing, secret scanning.
- **Unit tests** — each module in isolation.
- **Parity scenarios** — REST behaviour checked against Apache Atlas 2.4.0, with every expectation cited from the Atlas source ([ADR 052](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)).
- **End-to-end tests** — the built image against real services, not substitutes ([ADR 012](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/012-validation-runs-against-real-services/index.md>)).

When the automated tests pass, the feature branch is ready for review: one reviewer confirms independent understanding, and the change merges with two human signatures ([ADR 044](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)).

> [!IMPORTANT]
>
> **A green pipeline is necessary, not sufficient**
>
> The pipeline proves the change works; two humans sign that it is right — the task owner, who can explain the change, and one reviewer, who confirms independent understanding. A merge with green checks and one signature is a process violation, not a shortcut ([ADR 043](<https://aureliusenterprise.github.io/dependabot-uv-all-01eea2cee5/architecture/adr/043-ai-assisted-review-informs-the-signatures-it-does-not-replace-them/index.md>) keeps AI review advisory for the same reason).
