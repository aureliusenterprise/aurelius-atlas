# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-134. The design-system slice ports the in-use components, not the library

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** 7.2 ports the eight `@models4insight/components` folders the Aurelius
search/browse surface imports — `accordion`, `modal`, `hero`, `simple-search-input`,
`sortable-table-shell` + `sortable-table`, with `card` + `pagination` already present —
and defers the rest of the 34-folder library to the slices that consume them:
`select`/`quickview` to 7.7, `markdown`/`tree`/`date-picker` to 7.6, the
project/branch/user/permission modal family and the two search-input engines to 7.8 at
the earliest.

**Reason.** All 29 import sites in `apps/atlas/src` live under `app/search/**`; the
deferred families are imported by screens that arrive in 7.4–7.9, and a fifth of them
by nothing in the ported surface at all. Porting a component before its screen exists
means writing its stories and its specs against a guess of its caller, and ADR 053 R4
asks each increment for one readable capability, not a bulk migration. The leaf
primitives the legacy app styles with (buttons, tags, switches, checkboxes) are Bulma
classes in templates, not components, so they need no port.

**Alternatives.** Port all 34 folders: a PR roughly four times the budget of root
AGENTS.md, most of it unexercised. Port none and build components as screens need them:
each feature slice then invents its own card and modal, which is the shared-once rule
(ADR 053 R7) dissolved into ten slices.

**Consequences.** The roadmap row for 7.2 says "legacy shared components"; it now means
the in-use set, and the deferred folders are named in the increment's not-in-scope
table with their slice. A later slice that needs a deferred component adds it under its
own increment, where its caller can be reviewed with it.

### DD-135. Component services dissolve into signal state; nothing is ported as a store

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** The services the legacy components carry are dissolved rather than
ported. `SortableTableShellService` (a redux `BasicStore` holding sort, page and
selection) becomes `model()` state on `SortableTable`; `AbstractControlShell` and its
context objects become plain inputs with Bulma markup inlined; `FuzzySearchInputService`
and the `MonitorAsync` plumbing are not ported at all; `PageScrollService` in `Hero` is
dropped for the router's own scroll restoration. Where legacy state was persisted
(sort and page survive navigation via the store), persistence moves to the caller.

**Reason.** The custom store is the pattern the port exists to remove (DD-127, ADR 053
R3), and the purity gate refuses a state-owning `BehaviorSubject` in this tree. The
state those services hold is view state — which column is sorted, which page is open —
which is exactly what a `model()` is for, and a component that owns it in a signal can
be rendered in isolation in a story. Persistence is not the component's concern: the
browse screen keeps its sort in the URL (7.5), which is also what makes it shareable.

**Alternatives.** Port the store as a signal-based service in the lib: keeps the file
count low and gives every table a store it does not need, and a lib that owns
application state is what `libs/angular/AGENTS.md` forbids. Keep persistence in the
component with a `localStorage` key: works for one screen and breaks the moment two
tables share a route, as the browse surface does.

**Consequences.** Two legacy outputs (`rowIntersectionChanged`, from the intersection
observer used for infinite scroll) are dropped: paging is explicit, so the infinite-scroll
signal has no consumer. The legacy Jest assertions about store interaction are
re-expressed as component-level assertions (UIC-06), so the behavioural knowledge
survives while the abstraction does not.

### DD-136. Shared chrome strings are localisation units keyed by the legacy dictionary paths

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** A shared component's own strings — "Previous", "Next page", "No data
available", "Toggle content", the quickview tooltips — are `i18n` units in the
component's template, and their ids reuse the legacy `components.*` dictionary paths
(`@@components.sortableTableShell.previous`). The legacy component library's
translations (7 keys, `en-US` and `nl-NL`) are vendored as fixtures beside the app
dictionaries, and the webapp's generator bridges them into the same XLIFF catalogues
that carry the app's 495 strings. Text that belongs to a caller (a modal title, a
table's column names) is passed as content nodes, not as a string input.

**Reason.** WBP-05 forbids literal prose in a template, and the Dutch translations of
these seven strings already exist — dropping them would ship an untranslated table
header in the one language the port promises. The bridge keys catalogues by dictionary
path (DD-128) so a reviewer can diff a unit against the legacy entry, and the
completeness spec proves both locales; reusing the legacy paths keeps component chrome
and app text in one catalogue with one mechanism. Content nodes for caller-owned text
is what the built-in localisation cannot do for a string input: a translated string
that arrives as an `input()` is invisible to `extract-i18n`, so it can never be
translated.

**Alternatives.** `output()` events with the app supplying every string: no component
is usable in a story without its caller's dictionary, and the example app's existing
usage breaks (UIC-09). A `$localize` call per string: works, and loses the dictionary
path that ties a unit to its legacy source.

**Consequences.** `nx extract-i18n aurelius-atlas-webapp` now emits the lib's units,
because the app builds the library from source through the `tsconfig.base.json` path
alias. A component string with no legacy key (a state the Aurelius component never
had) gets a new id under `components.*` and gains a Dutch entry in the fixtures, so the
completeness gate is the point where a new chrome string is argued.

### DD-137. The purity gate is made executable over `libs/angular`

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** `check-webapp-purity.sh` gains the `libs/angular` tree it was documented
to grep (DD-131), and `aurelius-atlas-ui` gets a `check-purity` target wired as a
`dependsOn` of its `test` target, so CI enforces the legacy-construct ban on the
library as well as the app.

**Reason.** DD-131 states the gate greps `apps/aurelius-atlas-webapp` and
`libs/angular`; the script greps only the app's `src/`. The claim was written when the
library held six hand-written components and 7.2 is the first slice to fill it with
ported code — exactly the material a copied Aurelius file arrives in, with its
`NgModule` and its `BehaviorSubject` attached. A rule that is documented and not
checked is the failure mode DD-131 was written against.

**Alternatives.** An ESLint rule set in the library: carries what a linter can see
(`@NgModule`, a banned import) and nothing about a service that owns state in a
subject, so the grep is still needed. A shared CI step over both trees: correct, and it
puts the rule outside the project that documents itself (ADR 003), where a reviewer
editing the library will not find it.

**Consequences.** The gate runs twice per CI job, over two roots, from one script — so
one list of forbidden constructs stays the definition. Any exemption is an allow-list
entry in that script, a reviewed change in the open (DD-131's consequence), and 7.2's
ported components are expected to need none: the six existing library components are
already clean.

### DD-138. The Storybook preview loads `@angular/localize/init`

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** `.storybook/preview.ts` imports `@angular/localize/init` as its first
side-effect, the same polyfill the webapp build loads through its `polyfills` option.

**Reason.** A chrome string in a component template (DD-136) compiles to a `$localize`
call. Under the app's build that global exists; under Storybook's build it does not, so
every story whose template carries an `i18n` attribute throws `$localize is not
defined` at render — the `i18n` bridge silently made every story with chrome text
unrenderable, and the failure surfaces only in the browser, not in a unit test (Vitest
never runs the compiled template through localize).

**Alternatives.** A `polyfills` option on the Storybook targets: the executor schema
does not accept one. A no-op `$localize` in a story helper: works, and re-implements the
polyfill by hand, so it drifts from the real one.

**Consequences.** Stories render the English source text, which is what a visual
baseline and the `play()` queries assert on. A story that needs the Dutch text is out
of scope — translation is a per-app build-time concern; the completeness spec (SHL-08,
UIC-04) is what proves the catalogues carry both locales.
