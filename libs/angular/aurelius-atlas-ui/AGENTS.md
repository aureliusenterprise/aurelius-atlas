# aurelius-atlas-ui

Shared presentational Angular components. This file covers wiring specific to this
lib; workspace-wide rules live in the root `AGENTS.md` and the Angular lib recipe
in `libs/angular/AGENTS.md`.

## Layout

- `src/lib/<component>/` — one folder per component with `.spec.ts` and
  `.stories.ts` colocated; `src/index.ts` is the public API
- `.storybook/` — Storybook config, styles (imports brand tokens), and assets
- `ng-package.json` / `tsconfig.lib*.json` — ng-packagr-lite build config

## Wiring Checklist

- `tsconfig.base.json` — `aurelius-atlas-ui` path alias used by the frontend.
- `package.json` — peer deps: keep in sync with the workspace Angular major
  (currently stale at `^21` — update when touching this file).
- Styling comes from `@aurelius/atlas-brand` tokens; new colours belong there, not here.
- `chromatic` target depends on `decrypt` (SOPS) for the Chromatic token.
- `check-purity` — runs `apps/aurelius-atlas-webapp/scripts/check-webapp-purity.sh`
  from the workspace root (one script, one list of banned constructs; it greps
  `libs/angular` too, DD-048), wired as a `dependsOn` of `test`.
- Chrome strings: `i18n` attributes with ids reusing the legacy `components.*`
  dictionary paths (DD-047); the webapp's `extract-i18n` emits them into its
  catalogue because the app builds this lib from source through the path alias.

## Commands

```bash
nx storybook aurelius-atlas-ui            # dev server, port 4400
nx test aurelius-atlas-ui -c ci           # Vitest unit tests (runs check-purity first)
nx run aurelius-atlas-ui:check-purity     # the legacy-construct gate (UIC-07)
nx test-storybook aurelius-atlas-ui       # interaction tests (dev server on :4400 first)
nx build aurelius-atlas-ui                # ng-packagr-lite package build
nx build-storybook aurelius-atlas-ui -c ci  # compile all stories
```

## Conventions

- Every component ships a story; visual regression depends on it.
- Components are dumb: `input()`/`output()` only, no services with side effects
  (exception: `DarkModeService`, which owns theme persistence).
- New components: export from `src/index.ts`, add stories, add unit tests.

## Removal

Part of the spine. Removing it means removing the `aurelius-atlas-ui` alias, all
imports in `aurelius-atlas-frontend-example`, and its `mkdocs.yaml` entries.
