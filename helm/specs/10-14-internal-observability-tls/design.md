# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md).
Their [rules](../../../docs/architecture/conversion/design-log.md#rules)
still apply: an accepted entry is never edited except its status line, and a
changed decision is a new entry that supersedes the old one.

## Entries

### DD-653. Grafana rides the edge by default, with an HTTP health check

- **Status:** Proposed
- **Increment:** 10.14
- **Date:** 2026-11-16

**Context.** The observability chart shipped `global.hosts.grafana` off by
default (CHT-84, DD-276): the documented access path was a port-forward,
which works because the `grafana` client registers
`http://localhost:3000/login/generic_oauth`. The first real deployment
proved the posture cannot be the default. The realm's `grafana` client
registers only public redirect URIs (CHT-82 tokenises them from
`global.domain`), so a deployment that leaves the host off has no working
login at all — the port-forward is an extra path, not the only one.
Enabling the host live hit a second blocker: GKE's managed Gateway probes a
backend with plain HTTP on `/` (DD-645), and Grafana's UI answers 404
there, so the load balancer marked the backend unhealthy and served 503 for
every edge route. DD-645's policy renders the HTTPS variant only, because
every backend it covered served TLS. Grafana's backend is plaintext, so no
policy existed for it.

**Decision.** `global.hosts.grafana.enabled` becomes true in the umbrella's
values, so the listener, route, edge SAN, and health-check path for grafana
render with the stock gateway posture. The health-check template gains a
second shape: a listener whose backend is plaintext gets
`config.type: HTTP` with `httpHealthCheck.requestPath`, and a TLS backend
keeps the HTTPS variant. The grafana path defaults to `/api/health`, which
is Grafana's own readiness answer, so the load balancer declares the
backend healthy exactly when its pod is. The observability subchart keeps
its own `global.hosts.grafana.enabled` default false, so a standalone
render of that chart alone keeps the bare shape (its own CHT-84 test still
shows the port-forward posture); the umbrella always passes its block, so
every deployment of the whole system is on.

**Alternatives.** (a) Leave the host off and document "enable it to log in"
— rejected: a default that cannot log in is not a default, and it was the
documented path's first failure. (b) Point the HTTP probe at `/` and accept
the 404 as unhealthy — impossible: an unhealthy backend never serves. (c)
Serve TLS inside Grafana (`GF_SERVER_PROTOCOL=https`) and reuse the HTTPS
policy — rejected: the edge already terminates TLS for every other
component, a second TLS hop adds a leaf and a CA mount for no trust gain,
and Grafana's own certificate handling would then duplicate cert-manager's
job. (d) Register localhost redirect URIs so port-forward stays primary
— rejected: it widens a public client's redirect set for a developer path,
and the pentest trail (H4) pushed the opposite way.

**Consequences.** Every install of the umbrella routes `grafana.<domain>`
unless the operator opts out, so the edge Certificate's SAN list grows by
one and the `atlas` Gateway gains a third listener in every render test.
The health-check template now branches on the backend's wire protocol, and
`healthCheck.paths` names a path per listener rather than per TLS backend.
The runbook's Grafana section leads with the browser host and keeps the
port-forward as the secondary path.

### DD-654. Grafana's root URL follows the browser host, and its login carries PKCE and the email scopes

- **Status:** Proposed
- **Increment:** 10.14
- **Date:** 2026-11-16

**Context.** DD-276 left `GF_SERVER_ROOT_URL` unset on purpose: with a
request-derived root URL, a port-forward completes the login at the
`localhost` redirect the client registers. Behind the edge the same
emptiness breaks the login. Grafana builds its `redirect_uri` from the
inbound request, and the issuer answers "does not match any of the
registered redirect URIs" because only `https://grafana.<domain>` is
registered. Two issuer-side refusals sat behind it, each found by fixing
the one before. Grafana sent no PKCE challenge, and the `grafana` client
carries the realm's `pkce.code.challenge.method: S256` attribute (10.7's
hardening, CHT-76), so the authorize request was refused. And the client's
`defaultClientScopes` name `email` and `profile`, which the prod realm
asset never defined; Keycloak silently drops unresolvable references at
import (DD-656), so the request asked for a scope the realm could not
resolve and failed `invalid_scope`.

**Decision.** The observability chart derives `GF_SERVER_ROOT_URL` from the
same helper shape the umbrella and the keycloak chart use: the named
`global.hosts.grafana.host` wins, otherwise `https://grafana.<domain>`, and
nothing when the host is off or unnamed — so DD-276's port-forward posture
survives exactly where the edge route does not exist. The deployment always
sets `GF_AUTH_GENERIC_OAUTH_USE_PKCE: "true"` and
`GF_AUTH_GENERIC_OAUTH_SCOPES: openid profile email`, which are the scopes
the client's defaults name plus `openid`. The private CA mounts twice in
the pod: `/certs/ca.crt` for the datasource pin (DD-655) and
`/etc/ssl/certs/atlas-ca.crt` for Grafana's own outbound token call, which
is Go and reads the system trust store.

**Alternatives.** (a) Add localhost redirect URIs to the client — rejected
in DD-653's alternatives, and it does not help a browser that arrives at
the public host. (b) Set `GF_SERVER_ROOT_URL` always — rejected: a
port-forward then redirects to the public host, which breaks the isolated
access path DD-276 exists for. (c) Turn PKCE off on the client — rejected:
it undoes the realm's public-client hardening for one relying party's
convenience. (d) Ask only for `openid`, skipping email — rejected: the
client's defaults already request email and profile, and the email claim is
what maps a realm user to a Grafana identity.

**Consequences.** DD-276's "root URL stays unset" clause is superseded in
part: unset remains true when no browser host exists, and the spec text of
10.8 stays as written. The grafana login is now proven end-to-end in a
browser against the live cluster (the smoke user logged in and Grafana
answered `/api/user`). Live drifted in the same way: the running release's
configmap carried these two variables by hand, and the upgrade to this
chart makes that patch redundant instead of overwriting it blind.

### DD-655. Every internal observability hop rides TLS on the private CA

- **Status:** Proposed
- **Increment:** 10.14
- **Date:** 2026-11-16

**Context.** DD-270 made the app backends TLS-only, and the observability
mesh did not follow. The collector held the only mesh leaf (CHT-36), while
Prometheus, Loki, and Tempo served plain HTTP on their ClusterIP Services.
Prometheus's own config scraped them with `scheme` unset (http), Grafana's
datasources used `http://` URLs, and the collector posted to Loki and Tempo
over http. Telemetry in a data catalogue is not neutral: it carries query
text, entity names, and trace attributes, so a pod that can reach port 3100
or 9090 reads it. The live cluster was the proving ground, and it exposed
the mechanism constraints the design had to work around (each tested
against the shipped image versions): Loki parses its config strictly, so a
duplicate top-level key is a fatal parse error, and `-config.file`'s
comma-separated list loads only the first existing file rather than merging
the list. The hardened `dhi.io` images carry no shell, so the config could
not be concatenated in an init container.

**Decision.** The chart issues one leaf per mesh member from
`global.trust.issuerRef` — the collector keeps CHT-36's `<fullname>`, and
`<fullname>-loki`, `-tempo`, `-prometheus` join it. Each names only its own
Service's four cluster forms, so no leaf is valid for another's host.
`tls.componentSecrets.<name>` is the per-leaf bring-your-own switch and
drops the matching Certificate, mirroring the collector's `tls.secretName`.
Each backend mounts its Secret at `tls.mountPath` and its probes read
HTTPS. TLS reaches the config files through a render-time deep merge: the
template parses the dev byte-copy asset, merges a small TLS overlay, and
renders the result, so the file on disk never gains a duplicated key and
CHT-39's byte-copy guard still passes. Loki gains `server.http_tls_config`;
Tempo gains it plus `tls` on its OTLP grpc and http receivers, which closes
the plaintext ingest door inside the cluster. Prometheus runs
`--web.config.file` (a `tls_server` block) and scrapes each mesh job with
`scheme: https` and `tls_config.ca_file` pointed at the trust CA. The
collector's Loki and Tempo exporters become https with `tls.ca_file`, and
its prometheus exporter gains a `tls` server block. Grafana's datasources
become https with `tlsAuthWithCACert` and `secureJsonDataFiles.tlsCACert`.
Grafana's own probes stay HTTP, matching DD-653's plaintext backend.

**Alternatives.** (a) Append a second YAML document or a second file to the
config — rejected: both live-tested failures above. (b) Ship TLS-bearing
asset files and strip TLS for dev — rejected: it breaks CHT-39's single
source of truth and makes dev's copy the derived one. (c) mTLS on every
hop — rejected: it needs client leaves for each dialer (Prometheus scrapes
four jobs, Grafana dials three backends) for a threat the CA pin already
answers, and the collectors' OIDC ingest already authenticates producers
at the door. (d) A service mesh (Istio/Linkerd) — rejected: ADR 057 keeps
the chart dependency-free, and a sidecar injector is a larger cluster
prerequisite than four Certificates.

**Consequences.** Four Secrets appear per release where one did; a stalled
certificate renewal now breaks telemetry reads, so the leaves ride
cert-manager's renewal like every other leaf. Prometheus's internal
telemetry scrape (`otel-collector-internal`, port 8888) stays http — the
collector's telemetry server has no TLS option — and Loki's dskit gRPC
(:9095) stays plaintext because single-replica Loki calls it in-pod; both
are named in the spec's Deviations. The dev compose stays plaintext: the
chart assets are dev's bytes, and the compose ships no mesh CA to pin.

### DD-656. The prod realm defines the two built-in scopes its clients name

- **Status:** Proposed
- **Increment:** 10.14
- **Date:** 2026-11-16

**Context.** The prod realm asset is deliberately minimal (CHT-79): it
carries one custom client scope, `otel-ingest`, because Keycloak mints the
built-ins (`email`, `profile`, `roles`, `basic`, `web-origins`, `acr`) on a
fresh import. The `grafana` client's `defaultClientScopes` names `email`
and `profile` among others, which reads as harmless — until the live realm
proved otherwise. The authorize request failed `invalid_scope`, and the
realm's scope list showed only `otel-ingest`: Keycloak drops unresolvable
scope references during import and never mints a built-in a partial import
does not carry. The dev asset (`master.json`) defines the built-ins with
extra mappers and consent text, so the drift test could not catch the gap
on the prod side — there was no prod entry to compare.

**Decision.** The prod asset declares realm-level `email` and `profile`
client scopes, written in the minimal shape the login needs: `email`
carries the email property mapper and the `email_verified` attribute
mapper; `profile` carries username, given name, and family name. Each sets
no consent requirement, matching the built-in defaults, and the entries
name no ids so the import assigns them. They join `otel-ingest` as the
asset's only three scopes, keeping CHT-79's "no stock scope surface beyond
what a client reads" reading.

**Alternatives.** (a) Define nothing and let Keycloak mint the built-ins
— rejected: tested live, a fresh partial import does not mint the ones the
clients name, and the login fails. (b) Import the dev asset's richer
built-ins — rejected: they carry consent text and extra mappers the prod
realm's hardening deliberately leaves out (DD-273). (c) Trim the grafana
client's scope list to the resolvable names — rejected: email is the claim
that maps a realm user to a Grafana identity (DD-654), so trimming answers
the failure by removing the login's input.

**Consequences.** The realm asset gains two entries and the drift guard now
compares `otel-ingest` by name and asserts the two new scopes' mapper sets
(CHT-79's "audience scope stays the only custom one" stands). The grafana
client's other leftover scope names still resolve to nothing, which the
spec names as a deviation and leaves as the realm author's cleanup.

### DD-657. Grafana's tmp volume carries the startup plugin installs

- **Status:** Proposed
- **Increment:** 10.14
- **Date:** 2026-11-16

**Context.** With the login fixed, the dashboards stayed red: every panel
failed `plugin.notRegistered`, and the alert rules failed to evaluate for
the same reason. Grafana 13 moved the prometheus, loki, and tempo
datasources out of the binary — they are external plugins now, and the
server installs the missing ones from its catalog at startup. The dhi image
ships without them (its `plugins-bundled` path is empty), and the chart's
Tier 3 hardening gives every container a read-only root filesystem (DD-282:
"none of the five writes to its root"). The installer downloads each plugin
zip to `/tmp` before unpacking it to the plugins path, and `/tmp` on a
read-only root is read-only, so every install died with "read-only file
system". Dev's compose never showed it: its Grafana container carries no
hardened securityContext, so `/tmp` is writable there.

**Decision.** The Grafana container mounts an emptyDir at `/tmp` — the
collector's `cache` volume pattern (DD-282's one root-FS write, backed by
a volume) applied to Grafana's one. No version pin is added: Grafana's
installer resolves the catalog's current version for the running release,
and the installed plugins persist on the PVC's plugin path
(`GF_PATHS_PLUGINS=/var/lib/grafana/plugins`), so an upgrade reuses them.
`GF_PLUGINS_PREINSTALL` stays unset — with a writable `/tmp`, Grafana's own
startup set (every datasource its config references, catalog-resolved)
installs unasked, which the live cluster proved.

**Alternatives.** (a) Pin versions in `GF_PLUGINS_PREINSTALL` — rejected:
live testing showed the versioned entries 404 against the catalog for this
Grafana build, and the unversioned default set already covers the three
datasources the ConfigMap names. (b) Bake the plugins into the image
(a custom Grafana build) — rejected: it forks the hardened dhi image, the
chain's digest-pin and drift guard (CHT-92/96) for one convenience. (c)
Ship the plugin zips as ConfigMap or job-installed artifacts — rejected:
the installer is Grafana's own supported path, and an artifact copy would
re-implement its signature checks. (d) Leave the dashboards broken —
rejected: 10.3b shipped them as the point of the stack.

**Consequences.** The read-only-root rule stands everywhere; the emptyDir
is a named, documented exception of the same shape as the collector's
cache. The first boot of a new release downloads plugins from the public
catalog, so a cluster without egress to it needs the operator to prefill
the plugins PVC — noted in the runbook. A Grafana major upgrade
re-resolves and re-installs, and the PVC keeps the old copies until the new
ones land.
