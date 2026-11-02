# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-275. Grafana is a confidential realm RP; its client lives in the prod asset only

- **Status:** Accepted
- **Increment:** 10.8
- **Date:** 2026-10-31

**Context.** The pre-pentest finding H4: the cluster's Grafana answers with
DD-267's anonymous-Viewer posture, so `global.hosts.grafana.enabled` —
already wired end-to-end through the edge (10.3c) — would publish the
dashboards read-public. 10.7 shipped the `aurelius-atlas` realm and the
placeholder machinery; Grafana is the first workload whose login is a
relying-party flow of its own rather than the webapp's existing one.

**Decision.** A `grafana` client joins `files/aurelius-atlas.json` and the
prod asset **only** (CHT-81): confidential (`clientAuthenticatorType:
client-secret`, secret `${GRAFANA_CLIENT_SECRET}` — DD-256's
replace-placeholders resolver, fed from `<release>-grafana-oauth` exactly as
`${OTEL_INGEST_CLIENT_SECRET}` is), standard-flow + PKCE S256, ROPC off, no
service account. RBAC comes from the token: `role_attribute_path` grants
Viewer to every authenticated realm user and the client's `editor`/`admin`
client roles escalate — the realm is the access boundary, and escalation is
an explicit grant an operator makes in the Keycloak console. This is CHT-79's
first named parity exception (prod client ids = dev's ∪ {`grafana`}): the dev
compose Grafana stays anonymous-Viewer, a local dashboard over local
telemetry (DV-113) — the same two-shape posture as DD-273's identity split,
now with a concrete client proving the assets may diverge on purpose.

**Alternatives.** (a) Grafana's own auth proxy or the edge's OIDC auth filter
in front of it — rejected: the gateway filter would authenticate but not
carry identity into Grafana (dashboards lose viewer attribution, and
per-dashboard permissions stay Grafana's job anyway); generic_oauth is
Grafana's native OIDC RP and needs no edge change. (b) Put the client in
both realm assets — rejected: dev's Grafana is a compose convenience, and a
client the dev stack never uses is drift bait for CHT-79. (c) Map realm
_roles_ instead of client roles — rejected: realm roles would collide with
`aurelius-write`'s namespace and make Grafana escalation a realm-wide grant;
client roles scope it to Grafana's own console surface. (d) `admin` group
mapping from Keycloak realm admins — rejected: realm-admin should not
silently become Grafana-admin; explicit client roles keep escalation auditable.

**Consequences.** The umbrella's `secrets.grafanaOauth` Secret serves two
consumers (realm import + Grafana env) so the gate is either-consumer
(CHT-83); a `master`-only install generates nothing, CHT-80's rule. The dev
Grafana keeps DD-267's full anonymous posture — compose and cluster diverge
by design, and the CHT-79 test now names the exception, so a future client
added to one asset and not the other fails loudly and must be justified in
the spec like this one. Next free DD: 276.
