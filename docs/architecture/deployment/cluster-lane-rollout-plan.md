# E2E cluster-lane rollout plan (10.5b/c/d)

- **Status:** living plan — retires when 10.5d lands
- **Branch:** `feat/cluster-rollout-10-5b` (stacked on #189 ← #187)
- **Records:** executes the DD-280 verdict; DD-281 (retirements), DD-282 (the
  lane library) ride the per-suite PRs; specs:
  [10.5b](../conversion/increments/10-5b-cluster-lane-rollout-aux-and-core.md)
  (written), 10.5c/d (to write per the increment rules)

The 10.5 POC (DD-280, #187) proved one suite on the deployment. This plan
carries the verdict to the remaining suites. The steps below are locked by
user decisions (2026-10-30/31); the facts sections record what was verified
live so nothing has to be re-discovered.

## Locked decisions

1. **Order:** 10.5b = data2model + validate-entity (the REST twins) +
   `aurelius-atlas-core` (direct ES); 10.5c = webapp (Playwright);
   10.5d = lineage-model.
2. **Shared lane code = new pytest helper lib**
   (`libs/python/aurelius-atlas-cluster-lane`, parity-lib precedent: flat
   package, empty-targets `project.json`, dev-group member).
3. **Aux audience:** the minikube overlay overrides `AUTH_AUDIENCE` to
   `aurelius` for the aux charts (environment = values, CHT-04). The suites
   mint `azp=aurelius` tokens; the shipped per-service chart audiences stay.
4. **Outage/limiter tests:** RSL-01/RSL-02/SRV-09 deleted everywhere and the
   rules retired (DD-281, #189 — done). The shipped nginx limiter stays;
   chart guards stay.
5. **Browser DNS:** `/etc/hosts` entries registered at devcontainer startup;
   `install.sh hosts` maintains the fenced block from the live Gateway IP
   (browsers and `page.request` bypass the Python resolver shim).
6. **CI posture:** local-only. The `e2e-cluster` targets exist but no
   `.github/workflows/` change; compose stays the CI lane until a dedicated
   CI-shape increment.

## Steps

| Step | Scope                                                                                                                                                                                                                                                          | Status          |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| 0    | Retire RSL-01/RSL-02/SRV-09 (tests + rules, both lanes), DD-281                                                                                                                                                                                                | **done** — #189 |
| 1    | 10.5b: lane lib, server conftest refactor (honesty check), twins + core conftests, `e2e-cluster` targets ×3, audience overlay + chart guard, `install.sh hosts` + devcontainer refresh, spec + DD-282                                                          | **in progress** |
| 2    | 10.5c: webapp suite on the lane (realm redirectUris/webOrigins for `https://atlas.atlas.test/*` in BOTH `master.json` copies, password from Secret, footer test reads served `/config.json`, collector 4319/4321 port-forwards, browser leg via edge `/otel/`) | planned         |
| 3    | 10.5d: lineage-model on the lane (seed real atlas-server via the API instead of the compose `fixture-atlas`; port-forwards 21002/21001)                                                                                                                        | planned         |

## Verified design facts (live-checked 2026-10-31, minikube release `atlas`/ns `atlas`)

- CoreDNS rewrite `keycloak.atlas.test → atlas-keycloak.atlas.svc.cluster.local`
  (install.sh, DD-265) makes in-cluster JWKS discovery honest: pods verify
  `iss=https://keycloak.atlas.test/realms/master` — same origin the host lane
  mints from. Mint through the edge works: password grant for
  `aurelius-writer` at `https://keycloak.atlas.test/realms/master/...token`
  (password = `atlas-keycloak-users` Secret key `writer-password`, 32 chars).
- Lane-minted tokens carry `iss=<issuer>/realms/master`, `azp=aurelius`,
  `aud=otel-collector` on BOTH lanes (compose-lane probe identical) — the
  twins' audience check is `azp`/`aud` union vs `auth_audience`
  (`aurelius_atlas_auth.auth`), so only the overlay override is needed
  (decision 3). Aux route gates are `require_auth`-style (no write role on
  `POST /extract` / `POST /`).
- **Honest-TLS port-forward dial proven**: with the resolver shim mapping
  `<svc>.atlas.svc.cluster.local:<svc-port>` → `127.0.0.1:<free-port>`
  (host AND port rewritten in `getaddrinfo`), both httpx2 and the async
  `elasticsearch` client connect over verified TLS at the Service FQDN
  (SANs cover the 4-name block; ES adds the headless names). httpx2 is
  aiohttp-based for ES and both resolve at connect time.
- Aux app Services are ClusterIP-only (21001/21003) — port-forward, no
  HTTPRoute. Keycloak IS edge-routed (`keycloak.atlas.test/` → 8443), so the
  mint needs no forward. Tempo 3200, collector 4319/4321: forwards.
- Secrets: `atlas-keycloak-users` (`writer-password`, `reader-password`),
  `atlas-elasticsearch` (`elastic-password`), CA `aurelius-atlas-selfsigned-ca`
  (key `ca.crt`). Core `.env` keys: `ELASTICSEARCH_PORT/PASSWORD`; core e2e =
  23 tests, direct-ES only, namespaced aliases (DD-223) make shared-store
  writes safe.
- Twins tests are data-independent (`/extract` computes from the request
  body; validate-entity answers the static mock) — no cluster seeding.
- `server_direct` must stay a loopback URL dialled by Playwright
  (`ignore_https_errors`, ADR 039 — browsers bypass the shim); its
  readiness probe is the insecure curl check.
- Compose lane fixture pins: twins use dev Keycloak (`:8443`,
  `keycloak.localhost`, `nx certgen` CA) + the app image stack; core uses
  dev ES `.env`+certs. `aurelius` client = public, directAccessGrants,
  `aurelius-writer`/`reader` users (CHT-79 byte-copy parity between
  `dev/keycloak/import/master.json` and the helm files copy).
- Chart-test safety: `tests/test__charts_*` render aux charts at defaults
  (minikube overlay renders too in the edge suite) — the audience override +
  a new overlay guard test are additive-safe; `helm/environments/minikube.yaml`
  aux `config:` blocks are flat maps (Helm coalesces key-by-key — verified).

## Evaluated 2026-10-31, deferred: testcontainers k3s as cluster flavour

- `testcontainers.community.k3s` (the only Python option; the old
  `testcontainers.k3s` is a deprecated re-export): its `K3SContainer.__init__`
  is broken in 4.15.0 (host IP read pre-start). Raw `DockerContainer` + k3s
  flags works: boot→node-sync **21 s**, host kubectl over mapped 6443 OK,
  privileged OK, `local-path` SC OK.
- Unresolved gates for any CI-flavour decision: our digest-pinned image load
  (`docker save` → `k3s ctr -n k8s.io images import` — rc=3 in the spike,
  needs the CHT-52 lesson applied to k3s), and whether the Envoy Gateway
  LB address is host-routable without `minikube tunnel`.
- Decision: 10.5b design unchanged — the lane lib touches the cluster only
  via kubectl/helm CLI (flavour-agnostic). k3s-as-flavour is a candidate for
  the **CI-shape increment** (privileged k3s fits a CI pod far better than
  minikube). Spike script survived at `/tmp/k3s_spike.py` (throwaway).

## Watch items

- `/etc/hosts` IP churn: the conftest asserts edge resolution == live
  Gateway IP and names `install.sh hosts` on mismatch.
- Shared-cluster serialism: e2e suites on one umbrella must not run in
  parallel (collector port-forwards, shared ES) — document `parallel: false`
  in the targets.
- Realm asset edits (10.5c) touch chart contract guards CHT-79/96 — update
  both copies + guards in the same PR.
- devcontainer CA rebuilds stale project certs (mkcert OU = container id):
  `npx nx certgen <project>` regenerates; seen once already (lineage TLS 401).
- CHT space: 10.5b claims CHT-103..106; DD counter after #189: **next free
  DD: 282**. The design-log top table ends at DD-272 — no new rows.

## Verification (per PR)

- Compose lane byte-identical: `uv run pytest <project>/e2e` (server 37,
  data2model 7, validate-entity 7, core 23, webapp 105×3 browsers) — dev
  stacks (`nx run aurelius-atlas-dev-*:up`), certs fresh.
- Cluster lane: `tools/cluster/install.sh up` → `nx e2e-cluster <project>`
  cold + warm; negative gate (release down → fail-fast naming `install.sh
up`); `uv run pytest tests` (charts, 178 + new guards).
- kubectl/helm/docker/minikube/git-push commands need the unsandboxed flag;
  pre-commit Prettier reflows md tables — `git add -u && git commit` retry.
