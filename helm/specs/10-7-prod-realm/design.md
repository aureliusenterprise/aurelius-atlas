# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-274. `global.realm` as the values contract; host tokens substituted chart-side

- **Status:** Accepted
- **Increment:** 10.7
- **Date:** 2026-10-30

**Context.** Two realm facts had to reach every chart: the realm _name_
(eight charts' issuer URLs, token URLs, and the SPA's config named it as a
per-chart value default — seven copies of `realm: master` that could drift
from the realm the KC chart imported), and the _browser hosts_ the prod
asset's redirect URIs and web origins must carry (which the KC chart cannot
read from the umbrella's `global.hosts` — subcharts see only what the
umbrella passes as `global`).

**Decision.** `global.realm` joins the CHT-03 contract (default
`aurelius-atlas`): every consumer chart declares `global.realm` and derives
its realm from a per-chart `realm` helper (`default "aurelius-atlas"
.Values.global.realm`), so one umbrella value retargets the whole system; the
KC chart's own `realm.name` stays as a chart-level override for standalone
installs. The asset's browser hosts are chart-substituted, not credential
placeholders (CHT-77): `__ATLAS_HOST__`/`__DASHBOARD_HOST__` tokens in the
JSON, replaced literally by `configmap-realm.yaml` from
`global.hosts.atlas.host`/`global.hosts.dashboard.host` (the KC chart's
`global:` block declares them), falling back to `atlas.<domain>` /
`dashboard.<domain>` then `<release>.localhost` for bare renders — mirroring
the umbrella's host rule. The KC chart's `atlasHost`/`dashboardHost` helpers
mirror the umbrella's so both spellings of the same deployment agree;
credentials stay Keycloak's replace-placeholders business (DD-256
untouched): a render must never materialise a secret.

**Alternatives.** (a) Template the hosts into the JSON with Helm syntax —
rejected: `{{ }}` inside a chart asset breaks the byte-compare-style guards
and makes the file unparseable standalone; literal tokens keep the asset
plain JSON. (b) Per-chart realm values as today — rejected: the CHT-74
contract test exists precisely because seven defaults already drifted once
(`master` everywhere was the drift). (c) The umbrella re-exports the asset
as a ConfigMap override — rejected: the realm is the KC chart's asset (its
files/, its import flags); the umbrella composes, it does not own component
content.

**Consequences.** `global.realm` is first-boot-immutable like the issuer it
embeds — the values comment and the runbook say so. The bare chart renders
(helm.ts runs them with no values) stay guard-free via the
`<release>.localhost` fallback, so lint/template never fail for want of a
domain; a deploy whose hosts are unset everywhere still gets a render, and
the 10.5 smoke catches the nonsense hosts. The parity question between the
umbrella and KC host helpers is pinned by the umbrella suite's realm tests
rather than a shared helper library (DD-290's chart-local rule holds).
Next free DD: 275.
