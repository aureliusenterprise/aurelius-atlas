# E2E cluster-lane rollout plan (10.5b)

- **Status:** landed on the branch — retires when the PR merges
- **Branch:** `feat/cluster-rollout-10-5b` (stacked on #189 ← #187)
- **Records:** executes the DD-280 verdict; DD-281 (retirements), DD-282 (the
  lane library), DD-283 (the single-lane collapse — the user's 2026-10-31
  pivot: "Any migrated test suite shall only support kubernetes"), DD-284
  (webapp migration, lineage retirement, example-app drop) all ride this one
  increment; spec:
  [10.5b](../conversion/increments/10-5b-cluster-lane-rollout-aux-and-core.md)
  (folded 10.5c/10.5d in — the webapp migration and the lineage-model
  retirement)

The 10.5 POC (DD-280, #187) proved one suite on the deployment. This plan
carries the verdict to the remaining suites. The steps below are locked by
user decisions (2026-10-30/31); the facts sections record what was verified
live so nothing has to be re-discovered.

## Locked decisions

1. **Order:** 10.5b = data2model + validate-entity (the REST twins) +
   `aurelius-atlas-core` (direct ES), then the webapp (Playwright), then the
   lineage-model suite — the 10.5c/10.5d split folded into this increment
   when the webapp proved out and lineage retired (DD-284).
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
6. **CI posture:** local-only, widened by DD-283 — with the compose stacks
   deleted, every migrated `e2e` target needs a live minikube umbrella, so
   the workflows drop `e2e` from `affected`/`run-many` until a cluster-shaped
   runner lands (the k3s-flavour note below is the candidate).
7. **Single lane** (DD-283): no `ATLAS_E2E_TARGET`, no `lane_target()`, no
   `e2e-cluster` targets — a migrated suite's `e2e` target IS the cluster
   suite (`dependsOn: []` cancels the plugin's inferred compose-era deps).

## Steps

| Step | Scope                                                                                                                                                                                                                                                                      | Status          |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| 0    | Retire RSL-01/RSL-02/SRV-09 (tests + rules, both lanes), DD-281                                                                                                                                                                                                            | **done** — #189 |
| 1    | 10.5b: lane lib, server conftest refactor (honesty check), twins + core conftests, audience overlay + chart guard, `install.sh hosts` + devcontainer refresh, spec + DD-282                                                                                                | **done**        |
| 2    | Webapp suite on the lane: edge login, `install.sh realm-origins` (CHT-107, not the realm asset), password from Secret, footer test reads served `/config.json`, collector 4318/4319/4321 + Tempo forwards with pinned loopback ports. 105 tests × 3 browsers green. DD-284 | **done**        |
| 3    | ~~lineage-model on the lane~~ — **retired** instead: its compose fixtures were the test (canned files, no deployed counterpart); rules stay unit/scenario-covered. `e2e/` deleted, no target. DD-284                                                                       | **done**        |
| 4    | Single-lane collapse: `lane_target`/`ATLAS_E2E_TARGET`/`e2e-cluster` removed, `dependsOn: []` overrides, compose `e2e/docker-compose.yaml` files + webapp `e2e/config/` deleted, chart guards shrunk. DD-283                                                               | **done**        |
| 5    | Template examples dropped (apps + lib, realm origins :4200/:18443, dashboards, uv members, data-access example client). DD-284                                                                                                                                             | **done**        |
| 6    | CI: drop `e2e` from `affected`/`run-many` sets (cluster suites can't run there yet). DD-283                                                                                                                                                                                | last step       |

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
- CHT space: 10.5b claims CHT-103..107; DDs landed: 282–284, **next free
  DD: 285**. The design-log top table ends at DD-272 — no new rows.

## Verification (per PR)

- Single lane (the compose bar retired, DD-283): `tools/cluster/install.sh
up` → `nx e2e <project> -c ci` cold + warm on all five migrated projects
  (server 37, data2model 7, validate-entity 7, core 23, webapp 105×3
  browsers); negative gate (release down → fail-fast naming `install.sh
up`); `uv run pytest tests` (charts + shrunk guards).
- Free pinned loopback ports before webapp runs: the dev compose
  observability stack must be DOWN (its collector would answer the suite's
  forwards — silent false-green).
- kubectl/helm/docker/minikube/git-push commands need the unsandboxed flag;
  `sudo -n -E bash tools/cluster/install.sh hosts` (the `-E` keeps the
  kubeconfig); pre-commit Prettier reflows md tables — `git add -u &&
git commit` retry.
