# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-725. The webapp reads its version from the server, not from a file

- **Status:** Proposed
- **Increment:** 7.34
- **Date:** 2026-11-19

**Decision.** `appVersion` leaves `/config.json`, `AppConfig`, the chart's config
and the three shipped config files. A `VersionService` (`src/app/shell/version.service.ts`)
issues the one `GET /api/atlas/admin/version` the app makes, keeps the answer, and
gives readers an empty version until it lands (VER-01..03). The footer, the About
section and the PNG writer read the service. `AdminService.getVersion()` (APC-02)
is the client; the server's answer (ADM-01, DV-03) is unchanged.

**Reason.** The user asked for an endpoint that answers the app version and for the
value to leave the configuration. Both halves were already built: the release stamps
one number into the server package, every chart's `appVersion` and the image tags
(DD-288), so the answer of `admin/version` _is_ the app version (DD-165's own
reasoning). `config.json` was stamping the same number a second time, and every stamp
is a chance to be stale: the Helm chart derives it from `.Chart.AppVersion` and the
file could override it, while the dev, docker and e2e files all carried a literal
`0.0.0` no release ever matched. One reader, one source. The alternative reading of
the request — a new open `/version` route — duplicates ADM-01 for no reader: all
three consumers (footer, About, PNG save) sit behind the sign-in guard (APC-05), so
authentication costs them nothing.

**Alternatives.** A new `GET /api/aurelius/v1/version` open like `/tenancy` (TNW-01):
a second answer of one value, wrong until a logged-out screen needs it. Keep a build
stamp in the image (`git-version.json`, the Aurelius `VersionService`): bakes a value
the release already publishes, the exact drift this change removes. Ship a
`APP_VERSION` build-time define: fails SHL-10 — the runtime file is the settings
channel, and a build constant would make the image environment-specific.

**Consequences.** The footer's right side and About's version line are blank for the
moment after load, and the PNG drops its `Software` chunk while blank (VER-03, the
writer's existing skip). Both are the same degrade the About section already accepted
for its fetched time zones (SPL-07): no spinner and no error state. The read is not
retried beyond 7.26's resend, and its failure is silent by the same rule.

### DD-726. The footer prints the browser's current year

- **Status:** Proposed
- **Increment:** 7.34
- **Date:** 2026-11-19

**Decision.** `appCopyright` leaves `/config.json`, `AppConfig`, the chart's config
and the three shipped config files. The footer reads `new Date().getFullYear()` once
at construction (VER-04).

**Reason.** The user asked for the current year, always. The value was never a
deployment choice: the dev, docker and e2e files each carried 2022, the chart's
values carried 2026, and the shipped `.helm-rendered` output proved the chart's copy
was the live one. A year in a configuration is a date that silently goes stale, and
every one of those three files proves the point. `ShellFooter` is OnPush and built
once per page load, so the value cannot drift during a visit (SHC-08).

**Alternatives.** Keep the key and default it (a key nobody sets is a key to delete).
Compute it server-side and answer it (a whole round trip for the browser's clock,
which is the clock the reader of the footer sits in). A per-deployment override
through an env var: no such requirement exists, and the chart keeps `appName` as the
one shell string a deployment may still rename (SHC-02).

### DD-733. The landing's no-API test leaves out the start's version read

- **Status:** Proposed
- **Increment:** 7.34
- **Date:** 2026-11-20

**Decision.** The landing scenario that counts `/api` calls leaves out the version
read (`GET /api/atlas/admin/version`) beside the tenancy read it already leaves out.

**Reason.** VER-01 moved the version from `/config.json` to a read, and
`VersionService` starts it the first time the shell renders behind the guard (VER-02,
APC-05). The landing itself still issues no call, so the rule the scenario guards
(BRW-01, BRW-04) holds. The scenario reloads the page, and a reload restarts the app:
the read belongs to the start, exactly as 15.6's tenancy read does (TNW-02), which the
same test already carves out for the same reason.

**Alternatives.** Route the read and answer an empty version: the scenario then pins a
stub rather than the shipped start, and a second scenario would still need the same
exclusion. Move the version out of the shell: the footer is the version's primary
reader (VER-01).

**Consequences.** The scenario's carve-out is a two-entry list of start reads. A future
shell-level start read joins it, and each entry names the rule that owns the read.
