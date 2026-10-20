# aurelius-atlas-webapp

The Aurelius Atlas webapp — the legacy Aurelius interface rewritten in Angular
idiom, slice by slice (ADR 053, conversion increments 7.x). This file covers
wiring specific to this app; workspace-wide rules live in the root `AGENTS.md`
and the increment specs in `docs/architecture/conversion/increments/`.

## Layout

- `src/app/` — standalone, zoneless components; `app.config.ts` wires providers,
  `routes.ts` the shell routes; `config.ts` is the typed `/config.json` shape
- `src/locale/` — **generated** XLIFF catalogues (the Aurelius dictionary bridge,
  DD-039); regenerate with `node tools/generate-legacy-catalogue.mjs`, never hand-edit
- `tests/fixtures/` — the vendored legacy dictionaries (parity reference, SHL-08)
- `scripts/check-webapp-purity.sh` — the legacy-construct gate (WBP-02); runs as a
  `dependsOn` of `test`, so CI enforces it
- `dev/config.json` — runtime config, bundled **only** in the development build
- `proxy.conf.json` — dev-server proxy: `/api` → 8000, `/otel` → 4318 (HTTPS, CA-verified)
- `e2e/` — pytest + Playwright (chromium, firefox, webkit) against the built image

## Porting rules (every slice)

- Read the increment spec in `docs/architecture/conversion/increments/` first;
  implement its rule ids with `@pytest.mark.covers`-style traceability on the
  tests (`@pytest.mark.covers` is Python; TS tests cite the rule id in the test name).
- Angular idiom only: signals for state, standalone components, `inject()`,
  zoneless. The purity gate blocks NgModules, `@models4insight/`, ngx-translate,
  `environment.ts`, and state-owning `BehaviorSubject`s — do not loosen it to land code.
- Dictionary strings: reference the existing XLIFF ids (`@@a.b.c`); never add
  strings to components that aren't in the catalogue — extend the fixtures and
  regenerate when the legacy app gains keys.
- The legacy source for parity comparison is the clone at
  `.scratch/aurelius` (commit-pinned; see 7-0 spec).

## Commands

```bash
nx serve aurelius-atlas-webapp          # 4300 (nl-NL: -c nl-NL → 4301); long-running, run detached
nx test aurelius-atlas-webapp -c ci     # never without -c ci (watch mode hangs)
nx run aurelius-atlas-webapp:check-purity
nx lint aurelius-atlas-webapp
nx e2e aurelius-atlas-webapp            # builds image; starts keycloak + observability (needs Docker + SOPS key)
nx extract-i18n aurelius-atlas-webapp   # template catalogue refresh only (bridge files are source of truth)
```

Offline-safe: `test -c ci`, `lint`, `check-purity`, `extract-i18n`,
`docker-build`. Needs the SOPS key: `serve`, `e2e`. Needs Docker: `serve`, `e2e`.

## Conventions

- Components stay presentational; state in signal stores under the feature
  folder; HTTP only via the REST client lib slice 7.3 introduces.
- Every new component gets a Storybook story (7.2 wires the ui library pattern);
  every new route gets an e2e scenario.
- Template strings carry `i18n="@@legacy.key"` markers matching the catalogue ids.

## Removal

The webapp is a conversion-track app: removing it means stopping the 7.x
roadmap. Remove together: its `mkdocs.yaml` nav entry (none yet), the 7.x
roadmap rows in `docs/architecture/conversion/index.md`, and the clone
reference in `docs/architecture/conversion/increments/7-0-webapp-foundation.md`.
The example app (`aurelius-atlas-frontend-example`) stays — it is the pattern
reference and spine member; the webapp only replaces it once 7.x completes.
