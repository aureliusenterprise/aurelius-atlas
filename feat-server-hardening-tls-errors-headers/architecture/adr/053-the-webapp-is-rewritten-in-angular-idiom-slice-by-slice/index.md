# 053\. The webapp is rewritten in Angular idiom, slice by slice

- **Status:** Proposed
- **Date:** 2026-10-20
- **Deciders:** Aurelius Atlas maintainers

## Decision

**We will rewrite the Aurelius Atlas web interface in this workspace as `apps/aurelius-atlas-webapp`, one feature slice at a time, in current Angular idiom, and we will not port its custom patterns.** The Aurelius web interface (`apps/atlas` in the `aureliusenterprise/aurelius` repository, Angular 17.3, 62 NgModules, a custom Redux wrapper, and 20 shared libraries) is the starting material. Its features survive; its architecture does not.

Three properties of the target are fixed, not per-slice choices:

- **State is signals.** The custom store abstraction is removed outright and each slice's state becomes `signal()` and `computed()`. No adapter, no compatibility layer, no coexistence.
- **Presentational components are dumb and shared.** A visual component with no service side effects lives in `aurelius-atlas-ui`, takes `input()` and emits `output()`, and ships a story. Application components keep their own state and are not shared.
- **Every slice is tested before it is accepted**, by Vitest unit tests and by a Playwright end-to-end scenario. The Aurelius Jest suite is not carried over.

**The Aurelius web interface keeps running untouched while this proceeds,** and the template's example app stays as the pattern reference until the webapp replaces it ([DD-019](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/conversion/design-log/#dd-019-the-template-examples-stay-until-the-plan-is-done>)).

## Context

Aurelius Atlas re-implements the catalogue's server in Python ([ADR 046](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). Its users, though, are served today by two interfaces that are both unsuitable as the destination:

- **The Apache Atlas dashboards** are the reference implementation's UI — vendored and served at `/` and `/n/` ([DD-001](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/conversion/design-log/#dd-001-reference-is-apache-atlas-240-and-both-dashboards-are-served>)). They are the parity yardstick, not a product Aurelius intends to maintain: Angular 8-era, Grunt-built, and explicitly frozen.
- **The Aurelius web interface** is the product Aurelius does own and does want: five years of data-catalogue screens (search, browse, entity details, create and edit, governance quality, domains, lineage) built on the organisation's `@models4insight` platform.

That interface is expensive to keep. It sits four majors behind (17.3 against this workspace's 22.2), and its platform libraries carry patterns the workspace has since replaced — `NgModule` bootstrap, a hand-rolled Redux layer, a `TranslateService` abstraction, constructor injection, `BehaviorSubject` state. Upgrading it in place means crossing five `ng update` majors while those abstractions keep their old shape, and the result is Angular 22 running 2009 architecture.

The workspace also cannot host it as it stands: the target app bootstraps with `bootstrapApplication` and zoneless change detection, and `@angular/platform-browser-dynamic` — the package an `NgModule` bootstrap needs — is not installed at all. Serving the Aurelius interface from this workspace therefore requires the `NgModule` layer to go, not to be preserved.

The two forces in tension: the interface is the most valuable thing Aurelius has outside the server, and the fastest way to run it here is a mechanical upgrade that keeps all of it.

## Requirements

- **R1 — The interface runs in this workspace**, on its Angular, its Nx, its CI, and its hardened image. It is not a second application with its own toolchain.
- **R2 — The Aurelius interface keeps running while this work proceeds.** The port must not freeze the product that is serving users today.
- **R3 — No pattern is kept that the workspace has replaced.** Signals for state, standalone components, the built-in localisation, Vitest and Playwright. A slice that ports a custom abstraction has not delivered its slice.
- **R4 — The work is reviewable in pieces a person can read** ([ADR 044](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)). Each increment lands one coherent capability with its tests, not a bulk migration.
- **R5 — The Aurelius Jest suite is a source of behavioural knowledge**, so the rules it asserts are re-expressed in the new tests rather than silently lost.
- **R6 — The Apache Atlas parity contract is untouched** ([ADR 048](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>), [ADR 052](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)). The vendored dashboards stay as the reference UI for the REST contract.
- **R7 — Shared UI is shared once:** a presentational component exists in `aurelius-atlas-ui` with a story, and styling comes from the brand tokens.

## Alternatives

**Upgrade in place, then modernise.** Run the 17→22 `ng update` chain on the Aurelius app, vendor the result, and convert patterns afterwards. Cheapest route to a running Angular 22 app, and it satisfies R1 and R2. It fails R3 by construction — the app ships with its `NgModule` graph, Redux store, and `TranslateService` intact, and R4 turns the modernisation into one migration PR of tens of thousands of lines. It also needs the deprecated `platform-browser-dynamic` package installed, i.e. the workspace must add a dependency it has decided not to use. Rejected.

**Serve the Aurelius app unchanged from the Python server, as an external artifact.** Satisfies R1's deployment and touches nothing. It fails R3 entirely and leaves Aurelius with two Angular toolchains, two dependency trees, and two security postures to maintain — the opposite of adopting this workspace. Rejected.

**Port into `aurelius-atlas-frontend-example`,** the app that already demonstrates the target conventions. Removes the need for a new project and keeps one Angular app in the workspace. It fails R4: the example is deliberately small and legible as a pattern reference, and merging \~1,000 files of migrated product code into it destroys the thing it is for. Rejected.

**Rewrite the interface from scratch,** keeping only the REST client. Cleanest architecture and the best chance at R3. It fails R2 and R5 — five years of screen behaviour and the knowledge in 50 Jest suites are discarded, and nothing ships until the whole rewrite lands. Rejected.

**Rewrite slice by slice in a new project, keeping the Aurelius app running** — the decision. Satisfies R1 through R7. Its cost is duplication during the transition and a source tree with two copies of the same product, paid for legibility and reversibility.

## Tradeoffs

- **Positive:** Aurelius gains a web interface on this workspace's dependency set, built the way the rest of the system is built. Signals replace the custom store, which removes a layer readers of the code must learn before they can follow any screen. Each slice is a reviewable PR with its own tests, and the Aurelius app keeps serving, so the work is reversible at every boundary.
- **Negative:** the same screens exist in two codebases until the last slice lands, and Aurelius keeps paying for a four-major-behind Angular while the port proceeds. Behaviour is re-expressed, not inherited, so a rule asserted only in a Jest test and missed in review is a real regression risk (R5 is the mitigation, and it is manual). There is no compatibility layer to fall back on: a slice that lands with Redux in it is a defect, not a state.
- **Neutral / follow-ups:** the Aurelius interface becomes the served UI at some point in this track, which supersedes the plan to serve the Atlas dashboards at `/` ([DV-64](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/conversion/deviations/index.md>)). The example app and the template's Angular toolchain then leave with it ([DD-019](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/conversion/design-log/#dd-019-the-template-examples-stay-until-the-plan-is-done>)). The track is scheduled as increments 7.x in the [conversion ledger](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/conversion/#roadmap>) and starts with the application shell ([7.1](<https://aureliusenterprise.github.io/feat-server-hardening-tls-errors-headers/architecture/conversion/increments/7-1-webapp-shell/index.md>)), the one slice with no dependency on the catalogue API.
