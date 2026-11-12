# 13.4 The database scanner chart and schedule

- **Status:** in review
- **Pull request:** #326
- **Records:** adds CHT-123 and CHT-124 (here) and DD-516 and DD-517 (here);
  relies on 13.3 (DBS-01..12, DD-502..507), 12.3 (the shared CronJob contract,
  CHT-114..120 plus CHT-125 and DD-508..513), and DD-506 (the DSN is a secret
  setting)

## Scope

This increment delivers `apps/aurelius-atlas-db-scanner/helm`: a standalone
Helm chart that runs the database scanner as a Kubernetes `CronJob`, on the
shared shape 12.3's spec states (CHT-114..117, CHT-125) with the per-database
rules below. Its client registration, credential, and audience join are the
ones 12.3 states whole (CHT-118..120).

This increment does not deliver: a chart that scans several databases in one
release (13.3's rule stands — one DSN per run, so one release per database), or
a driver layer beyond the image's own (DBS-01: a deployment that scans another
product adds its driver to its own image). The database's own TLS stays inside
the DSN (CHT-123) and the telemetry leg is optional like every other trust leg
(CHT-125): a deployment turns each on with its own values.

## Rules

The shared rules (CHT-114..117, CHT-125) apply verbatim; only the
scanner-specific ones are stated here.

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHT-123 | The database under scan is named by an existing Secret, never a value: `<PREFIX>DSN` is a `secretKeyRef` into the Secret named by the required `database.dsnSecret.name` under the key `database.dsnSecret.key` (DD-506's rule extended to the chart — the DSN carries the database credentials, so it never enters a values file, a ConfigMap, or a render). `<PREFIX>SYSTEM_NAME` arrives from the required `database.systemName` value (DBS-03's no-default setting, guarded at the render like `schedule`). The scan knobs (`database.schemaName`, `database.schemaPatterns`, `database.tablePatterns`, `database.connectTimeoutSeconds`) are values that render only when set, keeping the app's defaults otherwise. |
| CHT-124 | One release scans one database (13.3's one-DSN rule at chart scale): the chart names its CronJob, ServiceAccount, and labels from the release (the fullname convention), so two releases of the same chart in one namespace run as two independent scanners with two identities. A driver outside the image stays an image concern (DBS-01): the chart adds no driver-volume value, because a sidecar or an init container for a wheel would ship unvetted code beside a signed image.                                                                                                                                                                                                                                    |

## Deviations

From Java Atlas: the legacy platform has no scheduled database reflection at
all (13.3's DV-150 states the difference); the chart inherits it, adds none.
From the dev run: the e2e suite's disposable Postgres (13.3's compose service)
stays compose-only; the chart points at whatever live database the operator's
DSN Secret names.

## Acceptance

- `uv run pytest tests/test__charts_db_scanner.py` — the CronJob shape on the
  shared contract (CHT-114..117, CHT-125, re-proven for this chart), the DSN
  and System joins and their guards (CHT-123), and the one-database naming
  (CHT-124).
- `npx nx run aurelius-atlas-db-scanner:helm-lint` / `:helm-template` /
  `:helm-config-scan` — the chart's share of the gates (CHT-06, DD-282). The
  DSN guard has a render-failure test (the bare render fails naming the two
  required values).
- The realm half rides 12.3's acceptance: this chart's client id is the
  deployment's registration name (absent from the shipped realm asset and the
  umbrella's Secrets, CHT-118/119) and is in the server audience default
  (CHT-120).
