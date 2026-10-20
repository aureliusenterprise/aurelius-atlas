# Testing Strategy

This page states how Aurelius Atlas is tested: the layers the gate stands on, and what each proves. The gate itself is defined once and runs everywhere ([ADR 014](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)) — the same checks locally and in CI. The commands, file conventions, and failure triage are the contributor guide's: [Testing](<https://aureliusenterprise.github.io/feat-webapp-landing/contributor-guide/testing/index.md>). The merge bar for conversion work is the Definition of Done in the [conversion roadmap](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/conversion/index.md>).

## The layers

| Layer | What it proves |
| --- | --- |
| Unit | Functions and modules in isolation, milliseconds-fast, offline; the store is a stand-in client |
| Parity scenarios | REST behaviour equals Apache Atlas 2.4.0 — expectations read from its source and its own tests, each citing where (ADR 052) |
| Traceability | Every public function and every specified rule id is named by a test ([ADR 049](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>)) |
| E2E (backend) | The **built image** against real services over TLS ([ADR 010](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>), [ADR 012](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/012-validation-runs-against-real-services/index.md>)) |
| E2E (frontend) | Critical user flows through the real browser stack |
| Visual | Visual regressions of the shared UI library — template slice, leaves with it (DD-019) |

Python units are milliseconds and offline-safe; e2e is the shipped artifact against real services — never mocks of the things being shipped. Parity is the layer the conversion adds: a scenario states the request and the response Atlas gives, and a visible difference is a recorded [deviation](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/conversion/deviations/index.md>), not a silent test change. Inside every layer, tests are written in the Arrange-Act-Assert shape — set the world up, run the thing, check the result — with behavior-oriented names and reusable fixtures in place of copy-pasted setup ([AAA](<https://semaphore.io/blog/aaa-pattern-test-automation>)).

The current stack, named once as evidence: [pytest](<https://docs.pytest.org/en/stable/>) with [`pytest-cov`](<https://github.com/pytest-dev/pytest-cov>) and [`pytest-mock`](<https://github.com/pytest-dev/pytest-mock>) for the Python layers, [Testcontainers](<https://www.testcontainers.org/>) to bring the real services up under E2E, [Playwright](<https://playwright.dev/>) for the browser flows, [Vitest](<https://vitest.dev/>) for the Angular side, [Storybook](<https://storybook.js.org/>) with [Chromatic](<https://www.chromatic.com/>) for the visual layer, all orchestrated by [Nx](<https://nx.dev/>).

> [!NOTE]
>
> **A stand-in store client in units, a real store in e2e — why both?**
>
> They prove different things at different costs. The stand-in keeps unit tests millisecond-fast and offline so a developer runs them constantly; the store integration itself — the part most likely to break against a real server — is proven where the unit of validation is the unit that ships: the built image against real services over TLS ([ADR 010](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>), [ADR 012](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/012-validation-runs-against-real-services/index.md>)).

## The CI gate

The gate is what protects production: no change reaches `main` — and nothing is released — without it. The stages, in the order they run:

1. **Quality** — formatting, linting, markdown, secret scanning.
2. **Traceability** — every function and rule named by a test, from collected markers, no run.
3. **Test + E2E** — the affected projects, secrets decrypted first, images built, real services started.
4. **Evidence** — one report page per change with results, coverage, and the rule/function trace ([ADR 049](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>)).
5. **Artifact + inventory + scan** — the image, its contents inventory ([ADR 033](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/033-shipped-artifacts-carry-a-contents-inventory/index.md>)), a vulnerability scan.
6. **Analysis** — code quality and security of the affected projects.

Merge requires all affected stages green; the evidence report is what reviewers read. The pipeline definition is in the repository's CI configuration.

## Indicators

The gate aims at delivery outcomes, not coverage for its own sake. The indicators follow the [DORA metrics](<https://www.devops-research.com/research.html>), with starting-point targets to be operationalized with business stakeholders:

| Indicator | Direction | Starting target | Intent |
| --- | --- | --- | --- |
| Change failure rate | Down | \< 15% | Less release risk, more confidence in delivery. |
| Mean time to restore | Down | \< 1 hour | Less customer impact when a failure occurs. |
| Lead time for changes | Down | \< 7 days | Predictable delivery from development to live. |

Each is measured from the system's own records: the failure rate from deployment logs and incident tracking, the restore time from detection to restoration in the incident record, the lead time from commit to deployment in the pipeline's metadata. Leading signals watch for trouble before users do: gate pass rates, the flaky-test rate and how quickly flakes are fixed, recurring regressions, execution time per layer, coverage of critical paths, and the share of changes that carry test updates.

> [!IMPORTANT]
>
> **Flaky tests are fixed, never skipped**
>
> A skipped test silently deletes the evidence the gate is made of: the report reads as green while the behaviour it stood for goes unproven. Retrying a flaky test hides its root cause — timing, isolation, shared environment — which is the bug worth fixing.

## Pointers

- Commands, conventions, flaky triage: [Testing guide](<https://aureliusenterprise.github.io/feat-webapp-landing/contributor-guide/testing/index.md>)
- Gates and evidence: [ADR 014](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>), [ADR 015](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/015-a-change-answers-for-what-it-caused/index.md>), [ADR 049](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>)
- Realism: [ADR 010](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>), [ADR 012](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/012-validation-runs-against-real-services/index.md>)
- Parity method: [ADR 052](<https://aureliusenterprise.github.io/feat-webapp-landing/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>), the [parity library](<https://aureliusenterprise.github.io/feat-webapp-landing/api-reference/libs/python/aurelius-atlas-parity/index.md>)
- Per-project commands: each project's `AGENTS.md`
