# 7.42 Webapp test harness

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-868 (here). No new rule ids. Cites AVS-01/02/04/06/13 (7.20,
  16.5d, 16.5j: the card and view shapes the builders answer), APC-07 (7.3: the
  Keycloak double carries no refresh loop), DET-15/17/56/65 (7.20, 16.5b, 16.5e,
  16.5j: the reads the settle helper and the section and score builders feed),
  EDT-09/DD-324 (7.7a, 16.5c: the write gate the double must satisfy),
  SHL-10/DD-300/DD-324 (7.1: the config and client id the gate reads),
  TNW-02/03/07/DD-636 (15.6: the tenancy answer), WBP-02/SHL-01/SHL-09/SHL-10/
  UIC-07 (7.0, 7.1, 7.2: the purity gate the harness stays inside), and ADR 064
  (16.5: the view doors whose URLs the constants name).

## Scope

Fourteen webapp specs built their own copy of the world a screen test needs.
Before this increment, 21 spec files wired the HTTP and router providers by hand,
nine declared a door URL constant, and ten kept their own whitespace collapse.
The copies drifted. A spec that asked for a door answer missed a field another
spec happened to set, an inline config carried no `atlasClientId` while the write
gate read that field (EDT-09, DD-324), and ten copies of one helper could not
drift back into step with each other.

This increment moves that world into `src/testing/` and ports the specs onto it:

- `api.ts` holds every door URL the specs assert on: 21 constants plus the audit
  URL builder. A spec names `VIEW_URL`, never the string.
- `auth.ts` holds the Keycloak double. One builder covers a role gate, a session
  read, and a sign-in probe. Its `hasResourceRole` reads the same token claims
  the real gate reads, so a spec of the gate itself exercises the real path.
- `config.ts` holds the fake runtime config and the tenancy provider. The config
  is a whole, valid `AppConfig` built the way `parseAppConfig` builds the real
  one, so a screen that starts reading a second config field fails in this
  increment rather than the next.
- `providers.ts` holds the provider set every routed screen spec configures by
  hand: real HTTP with the testing controller, an empty router, a valid config,
  a Keycloak double, tenancy off.
- `view-fixtures.ts` holds the entity builders (`card`, `view`, `ends`,
  `sectionsOf`, `quality`, `propagated`, `crumb`, `ruleScore`). They fill the
  fields a door always answers (AVS-06) and take an override for what the test
  names.
- `dom.ts` holds the whitespace collapse and the typedef-walk settle.
- `index.ts` is the barrel, and `harness.spec.ts` proves the harness itself.

Ported specs: `details`, `entity-editor`, `entity-relationship-input`,
`editor-state`, `results`, `search-layout`, `browse`, `settings-panel`,
`header`, `footer`, `catalogue-card`, `classification-combobox`,
`gov-quality-cards`, and `related-sections.state`. Two specs that pin a realm or
a store-shaped view keep their own value, built on the harness value instead of a
parallel literal.

It does **not** deliver: production-code changes (no file under `src/app/`
except specs changed), the layer rules for `src/testing/` (later phase),
`quality-fields.spec.ts` (its provider pair carries no shared world, so the port
is churn), or a harness double for the header spec's Logout probe (that spec
asserts the identity of one `vi.fn()` it hands to Keycloak, which the harness
double does not model — see DD-868).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The harness answers the real gate.** `provideScreenTest({ keycloak: {
atlasWrite: false } })` makes `canWriteEntities()` (EDT-09, DD-324) read false,
  and the default makes it read true. Proven by `src/testing/harness.spec.ts`,
  which runs the real helper in an injection context rather than asserting the
  double's own return value.
- **A fixture omits what a door omits.** `view()` carries the card fields, the
  qualified name, the empty tag list, and the two attributes a door always
  answers. `sections`, `quality`, `businessMetadata`, and `ruleScores` stay
  absent unless a test names them (AVS-06), so a screen reading a field the wire
  leaves out fails in the spec that added the read.
- **A ported spec names a constant, not a path.** The fourteen ported specs
  contain no literal door path: each names `VIEW_URL`, `SEARCH_URL`, or its
  sibling. Service specs outside this increment keep their own path
  (`retry-http.interceptor.spec.ts` proves the retry's status matrix, and
  `dashboards.service.spec.ts` reads one route of its own) — the harness's
  constants cover the screen doors today, and a later port adds one there.
- `scripts/check-webapp-purity.sh` (WBP-02) still enforces the legacy-construct
  rules, and the ports leave it green.

## Aurelius origin

Nothing here ports behaviour. The surface it replaces is Aurelius' own spec code,
which grew as each slice copied the previous slice's `TestBed` block. The
vendored dashboards (`apps/aurelius-atlas-dashboard`) are untouched.

## Deviations

None. No rule of Apache Atlas is involved.

## Acceptance

- `npx nx test aurelius-atlas-webapp -c ci` is green: 1,045 tests in 80 files,
  the same count per file as before the ports. The test-count check is
  `git stash` A/B over `grep -cE '^\s*it\('` per changed spec.
- `npx nx lint aurelius-atlas-webapp` reports no errors, and
  `scripts/check-webapp-purity.sh` passes as the `dependsOn` of `test`.
- `npx nx build aurelius-atlas-webapp` is green with `src/testing/**` in
  `tsconfig.app.json`'s `exclude`, which proves the harness never reaches the
  bundle. The harness is type-checked by `nx test` instead: a deliberate type
  error in `src/testing/dom.ts` fails the test target's bundle step, and the
  build target does not see it.
- The harness's own spec (`src/testing/harness.spec.ts`, 4 tests) covers the
  gate, the fixture defaults, and both DOM helpers. Vitest names it, and no rule
  id covers it: it tests test code.
