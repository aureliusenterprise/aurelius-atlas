# 7.34 Version and copyright: what `/config.json` no longer carries

- **Status:** in review
- **Pull request:** [#411](https://github.com/aureliusenterprise/aurelius-atlas/pull/411)
- **Records:** DD-725 (the version is the server's answer, `VER-01`), DD-726 (the
  copyright year is the browser's calendar year, `VER-04`), DV-182 (the footer's
  two values leave the config); supersedes SPL-12's no-fetch clause (7.14, whose
  one-version promise DD-165 keeps); amends SHC-06 (7.11), SHM-06 (7.12),
  LDG-31 (7.22d) and CHT-26 (10.3a) in place. Relies on ADM-01 (the version
  answer), DV-03 (its name and description), APC-02 (the typed admin client),
  SHL-10 (the runtime config), DD-288 (the release stamps the version),
  DD-165 (app and server share one release number).

## Scope

Two values leave `/config.json` and the `AppConfig` shape:

- `appVersion` — the release number. The webapp reads it from the server instead,
  from the answer `GET /api/atlas/admin/version` already gives (ADM-01). The
  footer, the settings panel's About section, and the lineage PNG's `Software`
  chunk read that answer.
- `appCopyright` — a year no deployment ever changed. The footer prints the
  current calendar year, taken when the page loads.

Three config files, the chart, and the chart's values drop both keys, so the same
image serves any deployment without stamping a build-time version into a file.

Not in scope:

| Not delivered here                                                       | Delivered by                                                  |
| ------------------------------------------------------------------------ | ------------------------------------------------------------- |
| A version answer that needs no user                                      | none — every consumer sits behind the sign-in guard (APC-05)  |
| The server's `/version` answer (name, release, revision)                 | 6.3 (ADM-01, DV-03) — reused here, unchanged                  |
| A runtime `appName` change per deployment                                | unchanged: `appName` stays in `/config.json` (SHC-02, SHL-10) |
| Serving a version to the legacy dashboard or the standalone bundle pages | the webapp is the only reader of these two values (DD-145)    |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VER-01 | The app version is what `GET /api/atlas/admin/version` answers in its `Version` key (ADM-01, DV-03). No deployment file names it: `/config.json`, its shape in `src/app/config.ts`, the chart's config, and the three shipped config files carry no `appVersion` key, and `parseAppConfig` ignores the key when one appears. Under the release strategy, app, server and charts carry one number (DD-165, DD-288), so the server's answer is the app's version. |
| VER-02 | A service holds the answer: it starts the read when the app starts, keeps the value, and gives an empty version to any reader until the answer arrives. It is the single fetch — every reader of the version takes it from the service, and the footer, the About section, and the PNG writer cause no second request. The read is not retried (7.26's retry covers it when its method stays idempotent).                                                       |
| VER-03 | A blank version prints nothing. The footer leaves its right side empty and the About section prints only the name while no answer has arrived. The PNG writer writes no `Software` chunk while there is no version, under LDG-31's empty-field skip (the `addTextMetadata` skip the writer already applies).                                                                                                                                                    |
| VER-04 | The footer's copyright year is the browser's calendar year at load. It needs no configuration: `appCopyright` is gone from `/config.json`, its shape, the chart's config, and the three shipped config files.                                                                                                                                                                                                                                                   |

## Aurelius origin

The Aurelius app (`.scratch/aurelius`, the commit 7-0 pins) reads both values from
build-time files:

- `libs/shell/src/lib/footer/footer.component.{ts,html}` — the footer anatomy this
  app ports (SHC-06). It shows `ShellConfigService.appCopyright`, `appName`, and
  the version.
- `libs/shell/src/lib/shell-config.service.ts` — `appCopyright` comes from the
  `shell` block of `environments/environment.ts`.
- `libs/version/src/lib/version.service.ts` — `appVersion` composes the Node
  package version and the git hash into `${version}#${hash}`, read from a generated
  `git-version.json` baked into the bundle.

Both channels are Aurelius `environment.ts` values, the channel 7.1 replaced with
one runtime file (SHL-10, DD-130). The Aurelius footer reads `ShellConfigService`
and `VersionService`, and DD-145 collapses those two into `APP_CONFIG`. This
increment moves the two values off the file instead: the year is derived, and the
version's Aurelius twin (`VersionService`, a value baked at build time) changes to
a value read from the server at runtime.

## Deviations

DV-182: the footer's copyright year is the current year, not the year a
configuration names. Aurelius bakes `shell.appCopyright` into `environment.ts`, so
its footer ages silently. Atlas 2.4.0's dashboard has no Aurelius footer (DV-03's
product-frame class).

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/shell/footer.component.spec.ts` — VER-03/04:
  the year is the current one, and an unanswered version leaves the right side blank.
- `apps/aurelius-atlas-webapp/src/app/shell/version.service.spec.ts` — VER-01/02/03:
  the one read, the empty value before the answer, the answer after it, and a failed
  answer that keeps the empty value without throwing.
- `apps/aurelius-atlas-webapp/src/app/config.spec.ts` — VER-01: `appVersion` and
  `appCopyright` are neither required nor returned.
- `apps/aurelius-atlas-webapp/src/app/settings/settings-panel.component.spec.ts` —
  SPL-12 (amended): the About section prints the name plus the version from the service.
- `apps/aurelius-atlas-webapp/src/app/search/details/lineage/save-view-as-image.spec.ts` —
  VER-03: no version means no `Software` chunk (LDG-31's skip).
- `tests/test__charts_webapp.py` — CHT-26 (amended): the rendered `/config.json`
  carries neither key.
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp.py` — SHC-09 (amended):
  the footer's year is the current one and its version is the server's answer;
  SHL-02's config test proves the file still serves.
- Run: `npx nx test aurelius-atlas-webapp -c ci`, `npx nx build aurelius-atlas-webapp`,
  `uv run pytest tests/test__charts_webapp.py`, `nx lint aurelius-atlas-webapp`.
