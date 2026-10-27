# 7.13 UI components: details set

- **Status:** in progress
- **Pull request:** [\#104](<https://github.com/aureliusenterprise/aurelius-atlas/pull/104>)
- **Records:** DD-154, DD-155, DD-156 (the dark ink ramp); relies on ADR 053, DD-135, DD-136, DD-142

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits, and of the design-system track opened by [7.2](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-igorshubovych-markdownlint-cli-0.49.1/architecture/conversion/increments/7-2-design-system/index.md>), whose UIC rule ids (UIC-01..10) this increment continues (UIC-11..15).

## Scope

Port four more dumb, signal-driven components into `aurelius-atlas-ui` — the pieces the 7.6 (details) screens will compose, extracted early because their presentation is pure and their data wiring is not needed to build, spec and story them:

- **`breadcrumbs`** ← `apps/atlas/src/app/search/components/bread-crumbs` — the Bulma `nav.breadcrumb` trail with per-item icons and a warning chip. The legacy component's `BreadCrumbsService` (a redux `BasicStore`) and its `$APP_SEARCH_DOCUMENT_PROVIDER` injection are data wiring: the ported component takes `items`/`warning`/`activeGuid` inputs and emits `itemClicked`; the trail-building service arrives with 7.6.
- **`entity-card`** ← `apps/atlas/src/app/search/components/cards/details-card` (+ its `entity-type-name`/`type-name` badge) — the Bulma card: title link, type-name badge, `[card-content]`/`[card-quality]` slots, loading state. The legacy `cardsByType`/`ngComponentOutlet` per-type bodies are app anatomy (7.6); the port projects content. The card emits `entityClicked(guid)` — DD-154.
- **`properties-item`** ← `apps/atlas/src/app/search/details/components/properties/properties-item` — the property-value renderer: strings/numbers/booleans as title-cased text, link arrays as anchors (emitting `itemClicked`), empty arrays as the N/A label.
- **`select`** ← `libs/components/src/lib/select` — the Bulma select field: label, options, null/no-data messages, timestamp display, invalid help, and a search button that emits `searchRequested` — the legacy embedded `SearchModal` (repository-fed table) is app wiring, wired in 7.7: DD-155.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| `simple-search-input` | already ported as `SearchField` (7.2, DD-135) |
| Trail-building service, `iconsByType` type→icon meta, `search/details` route wiring | 7.6 (details) — the lib defines, the app composes |
| The select's search modal + repository data | 7.7 (editor), via `searchRequested` (DD-155) |
| `markdown`, `tree`, `date-picker` (third-party deps: `ngx-markdown`, `@angular/material`) | the 7.2 deferral stands; needs its own DD |
| Wiring these components into webapp screens | 7.6 / 7.7 |

## Semantics

| Id | Rule |
| --- | --- |
| UIC-11 | `breadcrumbs` renders the Bulma `nav.breadcrumb.is-small.has-arrow-separator`; items are anchors, the `activeGuid` item gets `li.is-active`; a `warning` renders the legacy warning chip; clicking/Enter on a crumb emits `itemClicked(guid)`. |
| UIC-12 | `entity-card` renders the Bulma card: title anchor (emits `entityClicked(guid)` on click/Enter), the type-name badge (`icon-text`: icon, `typeAlias ?? typeName`, optional base-type suffix), `[card-content]` and `[card-quality]` projection slots; `loading()` swaps the body for the legacy loading row (label + `loader`). |
| UIC-13 | `properties-item` renders a string/number/boolean `value` title-cased; an array of `{guid, displayText}` as anchors emitting `itemClicked(guid)`; an empty array as the N/A label; other objects render nothing (the legacy behaviour). |
| UIC-14 | `select` renders the Bulma field: label, fullwidth native select bound two-way to `value` (`model()`), options from `options()` + `displayField()`, the `nullInputMessage`/`noDataMessage` placeholder option, `isTimestamp()` formats option labels, `disabled()`, `invalid()` paints `is-danger` + the required help, the search button emits `searchRequested` (DD-155). |
| UIC-15 | Every component: chrome strings are caller-supplied inputs with the legacy English defaults (DD-136); icons arrive as `IconDefinition` inputs (`iconsByType` is app meta); each ships a story, interactive ones a `play()` test; the purity gate (DD-131/DD-137) stays green. |

## Aurelius origin

The Aurelius (legacy) sources whose presentation this ports, so reviewers can compare: `apps/atlas/src/app/search/components/bread-crumbs/`, `apps/atlas/src/app/search/components/cards/details-card.component.*` + `components/entity-type-name/` + `components/type-name/`, `apps/atlas/src/app/search/details/components/properties/properties-item/`, `libs/components/src/lib/select/` (+ `control-shell`).

## Deviations

- Pulled forward: 7.2's deferral table sent `select` to 7.7 and the breadcrumbs/card anatomy to 7.4–7.6. Their **presentation** is pure, so it is ported now as dumb components; the **data wiring** each source carried (redux stores, repository services, `cardsByType`, the search modal) stays in its original slice. No `deviations.md` entry — this is sequencing inside the webapp track, not an Atlas deviation.
- DD-154: the card emits `entityClicked` instead of the legacy self-navigation.
- DD-155: the select emits `searchRequested`; the search modal is app wiring; the reactive-form/`ControlShell` base dissolves into `model()` (as DD-135 did for `SearchField`), and the `compareWith` default is strict equality, not lodash `isEqual`.

## Acceptance

- `libs/angular/aurelius-atlas-ui/src/lib/{breadcrumbs,entity-card,properties-item,select}/*.spec.ts` (Vitest) — behaviours naming UIC ids in the test names (UIC-11..14).
- `nx build-storybook aurelius-atlas-ui -c ci` compiles the new stories; `nx test-storybook aurelius-atlas-ui` — the `play()` interactions pass (UIC-10 pattern).
- `check-purity` (the lib `test` target) stays green (UIC-15).
- Consumer regression: `nx test aurelius-atlas-webapp -c ci` (87) and `nx test aurelius-atlas-frontend-example -c ci` (75) unchanged — the apps consume no new component yet; `nx build aurelius-atlas-ui` compiles the extended public API.
- Umbrella checks: `nx lint` both projects; `nx e2e aurelius-atlas-webapp` unchanged.

### Definition of done, in order

1. `nx test aurelius-atlas-ui -c ci` green.
2. Every story renders; `nx test-storybook aurelius-atlas-ui` green.
3. `nx lint aurelius-atlas-ui`, `nx build aurelius-atlas-ui` green.
4. `libs/angular/aurelius-atlas-ui/README.md` and `AGENTS.md` list the new components.
