# 7.24 Data quality rules and the governance banner

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DET-35..36 (the field row of DET-16, amended into DET-24/DET-25),
  EDT-21..24, UIC-36..39; adds DD-444..448 (here) and DV-144 to
  [deviations](../../../../docs/architecture/conversion/deviations.md) in the
  implementation PR; relies on DET-17..22/DD-368 (the section machinery),
  DD-369 (this slice closes its field-box and editor rows, the rest stands),
  VE-01..05/DV-67 (the validate-entity mock is the backend), DV-75/AUX-04 (the
  app verifies the browser client's token), DD-384/DD-387 (the aux data-path
  pattern), DD-139/DD-142 (client-composed prefix, TLS-verified proxy),
  DD-223 (the e2e suite owns its named services), CHT-20..32/CHT-60..73 (the
  chart joins and the ingress allow).

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The legacy app carried two quality concepts. _Data quality_ rules
(`m4i_data_quality` entities) measured a field's content. _Governance quality_
rules (`m4i_gov_data_quality`) measured a record's completeness, and the editor
showed the verdicts live while a record was edited. The legacy score numbers
came from Flink jobs that computed `dqscore_*` documents
([DD-369](../7-21a-details-sections/design.md#dd-369-sourceless-sections-render-nothing-not-zeros)).
This product runs no rule evaluator, so the scores, the pies, and the compliant
per-entity verdicts stay out (the 7.25 row). What the store already holds is
the rules themselves, the field→rule association, and the deployed 8.3 mock
that answers the editor's validation call.

Delivered here:

- the field page's **Data Quality Rules box** (DET-35): a card section seeded
  from the field's own `dataQuality` relationship end, drawn by the 7.21a
  machinery unchanged, and its stats-bar and side-navigation entries back in
  legacy order (DET-36). This closes the `#related-rules` row of DD-369's
  hold-out list.
- the editor's **governance banner** (EDT-21..24): the draft entity goes to the
  8.3 mock at `POST /`, and the answer's rule lines render under the form
  controls they name, on open and on every change (debounced), with failures
  swallowed as the legacy did. The browser's way there is the 7.22a pattern
  applied to the second aux API: a `/validate-entity/` nginx location, a
  bearer token, and the optional `validateEntityBaseUrl` config key.
- the four **dumb quality components** the 7.25 return needs (UIC-36..39):
  `data-quality-pie`, `quality-dimension-list`, `gov-quality-list`,
  `quality-badge`. They ship with stories and unit tests only, before their
  data exists (DD-447).

Explicitly not delivered here, with the increment that will:

| Not delivered                                                      | Lands with    | Why                                                                                                                |
| ------------------------------------------------------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------ |
| The field page's Data Quality score box and stat (`#data-quality`) | 7.25          | No `dqscore_*` source (DD-369, unchanged)                                                                          |
| The Governance Quality Rules box on the nine details pages         | 7.25          | Needs per-entity verdicts the evaluator produces                                                                   |
| The rule cards' DQ/dimension sort options                          | 7.25          | The sort list stays the DET-19 pair until real score and dimension rows exist (DD-368's uniform list)              |
| Card quality badges and pies                                       | 7.25          | `entity-card`'s `showQuality` slot stays off, the seam DD-367/DD-369 left open                                     |
| The compliant/non-compliant cards of a `m4i_gov_data_quality` page | 7.25          | Unchanged                                                                                                          |
| The quickview's Data governance addon                              | 7.25          | 7.22c's deferral, unchanged                                                                                        |
| The search-side data-quality list and DQ result cards              | 7.25          | The App Search `data_quality` surface stays retired (ADR 054), and the evaluator has no row yet                    |
| Real (non-mock) verdicts                                           | 7.25 + engine | DV-67 stands: the deployed backend answers the fixed mock document, and this slice renders exactly what it returns |

## Semantics

TS tests name the ids (the 7.21a convention). The mock's contract is cited,
not restated: VE-01 owns the route, VE-02 the document, VE-03 the token.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-35 | The `m4i_field` layout row (DET-16) gains a third card section: anchor `related-rules`, title `search.details.field.dataQualityCards.title`, seed key `dataQuality`. DET-17..22 apply unchanged: ACTIVE seed entries with a guid, deduped, chunked bulk resolve, client-side search, sort, and paging. A field whose end is empty renders the box at its zero count, as every DET-17 section does (DET-27’s Child Entities case).                                                                                                                                                                                                                                                                     |
| DET-36 | The field layout's stats bar gains the `search.details.field.dataQualityRules` stat between Child Fields and Properties, its value the DET-24 section count, and its side navigation gains the matching link. The `search.details.field.dataQuality` score stat and its link stay out (DD-369, unchanged).                                                                                                                                                                                                                                                                                                                                                                                            |
| EDT-21 | `ValidateEntityService.validateEntity(entity)` issues `POST {baseUrl}/` with the draft entity as the body and answers the typed `EntityValidationResponse`: one entry per card key (`name`, `definition`, `dataEntity`, `domainLead`, the mock's set), each `{ items, isNonCompliant }` with `gov_quality`-shaped items (`result.raw`, `compliant.raw` as `"0"`/`"1"`, `dataqualityruledimension.raw`). The method adds no query string. VE-01/VE-02 are the contract.                                                                                                                                                                                                                                |
| EDT-22 | The browser reaches the aux API same-origin at `/validate-entity/`: the webapp's nginx gains the location (TLS-verified upstream, name pinned, the DD-142 posture, the user token carried by the `bearerTokenConfig` entry for the new prefix), `/config.json` gains the optional `validateEntityBaseUrl` key (default `/validate-entity`, parsed like `lineageModelBaseUrl`), the dev proxy gains the `/validate-entity` → `:21003` entry, `nx serve aurelius-atlas-webapp` gains the `aurelius-atlas-validate-entity:serve` dependency, and the webapp's e2e compose carries the container (DD-223). No auth change lands on the app: VE-03 already verifies the browser client's audience (DV-75). |
| EDT-23 | The editor validates the draft entity when the drawer opens and after every form change debounced 200 ms (the legacy trigger). A failed call (any 4xx/5xx, or no answer) renders no lines and raises no alert (the legacy's quiet swallow), and the drawer stays usable. A newer draft replaces an older answer in flight (the generation guard, DET-08's sibling).                                                                                                                                                                                                                                                                                                                                   |
| EDT-24 | The drawer renders one line per item of a response card whose key names a rendered form control: the success or warning icon from `compliant.raw` (`"1"`/`"0"`), then the `result.raw` text, at the legacy's small size. A control with no card of its key renders nothing, and a card with no control of its key renders nothing (the mock answers four keys for every entity).                                                                                                                                                                                                                                                                                                                      |
| UIC-36 | `data-quality-pie`: inputs `value` (0..100) and `size` (px). The two-layer CSS pie of the legacy stylesheet (the green arc over the red ring), the host `title` the `value` percent. No data knowledge beyond the number.                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| UIC-37 | `quality-dimension-list`: inputs `dimensions` (`{ dimension, score (0..1), count }[]`, caller's order) and `notAvailable` text. The empty list shows the placeholder; else one row per entry: the UIC-36 pie, the score as a percent to one decimal at most (the legacy `percent: '1.0-1'`), the dimension word, the count (the legacy list's rows).                                                                                                                                                                                                                                                                                                                                                  |
| UIC-38 | `gov-quality-list`: inputs `nonCompliant` (`{ message, detail }[]`) and `loading`. Loading shows the spinner tag, the empty list the green check, a non-empty list the warning icon with the count and a hover dropdown that lists the rows (message as the heading, detail as the line). The legacy's infinite-scroll container stays out; the rows are the caller's page.                                                                                                                                                                                                                                                                                                                           |
| UIC-39 | `quality-badge`: the card quality-column content: the UIC-36 pie beside the percent text to one decimal at most (the legacy card's `dqscore` badge). It projects into the `entity-card` `[card-quality]` slot (7.13's `showQuality` input) when a later slice turns it on.                                                                                                                                                                                                                                                                                                                                                                                                                            |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
cited by path so a reviewer can compare:

- `apps/atlas/src/app/search/details/field/data-quality-cards/**` — the box
  DET-35 ports: its query ran against the App Search `data_quality` index with
  the filter `fieldguid: [entityId]` and the sorts `name`,
  `dataqualityruledimension`, `dqscore`. The seed source and the two score
  sorts change (DD-444, the not-delivered table), the box does not.
- `apps/atlas/src/app/search/details/field/field-details.component.html` — the
  `#related-rules` box between `#data-quality` and `#gov-quality`, and the
  stats pair (`search.details.field.dataQualityRules` between Child Fields and
  Properties) DET-36 restores. The score box and the governance box stay out.
- `libs/atlas/api/src/lib/gov-quality/gov-quality-api.service.ts` and
  `gov-quality-api-client.service.ts` — the client EDT-21 twins:
  `POST validate_entity` with the entity, `EntityValidationResponse` read as
  the cards consume it.
- `apps/atlas/src/app/search/components/editor/services/entity-validate/entity-validate.service.ts` —
  the trigger EDT-23 ports: the opened entity merged with the form's
  `valueChanges` debounced 200 ms, a quiet task, `catchError` to the empty
  answer.
- `apps/atlas/src/app/search/components/editor/components/gov-quality-display/gov-quality-display.component.{ts,html}`
  — the line markup EDT-24 ports: the success/warning icon by `compliant.raw`,
  the `result.raw` text, `is-size-7`.
- `apps/atlas/src/app/search/components/data-quality-pie/**`,
  `data-quality-list/**`, `cards/components/governance-quality-list/**`, and
  the `dqscore` badge column in `cards/*/[type]-details-card.component.html` —
  the render UIC-36..39 rebuild as dumb components (DD-447).
- `apps/atlas/proxy.conf.json` (`/validate_entity` → the legacy Flask app on
  `:7200`) — what EDT-22's location replaces.

## Deviations

Against Apache Atlas: none, no server surface is added or changed. Against the
Aurelius product:

- **DV-144** (joins `deviations.md` in the implementation PR): the legacy
  serves the API at `validate_entity` (an underscore path of its deployment
  proxy); Aurelius Atlas serves it at `/validate-entity/` behind the webapp's
  own nginx, beside `/api/`, `/otel/`, and `/lineage-model/` (DD-445, the
  DV-142 sibling).
- the rule box reads the field's `dataQuality` relationship end, not the
  App Search `data_quality` index (DET-35, DD-444). That index surface is
  already retired by ADR 054, so this is that decision's consequence, not a
  new one. The card columns the legacy filled from the rule documents
  (`dataqualityruledimension`, `dqscore`) come from the rule entity itself,
  and the score column has no source and stays out (DD-369).
- the banner's verdicts are the mock's canned rows (DV-67 restated, not new).
  This slice renders the deployed contract exactly, so the evaluator's return
  (7.25) needs no rule change here.

## Acceptance

- Vitest (unit): `section-config.spec.ts` and `related-sections.state.spec.ts`
  cover DET-35/DET-36 (the field row's section, stats, and nav in legacy
  order, the empty end rendering no box). `validate-entity.service.spec.ts`
  covers EDT-21 (route, body, typed read). The webapp's config spec covers the
  new key's parse and default, the interceptor spec the new prefix (EDT-22).
  `entity-editor.component.spec.ts` covers EDT-23 (open, debounce, swallow,
  generation guard) and EDT-24 (lines by card key, nothing for unmatched
  controls). The ui library specs cover UIC-36..39 per component.
- Storybook: one story per new component (UIC-36..39), the visual pins living
  there per the repo rule (e2e guards interactions, not pixels).
- e2e (Playwright, three browsers, the built image with the aux container in
  the suite's own compose): the field page shows the rules box, its cards, and
  the restored stat and link over the seeded corpus (DET-35/DET-36). The
  editor drawer shows the mock's banner lines under Name and Description
  (EDT-24). An aborted validation call (`page.route` abort) leaves the drawer
  usable with no alert (EDT-23).
- `uv run aurelius-atlas-trace check` reports no gap for the new ids, and
  `java-map.md` gains the two origin rows in the same PR.
