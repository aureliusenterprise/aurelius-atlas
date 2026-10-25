# 7.5 Browse landing page

- **Status:** in progress
- **Pull request:** [\#101](<https://github.com/aureliusenterprise/aurelius-atlas/pull/101>)
- **Records:** ADR 053; DD-143, DD-144; relies on ADR 007, DD-126, DD-128, DD-134, DD-135, DD-136, DD-140, DD-141, UIC rules (7.2)

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/fix-tls-stacks-own-mounted-certs/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

Port the Aurelius **landing page** — the `browse` screen the router redirects to (`'' -> /search/browse`, SHL-04) — replacing the 7.1 placeholder with the real screen:

- the hero block (title + description, `browse.component.html`)
- the three context cards — business, technical, governance — each with its title, description, exploring text, and info icon (the three section components)
- the three info modals: a description paragraph plus a static table of (icon, type name, description) rows, composed from the 7.2 `aurelius-atlas-ui` `modal` and `sortable-table` (the modal table data is the legacy `tableData` constants — static content, localized by dictionary key)

The page is the product's first real screen with zero API dependency: every string lives in the XLIFF bridge already (the `search.browse.*` keys are all present), and no data is fetched. This is what "the landing page" means for the port: the screen as it renders before any search exists.

Explicitly not delivered here, with the increment that will:

| Deferred | Lands with | Why |
| --- | --- | --- |
| The cards' search fields (`simple-search-input`) and the "explore" buttons (`directTo*`) | The search slice (7.4, gated by server 4.1 + 2.3 — DD-140) | Both are search navigation: they set `SearchService.query/filters` and route to `/search/results`, a screen whose API does not exist yet. Porting the affordance without its destination is the speculative build DD-140 rejects (DD-143) |
| The Shell chrome (header, footer, global nav) | The search slice | Aurelius wraps every screen in `libs/shell`, and the header's centrepiece is the global search bar; wiring the chrome is one decision with the search entry point, not two (DD-143) |
| `directToUser` (governance card: search the signed-in user's e-mail) | The search slice | Same: search navigation; the e-mail is now available from Keycloak, the results page is not |
| Search client, results, details | 7.4 / 7.6, after server 4.1 / 2.3 | API not ready (user decision, 2026-10-20: hold all search until the API is ready) |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name (`@pytest.mark.covers(..., rules=["BRW-NN"])`; TS/e2e tests name the id in the test title).

| Id | Rule |
| --- | --- |
| BRW-01 | `/search/browse` renders the hero block — the `search.browse.title` heading and the `search.browse.description` paragraph, keeping the `#browse-placeholder` id the 7.1 shell tests anchor to — followed by the three context cards in Aurelius's order: business, technical, governance |
| BRW-02 | Every visible string on the page carries its legacy dictionary key as its i18n id (`@@search.browse.<context>.<key>`), with no literal prose in templates (WBP-05); the keys all exist in the XLIFF bridge, so both locales render fully (the completeness spec proves it) |
| BRW-03 | Each card's info icon opens that card's info modal: a description paragraph and a table of the legacy static rows — business: data domain / data entity / data attribute; technical: system / collection / dataset / field; governance: domain lead / data owner / data steward — each row an icon, a type name and a description, every string localized by its `search.browse.<context>.infoModal.*` key; the modal opens on icon click and closes via the ui-lib modal's close affordance |
| BRW-04 | The landing page issues no HTTP requests: component specs prove an empty `HttpTestingController`, and the e2e landing scenario records zero `/api` calls (the screen exists before its API does) |
| BRW-05 | The page is zoneless/Angular-idiom (standalone, OnPush, signals, `inject()`): modal open state is the ui-lib modal's model signal, card data is static consts, no store, no `BehaviorSubject` (DD-135, purity gate) |
| BRW-06 | No search affordance is ported: no search field, no explore button, no route to results (DD-143); the page's links and buttons are exactly the info-icon opens |
| BRW-07 | e2e (authenticated, chromium/firefox/webkit): the landing renders all three cards with localized titles; clicking a card's info icon opens its modal with its type-name rows visible; closing returns to the landing; the nl-NL locale renders the Dutch card titles |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit pinned by 7-0), `apps/atlas/src/app/search/browse/`:

- `browse.component.{ts,html}` — the hero + three-card grid (`BrowseComponent`)
- `business-context/`, `technical-context/`, `governance-responsibilities/` — the section components (their `directTo*` methods and `simple-search-input` are the deferred affordances)
- `*/info-modal/*-info-modal.component.{ts,html}` — the static type tables (`tableConfig` / `tableData` constants)

## Deviations

None against Apache Atlas: this slice is an Aurelius product screen, and Atlas has no equivalent UI.

Against the Aurelius product, one intended difference is recorded in [design-log](<https://aureliusenterprise.github.io/fix-tls-stacks-own-mounted-certs/architecture/conversion/design-log/index.md>): the landing page is ported **statically** — search affordances and the Shell chrome arrive with the search slice (DD-143), because the user has put all search work on hold until the server search API (4.1, with 2.3 entity read) exists.

## Acceptance

- Vitest (unit, `nx test aurelius-atlas-webapp -c ci`):

  - `search/browse/browse.component.spec.ts` — hero + three-card order (BRW-01), no outstanding requests (BRW-04)
  - card component specs (business/technical/governance) — strings render from the catalogue keys (BRW-02), info icon opens the modal (BRW-03), no search affordance in the DOM (BRW-06)
  - info-modal specs — table rows match the legacy `tableData` (BRW-03)
  - `i18n-completeness.spec.ts` — every `@@search.browse.*` id used by the new templates exists in both locale catalogues (BRW-02)
- e2e (`nx e2e aurelius-atlas-webapp`): landing cards render (BRW-07), modal open/close flow (BRW-03/BRW-07), nl-NL titles (BRW-02/BRW-07); the 7.1 hero assertions (`EN_PLACEHOLDER`/`NL_PLACEHOLDER` on `#browse-placeholder`) stay green — the hero keeps its id (BRW-01)
- Purity gate green (BRW-05); example app untouched.
