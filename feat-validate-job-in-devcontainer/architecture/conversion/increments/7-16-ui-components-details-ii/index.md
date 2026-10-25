# 7.16 UI components: details chrome set

- **Status:** in progress
- **Pull request:** [\#110](<https://github.com/aureliusenterprise/aurelius-atlas/pull/110>)
- **Records:** DD-189 (the chip atom is the classification chip), DD-190 (the type-name badge is its own component), DD-191 (details navigation is a shell; the scroll directive stays app-side), DD-192 (the section count bar is `section-stats`); relies on ADR 053, DD-135, DD-136, DD-154, DD-155, UIC-15

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/feat-validate-job-in-devcontainer/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits, and of the design-system track opened by [7.2](<https://aureliusenterprise.github.io/feat-validate-job-in-devcontainer/architecture/conversion/increments/7-2-design-system/index.md>), whose UIC rule ids (UIC-01..10) 7.13 continued (UIC-11..15); this increment carries the series on (UIC-16..20).

## Scope

7.6 shipped the details skeleton with its chrome inline. Four pieces of that chrome — and of the legacy details screen around it — are **pure presentation** whose data wiring is not needed to build, spec and story them: the same seam 7.13 cut (its "pulled forward" deviation), applied one screen deeper. Port them into `aurelius-atlas-ui` as dumb, signal-driven components:

- **`classification-chip`** ← `apps/atlas/src/app/search/components/classification/` (+ the identical `search/components/term/` shell) — the Bulma `tags.has-addons` chip: icon lead tag, label tag with tooltip, optional propagation tag whose hoverable dropdown projects the sources list, loading state. The legacy `ClassificationService`/`ClassificationSourceService` (App Search lookups by guid) are data wiring: name, description, `propagated` and the sources list arrive as inputs; the sources' rows are caller-projected (DD-189).
- **`type-name`** ← `apps/atlas/src/app/search/components/type-name/` — the type badge: icon, `typeAlias ?? typeName`, optional base-type suffix. 7.13 inlined this badge inside `entity-card` (UIC-12); the details header (`.subtitle.name`), the propagated-sources rows, and 7.7's editor all use it standalone, so it is extracted as a component and `entity-card` consumes it (DD-190).
- **`details-navigation`** ← `apps/atlas/src/app/search/details/components/navigation/` — the section-navigation shell: Bulma up-dropdown around a `menu` (label input, `ng-content` for the `li` list, toggle button state is presentational). The legacy `DetailsNavigationItem` directive (smooth-scroll into view) is DOM behaviour on the app's document — it stays app-side (DD-191).
- **`section-stats`** ← the count bar duplicated in `details/default/default-details.component.html` (one stat) and `details/gov-quality/gov-quality-details.component.html` (three stats) — `nav.level` of heading-link + count items; `items: { label, target, count }` in, `itemClicked(target)` out (the nav directive's anchor click, turned into an emit, DD-154's pattern). The heading/count typography pair is the Aurelius shape (DD-192).

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Wiring these into the details screen (header chips, nav, count bar) | the 2.3+7.6 wiring increment (7.6's deferral table) |
| The sources' media rows (name link + crumbs + type badge, repository-fed) | 7.6 wiring — the chip projects them; `type-name` is its badge (DD-189) |
| `DetailsNavigationItem` scroll directive, `iconsByType` | the webapp (app meta and DOM behaviour, UIC-15's split) |
| The nine type components, lineage, quality cards, edit affordance | 7.6 deferral table (unchanged) |
| `details-header` composition (title + chips + crumbs + edit action) | 2.3+7.6 — it composes these four; spec it where its data (the entity DTO) is |
| `media-row`, `section-heading` (Tier 2 of the 7.6 audit) | their own increment, keyed when their screens are specced |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name in the test title (the TS pattern, UIC-11..15's precedent).

| Id | Rule |
| --- | --- |
| UIC-16 | `classification-chip` renders the Bulma `tags.has-addons` chip: the lead tag (caller `icon`, `aria-hidden`, the chip's accessible `label` text) and a label tag carrying `label()` with `title` = `tooltip()`; `loading()` swaps the label tag for the loader tag. A `propagated()` chip adds the `is-hoverable` trigger tag (caller `propagatedIcon`, `title` = `propagatedLabel()`); its dropdown menu projects `[chip-sources]` under the `originLabel()` line. Inputs replace the legacy services; the term chip is the same atom with `is-info` on the lead tag — one component, colour is an input. |
| UIC-17 | `type-name` renders the `span.icon-text` badge: `title` = `typeAlias ?? typeName`; the icon `span.icon` (caller `icon` + `iconClass()`) when `showIcon()`, the name span (`typeAlias ?? typeName`) when `showTypeName()`, and `&nbsp;(typeName)` when `showBaseTypeName() && typeAlias()`. Nothing renders when neither name is set. `entity-card`'s badge is this component (UIC-12's rendered output is unchanged — its spec stays green as the regression proof). |
| UIC-18 | `details-navigation` renders `box.is-paddingless` \> `dropdown.is-up.is-right` with the toggle `button.is-text.is-large` (caller `toggleIcon`; toggles `is-active`, the Bulma CSS does the rest), and a `nav.menu` with the `menu-label` label (caller-supplied, DD-136) + the `ul.menu-list` holding projected `li`s. The component owns no scroll, no anchors: items are caller markup, so the app's directive (DD-191) wires them. |
| UIC-19 | `section-stats` renders `nav.level` with one `level-item.has-text-centered` per item: `p.heading > a` (href `#target`, emits `itemClicked(target)` on activation) + `p.title` with the count. `items()` is the whole input; counts arrive rendered-as-text from the caller. The default-details bar is one item, the gov-quality bar three — one component, both shapes. |
| UIC-20 | Every component: chrome strings are caller-supplied inputs with the legacy English defaults (DD-136); icons arrive as `IconDefinition` inputs (UIC-15); each ships a story, interactive ones a `play()` test (UIC-10's pattern); the purity gate stays green (DD-131/DD-137). The legacy defaults chosen here are the catalogue's English values of the existing bridge keys (`search.components.classification.isPropagated`/`.originates`, `search.components.term.term`, `search.details.components.navigation.details`). |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit pinned by 7-0), so reviewers can compare:

- `apps/atlas/src/app/search/components/classification/classification.component.{ts,html,scss}` — the chip; its `classification.service.ts` (type-definition lookup) and `classification-source/` (repository-fed media rows) are the data wiring not ported; the chip's loading tag and propagated dropdown are
- `apps/atlas/src/app/search/components/term/term.component.{ts,html}` — the chip's twin (`is-info` lead, one label); its `term.service.ts` is data wiring
- `apps/atlas/src/app/search/components/type-name/type-name.component.{ts,html,scss}` — the badge; `iconsByType` (`search/meta`) is app meta, an input here
- `apps/atlas/src/app/search/details/components/navigation/details-navigation.component.{ts,html}` — the nav shell; `details-navigation-item.directive.ts` (scrollIntoView) stays app-side (DD-191)
- `apps/atlas/src/app/search/details/default/default-details.component.html`

  - `details/gov-quality/gov-quality-details.component.html` — the two count bars `section-stats` unifies; `details/details.component.html` — the chip call sites (`classifications-list`, the meanings row)

## Deviations

None against Apache Atlas: these are Aurelius product components; Atlas's own details UI is its dashboard (ADR 046, the parity reference stays).

Against the Aurelius product, the intended differences are recorded in [design-log](<https://aureliusenterprise.github.io/feat-validate-job-in-devcontainer/architecture/conversion/design-log/index.md>): DD-189 (the chip is the classification chip — the term variant is the same atom, colour an input; sources project in), DD-190 (the badge is extracted from `entity-card`, which then consumes it — 7.13's inlining reversed, with UIC-12's spec as the regression proof), DD-191 (the nav is a shell; the scroll directive stays app-side), DD-192 (the count bar is one component for both call sites). Sequencing inside the webapp track, as 7.13's "pulled forward" note — no `deviations.md` entry.

## Acceptance

- Vitest (unit), naming UIC ids in the test titles:

  - `libs/angular/aurelius-atlas-ui/src/lib/classification-chip/classification-chip.component.spec.ts` (UIC-16, UIC-20)
  - `libs/angular/aurelius-atlas-ui/src/lib/type-name/type-name.component.spec.ts` (UIC-17); `entity-card.component.spec.ts` unchanged and green as the extraction's regression proof
  - `libs/angular/aurelius-atlas-ui/src/lib/details-navigation/details-navigation.component.spec.ts` (UIC-18, UIC-20)
  - `libs/angular/aurelius-atlas-ui/src/lib/section-stats/section-stats.component.spec.ts` (UIC-19, UIC-20)
- Storybook: a story per component; `nx test-storybook aurelius-atlas-ui` — the toggle and `itemClicked` `play()` interactions pass (UIC-20, the UIC-10 pattern).
- Purity gate green; consumer regression: `nx test aurelius-atlas-webapp -c ci` (185) and `nx test aurelius-atlas-frontend-example -c ci` (75) unchanged — no app consumes a new component yet; `nx build aurelius-atlas-ui` compiles the extended public API.
- Umbrella checks: `nx lint aurelius-atlas-ui aurelius-atlas-webapp`; `nx e2e aurelius-atlas-webapp` unchanged (the screen wiring is 2.3+7.6).

### Definition of done, in order

1. `nx test aurelius-atlas-ui -c ci` green (the four specs + entity-card regression).
2. Stories render; `nx test-storybook aurelius-atlas-ui` green.
3. `nx lint aurelius-atlas-ui`, `nx build aurelius-atlas-ui` green; purity gate green.
4. Consumer regressions green (`nx test aurelius-atlas-webapp -c ci`, frontend example).
5. `libs/angular/aurelius-atlas-ui/README.md` and `AGENTS.md` list the new components; spec status → `done`, roadmap row flipped, DD-189..192 accepted.
