# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-126. The webapp is a new project, not the Aurelius app upgraded in place

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The Aurelius interface is rewritten as `apps/aurelius-atlas-webapp`, a new Nx
project on this workspace's Angular 22, Nx 23, and TypeScript 6. Only source moves: the Aurelius
`project.json`, `tslint.json`, Jest config, `jest-preset-angular`, and the root dependency set are
left in the Aurelius repository. Targets are inferred by this workspace's plugins, and tests are
Vitest.

**Reason.** An in-place upgrade must cross five `ng update` majors with the custom abstractions
intact, and needs `@angular/platform-browser-dynamic`, which this workspace does not install
because its apps bootstrap with `bootstrapApplication`. Vendoring the upgraded result therefore
adds a deprecated dependency and lands the whole NgModule graph in one review. A new project lets
each slice arrive on the target's rules, and the Aurelius app keeps serving while they do
([ADR 053](../../../../docs/architecture/adr/053-the-webapp-is-rewritten-in-angular-idiom-slice-by-slice.md)).

**Alternatives.** Upgrade in place then modernise: fails the "no replaced pattern survives" rule
and produces one unreviewable migration. Serve the Aurelius app as an external artifact: leaves two
Angular toolchains and two dependency trees to maintain. Port into
`aurelius-atlas-frontend-example`: destroys the small legible reference the example is for.

**Consequences.** The same screens exist in two codebases until 7.10 removes the example app. The
clone is kept at `.scratch/aurelius` as the reference checkout, git-ignored and outside the Nx
graph; every `Aurelius origin` citation in the 7.x increments points into it, and it is re-fetched
by path when a citation must be checked.

### DD-127. Signals replace the custom store; each slice owns its state

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The Aurelius `@models4insight/redux` layer (`Store`, `BasicStore`, `StoreService`,
`ReduxModule.forRoot`) is not ported and has no adapter. Each slice rewrites its state as
`signal()` with `computed()` for derived values, in an injectable following the signal-service
pattern of `aurelius-atlas-frontend-example`. A `Subject` survives only as an event stream inside
RxJS interop (`toObservable`, `toSignal`, `takeUntilDestroyed`), never as the owner of state.

**Reason.** The wrapper is a hand-rolled Redux: 24 Aurelius files import it, and its
`BehaviorSubject` state is the main reason the app cannot run zoneless — change detection depends
on zone patches seeing the emissions. Signals give the same explicit state, the same derived
values, and change detection that needs no zone. Keeping a compatibility layer would preserve the
abstraction the rewrite exists to remove, and every reader of a screen would meet it first.

**Alternatives.** NgRx: a dependency ADR 050 removes from the system, and signals make its store,
selectors, and effects redundant here. Keep the wrapper on Angular 22: cheapest per slice, and it
leaves the custom abstraction in front of every screen, which is what the requirement forbids.
Component-local signals with no service: shares nothing, so the cross-screen state the wrapper
carries (selected entity, filters, breadcrumbs) finds no home.

**Consequences.** State behaviour is re-expressed, not inherited, so the Aurelius store specs are
read as the source of assertions (ADR 053 R5). The purity check fails a state-owning `Subject`, so
a slice cannot keep one by accident.

### DD-131. Webapp purity is a checked gate, not a review convention

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The rules that say the webapp is not the old app are enforced by a check that runs in
CI: `nx run aurelius-atlas-webapp:check-purity` greps `apps/aurelius-atlas-webapp` and
`libs/angular` for `@NgModule`, `platformBrowserDynamic`, `@models4insight/`, `@ngx-translate/`,
`environments/environment`, and a state-owning `new BehaviorSubject` outside RxJS interop, and
fails on a match. The same rules are expressed as ESLint restrictions where the plugin supports
them.

**Reason.** Four slices in, a reviewer's attention is on the feature, and a copied Aurelius file
arrives with its `NgModule` and its `BehaviorSubject` attached — the exact imports the Aurelius
codebase is full of, and the ones ADR 053 forbids. A rule that only a person can notice during
review is a rule that decays, and the gate that refuses a change is defined once and runs
everywhere ([ADR 014](../../../../docs/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere.md)).

**Alternatives.** Rely on code review: free, and it decays exactly when slices get large. Rely on
the compiler: it catches `@ngx-translate` when the package is absent, and catches nothing about
`Subject`-owned state, which compiles cleanly. Rely on ESLint alone: no rule exists for
"this `Subject` owns state", so the grep carries what lint cannot.

**Consequences.** The gate is a maintenance cost of its own and must be read as a floor, not as
the definition of good Angular — idioms it cannot see (`input()` versus `@Input`, control flow,
`OnPush`) stay with review. Its allow-list is where an exemption is argued in the open, so an
escape hatch is a reviewed change rather than a quiet one.
