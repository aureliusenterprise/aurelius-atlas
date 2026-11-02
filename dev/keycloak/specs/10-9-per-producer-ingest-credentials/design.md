# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-277. Per-producer ingest secrets: one realm-shaped Secret, dev stays shared

- **Status:** Accepted (completes DD-196's deferral)
- **Increment:** 10.9
- **Date:** 2026-10-31

**Context.** The pre-pentest triage's M5: the seven `otel-*` ingest clients
share one secret end to end — one placeholder in both realm assets, one key
in `<release>-otel-clients`, one join in all six cluster producers. A leak
from any producer's container forges telemetry for all seven (the collector
verifies signature and audience, not which client the bearer was minted
for). DD-196 deferred per-client secrets deliberately for the dev compose;
7.18 left the cluster side unported, so the deferral quietly became the
production shape. DD-196's own note assumed "prod deployments inject
per-client secrets, the realm import supports it as-is" — which the shared
placeholder made untrue until the asset itself spells one placeholder per
client.

**Decision.** Three calls, all decided autonomously (user pre-authorised):

1. **One Secret with per-client keys, not seven Secrets.** The umbrella's
   `<release>-otel-clients` gains one key per client id on a non-master
   realm — each value independently lookup-preserved, values-overridden
   (`secrets.otelClients.clients.<client-id>`), or fresh (CHT-19's pattern
   seven times over). Six producers each mount the same one Secret they
   mount today, under their own key; the RBAC/secret-count/nothing-special
   story is unchanged, and rotation of one producer touches one key of one
   object.
2. **Realm-conditional keys — the `master` hatch keeps the shared key
   everywhere.** Secret shape, KC StatefulSet env shape, and every producer
   join read the same realm chain (CHT-80's gate, generalized), so
   `global.realm=master` renders today's single-key behavior verbatim and
   existing overrides (`secrets.otelClients.secret`) keep working. Prod-only
   keys would have broken the documented escape hatch; prod-only Secret +
   shared dev asset is also CHT-79's second named exception, recorded
   rather than papered over.
3. **Dev compose stays shared.** `import/master.json` keeps
   `${OTEL_INGEST_CLIENT_SECRET}` in all seven clients; DD-256's byte-copy
   guard and the four e2e suites stay untouched. Seven secrets multiply the
   `.env.enc` surface and the placeholder machinery for a loopback-only
   stack — DD-196's dev deferral stands (CHT-91).

The placeholder mapping is the one deterministic rule in the asset (client
id uppercased, `-` → `_`, suffixed `_CLIENT_SECRET`, CHT-87) and the charts
derive env names from the roster mechanically, so the asset, the Secret
keys, the StatefulSet envs, and the six producer joins are four spellings
of one list — with a roster-drift test pinning the three cluster spellings
against the asset.

**Alternatives.** (a) Seven Secrets, one per client — rejected: more
rendered objects and six join sites per producer chart to select among,
for a separation one Secret's keys already give. (b) Prod-only keys with
no realm gate — rejected: breaks `master` renders (the realm-conditional
`atlas-keycloak.realm.name=master` shape is tested, and operators do use
it for local debugging). (c) Full per-client dev posture — rejected with
DD-196's reasoning: dev's threat model is loopback, and the incremental
`.env.enc`/import churn buys nothing there. (d) Rotating via realm import
values on every upgrade — rejected as scope: the import applies at first
boot only (IGNORE_EXISTING), live rotation stays admin-console work; this
increment shrinks the blast radius, the runbook records the procedure.

**Consequences.** CHT-79's parity rule is amended a second time (prod otel
peers equal dev minus `id` **and** `secret`, the secret delta pinned to the
mapping rule). `otel-postgres` keeps its roster seat with no cluster
consumer — the realm defines the client, the dev compose consumes it; a
future Postgres chart joins its own key with no chart change here. The
known mixed-render edge (chart-local `atlas-keycloak.realm.name=master`
without `global.realm=master` yields a shared-key Secret under per-client
joins) rides CHT-74's existing rule that `global.realm` is the one-value
retarget — documented in the umbrella AGENTS note, not guarded in the
template. Rotation is now per-producer: leak one container, rotate one key,
restart one producer (runbook §Credentials).
Next free DD: 278.
