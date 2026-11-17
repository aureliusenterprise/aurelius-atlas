# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md).
Their [rules](../../../docs/architecture/conversion/design-log.md#rules)
still apply: an accepted entry is never edited except its status line, and a
changed decision is a new entry that supersedes the old one.

## Entries

### DD-658. Browser hosts carry the product role, not the pod name

- **Status:** Proposed
- **Increment:** 10.15
- **Date:** 2026-11-16

**Context.** The edge subdomains defaulted to the component name behind
them: the webapp answers on `atlas.<domain>` (the same word as the whole
product), the identity provider on `keycloak.<domain>` (a product name
browsers have no use for), Grafana on `grafana.<domain>` (a tool name).
The operator review asked for hosts that read by role: the app, the
sign-in door, the observability surface.

**Decision.** The `global.hosts` entry keys and their derived defaults
become `app`, `auth` and `o11y`; `dashboard` keeps its name. Every
consumer follows the one rule: listener names, edge Certificate SANs,
health-check policy names and `paths.<key>` lookups, the realm asset
placeholders (`__APP_HOST__`, `__O11Y_HOST__`), Grafana's root URL, and
the component charts' issuer fallback (`auth.<domain>` — Keycloak pins its
issuer from the host, so the issuer moves with the rename). The internal
Service names and the CHT-13 name rule are machine-facing and stay. No
old-key alias ships (see the spec's deviations).

**Alternatives.** (a) Keep the keys, ship new defaults in
`hosts.<key>.host` of an overlay: rejected — the keys leak into resource
names (`atlas-grafana` HealthCheckPolicy, `atlas-keycloak` listener) and
into values files forever, which is the confusion being fixed. (b)
`ollie`: rejected — cute, opaque; `o11y` is the established numeronym.
(c) Keep `keycloak` because the issuer URL is load-bearing and moving it
invalidates live tokens: weighed and accepted as a cost — the issuer is
derived, not configured, and atlas-dev is the only deployment; a future
real deployment renames before it has users, or treats the rename as an
identity-provider migration.

**Consequences.** The realm asset's placeholder tokens change, so the
keycloak chart's substitution lines and its chart tests move with the
umbrella. Keycloak's issuer pin moves with the host, and every relying
party derives it from the same rule, so no consumer drifts. On a live
deployment the rename means: DNS for the three new names first, upgrade,
then retire the old names; runbook §rename states it. The dev compose
stacks and e2e fixtures keep `keycloak.localhost` — they run the master
realm outside the chart's host rule, and renaming them buys nothing.

### DD-659. Grafana admits role-holders only

- **Status:** Proposed
- **Increment:** 10.15
- **Date:** 2026-11-16

**Context.** CHT-84's role mapping ends in `: "Viewer"`: every realm user
who completes the OIDC dance gets read access to the metrics, logs and
traces of every workload. The review asked for a role requirement
instead. The `grafana` client already defines `admin` and `editor` client
roles (10.8's asset); nothing assigned them, so the roles were decoration.

**Decision.** Drop the Viewer fallback and set
`GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_STRICT=true`. A user holding the
`grafana` client role `admin` signs in as Admin, one holding `editor` as
Editor, and a user holding neither is denied at the callback (Grafana's
own strict-mapping behavior, 13.x). Who holds the roles is deployment
state: the realm's `grafana` client grants them per person (runbook). The
generated password admin (`GF_SECURITY_ADMIN_*`, DD-275's recovery Secret)
is untouched — denying role-less users must not lock the operator out of
their own Grafana.

**Alternatives.** (a) `allowed_groups` with a dedicated Keycloak group:
rejected — the client roles already exist, and Grafana reads them from
the token it already receives; a group adds a claim mapper for nothing.
(b) Keep Viewer, add an allow-list later: rejected — a default-open
observability surface is exactly what DD-643..DD-656 have been tightening
around; the mesh went TLS-private one increment ago.
(c) `auto_assign_org_role` tweaks: rejected — strict is documented as the
deny switch and keeps one source of truth (the client role).

**Consequences.** An upgrade to this chart locks out every role-less
realm user from Grafana until someone grants roles — on atlas-dev, that
someone is the two admin accounts of DD-660, granted in the same change.
The chart test pins the absence of `"Viewer"` in the mapping and the
presence of the strict flag. The `editor` role stays unassigned by
default: it is the middle rung an operator hands out, not a default.

### DD-660. Platform admins are deployment state, seeded by a runbook step

- **Status:** Proposed
- **Increment:** 10.15
- **Date:** 2026-11-16

**Context.** The prod realm asset ships exactly one user: the
provisioning service account (CHT-80 — the asset is userless by rule; the
10.7 hardening removed the demo humans on purpose). The Keycloak console
is reachable today only through the install-time bootstrap admin, and
nobody holds `grafana:admin`, so after DD-659 no person could sign in to
Grafana at all. The review asked for named human admins (two people at
Aurelius Enterprise) with console and Grafana access, each also a member
of the staged `aurelius` tenant organization (ADR 063's tenancy comes
later, in the 15.x series; membership now is inert and forward-looking).

**Decision.** Keep the asset userless. The runbook gains an "Admin
accounts" step, run once per deployment through the admin API: create the
user, `credentials` with `temporary: true` (a generated password the
first login must replace), `realm-management` `realm-admin` (console),
`grafana:admin` (observability), the four `atlas-*` client roles of the
`aurelius-atlas-server` client (the Atlas API — AUZ-02's doors are that
client's roles, which no admin grant implies; dev's `aurelius-writer`
holds the same four), and add the user to the `aurelius` organization
with the `atlas-read` group — the same shape the 15.3 provisioning code
(`ensure_organization`, `add_member`, `add_to_read_group`) would produce
for any tenant member. The password value never lands in Git, a chart, or
a log line: the step writes it to a file the operator reads and shreds.

**Alternatives.** (a) Ship the two accounts in the realm asset: rejected
— CHT-80's userless rule exists because an asset user is a permanent
credential surface replicated to every install; these people belong to
one deployment. (b) Keycloak's admin console via FGAP scoped roles
instead of `realm-management:admin`: deferred — full admin is what "can
run the identity provider" means today; a scoped operator role is its own
future increment. (c) A Helm hook Job creating the accounts from values:
rejected — values files end in Git and CI dumps, and a password has no
place there; `temporary: true` with an out-of-band handoff does.

**Consequences.** A fresh install has no human until the operator runs
the step — stated in the runbook next to the bootstrap admin, which
remains the recovery door. The `aurelius` organization is created in the
same step with the four role groups (`atlas-read`, `atlas-write`,
`atlas-types`, `atlas-admin`) the tenancy code names, so when 15.x
provisioning turns on, it finds the organization it expects rather than
fighting a hand-made shape. The step is idempotent (search-before-create
by username and alias), so re-running it after an incident is safe.

### DD-661. The realm defines the roles scope and the path parses

- **Status:** Proposed
- **Increment:** 10.15
- **Date:** 2026-11-16

**Context.** The live validation of DD-659 failed twice before it passed.
First: no token ever carried `resource_access.<client>.roles`, because
the prod realm asset never defines a `roles` client scope while every
browser client names it in its default scopes — Keycloak drops
unresolvable scope references at import (the import log warned
"Referenced client scope 'roles' doesn't exist"), so the claim simply
never minted. The old non-strict mapping hid this: its fallback assigned
a role whatever the expression read. Second: the mapping expression this
chart inherited from DD-275 is written with `? :`, and JMESPath has no
ternary operator — the expression fails to parse (a lexer error), the
lookup yields nothing, and again only the `"Viewer"` fallback made sign-in
appear to work. Strict mapping exposed both faults at once: every user,
role-holder included, was denied.

**Decision.** Two fixes ship together. The realm asset gains a `roles`
client scope: one `oidc-usermodel-client-role-mapper` whose claim name is
`resource_access.${client_id}.roles`, multivalued, on both the ID and
access tokens, with consent hidden — the shape Keycloak's own built-in
scope has, trimmed like the email/profile scopes of CHT-133. Every client
that already named the scope now resolves it. The Grafana path is written
in the JMESPath the parser accepts:
`contains(resource_access.grafana.roles[*], 'admin') && 'Admin' ||
contains(resource_access.grafana.roles[*], 'editor') && 'Editor' || ''`.
The chart tests pin both: the scope's mapper config, and the exact
expression.

**Alternatives.** (a) A client-level protocol mapper on the `grafana`
client instead of a realm scope: rejected — the server's authorization
(AUZ-02) reads the same claim shape for its own client, and one scope
definition serves every client that already names it. (b) Keep the
broken expression and set `role_attribute_strict=false`: rejected —
that is the default-open behavior DD-659 removes. (c) Rely on the
userinfo endpoint instead of the ID token: rejected — Grafana evaluates
the ID token first, and the claim belongs there.

**Consequences.** The CHT-133 lesson repeats one scope wider: an asset
may only name scopes it defines, and the scope-list test now guards
`roles` beside email/profile/otel-ingest. On atlas-dev the same fix
applies live (the realm cannot re-import without wiping the DD-660
accounts, so the scope is created through the admin API and attached to
each client that names it). Anyone reading a pre-DD-661 token capture
finds no roles claim — expected, nothing minted one.

### DD-662. The Postgres volume mounts with fsGroupChangePolicy OnRootMismatch

- **Status:** Proposed
- **Increment:** 10.15
- **Date:** 2026-11-16

**Context.** The rc.8 upgrade of atlas-dev failed its `--atomic` gate:
the recreated Postgres pod crashlooped on `data directory
"/var/lib/postgresql/18/data" has invalid permissions`. Postgres 18
insists on 0700 or 0750; the mounted directory read 2770. The kubelet's
default `fsGroupChangePolicy` (`Always`) recursively re-applies
group-ownership with setgid and group-writability on **every** remount,
and a StatefulSet pod recreate is a remount — the first boot was fine
because the volume provisioned at the right mode and was never remounted
under rc.7.

**Decision.** The Postgres pod's security context gains
`fsGroupChangePolicy: OnRootMismatch`: the group change applies only
when the volume root's ownership actually mismatches, which a provisioned
volume already satisfies, so the recursive chmod stops and the 0700 data
dir survives remounts. The chart test pins the policy next to the boot
assertions. On atlas-dev the same policy was patched onto the running
StatefulSet and the data dir chmod'ed back to 0700 once (root), which is
what the next helm upgrade now also ships.

**Alternatives.** (a) Drop `fsGroup` and run the data dir as uid 70 with
no group: rejected — the cert-copy boot and socket dir rely on the group
today, and the policy fix is the documented answer for strict-mode
databases (e.g. the upstream Postgres chart does the same). (b) Chmod at
boot from an init container: rejected — it re-chowns 5 Gi every start,
and the recursion is what caused the problem. (c) A hand-patch only:
rejected — every future recreate would hit it again.

**Consequences.** Any strict-mode database pod follows the same line:
fsGroup needs the policy, or the first recreate breaks it. The rc.7
cluster never showed the defect because its Postgres pod was created
once; upgrades that recreate pods are where it surfaces. Next free DD: 663.

### DD-663. The platform gets its own admin service client

- **Status:** Proposed
- **Increment:** 10.15
- **Date:** 2026-11-16

**Context.** The admin operations (import, export, purge, audits) ask
for `atlas-admin`, a role only a human user carried, so driving them
programmatically meant changing Keycloak configuration first: enabling
direct access grants on the server's own client, signing in as a
person with a password, then undoing the change. That is both a manual
fiddle and a hole left open while it runs. The four scanner clients and
the provisioning client (DD-458, DD-469, DD-506, DD-499, DD-600) prove
the shape that works: a confidential service client whose
client-credentials token the server accepts by `azp` (AUT-02), with the
client id in the chart's default `AUTH_AUDIENCES` (DD-513). What was
missing is one carrying `atlas-admin` too — no machine client held all
four roles.

**Decision.** A new realm client `aurelius-atlas-admin` in both shipped
assets (and the dev asset): confidential, service accounts only, every
browser flow off, the organization-group mapper as a default scope
(RLM-04). Its service account holds the four roles of the server's
client (`atlas-read`/`-write`/`-types`/`-admin`); in the dev realm it is
a member of `operators` in the four matching groups, which is what
tenants-on needs to resolve a store. Its secret is a `${...}`
placeholder fed by `<release>-admin-client` (key `client-secret`), the
umbrella generating and preserving it as the server client's Secret is
(CHT-109), and the client id joins the server chart's default audiences
beside the scanners' and validate-entity's. The secret in that Secret is
the operator's handle: read it, mint a client-credentials token, call
the API — no Keycloak change, and no human password involved.

**Alternatives.** (a) Turn on direct access grants and password-grant as
a user: rejected — it is what happened for the first demo import, and
every caller would repeat the toggle; leaving it on opens password
grants on the server's client. (b) Reuse the provisioning client:
rejected — it is deliberately an identity-provider client (its roles are
`realm-management`'s, not the catalogue's) and giving it catalogue rights
blurs what a tenant-provisioning breach reaches. (c) A generic
`atlas-admin` realm role: rejected — the authorizer reads the four roles
off the server's client (AUZ-01); a realm role grants nothing.

**Consequences.** Any client-credentials caller — an operator's script,
a future command, the demo importer — works out of the box, and the
credential rotates through the Secret like every other. The client
ships in the hardened realm too, so a stock install has an admin
identity; a deployment that wants none trims the audience and deletes
the client. With tenancy on, a token must name one organization: the dev
realm's service account is a member of `operators` in its four groups,
and a deployment running tenancy on the hardened realm adds the same
membership where it provisions its organizations — the step its human
operators take there anyway.

### DD-664. The dashboard's Keycloak panels ride a scrape, not the push

- **Status:** Proposed
- **Increment:** 10.15
- **Date:** 2026-11-17

**Context.** Every Keycloak server panel on the dashboard (requests,
latency, 5xx, GC, threads) has never shown data. Three independent faults
sat on top of each other (live-proved on atlas-dev). First, Keycloak
ships `KC_METRICS_ENABLED` and `KC_TRACING_ENABLED` off by default, so
its exporter carried nothing. Second, Keycloak's Quarkus OTLP sender
ignores the generic `OTEL_EXPORTER_OTLP_ENDPOINT` and
`OTEL_EXPORTER_OTLP_HEADERS` (the chart already knew this for the
certificate and set `QUARKUS_OTEL_EXPORTER_OTLP_TRUST_CERT_CERTS`).
Enabled as-is, Keycloak dials `localhost:4317` and, when pointed at the
collector by the prefixed endpoint alone, the collector answers gRPC 16
"missing or empty authorization header". Third, even a working push
lands OTLP-native names (`http_server_request_duration_seconds_bucket`,
`jvm_memory_heap_used_bytes`) which are the names every other service's
Python/Java pusher already uses, so the pushed series join
`aurelius-atlas-server`-style jobs, and the dashboard's
`http_server_requests_milliseconds_*` names match nothing in either
world. The management port's own `/metrics` (Micrometer text, no auth,
TLS from the same CA, SANs covering the Service name) was verified
working, but CHT-71 keeps 9000 out of every rule and the Service.

**Decision.** Scrape what the push cannot carry, and fix the push for
what it can. (a) The chart sets `KC_METRICS_ENABLED=true` and
`KC_TRACING_ENABLED=true` and mirrors the collector endpoint and the
legacy-token header into `QUARKUS_OTEL_EXPORTER_OTLP_ENDPOINT` and
`QUARKUS_OTEL_EXPORTER_OTLP_HEADERS` (the same secret key). Traces
arrive that way, proved live (export failures stop, spans reach Tempo's
collector leg). (b) The keycloak puller grows a second pipeline: a
prometheus receiver scraping `<release>-keycloak:9000/metrics` over TLS
with the chart CA, attributed by its own resource processor to
`service.name=keycloak` (the dashboard's `exported_job` pin). The
postgres pipeline keeps `keycloak-infra` unchanged. This needs a
Service entry for 9000 and a NetworkPolicy rule admitting the puller
alone, both gated exactly as the puller is (telemetry plus the bundled
database). (c) The dashboard renames its server-row queries to the raw
Micrometer names (`http_server_requests_seconds_*`,
`jvm_gc_pause_seconds_count`, `jvm_threads_states_threads`,
`http_server_requests_seconds_max`) and the Duration panel's unit from
ms to s. (d) The Logs row is deleted: Keycloak exports no logs by
design (Loki is the server slice's only log store, DD-239's scope). The
compose pair gains the same four envs and the same second pipeline
(plain HTTP there, ADR 039's named relaxation on the dev management
listener).

**Alternatives.** (a) Fix the push only: rejected. The pushed names
clash with every other service's JVM/HTTP series, and the dashboard
would pin `jvm_memory_heap_used_bytes` shared with Elasticsearch's push
under `dev-elasticsearch`. (b) Remove the dead rows and keep only the
Postgres row: rejected while a clean scrape path exists. The identity
provider's RED signals are what an operator checks during a login
outage. (c) Scrape over plain HTTP in-cluster: rejected. Prod mode puts
TLS on the management listener (DD-260) and the chart CA covers the
Service name, so TLS costs one `tls_config` block.

**Consequences.** The dashboard's server row fills within one scrape
interval of a deploy, with the dashboard's own `exported_job="keycloak"`
pin honored. Tracing works through the same prefixed pair. The pushed
OTLP-named JVM/HTTP series also arrive (from the metrics feature) and
sit unused. They attribute to `keycloak`, so they stay out of the other
jobs' series. A deployment that disables telemetry loses the 9000
Service entry and rule again, as every puller surface already does. The
`keycloak-metrics-puller` Deployment now carries the whole keycloak
metrics story (server plus database), and its name reads right.
Next free DD: 665.
