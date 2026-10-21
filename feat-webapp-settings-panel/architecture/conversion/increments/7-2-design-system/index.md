# 7.2 Design system

- **Status:** in progress
- **Pull request:** \#99
- **Records:** ADR 053; DD-045, DD-046, DD-047, DD-048, DD-049; relies on ADR 007, DD-042

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

Port the shared components the Aurelius interface's search/browse surface actually uses into `aurelius-atlas-ui` as dumb, signal-driven components with stories, and make the documented purity gate (DD-042) real for `libs/angular`.

Every `@models4insight/components` import in `apps/atlas/src` sits under `app/search/**` (29 sites). The in-use set is eight folders — three already exist in the target lib in Angular idiom and are verified and extended, five arrive as ports:

- **`accordion`** (11 uses) — exists; extended with the legacy `ariaLabel` input, the legacy toggle-content string, real behavioural specs; the swapped `collapse()`/`expand()` bug fixed.
- **`modal`** (6 uses) — exists; extended with the legacy card anatomy: `[modal-header]`, `[modal-footer]` slots, `confirmLabel`/`cancelLabel` inputs, backdrop-click close.
- **`card` + `pagination`** (card grid; `ngx-pagination` in the shell) — exist; carry the chrome strings (UIC-04) and get real specs.
- **`hero`** (1 use) — the search header: Bulma hero with `title`/`subtitle` inputs and `[before-title]`, `[after-title]`, `[navigation]` slots. The legacy component's embedded `router-outlet` is app wiring, not component API — it stays in the app (7.5).
- **`simple-search-input`** (9 uses) → **`search-field`** — the `ControlShell` base and its reactive form dissolve into `query = model()` + `querySubmitted = output()`.
- **`sortable-table-shell` + `sortable-table`** (7 uses) → **`sortable-table`** — headers and rows via content slots with per-column directives; sort, page and selection as `model()` state; paging through the existing `Pagination`.

The legacy component-lib translations (`components.*`, 7 keys) are vendored as fixtures next to the app dictionaries and become the lib's `i18n` unit ids (DD-047), so the webapp's XLIFF bridge carries component chrome in both locales.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| The `Shell` chrome (nav bar, breadcrumbs, app bar) | 7.4 (search), 7.5 (browse) |
| `select`, `quickview` (editor anatomy) | 7.7 (editor) |
| `markdown` (drags `marked` + `dompurify` into the dependency graph) | 7.6 (entity details) |
| `tree`, `date-picker` (the only `@angular/material` users) | 7.6 (details), 7.7 (editor) |
| Project/branch/user/permission modals, `user-search-*`, `fuzzy-search-input` | consumed by no screen of the ported surface; 7.8 if ever |
| Wiring the components into the webapp's screens | 7.4 – 7.9 (the app composes; the lib defines, user rule) |

## Semantics

| Id | Rule |
| --- | --- |
| UIC-01 | Every component is standalone, `OnPush`, takes state through `input()`/`model()`/`output()`, and injects no service with side effects (WBP-04) |
| UIC-02 | Every component ships a CSF3 story per visual state, and `nx build-storybook aurelius-atlas-ui -c ci` compiles them all |
| UIC-03 | Styling is Bulma utilities and `@aurelius/atlas-brand` tokens; no literal colours in component styles |
| UIC-04 | No `@ngx-translate` pipe: chrome strings carry `i18n` attributes whose ids reuse the legacy `components.*` dictionary keys (DD-047); title/footer text slots accept caller-localised content nodes |
| UIC-05 | No `@angular/material` and no `ngx-pagination`: sorting is header clicks over `model()` state, paging is the existing `Pagination` component |
| UIC-06 | The behaviours the legacy Jest specs assert are re-expressed as Vitest specs naming the rule ids in the test names (ADR 053 R5) |
| UIC-07 | The purity gate (WBP-02) greps `libs/angular` as DD-042 states, runs in CI, and passes (DD-048) |
| UIC-08 | The lib's peer dependencies match the workspace majors (Angular 22, `@fortawesome/angular-fontawesome` 5); lib and example app build green |
| UIC-09 | The public API grows additively — existing component APIs unchanged, `aurelius-atlas-frontend-example` builds and tests green (DD-047) |
| UIC-10 | The interactive components (`accordion`, `modal`, `search-field`, `sortable-table`) ship `play()` stories and `nx test-storybook aurelius-atlas-ui` passes |

UIC-04 and UIC-09 together are the localisation rule for shared chrome: the component owns its string (it is part of the design), the app owns its translation, and one catalogue covers both because the ids are the legacy dictionary paths the XLIFF bridge already keys on.

UIC-09's additive constraint exists because the example app consumes the lib today; 7.2 must not break the app that is the pattern reference until 7.10 retires it. The webapp consumes no lib component yet — once a slice wires one in (7.4+), its `extract-i18n` run emits the template's `@@components.*` units into the catalogue the DD-047 bridge already keys, and the completeness spec keeps proving both locales.

## Aurelius origin

Cited by path in `aureliusenterprise/aurelius` at the cloned commit, so a reviewer can compare:

| Aurelius | Becomes |
| --- | --- |
| `libs/components/src/lib/accordion` | `aurelius-atlas-ui: Accordion` (extended) |
| `libs/components/src/lib/modal` (+ `AbstractModal`, context object) | `aurelius-atlas-ui: Modal` (extended; context → inputs) |
| `libs/components/src/lib/hero` (embedded `router-outlet`) | `aurelius-atlas-ui: Hero` (section + slots only) |
| `libs/components/src/lib/simple-search-input` (+ `ControlShell`) | `aurelius-atlas-ui: SearchField` |
| `libs/components/src/lib/sortable-table-shell` + `sortable-table` | `aurelius-atlas-ui: SortableTable` (+ column directive) |
| `libs/components/src/translations/{en-US,nl-NL}.json` (`components.*`) | `tests/fixtures/components-*.json` → XLIFF `@@components.*` ids |
| `libs/components/src/lib/control-shell` (`AbstractControlShell`) | dissolved: Bulma field markup inlined where used |
| `sortable-table-shell.service` (redux `BasicStore`: sort, page, selection) | dissolved: `model()` state on the component |
| `matSort`, `ngx-pagination`, `intersection-observer` directive | dropped: header-click sorting, `Pagination`, paging |
| `libs/components/src/lib/*/ *.module.ts` | standalone components (WBP-02) |

## Deviations

None against Apache Atlas: the Aurelius interface is Aurelius's own, and the Atlas dashboards are untouched (WBP-07). Against the Aurelius product, the intended differences are recorded in [design-log](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/conversion/design-log/index.md>): the scope split of the component library (DD-045), the dissolution of component services into signal state (DD-046), chrome strings moving to the built-in localisation keyed by the legacy dictionary paths (DD-047), and the purity gate made executable over `libs/angular` (DD-048). No new `DV` entry: the UI swap itself is DV-11.

## Acceptance

- `libs/angular/aurelius-atlas-ui/src/lib/**/*.spec.ts` (Vitest) — one spec per component, behaviours naming UIC ids in the test names: accordion toggle/ariaLabel, modal open/close/confirm/cancel/backdrop, search-field query two-way + submit + clear, sortable-table sort cycle/paging/selection/empty, hero slots, card/pagination chrome strings. UIC-06.
- `src/app/i18n-completeness.spec.ts` — the completeness spec, extended to the vendored `components-*.json` fixtures: every legacy `components.*` key and value present in both catalogues, and every `@@components.*` id in a library template defined by them (UIC-04).
- `nx build-storybook aurelius-atlas-ui -c ci` — stories compile (UIC-02); `nx test-storybook aurelius-atlas-ui` — the `play()` interactions pass (UIC-10).
- `apps/aurelius-atlas-webapp/scripts/check-webapp-purity.sh` extended to `libs/angular` (UIC-07), wired as `check-purity` on the lib's `test` target.
- Consumer regression: `nx build aurelius-atlas-frontend-example` and `nx test aurelius-atlas-frontend-example -c ci` (UIC-09).
- Umbrella checks for both projects: `nx build`, `nx test -c ci`, `nx lint`, plus `nx e2e aurelius-atlas-webapp` unchanged (the webapp consumes no lib component yet).

### Definition of done, in order

1. `nx test aurelius-atlas-ui -c ci` green with the coverage gate; `nx lint` and `nx build aurelius-atlas-ui` green on the bumped peer deps.
2. The purity gate greps `libs/angular` in CI and passes.
3. Every story renders in Storybook, light and dark — a reviewer's visual pass.
4. The example app builds and tests green on the extended lib (UIC-09).
5. The generator emits the `components.*` units and the completeness spec proves them in both locales (UIC-04, DD-047).
6. `libs/angular/aurelius-atlas-ui/AGENTS.md` and `README.md` describe the new components, per [ADR 003](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/adr/003-every-project-documents-itself/index.md>).
