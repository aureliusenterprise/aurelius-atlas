# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-296. 6.1a's required auth settings land in the charts as joins

- **Status:** Accepted
- **Increment:** 10.12
- **Date:** 2026-11-01

**Decision.** 6.1a (main, #188; DD-250) made `auth_server_url` and
`auth_client_secret` required settings with no defaults: a server pod that
boots without them dies at settings load. The chart track forked before that
merge, so the 10.x charts render no `AUTH_*` env and an umbrella install of a
post-6.1a image crash-loops. This increment lands the auth block as joins,
never literals (CHT-108): `AUTH_SERVER_URL` from the chart's CHT-03 issuer
helper (whose required-guard now fires on every render, so an authless render
fails at the gate rather than at the pod), `AUTH_REALM` from `global.realm`
(CHT-74), `AUTH_CLIENT_ID`/`_AUTH_AUDIENCES` from the server chart's `auth`
values block (the server's own confidential client plus the webapp's `aurelius`
client — AUT-02/AUT-10), `AUTH_CA_FILE` from the Certificate's mounted
`ca.crt`, and `AUTH_CLIENT_SECRET` from the new `<release>-server-client`
Secret (CHT-109), the same Secret the Keycloak chart feeds the realm import's
`${ATLAS_SERVER_CLIENT_SECRET}` (CHT-110) — both shipped realm assets carry
the placeholder (master's client since 6.1a), so unlike the grafana
credential (CHT-83) this one is not realm-gated. The prod realm asset gains
the `aurelius-atlas-server` client, hardened and host-tokenised like its
`aurelius` peer, its `login.jsp` redirects naming both browser hosts.

**Reason.** The webapp's nginx `/api/` proxy already forwards the browser's
bearer token, so the API leg authenticates end-to-end with no chart change —
the gap is only the server's own boot. The dashboards' sign-in leg
(`login.jsp`, AUT-05) lands on the server's host, and the dashboard host
stays `enabled: false` by default (ADR 054): the browser leg therefore works
exactly where it is exposed, and nothing in the stock shape changes for
operators who never enable it. The secret rides the CHT-87/88 placeholder
mechanism (one client, one placeholder, one key — rotation story like every
other client credential), and the CHT-79 drift guard keeps the two realm
assets' server clients peer-faithful the way they keep the otel-* ones.

**Consequences.** The umbrella's generated-secret roster gains
`<release>-server-client` (lookup/preserve/override, gated on either
consumer). The server chart's values gain the `auth` block and
`credentialSecrets.serverClient`. Any cluster install of a post-6.1a image
before this increment crash-loops — the charts and the app must ship as one
release. The webapp's own login flow (keycloak-js against the `aurelius`
public client) is 7.x behaviour and unchanged.

### DD-297. The aux APIs' AUTH_REALM joins global.realm

- **Status:** Accepted
- **Increment:** 10.12
- **Date:** 2026-11-01

**Decision.** The three aux charts (data2model, lineage-model,
validate-entity) carried `AUTH_REALM: master` as a static entry in their
`config:` values blocks — written when their settings were authored, while
the cluster's only realm was still `master`. 10.7 (CHT-74) moved the
cluster's default realm to `aurelius-atlas` and enumerated the
realm-bearing envs; the aux `AUTH_REALM` was missed, so on a prod-realm
cluster the aux APIs fetched discovery/JWKS from `/realms/master` and every
browser token (issued by `aurelius-atlas`) failed verification — a latent
drift no render-time test caught, because the value was a literal. It now
renders as a deployment join from each chart's existing realm helper
(CHT-111), and the umbrella suite pins the server's and the three aux pods'
`AUTH_REALM` against the realm the Keycloak chart imports.

**Reason.** CHT-74's rule is that `global.realm` is the one realm fact and
every consumer derives from it; a literal is a second source of truth by
definition. The `master` escape hatch keeps working — it retargets the same
one fact — and the settings' own default (`master`) stays the standalone
default for compose/dev, which the charts never relied on anyway.

**Consequences.** `AUTH_REALM` leaves the aux charts' `config:` maps, which
are for verbatim operator settings, not derived joins. Any future
realm-bearing env joins the same enumeration (the umbrella suite's
`/realms/...` sweep plus the named AUTH_REALM pins).

### DD-299. helm-lint vendors umbrella dependencies like helm-template

- **Status:** Accepted
- **Increment:** 10.12
- **Date:** 2026-11-01

**Decision.** The helm plugin's `helm-lint` target gains the
`helm dep update <chart> >/dev/null &&` prefix that `helm-template` and
`helm-config-scan` already carry, for every chart.

**Reason.** The umbrella's subchart tarballs (`helm/charts/`) are gitignored;
they exist only where someone has run `helm dep update` or `helm package -u`.
Locally the lint always saw them, so the bare `helm lint` passed everywhere
it was tried — but on a fresh CI checkout the umbrella lints with no
dependency default values, and its own templates nil-pointer on
`(index .Values "atlas-keycloak").realm.name` (a shape 10.12's
`secret-keycloak.yaml` made unavoidable: it reads the subchart's realm name
through the umbrella values the subchart defaults provide). The failure is
the checkout's, not the chart's: the render targets had always vendored first
(DD-282 learned the same about Trivy's renderer); `helm-lint` was the one
target that assumed vendored state. `helm dep update` is a no-op for the
dependency-free component charts and its `file://` repositories never leave
the machine, so the prefix is uniform and cheap.

**Consequences.** #205's `Lint & render charts` step goes green on a clean
runner; the plugin's three render-family targets now share one provenance
rule: never trust `helm/charts/` to exist. Next free DD: 300.
