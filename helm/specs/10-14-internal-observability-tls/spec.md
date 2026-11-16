# 10.14 Grafana at the edge, a TLS-internal observability mesh

- **Status:** in review
- **Pull request:** (this PR)
- **Records:** DD-653..657 (adds), DD-653 (supersedes DD-276's "root URL
  stays unset" clause in part, and CHT-128's "never grafana" clause),
  DD-654 (relies on: DD-275's grafana client, DD-276's request-derived
  fallback), DD-655 (relies on: DD-256's byte-copy assets, DD-270's TLS
  backends, DD-286's collector leaf), DD-656 (relies on: CHT-79's minimal
  prod asset), DD-645 (relies on: the health-check gate), DD-652 (relies
  on: the trust Bundle)

## Scope

The first Grafana login through the published edge (`atlas-dev`, rc.7)
failed in three stacked ways, the dashboards behind it stayed red, and the
mesh served plaintext. Each failure was fixed and proven live on the
cluster first, then baked into the charts here, so the next release
installs the validated posture with no manual cluster edits:

1. **Grafana was not at the edge.** The chart shipped its browser host
   disabled (CHT-84's port-forward posture), but the realm's `grafana`
   client registers only public redirect URIs, so a deployment without the
   host cannot complete a login at all. `global.hosts.grafana.enabled` is
   now true by default (CHT-132, DD-653). Grafana's backend is plaintext
   (the edge terminates TLS in front of it), and GKE's default HTTP probe
   gets a 404 from the UI, so the health-check template gained an HTTP
   variant for plaintext backends. Without that policy the load balancer
   served 503 for every edge route, grafana included.
2. **The login died before Grafana saw it.** Grafana builds the OIDC
   redirect from its request when `GF_SERVER_ROOT_URL` is unset (DD-276),
   so the browser's `localhost` redirect was rejected by the issuer. It now
   follows the browser host whenever the host is on (DD-654). Two further
   issuer-side refusals: the client carries
   `pkce.code.challenge.method: S256` (PKCE is 10.7's hardening), so
   Grafana must send a challenge (`GF_AUTH_GENERIC_OAUTH_USE_PKCE`), and
   the client's default scopes name `email` and `profile`, which the prod
   realm asset never defined, so the authorize request failed
   `invalid_scope`. The asset now defines both (DD-656), and Grafana asks
   for `openid profile email`.
3. **The observability hops were plaintext.** The collector's leaf was the
   only mesh certificate (CHT-36); Prometheus, Loki, and Tempo answered
   plain HTTP inside the cluster. Every backend now serves TLS from its own
   private-CA leaf, its probes read HTTPS, Prometheus scrapes over
   CA-pinned HTTPS, the collector's Loki and Tempo exporters pin the CA,
   and Grafana's datasources ride HTTPS with the CA pinned by file
   (CHT-134, DD-655). Tempo's OTLP receivers close too, so no plaintext
   ingest door stays.
4. **The dashboards could not query.** Grafana 13 ships prometheus, loki,
   and tempo as external plugins and installs the missing ones at startup,
   but its installer writes to `/tmp`, which the read-only root hardening
   makes read-only — every install failed and every panel died
   `plugin.notRegistered`. The Grafana container mounts an emptyDir at
   `/tmp` (DD-657, the collector-cache pattern), and its queries then ride
   the TLS mesh.

This increment does **not** deliver: TLS on the collector's own telemetry
port (`:8888`, which has no server-side TLS option, named under
Deviations), TLS on Loki's dskit gRPC port (`:9095`, a single-replica
in-pod hop), TLS inside the dev compose (the compose carries no mesh CA,
named under Deviations), or a change to the browser-facing posture of any
other component. A stock render (gateway off, no domain) keeps DD-276's
port-forward login and grows only the four mesh leaves.

## Semantics

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHT-132 | `global.hosts.grafana.enabled` defaults to true at the umbrella: the grafana listener, its HTTPRoute, its edge-Certificate SAN, and its `HealthCheckPolicy` render with the stock gateway posture. Its policy is the HTTP variant (`config.type: HTTP`, `httpHealthCheck.requestPath` from `global.gateway.healthCheck.paths.grafana`, default `/api/health`) because its backend is plaintext; every TLS-backend listener keeps the HTTPS variant (DD-645). Set the host false to return to the port-forward-only posture. A `HealthCheckPolicy` still renders only when `global.gateway.healthCheck.enabled` (GKE-specific kind, CHT-128 unchanged).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| CHT-133 | When the grafana browser host is on (its `enabled` is not false and either `host` or `global.domain` names one), the Grafana deployment sets `GF_SERVER_ROOT_URL` to that host over `https://`. Off or unnamed: the variable stays unset and Grafana keeps DD-276's request-derived shape. Either way the deployment sets `GF_AUTH_GENERIC_OAUTH_SCOPES: openid profile email` and `GF_AUTH_GENERIC_OAUTH_USE_PKCE: "true"`, and the prod realm asset defines realm-level `email` and `profile` client scopes (the minimal built-ins: the mappers the logins read). The trust CA mounts both at `/certs/ca.crt` (the datasources' pin) and `/etc/ssl/certs/atlas-ca.crt` (the OIDC token call's Go trust store).                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| CHT-134 | The observability chart renders one Certificate per mesh member: the collector (named `<fullname>`, CHT-36 unchanged) plus `<fullname>-loki`, `<fullname>-tempo`, `<fullname>-prometheus`, each with only its own Service's cluster names and each issued by `global.trust.issuerRef`. `tls.componentSecrets.<name>` (or `tls.secretName` for the collector) brings your own leaf and drops the matching Certificate. Each backend mounts its leaf Secret at `tls.mountPath` and probes HTTPS; Grafana keeps HTTP probes (plaintext UI, edge-terminated). Loki and Tempo merge a TLS overlay into their dev byte-copy assets at render (CHT-39 stands for the files; the merged ConfigMap carries `server.http_tls_config`, and Tempo's OTLP grpc and http receivers their `tls` blocks). Prometheus serves TLS via `--web.config.file`, scrapes every mesh job with `scheme: https` and the CA (exception: `otel-collector-internal`, named under Deviations), the collector's Loki/Tempo exporters are https with `tls.ca_file`, its prometheus exporter serves TLS, and Grafana's datasources are https with `tlsAuthWithCACert` and the CA pinned by file. |

## Java origin

Not a port. The rules are deployment posture; Apache Atlas 2.4.0 ships no
observability mesh.

## Deviations

No Atlas deviation — this is chart-internal. Against the chart's own
earlier records and against any operator's reading of "TLS everywhere":

- **Dev compose stays plaintext** (DD-655). The compose ships no mesh CA,
  and CHT-39 pins the chart assets to dev's bytes, so the TLS lives in
  render-time overlays, not in the files. The dev stack's loopback pinning
  (10.11) stands in for transport trust there.
- **Collector telemetry `:8888` stays plaintext** (DD-655). The
  collector's internal telemetry metric server has no TLS option in the
  binary's version; its scrape job keeps `scheme: http`. The port is not
  published (ClusterIP chart, no edge route).
- **Loki's dskit gRPC (`:9095`) stays plaintext** (DD-655). Single-replica
  Loki calls it in-pod only.
- **The prod realm's grafana client names scopes the asset never defined**
  is fixed by defining them (DD-656). Keycloak silently drops
  unresolvable scope references at import, so the client's leftover
  `web-origins`, `acr`, `roles`, and `basic` default-scope names still
  vanish as they did before — the login works because the two it reads are
  now real. Trimming the client's scope list is the realm author's next
  cleanup, not this increment.
- CHT-128's "never grafana" clause and DD-276's "root URL stays unset"
  clause are restated by CHT-132 and CHT-133 (DD-653, DD-654). The 10.8
  and 10.13 spec texts stay as written (records are the history).

## Acceptance

`tests/test__charts_observability.py` —
`test__collector_pipeline_is_the_dev_shape` (CHT-34+134),
`test__the_mesh_serves_tls_with_cluster_names_only` (CHT-36+134),
`test__brought_leaves_drop_the_matching_certificates`,
`test__backends_mount_their_leaf_and_probe_https` (CHT-134),
`test__loki_and_tempo_config_is_the_dev_asset_plus_the_tls_overlay`
(CHT-39+134), `test__prometheus_argv_and_scrape_config_retargeted`
(CHT-38+134), `test__datasources_pin_uids_the_crosslinks_and_the_ca`
(CHT-40+134), `test__grafana_logs_in_through_the_realm` (CHT-84+133),
`test__grafana_root_url_follows_the_host` (CHT-133),
`test__grafana_writable_tmp_carries_the_plugin_installs` (CHT-134/DD-657);
`tests/test__charts_edge.py` — `test__gateway_listeners_per_enabled_host`,
`test__edge_leaf_covers_the_browser_hosts`, `test__one_route_per_listener_with_one_backend`,
`test__health_check_policies_cover_every_backend` (CHT-132);
`tests/test__charts_umbrella.py` — `test__certificates_reference_the_umbrella_issuer`
(CHT-134); `tests/test__charts_keycloak.py` —
`test__prod_asset_carries_only_the_application_surface`,
`test__prod_asset_stays_peer_faithful_to_the_dev_asset` (CHT-133/79).
Offline: `uv run pytest tests/test__chart*.py -q --no-cov`. On-cluster: the
redeploy of `helm/environments/gke.yaml` onto `atlas-dev` must bring three
new mesh Certificates Ready, a passing Prometheus target set over https,
and a browser Keycloak login at `https://grafana.<domain>` with zero manual
cluster edits (the acceptance for the whole increment).
