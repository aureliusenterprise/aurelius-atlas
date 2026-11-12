# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-516. The DSN arrives as a Secret reference and the render guards it

- **Status:** Proposed
- **Increment:** 13.4
- **Date:** 2026-11-12

**Decision.** `<PREFIX>DSN` renders only as a `secretKeyRef` into the Secret
named by the required `database.dsnSecret.name` value (CHT-123). A DSN string
as a value is not an option the chart offers: `helm-config-scan` and the
contract test both pin that no rendered document carries a `dsn` literal, and
`database.systemName` is required beside it (DBS-03's no-default setting moved
from runtime exit 1 to render failure).

**Reason.** DD-506 already treats the DSN as the app's most sensitive setting
— suppressed from the CLI help because it embeds a live database's
credentials. A values file is the worst home for such a string: it rides
`helm get values`, CI logs, and Git history, which is exactly what R5 and the
Trivy KSV-0109 gate exist to keep out of charts. The reference shape is the
chart tree's standing one for credentials (the aux charts' `secretRefs`).
Guarding `systemName` at render follows CHT-02: DBS-12 refuses an empty value
with exit 1 at 03:00; the guard says the same thing at `helm install`, where a
human is reading.

**Alternatives.** A `database.dsn` value with a warning comment: one footgun
with a comment on it is still a footgun, and the Trivy rule would fire on every
deployment that fell into it. External Secrets / Sealed Secrets integration:
the chart cannot know which controller a customer runs; naming a Secret is the
interface every one of them fills.

**Consequences.** A deployment stands up its Secret before the chart installs,
by hand or by its own secret tooling — the README states it as a prerequisite
(CHT-123). The two required guards mean the chart's `tests/values.test.yaml`
names both, which keeps every CI render honest about the shape.

### DD-517. One release per database; no driver layer in the chart

- **Status:** Proposed
- **Increment:** 13.4
- **Date:** 2026-11-12

**Decision.** Multi-database deployments install the chart once per database,
each release with its own name, `database.dsnSecret`, and
`database.systemName` (CHT-124). The chart ships no driver-install mechanism:
no init container that pip-installs into a shared volume, no sidecar, no
`drivers` value. A deployment that scans a product whose driver the image lacks
builds its own image from the published one and sets `image.name`/`tag`.

**Reason.** 13.3 fixed the run shape — one DSN, one System, one scan (DBS-02,
the Scope table's "A second database in one run" row). The chart inherits it
rather than inventing a per-entry loop the app cannot run. The fullname
convention already gives two releases in one namespace distinct CronJob,
ServiceAccount, and label sets (each release keeps its own scan's identity and
schedule), so multi-database needs no new chart feature — only an operator
choosing release names, which Helm already requires to differ.
Runtime-installed drivers would download unsigned code into a signed, hardened,
read-only-root image (CHT-94's chain) at container start: DBS-01's genericity
is SQLAlchemy's, and the driver set an image carries is a supply-chain decision
belonging to a build, not a scheduler.

**Alternatives.** A `databases:` list rendered to N CronJobs: duplicates the
app's run boundary in Go template, splits one Secret across N jobs, and the
System-name and schedule knobs stop being one-per-database. An init container
installing wheels: rejected above.

**Consequences.** The scanner's README carries a two-database install example
(the same chart, two releases). The umbrella stays out either way (DD-508): a
customer scanning ten databases installs ten releases in whatever namespace
reaches their databases, which is the topology DD-508 chose in the first place.
