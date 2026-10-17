# aurelius-atlas-dashboard

The Apache Atlas 2.4.0 dashboards, vendored (DD-017). This file covers wiring specific to this project;
workspace-wide rules, including the conversion workflow, live in the root `AGENTS.md`.

## Layout

- `dashboardv2/`, `dashboardv3/` — the `release-2.4.0` source, byte for byte apart from `PATCHES.md`
- `PATCHES.md` — every change made to the vendored source, one commit each (DSH-05)
- `LICENSE`, `NOTICE` — Apache Atlas's, kept with the source it covers
- `build.Dockerfile` — `grunt build-minify` for both dashboards in the hardened Node 24 image
- `dist/` — the build output (git-ignored): `dashboardv2` at the root, `dashboardv3` in `n/`

## Rules

- **Never edit the vendored source in passing.** A change is a new row in `PATCHES.md` and its own
  commit; the formatters, linters and hooks skip `dashboardv2/` and `dashboardv3/` on purpose.
- The behaviour or look of the dashboards does not change (ADR 046, DD-001). The server answers the
  calls they make; the dashboards are not adapted to the server.

## Wiring Checklist

- `project.json` — the `build` target and its inputs; `aurelius-atlas-server` lists this project in
  `implicitDependencies` and in the `serve`, `docker-build` and `docker-publish` `dependsOn`, so each
  builds it first.
- `apps/aurelius-atlas-server/Dockerfile` — copies `dist/` into the image and sets
  `AURELIUS_ATLAS_SERVER_DASHBOARD_DIR`.
- `.dockerignore` — keeps local `node_modules/`, `dist/` and `public/js/libs/` out of the build context.
- `.pre-commit-config.yaml`, `.prettierignore`, `eslint.config.mjs` — exclude the vendored directories.

## Commands

```bash
npx nx build aurelius-atlas-dashboard     # docker buildx; writes dist/
npx nx e2e aurelius-atlas-server -c ci    # both dashboards in Chromium against the server image
```

## Removal

Not removable: the dashboards are part of the product (ADR 046).
