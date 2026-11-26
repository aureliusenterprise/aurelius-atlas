# 21.2 Design decisions

## DD-893 — The deployment carries no credential, because the app has no identity

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-18, MCP-22, MCP-23, DV-208, ADR 072, DD-890, DD-196, CHT-109

Every other auxiliary API ships a small credential trail with its chart and its compose
piece: a realm client of its own, a `${<APP>_CLIENT_SECRET}` placeholder in the realm
imports, a generated Secret in the umbrella, a mirrored value in the app's `.env`, and an
`otel-<app>` ingest client (CHT-109, DD-196, DD-499). MCP keeps none of it, and 21.1 already
fixed the reason: the app forwards the caller's own token and never signs with an identity
of its own (MCP-03, DD-890, DV-208). A credential would be dead weight at best and a
temptation at worst — a reviewer who finds a client secret in this app will assume a leg
exists and wire one.

Concretely, the absence is asserted where its presence is the convention:

- `infra/keycloak/import/master.json`, the production realm and the standalone
  realm gain no client (no service account, no `atlas-read` grant, no
  placeholder), and the umbrella gains no `secret-mcp-client.yaml`. The realm's
  `master`-only secret render (the
  `VALIDATE_ENTITY_CLIENT_SECRET` gate) gains no MCP branch.
- The compose piece names no `SERVER_CLIENT_SECRET`, no `TOKEN_URL`, and no `OTEL_*` key.
- The chart has no `credentialSecrets` block and no `telemetry` block. The umbrella's
  `atlas-mcp` values block therefore has no secret sibling.
- No ingest client means no entry in the observability peer roster or the producer list —
  the app emits no spans, which matches ADR 072 R6 without pretending to a leg it cannot
  sign for. Telemetry can arrive later as its own decision; it must not be copied in from
  a sibling.

The verifier still needs the issuer and the audience, which are not credentials. MCP
verifies the webapp's `aurelius` audience, the same posture the deployed validate-entity
chart takes since 7.24 (DD-435, AUX-04): an agent mints the token the browser mints, and
that token stops at the gate (DV-75). So the server chart needs no new entry in
`auth.audiences`, and the NetworkPolicy peer is the webapp pod that proxies it — the same
shape as the other aux services (EDT-22, CHT-70).

One asymmetry is now visible on the surface rather than buried in code: in a rendered
deployment, MCP is the only auxiliary chart without a credential join. That is the point
of recording it here — DV-208 says the same thing about the wire.

## DD-894 — Agents reach the app through the webapp's proxy, not a new host

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-19, CHT-30, DD-142, DD-270, DD-435, ADR 069, R6 (ADR 072)

The auxiliary APIs are never dialed by the edge directly. The gateway and the chart's
listeners route four hostnames (app, auth, dashboard, o11y); every aux call travels
through the webapp's own nginx (`/validate-entity/`, `/lineage-model/`), and the data path
is tested as one path (DD-142, DD-435). MCP joins that pattern rather than asking for a
listener of its own.

The alternative — a new `mcp.<domain>` host with a gateway listener, its own HTTPRoute, its
own edge certificate SAN and a gateway location in the bundle — was rejected for three
reasons. It widens the host roster ADR 069 keeps small (one address says one thing). It
would put the app behind a _second_ proxy whose NetworkPolicy peer is the edge rather than
the webapp pod, which the aux chart suite has no convention for. And it buys nothing an
agent needs: an MCP client takes a URL, so `https://atlas.<domain>/mcp/` is as addressable
as a hostname, and it inherits the webapp proxy's rate limit, access log and TLS
termination, all already reviewed.

The proxy block is _not_ a copy of the REST locations, because the protocol streams. The
`/mcp/` location:

- turns `proxy_buffering` off, so a server-streamed response reaches the client as it is
  produced instead of at the end,
- speaks `proxy_http_version 1.1` with an empty `Connection` header for the keep-alive the
  session rides,
- carries a long `proxy_read_timeout` (3600s, the value the traced `/api/` location already
  uses for long calls) so a slow tool does not sever an open session,
- forwards the `Mcp-Session-Id` response header untouched (no rewrite hides it) and keeps
  the `/mcp` prefix on the upstream request, which is the path the app mounts at,
- rides the same TLS + `proxy_ssl_name aurelius-atlas-mcp` verification as its siblings,
  and the same 600r/m limit zone, since a runaway agent loop is the failure mode to bound.

The chart's webapp takes the upstream join through values (`mcp.service`/`mcp.port`,
`nginx.mcpUpstream`/`nginx.mcpUpstreamName`) exactly as it takes the validate-entity one,
so a diverging deployment renames the peer without editing the template. The same location
lands in the bundle's `docker/webapp/nginx.conf`, keeping the two edges honest about the
same surface.

## DD-895 — The chart is the aux copy, adapted: two siblings in, no credential out

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-20, MCP-21, MCP-22, DD-290, CHT-02, CHT-27, CHT-28

Charts keep per-chart copies of their templates by design (DD-290: no shared library chart
for workloads, so a slice deletes cleanly, ADR 002). The MCP chart is therefore a
copy-adapt of `apps/aurelius-atlas-validate-entity/helm/`, and its diff is the interesting
part:

- `component: mcp`, `port: 21005`, `componentEnvPrefix: AURELIUS_ATLAS_MCP_`,
  `image.name: aurelius-atlas-mcp`.
- One join becomes two: `atlas{service:"", port:21000}` and
  `validateEntity{service:"", port:21003}`, each derived with the siblingService rule when
  the name is empty (CHT-28). `SERVER_BASE_URL` and `VALIDATE_ENTITY_BASE_URL` render from
  them as `https://<service>:<port>`. This is the first aux chart with two catalogue
  siblings; neither can be hardcoded because both are release-relative.
- Dropped: `credentialSecrets`, the whole `telemetry` block, the `.otelClientId` helper, and
  the OTEL `config` keys. `serviceAccount.automountServiceAccountToken: false` stays — the
  app needs no API access (DD-461's posture).
- Kept verbatim: the Certificate (CHT-27: SANs = Service name and FQDNs, `ca.crt` beside
  the pair, which is what `AUTH_CA_FILE` and the upstream TLS both read), probes on
  `/liveness` (MCP-15), the nonroot/65532 security context, the PDB above one replica, the
  NetworkPolicy peer-joins-by-pod-label rule (CHT-70), and `validate.yaml`'s
  issuer-required guard.

The image's own `HEALTHCHECK` and `ENV` (21.1's Dockerfile) already follow the cert pair,
so the chart and the container agree about HTTPS without either restating the rule.

## DD-896 — The umbrella joins by roster, and the rosters extend

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-23, MCP-17, DD-288, DD-674, DD-223

CI discovers work by glob (a `Chart.yaml` brings `helm-*`, a `Dockerfile` brings
`docker-*`, a `sonar-project.properties` brings `sonar`), and every workflow runs
`nx affected` or `run-many`. Nothing in `.github/workflows/` names an auxiliary app, so the
app joins CI the moment its files exist. What does need hand-editing is the small set of
rosters that enumerate components, and each is extended rather than special-cased:

- `helm/Chart.yaml` gains the dependency with the pinned equal version (DD-288) and the
  `atlas-mcp.enabled` condition; `helm/values.yaml` gains `atlas-mcp: {enabled: true}` and
  no secret entry (DD-893). `helm/Chart.lock` regenerates.
- `docker/docker-compose.yaml` gains the `include:` block with `env_file: stack.env`;
  `docker/stack.env` gains `MCP_CERTS_DIR=../certs`; `docker/.env.example` gains
  `MCP_IMAGE` and `MCP_CERTS_DIR`, which is also how `tools/standalone_bundle.py` discovers
  images — there is no second image list to forget (DD-677). `docker/certs.txt` gains the
  leaf line.
- The root Python workspace needs nothing: the member, dev group, uv source and pyright
  environment landed with 21.1.
- The root test rosters extend: `AUX_CHARTS` in `tests/conftest.py` and the parametrized
  maps in `tests/test__charts_aux.py`, the umbrella's certificate-name set and realm loop,
  the standalone pieces and guarded-path tuples, and the image-digest values paths. The
  aux suite's OTEL map gains an explicit "this chart has none" case rather than an invented
  client id (DD-893).

The suite that pins the standalone host story (issuer, otel, proxy network) and the demo
realm roster stay untouched, because the app joins neither the ingest producers nor the
service clients — a change there would mean the credential posture had slipped.

## DD-897 — The chain test waits for its own increment; 21005 was already taken

- **Status:** accepted
- **Date:** 2026-11-26
- **Relates to:** MCP-24, DD-892, DD-200, DD-223, ADR 062

21.1 deferred the e2e chain along with the deployment, and the two split cleanly now: the
deployment increment is provable offline (chart renders, piece structure, proxy text),
while the chain needs Docker, the SOPS key, a real server and a real verdicts API, and it
fails in ways unrelated to these files. Splitting keeps each PR near the review ceiling
(root `AGENTS.md`: one increment, roughly 1,500 production lines) and keeps the deployment
gate green without waiting on a suite that cannot run in the same loop.

Two facts for 21.3, recorded now so it does not re-derive them:

- The chain stands the **real** server (the tools are the catalogue) plus the verdicts API,
  and its host port cannot be 21005: the fixed e2e sidecar ladder already uses 21005
  (quality scanner), 21006 (kafka scanner), 21007 (db scanner) and 21008 (validate-entity's
  server sidecar). The MCP stack continues at **21009** for its server sidecar. The app
  itself takes a random host port in the stack, as its siblings do.
- Its token probe is not a leg probe: the aux suites mint a client-credentials token to
  prove a service leg before the stack starts (DD-200's hint, a recreate-Keycloak remedy).
  MCP has no leg, so its probe mints a browser `aurelius` token and makes sure it carries
  `atlas-write` for the write tools (MCP-11). Like every suite it leaves the shared
  `infra/*` stacks running (DD-223).

The SonarCloud join lands here rather than in 21.3 because it is a deployment fact of the
package, not of the chain: `sonar.sources` is the package plus its Dockerfile,
`sonar.tests` is the unit suite (the chain adds `e2e` to that list in 21.3), and both sarif
reports ride `sonar.sarifReportPaths`. The project key
`aureliusenterprise_aurelius-atlas-mcp` must exist in the org before the analysis runs —
the token cannot create projects, so it is a one-time console step by a maintainer, the
same gate the embedder is still waiting on.
