# Design Log

The archive of the technical decisions made during the conversion that are too
implementation-specific for an ADR but must not be lost: storage layout, identifiers, query
translation, test tooling. Business-level decisions are ADRs in
[Architecture Decisions](../adr/index.md).

Each new entry lives in the `design.md` of the increment that makes it, next to that increment's
spec ([ADR 051](../adr/051-the-conversion-proceeds-in-specified-increments.md)); where, is what
the [Moved entries](#moved-entries) index keeps per number. This page holds the entries written
before that layout (DD-001 to DD-094, DD-126 to DD-176, DD-180 to DD-213, DD-218 to DD-221,
DD-234 to DD-246, DD-248 to DD-252 and DD-300 to DD-301 are moved out; what is listed below
stays): it is read-only
history. Nothing is appended here.

## Rules

- Entries are numbered `DD-NNN`, consecutively across the repository; numbers are never reused,
  and an unused number (see the note under [Moved entries](#moved-entries)) stays unused.
- Statuses: **Proposed** → **Accepted**, then optionally **Superseded by DD-NNN**.
- An accepted entry is never edited except its status line. A changed decision is a new entry
  that supersedes the old one.
- Every entry names the increment that introduced it, and lives next to that increment's spec:
  `<project>/specs/N-M-slug/design.md`.
- An increment that makes a decision adds its entry in the same pull request.

## Entry template

```markdown
### DD-NNN. Decision as a statement

- **Status:** Proposed | Accepted | Superseded by DD-NNN
- **Increment:** N.N
- **Date:** YYYY-MM-DD

**Decision.** What we do, in one or two sentences.

**Reason.** Why, in terms of the requirements of the increment.

**Alternatives.** What else was considered and why it lost.

**Consequences.** What follows, including what must be revisited and when.
```

## Log

| #                                                                                                                | Decision                                                                                                                                                                                                                        | Increment     | Status               |
| ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | -------------------- |
| [DD-177](#dd-177-the-parallel-tracks-colliding-dddv-ids-renumber-to-the-7x8x-side)                               | The parallel tracks' colliding DD/DV ids renumber to the 7.x/8.x side                                                                                                                                                           | —             | Accepted             |
| [DD-178](#dd-178-the-merge-resolves-the-opentelemetry-version-split-to-the-1451066b1-set)                        | The merge resolves the OpenTelemetry version split to the 1.45.1/0.66b1 set                                                                                                                                                     | —             | Accepted             |
| [DD-179](#dd-179-the-branchs-second-collision-band-renumbers-above-mains-tail)                                   | The branch's second collision band renumbers above main's tail                                                                                                                                                                  | —             | Accepted             |
| [DD-214](#dd-214-the-test-suite-review-of-2026-10-24-scopes-the-hardening-increments)                            | The test suite review of 2026-10-24 scopes the hardening increments                                                                                                                                                             | cross-cutting | Accepted             |
| [DD-215](#dd-215-the-ci-pipeline-drops-the-traceability-check-and-report)                                        | The CI pipeline drops the traceability check and report; the tools stay as local aids                                                                                                                                           | cross-cutting | Accepted             |
| [DD-216](#dd-216-stacks-own-the-tls-material-they-mount)                                                         | Stacks own the TLS material they mount                                                                                                                                                                                          | cross-cutting | Accepted             |
| [DD-217](#dd-217-the-search-client-lands-on-both-sides-of-the-wire-ahead-of-74)                                  | The search client lands on both sides of the wire, ahead of 7.4                                                                                                                                                                 | cross-cutting | Accepted             |
| [DD-226](#dd-226-the-dev-stacks-restart-windows-are-unbounded)                                                   | The dev stacks' restart windows are unbounded: an attempt budget burns out before Keycloak is up                                                                                                                                | cross-cutting | Accepted             |
| [DD-227](#dd-227-the-store-es-e2e-suite-is-removed-it-evaluated-the-dev-environment-not-production)              | The store-es e2e suite is removed: it evaluated the dev environment, not production                                                                                                                                             | cross-cutting | Accepted             |
| [DD-228](#dd-228-dev-posture-tests-leave-the-suites-the-sweep-of-dd-223s-rule-applied)                           | Six dev-posture e2e tests are removed: they asserted the dev box's deployment state, not shipped behaviour                                                                                                                      | cross-cutting | Accepted             |
| [DD-229](#dd-229-the-shape-a-tail-overlaps-the-test-graph-shares-its-daemon)                                     | Shape-A wall-time tuning: docker-build rides the test graph, sonar overlaps Storybook, cache save on miss                                                                                                                       | cross-cutting | Accepted             |
| [DD-230](#dd-230-parallelism-stays-at-the-default-the-scanner-cache-moves-to-the-pvc)                            | Nx parallelism stays at the default (5 regressed); the SonarScanner download cache moves to the PVC; engine scoping measured away                                                                                               | cross-cutting | Accepted             |
| [DD-231](#dd-231-teardown-downs-the-compose-stacks-prune-only-sweeps-corpses)                                    | CI teardown downs every compose stack: prune only sweeps stopped containers, so the stacks rode through the tail                                                                                                                | cross-cutting | Accepted             |
| [DD-232](#dd-232-the-ci-pipeline-is-a-fan-out-dag-the-pool-is-per-pod-emptydir)                                  | CI splits into validate then {e2e, scan-sonar, chromatic} on a 3-pod pool; the RWO cache PD retires for per-pod emptyDir                                                                                                        | cross-cutting | Accepted             |
| [DD-233](#dd-233-the-toolchain-caches-bridge-pod-churn-through-the-cache-server)                                 | Fan-out pods churn: uv/pre-commit/sonar caches bridge across pods on the cache server (cold-pod tax measured away)                                                                                                              | cross-cutting | Accepted             |
| [DD-247](#dd-247-journal-writes-do-not-wait-for-a-refresh)                                                       | Journal writes do not wait for a refresh                                                                                                                                                                                        | cross-cutting | Proposed             |
| [DD-253](#dd-253-the-chart-contract-suite-lives-at-the-workspace-root-and-renders-with-the-helm-cli)             | The chart-contract suite lives at the workspace root (`tests/`) and asserts rendered manifests via the `helm` CLI                                                                                                               | 10.2          | Accepted             |
| [DD-254](#dd-254-deploy-time-credential-generation-lands-in-102-with-publish-and-rotation-in-104)                | The umbrella's `randAlphaNum` + `lookup` credential generation ships in 10.2; retrieval/rotation polish stays in 10.4                                                                                                           | 10.2          | Accepted             |
| [DD-255](#dd-255-the-coredump-agent-ships-as-its-own-image-project)                                              | The ES coredump agent ships as the `aurelius-atlas-elasticsearch-agent` image, not a ConfigMap-embedded jar                                                                                                                     | 10.2          | Accepted             |
| [DD-256](#dd-256-the-realm-is-a-byte-copy-chart-asset-and-its-placeholders-resolve-in-keycloak)                  | The realm is a byte-copy chart asset rendered verbatim; its `${...}` placeholders resolve in Keycloak, never by Helm                                                                                                            | 10.2          | Accepted             |
| [DD-257](#dd-257-stateful-workloads-run-as-their-images-declared-uid-with-fsgroup-for-volumes)                   | Each stateful pod pins its hardened image's declared uid (ES 1000, KC 65532, PG 70) with `fsGroup` for volumes — no privilege drop                                                                                              | 10.2          | Accepted             |
| [DD-258](#dd-258-a-bundled-database-dates-its-consumer-with-a-wait-init-and-its-own-probe-sans)                  | Keycloak waits for the bundled Postgres via an init container (the compose `depends_on: service_healthy` port); the DB cert carries the probe's loopback SAN                                                                    | 10.2          | Accepted             |
| [DD-259](#dd-259-the-chart-managed-trust-root-is-a-namespaced-self-signed-issuer-chain)                          | The default trust root is a namespaced self-signed-issuer chain (bootstrap → CA Certificate → CA issuer); a bare self-signed ClusterIssuer mints a per-certificate root (partially supersedes DD-286)                           | 10.2          | Accepted             |
| [DD-260](#dd-260-keycloaks-management-interface-is-tls-in-prod-mode-probes-included)                             | Prod-mode Keycloak serves TLS on the management port; probes are HTTPS and the startup budget covers the per-container re-augmentation                                                                                          | 10.2          | Accepted             |
| [DD-261](#dd-261-the-two-hop-edge-names-both-client-ip-trust-hops)                                               | The Gateway in front of the webapp makes DD-238's TCP-trust assumption false: realip from the gateway network, forwarded_allow_ips from values                                                                                  | 10.3a         | Accepted             |
| [DD-262](#dd-262-the-webapp-nginx-config-resolves-at-pod-start-not-at-helm-render)                               | The nginx ConfigMap is a byte-copy asset; its placeholders (incl. the ingest bearer) resolve at pod start in an init container, never at Helm render                                                                            | 10.3a         | Accepted             |
| [DD-263](#dd-263-backendtlspolicy-renders-the-v1-cacertificaterefs-list)                                         | The edge BackendTLSPolicy renders the stable v1 `caCertificateRefs` list — the experimental `v1alpha3` singular ref is not in the standard CRD bundle                                                                           | 10.3a         | Accepted             |
| [DD-264](#dd-264-the-webapps-emptydirs-mount-below-the-images-symlink-baked-in-paths)                            | Writable emptyDirs mount below the nginx image's symlinked paths; upstream placeholder defaults are cluster FQDNs because the stub resolver ignores search domains                                                              | 10.3a         | Accepted             |
| [DD-265](#dd-265-the-issuers-public-name-resolves-inside-the-cluster-too-split-horizon)                          | Split-horizon issuer: a runbook CoreDNS entry resolves `keycloak.<domain>` to the Keycloak Service (which gains a 443 port); Keycloak and every consumer keep the public URL, so the issuer claim is one value in both horizons | 10.3b         | Accepted             |
| [DD-266](#dd-266-scrape-with-static-configs-and-slice-owned-puller-deployments)                                  | The cluster answers 10.2's deferred scrape question the compose's way: Prometheus static configs over chart Services, plus ES/Keycloak `metrics-puller` Deployments; no Prometheus Operator                                     | 10.3b         | Accepted             |
| [DD-267](#dd-267-grafanas-admin-password-is-a-generated-secret-and-the-login-form-stays-disabled)                | Grafana gets an umbrella-generated `-grafana-admin` Secret; with `adminPasswordSecret` unset the dev anonymous-Viewer-only posture (login disabled) stands unchanged                                                            | 10.3b         | Accepted             |
| [DD-268](#dd-268-the-clusters-deployment-environment-is-named-by-values-not-baked-as-development)                | The collector's `deployment.environment.name` comes from values (default `cluster`); the dev compose keeps `development` — environment, not drift                                                                               | 10.3b         | Accepted             |
| [DD-269](#dd-269-the-boot-gate-image-is-curl-not-busybox-wget-cannot-handshake-keycloaks-tls)                    | The issuer-wait init ships as `dhi.io/curl` with native retry; busybox wget resets against Keycloak's TLS, and the hardened curl image has no shell for a loop                                                                  | 10.3b         | Accepted             |
| [DD-270](#dd-270-the-webapp-serves-tls-behind-the-gateway-the-last-plaintext-hop-closes)                         | The webapp's listener serves TLS and the umbrella adds its BackendTLSPolicy; the last plaintext backend hop closes (supersedes DD-285's plaintext-backend clause)                                                               | 10.3c         | Accepted             |
| [DD-271](#dd-271-network-policy-ownership-the-umbrella-deny-all-and-the-charts-additive-allows)                  | The umbrella renders the namespace default-deny; each chart renders its own additive ingress allows; the two never overlap, so no switch opens the namespace (CHT-60/72)                                                        | 10.6          | Accepted             |
| [DD-272](#dd-272-the-edge-allows-source-is-a-knob-with-an-all-namespaces-default)                                | The gateway edge allows read `networkPolicy.gatewayNamespaces`; the default admits every namespace, because a public browser edge's data-plane placement varies per cluster and a wrong pin silently black-holes the edge       | 10.6          | Accepted             |
| [DD-283](#dd-283-one-chart-per-component-under-an-umbrella-published-as-oci-artifacts)                           | One chart per component under an umbrella, published as OCI artifacts from `charts/`                                                                                                                                            | 10.1          | Superseded by DD-290 |
| [DD-284](#dd-284-helm-targets-are-inferred-from-chartyaml-by-a-plugin-mirroring-dockerts)                        | Helm targets are inferred from `Chart.yaml` by a plugin mirroring `docker.ts`                                                                                                                                                   | 10.1          | Superseded by DD-293 |
| [DD-285](#dd-285-the-edge-is-gateway-api-not-ingress-nginx)                                                      | The edge is Gateway API, not ingress-nginx (retired March 2026); instrumentation and Istio are out                                                                                                                              | 10.1          | Accepted             |
| [DD-286](#dd-286-tls-trust-is-cert-manager-issuers-each-pinned-ca-is-a-configmap-of-the-trust-root)              | TLS trust is cert-manager issuers; the CA each consumer pins is a ConfigMap of the cluster trust root                                                                                                                           | 10.1          | Accepted             |
| [DD-287](#dd-287-the-umbrella-owns-shared-secrets-generated-at-install-and-preserved-on-upgrade)                 | The umbrella owns shared secrets; the webapp's telemetry token is a browser-reachable public constant                                                                                                                           | 10.1          | Accepted             |
| [DD-288](#dd-288-the-umbrella-pins-its-component-charts-to-its-own-version-chart-version-equals-release-version) | The umbrella pins its component charts to its own version; chart version equals release version, `appVersion` is the tag                                                                                                        | 10.1          | Accepted             |
| [DD-289](#dd-289-the-chart-gate-renders-each-charts-own-values-files-the-release-refreshes-chartlock)            | The chart gate renders each chart's own values files separately; the release refreshes Chart.lock in `afterAllProjectsVersioned`                                                                                                | 10.1          | Accepted             |
| [DD-290](#dd-290-component-charts-live-next-to-their-projects-helpers-are-chart-local)                           | Component charts live in `apps/<app>/helm` / `dev/<name>/helm`; helpers are chart-local, no library charts                                                                                                                      | 10.1          | Accepted             |
| [DD-291](#dd-291-the-chartyaml-is-the-charts-whole-nx-identity-no-chart-projectjson)                             | The `Chart.yaml` is the chart's whole Nx identity: the plugin infers name, targets, release actions, and umbrella edges                                                                                                         | 10.1          | Superseded by DD-293 |
| [DD-292](#dd-292-the-umbrella-sits-at-the-workspace-root-helm)                                                   | The umbrella lives at `helm/` in the workspace root: the chart tree is all `helm/` directories, `charts/` is gone                                                                                                               | 10.1          | Accepted             |
| [DD-293](#dd-293-helm-targets-merge-onto-the-owning-project-a-chart-is-not-a-project)                            | Helm targets merge onto the owning project: a chart is not a project                                                                                                                                                            | 10.1          | Accepted             |
| [DD-294](#dd-294-the-minikube-trial-findings-in-the-aux-charts-land-in-103)                                      | The minikube trial's two aux-chart findings (unbackable CA mount, lineage-model upstream URLs) are fixed in 10.3                                                                                                                | 10.1          | Accepted             |
| [DD-295](#dd-295-chart-track-id-collisions-with-main-renumber-above-both-ranges)                                 | Chart-track id collisions with main renumber above both ranges                                                                                                                                                                  | —             | Accepted             |
| [DD-296](#dd-296-61as-required-auth-settings-land-in-the-charts-as-joins)                                        | 6.1a's required server-auth settings land in the charts as issuer/realm/secret joins; the dashboards' browser leg stays dashboard-host-gated                                                                                    | 10.12         | Accepted             |
| [DD-297](#dd-297-the-aux-apis-auth_realm-joins-globalrealm)                                                      | The aux APIs' AUTH_REALM was a static `master` config literal; it joins `global.realm` like every other realm-bearing env (CHT-74)                                                                                              | 10.12         | Accepted             |
| [DD-298](#dd-298-a-stuck-pending-install-release-is-cleared-by-uninstall)                                        | `helm install --wait` against a never-Ready workload leaves the release `pending-install` until uninstalled — runbook warns                                                                                                     | 10.1          | Accepted             |
| [DD-299](#dd-299-helm-lint-vendors-umbrella-dependencies-like-helm-template)                                     | `helm-lint` runs `helm dep update` before linting: the umbrella's gitignored subchart tarballs otherwise leave a fresh checkout without dependency values                                                                       | 10.12         | Proposed             |

### DD-177. The parallel tracks' colliding DD/DV ids renumber to the 7.x/8.x side

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into
  `feat/api-client-libraries`, PR #143)
- **Date:** 2026-10-24

**Decision.** The 2.x/3.x track (server spine, entity store, relationships,
classifications, tasks, audits) and the 7.x/8.x track (webapp shell, aux APIs,
client libraries) branched at DD-036/DV-10 and minted ids in parallel: main
took DD-037..089 and DV-11..46, the branch took DD-037..088 (51 ids, the same
numbers, different decisions) and DV-11..27. The merge renumbers the **branch
side above both ranges**: DD-037..088 → DD-126..176 and DV-11..27 → DV-47..61
in ascending order — DV-18/DV-22 included, to DV-62/DV-63, because main's DD-049
retired its own DV-18/DV-22 rows and retired numbers are never reused — and this
entry (DD-177) records it. Main's ids keep their numbers. The citation sweep
rewrote every spec, doc, code comment, scenario, `.env` comment, and trace
marker on the branch side; a chain whose members renumber non-consecutively
becomes an explicit list (`DD-059/062` → `DD-148, DD-151`).

**Reason.** Main's 2.x decisions are merged and cited by merged code — they
are the accepted record, and the ledger's rule (numbers are never reused,
accepted entries are never edited) protects them. The branch's specs are the
in-progress side of the same ledger, so it is the side allowed to move; moving
51+17 ids in one mechanical, reviewable sweep costs less than living with
ids that mean two things. The branch's non-colliding ids stay: DD-089..125
is untouched, and the new range starts above main's DD-089 with room for
this entry. DD-065 is main's alone (the branch mints no DD-065).

**Consequences.** The merge of main into the branch is conflict-free for the
id ledger: the two tracks occupy disjoint ranges. The mapping table (branch
old → new) is this entry's appendix, below; every pre-merge commit message
cites the OLD numbers — commit history is not rewritten, and the appendix is
the lookup from a commit's citation to the merged record. The design-log and
deviations tables are sorted by number, so the renumbered entries interleave
with main's by position only after the merge sorts them; within the branch
the sweep is in-place (ascending order). The untracked dev `.env` files
(decrypted from the renumbered `.env.enc` comments) refresh on the next
`nx decrypt`.

| Old    | New    | Old    | New    | Old    | New    |
| ------ | ------ | ------ | ------ | ------ | ------ |
| DD-037 | DD-126 | DD-056 | DD-145 | DD-075 | DD-163 |
| DD-038 | DD-127 | DD-057 | DD-146 | DD-076 | DD-164 |
| DD-039 | DD-128 | DD-058 | DD-147 | DD-077 | DD-165 |
| DD-040 | DD-129 | DD-059 | DD-148 | DD-078 | DD-166 |
| DD-041 | DD-130 | DD-060 | DD-149 | DD-079 | DD-167 |
| DD-042 | DD-131 | DD-061 | DD-150 | DD-080 | DD-168 |
| DD-043 | DD-132 | DD-062 | DD-151 | DD-081 | DD-169 |
| DD-044 | DD-133 | DD-063 | DD-152 | DD-082 | DD-170 |
| DD-045 | DD-134 | DD-064 | DD-153 | DD-083 | DD-171 |
| DD-046 | DD-135 | DD-066 | DD-154 | DD-084 | DD-172 |
| DD-047 | DD-136 | DD-067 | DD-155 | DD-085 | DD-173 |
| DD-048 | DD-137 | DD-068 | DD-156 | DD-086 | DD-174 |
| DD-049 | DD-138 | DD-069 | DD-157 | DD-087 | DD-175 |
| DD-050 | DD-139 | DD-070 | DD-158 | DD-088 | DD-176 |
| DD-051 | DD-140 | DD-071 | DD-159 | DV-11  | DV-47  |
| DD-052 | DD-141 | DD-072 | DD-160 | DV-12  | DV-48  |
| DD-053 | DD-142 | DD-073 | DD-161 | DV-13  | DV-49  |
| DD-054 | DD-143 | DD-074 | DD-162 | DV-14  | DV-50  |
| DD-055 | DD-144 | —      | —      | DV-15  | DV-51  |
| —      | —      | —      | —      | DV-16  | DV-52  |
| DV-17  | DV-53  | DV-21  | DV-56  | DV-25  | DV-59  |
| DV-18  | DV-62  | DV-22  | DV-63  | DV-26  | DV-60  |
| DV-19  | DV-54  | DV-23  | DV-57  | DV-27  | DV-61  |
| DV-20  | DV-55  | DV-24  | DV-58  | —      | —      |

DD-065 is main's alone (the branch mints no DD-065), and the branch's
DD-089..125 sit above main's range — both untouched.

### DD-178. The merge resolves the OpenTelemetry version split to the 1.45.1/0.66b1 set

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into
  `feat/api-client-libraries`, PR #143)
- **Date:** 2026-10-24

**Decision.** The merged `uv.lock` is re-resolved to one OpenTelemetry set:
the OTLP exporter and SDK at 1.45.1, the instrumentation family (core, asgi,
fastapi, httpx, logging, system-metrics) at 0.66b1 — main's set. The text
merge had kept the branch's `opentelemetry-instrumentation-logging`/
`-system-metrics` at 0.65b0 under main's `opentelemetry-instrumentation`
0.66b1, and 0.65b0 pins the core at `==0.65b0`: the four app Docker builds
fail `ResolutionImpossible`. The two otel seam tests follow the 1.45.1
exporter's internals: the ingest session moved from `OTLPSpanExporter._session`
to `._client._transport._session`, and the metric exporter's resolved headers
from `._headers` to `._client._headers`.

**Reason.** Main's lock is the accepted record (DD-177), and the pins are
exact-equality inside the instrumentation family — a mixed set is not a
solution pip can install, so the merged lock must resolve to one generation.
The seam tests assert the wiring through the exporter's private structure
(their declared purpose: the session/headers the ingest pipeline attaches);
re-pointing them at the moved attributes keeps the same assertion on the
same object graph.

**Consequences.** `nx run-many -t test e2e -c ci` is green again for the
otel lib and the four Docker builds. The exporter's private attributes are
not a public API: the tests are pinned to the locked version, and a future
OTel bump must re-point them the same way. No production code changed —
`build_otlp_pipeline` passes `session=` through the constructor, which is
public in both versions.

### DD-179. The branch's second collision band renumbers above main's tail

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into
  `feat/api-client-libraries`, PR #143)
- **Date:** 2026-10-24

**Decision.** Round 1 (DD-177) planned to main's DD-089 and DV-46; main's
tail is DD-090 and DV-47 (the classification-search entry and row, 4.1).
The merge of main's ledger keyed by id and kept HEAD, dropping main's
DD-090 entry and DV-47 row; this entry restores both, and renumbers the
branch's second band above main's tail and above DD-177/DD-178: DD-090..125
→ DD-180..214 (the branch mints no DD-104, so the shift is not uniform)
and DV-47..63 → DV-64..80, with the citation sweep over every spec, doc,
code comment, scenario, `.env` comment, and trace marker on the branch
side. The mapping table is this entry's appendix.

**Reason.** The same as DD-177: main's ids are the accepted record cited
by merged code, and the ledger's rule (numbers are never reused, accepted
entries are never edited) protects them; the in-progress side moves. The
band DD-090..125 minted above DD-088 because main's tail was DD-089 when
it was minted — main kept minting, and the merge proved the tail moved.

**Consequences.** The id ranges of the two tracks are disjoint: main
DD-001..090 / DV-1..47, the branch DD-126..176, DD-180..214 / DV-64..80.
Every pre-merge commit message cites the OLD numbers; DD-177's and this
entry's appendices are the lookup. The untracked dev `.env` files refresh
on the next `nx decrypt`.

| Old    | New    | Old    | New    | Old    | New    |
| ------ | ------ | ------ | ------ | ------ | ------ |
| DD-090 | DD-180 | DD-103 | DD-193 | DD-116 | DD-205 |
| DD-091 | DD-181 | DD-105 | DD-194 | DD-117 | DD-206 |
| DD-092 | DD-182 | DD-106 | DD-195 | DD-118 | DD-207 |
| DD-093 | DD-183 | DD-107 | DD-196 | DD-119 | DD-208 |
| DD-094 | DD-184 | DD-108 | DD-197 | DD-120 | DD-209 |
| DD-095 | DD-185 | DD-109 | DD-198 | DD-121 | DD-210 |
| DD-096 | DD-186 | DD-110 | DD-199 | DD-122 | DD-211 |
| DD-097 | DD-187 | DD-111 | DD-200 | DD-123 | DD-212 |
| DD-098 | DD-188 | DD-112 | DD-201 | DD-124 | DD-213 |
| DD-099 | DD-189 | DD-113 | DD-202 | DD-125 | DD-214 |
| DD-100 | DD-190 | DD-114 | DD-203 | DV-47  | DV-64  |
| DD-101 | DD-191 | DD-115 | DD-204 | DV-48  | DV-65  |
| DD-102 | DD-192 | —      | —      | DV-49  | DV-66  |
| —      | —      | —      | —      | DV-50  | DV-67  |
| —      | —      | —      | —      | DV-51  | DV-68  |
| —      | —      | —      | —      | DV-52  | DV-69  |
| —      | —      | —      | —      | DV-53  | DV-70  |
| —      | —      | —      | —      | DV-54  | DV-71  |
| —      | —      | —      | —      | DV-55  | DV-72  |
| —      | —      | —      | —      | DV-56  | DV-73  |
| —      | —      | —      | —      | DV-57  | DV-74  |
| —      | —      | —      | —      | DV-58  | DV-75  |
| —      | —      | —      | —      | DV-59  | DV-76  |
| —      | —      | —      | —      | DV-60  | DV-77  |
| —      | —      | —      | —      | DV-61  | DV-78  |
| —      | —      | —      | —      | DV-62  | DV-79  |
| —      | —      | —      | —      | DV-63  | DV-80  |

### DD-214. The test suite review of 2026-10-24 scopes the hardening increments

- **Status:** Accepted
- **Increment:** cross-cutting (rides the delivery docs; no roadmap row — the
  hardening increments 8.6/8.7/7.19/9.1 carry their own rows when specified)
- **Date:** 2026-10-24

**Context.** Development added tests ad hoc per increment. A workspace-wide
review (all apps, all Python libraries, all frontend projects, both e2e
suites) measured coverage and scored every suite against the five non-happy
flow categories (input/validation, business rule/auth, infrastructure,
interrupted/async, edge-case). Findings: infrastructure failure testing is a
house strength (lineage-model, store-es, auth); the systematic holes are
mid-request infra failures (server, core), frontend session lifecycle and
error UX breadth (7 of 71 webapp-side specs assert an HTTP error), the client
libraries' response-shape failures (2xx-with-garbage-body, timeout vs connect
error), and data2model's view-edge/dynamic-view engine paths (0%). No coverage
threshold exists in CI, and the Python libraries' `coverage.xml` is generated
in CI only, not committed.

**Decision.** The review's findings, verdicts, ranked deferred backlog, and
template-code exemptions are recorded in
[Test Suite Review](../platform/delivery/testing-review.md), kept as a dated
review page (reviews record, they do not drift). Four hardening increments
proceed from it, one PR each, spec-first. The review's first finding about
the ledger: **the failure semantics are almost all already specified — the
tests are what is missing** (DTM-04/06/07 state the view-edge and dynamic-view
paths at 0% coverage; LM-07/11/12/13 state the transport-failure, fast-fail,
and outage-counting behaviours; CL-04/05/06 state the client failure
contract; APC-04/05, ALR-04/05, SHC-05 state the frontend's). The increments
therefore cite the existing ids, and mint new ones only where a finding names
behaviour no rule states: **8.6** aux API failure hardening (proves
DTM/LM/VE ids, adds negative parity scenarios), **8.7** client failure
contract (adds CL-08 — a 2xx body that fails its model is the contract
failing, not succeeding; proves CL-04/05/06), **7.19** frontend failure UX
(proves APC/ALR/SPL/SHC ids; the example app's editor has no increment spec,
its tests carry plain names), **9.1** resilience e2e with targeted
container-stopping scenarios (the only new prefix, `RSL`). Coverage
enforcement stays where it is: the
SonarQube quality gate — no `--cov-fail-under`, no Vitest
`coverage.thresholds`, no new CI flag. The server-spine findings (mid-request
store failure, concurrent store writes) are explicitly deferred to the 2.x
track as ranked backlog #1, not dropped.

**Reason.** The gate already measures coverage (the `-c ci` configs write
`coverage.xml`/`lcov.info`, CI uploads them, `nx affected -t sonar` feeds
Sonar, whose quality gate fails on low levels — including new-code coverage,
which ratchets naturally with every hardening PR); a second local flag would
duplicate the gate and fight ADR 014's "defined once, runs everywhere". The
priority split (frontend / aux APIs / clients first) follows where the
representativeness gaps bite the conversion's next increments; the server
spine's mid-request failures pair with 2.2's entity-store work, which changes
those same call paths.

**Alternatives.** (a) A per-project coverage ratchet in the Nx python plugin
and Vitest configs — refused, see Reason (and the user's call of this date).
(b) One workspace-wide coverage floor — refused: the template baseline is
heterogeneous and a uniform floor would punish the vendored dashboard and
the example apps. (c) Destructive failure-injection e2e as a nightly
resilience suite — refused for now in favour of a small number of targeted
scenarios inside the existing per-PR e2e suites (≤2 min budget each), the
same realism bar as ADR 012.

**Consequences.** The review page is the reference for "what was known on
this date"; its numbers are a snapshot, the trace report stays the live
system of record. Rule-id reservations: **CL-08** (8.7's one new rule) and
`RSL-01…` (9.1); the other increments cite existing ids — minting new ids for
already-specified behaviour would fork the ledger. The fastapi-example, `sdk`'s
aws/msal/logger, aurelius-atlas-example, and the dashboard are exempted from
hardening (matching the trace check's `exclude-projects` and DD-017).
Phase ordering: 8.6 and 8.7 parallel, 7.19 parallel, 9.1 after 8.6 and 7.19.

### DD-215. The CI pipeline drops the traceability check and report

- **Status:** Accepted
- **Increment:** cross-cutting (rides the CI pipeline; no roadmap row)
- **Date:** 2026-10-24

**Context.** Increment 0.3 wired [ADR 049](../adr/049-every-function-and-rule-is-traceable-to-a-test.md)
into the pipeline: the `validate` job runs `aurelius-atlas-trace check` (collection only, no test
runs) and the `test` job builds an HTML trace report from the JUnit, coverage, and trace files. The
check proves that a test _names_ a function or rule id; it never runs anything. The desired
behaviour of every increment is already encoded in its unit tests, which the pipeline runs, so the
gate restates what the suites prove. Keeping the declarations true across the whole surface —
TypeScript citations, end-to-end claims, rules whose proof lives in another repo — turned into
bookkeeping that fails CI without indicating a missing test.

**Decision.** `.github/workflows/ci.yaml` drops both steps: the `validate` job no longer runs
`aurelius-atlas-trace check`, and the `test` job no longer runs `aurelius-atlas-trace report` or uploads the
`test-report` artifact. What blocks a merge is a failing test. The trace lib, the `covers` marker, and the
`--trace-json` plumbing stay in the repo as local tools and a code-review convention — `nx test`/`nx e2e`
keep writing the files, and anyone can run `check` or `report` themselves. Coverage enforcement is
unchanged: the SonarQube quality gate
([DD-214](#dd-214-the-test-suite-review-of-2026-10-24-scopes-the-hardening-increments)). Parity scenarios
keep their citation discipline ([ADR
052](../adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source.md)) and the parity lib
keeps its own checks — that is how expected behaviour is justified, not a trace gate. The business-level
decision is [ADR 056](../adr/056-behaviour-is-proven-by-executed-tests-not-by-a-trace-gate.md), which
supersedes ADR 049; `DD-009` (the record:
`libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`), `DD-010` (the record:
`libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`), and `DD-011` (the record:
`libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`) describe the tools, which
remain, so they stand as written.

**Alternatives.** (a) Widen the gate to prove the gaps away (TypeScript citations, end-to-end
markers, seams for cross-repo rules) — refused: more mechanism proving declarations, no executed
behaviour. (b) Keep the check as a non-blocking warning — refused: an unenforced gate is
documentation nobody reads, and the noise stays. (c) Delete the trace lib as a slice now —
refused: the marker is a useful review pointer and removing it would rewrite every test's
metadata for no gain; it is removable later as one slice.

**Consequences.** The pipeline is smaller and says only what it can prove. The per-change
published trace report is gone; reviewers read the tests and the coverage report. Increment specs
that list `aurelius-atlas-trace check` in their "gates" describe the verification the increment
was accepted with — they are dated records, not promises about current CI, and are not edited.

### DD-216. Stacks own the TLS material they mount

- **Status:** Accepted
- **Increment:** cross-cutting (e2e wiring; no roadmap row)
- **Date:** 2026-10-25

**Context.** The webapp's e2e stack runs the real Atlas server behind the nginx `/api/` proxy ( `DD-142` (the
record: `apps/aurelius-atlas-webapp/specs/7-3-api-client-auth/design.md` )), and the server container mounted
`apps/aurelius-atlas-server/certs` — the server project's own material, because its leaf carries the
`aurelius-atlas-server` SAN nginx verifies against. The webapp's `e2e` target declared the server's
`docker-build` and the dev stacks' `up` as `dependsOn` but not the server's `certgen` : Nx's compose plugin
infers `certgen` from the compose **owner's** `tls.json` (tools/plugins/docker-compose.ts), so a sibling
project's `certs/` mount is invisible to it. When the devcontainer was rebuilt, mkcert regenerated its root CA
and every project self-healed its own material on its next `certgen` — the server's stayed signed by the old
CA, its server container failed Elasticsearch TLS verification, exited 3 during `docker compose up --wait` ,
and every webapp e2e test errored at fixture setup.

**Decision.** The stack mounts only its owning project's certs. `tls.json` for the
webapp gains an `aurelius-atlas-server` service (the same SANs the server project
issues: the service name, localhost, 127.0.0.1), so the webapp's own `certgen` — already
a `dependsOn` of `e2e` and `serve`, and auto-wired by the compose plugin's rule —
generates the leaf the server container wears. `e2e/docker-compose.yaml` mounts
`../certs` for it, and no cross-project `certgen` dependency is needed. The CA bundle
is the shared mkcert root, so the server's verification of the dev Elasticsearch, the
collector, and Keycloak is unchanged; the dev server (`nx serve aurelius-atlas-server`)
still presents the server project's own leaf.

**Alternatives.** (a) Declare `{projects: ["aurelius-atlas-server"], target: "certgen"}`
on the webapp's `e2e` — the pattern PR #143 used for lineage-model → data2model, and
correct: it keeps one issuer per identity. Refused for the webapp because the mount is
part of the webapp's e2e stack, and a stack should carry its own material: with the
`dependsOn`, "the webapp project needs the server project's certs" is a fact recorded
only in a mount string, and certgen stays a target whose trigger (the devcontainer
rebuild) lives outside the project that consumes it. (b) Have `certgen.sh` refresh
every project's material — refused: a project's target writing into other projects
breaks the slice ownership ADR 002 relies on. (c) Teach the compose plugin to parse
volume mounts and auto-add the owning project's `certgen` — deferred; it generalises
the inference rule but adds plugin magic for a pattern (stacks that embed a sibling's
image) the explicit `dependsOn`/manifest already covers.

**Consequences.** `nx e2e aurelius-atlas-webapp` is self-sufficient for TLS: a fresh
container rebuilds the webapp's `certs/` (server leaf included) before compose starts.
Two projects now issue a leaf for the `aurelius-atlas-server` name — the server's for
its own stacks, the webapp's for the e2e stack — which is dev-only identity, gitignored
and never shipped (ADR 006); `apps/aurelius-atlas-server/certs` is no longer read by
the webapp stack. The same audit swept the workspace's other two cross-project cert
mounts (the only ones beyond this): the observability collector pinned its OIDC
`issuer_ca_path` to the webapp's CA copy mounted at `/dev-ca`, which no target
produced — it now verifies the issuer against its own `certs/ca.pem` (the mkcert root
is shared workspace-wide, byte-identical copies), so the mount and its producer
disappear together. The lineage-model e2e stack mounted data2model's certs behind an
explicit cross-project `certgen` `dependsOn` (PR #143 — the pattern this entry's
alternative (a)); it now follows this entry's decision: `tls.json` gains the
`aurelius-atlas-data2model` service, the stack mounts `../certs`,
and the cross-project `certgen` `dependsOn` is gone (its `docker-build` stays — the
image is data2model's artifact). After this, no compose file mounts another project's
`certs/`: every stack's TLS material is generated by the stack owner's own `certgen`,
matching the frontend-example, whose `tls.json` already listed all three services its
e2e stack hosts.

### DD-217. The search client lands on both sides of the wire, ahead of 7.4

- **Status:** Accepted
- **Increment:** cross-cutting (the 8.4 client family and the 7.3 Angular client; no roadmap row)
- **Date:** 2026-10-26

**Context.** Increments 4.1/4.2 gave the server the discovery routes
(`/api/atlas/v2/search/**`), and the Python client gained them as
`AtlasClient.search` (CL-13, the 8.4 family). On the frontend, 7.3 deliberately
ported only the surface the server implemented then (DD-140), leaving every
search call to 7.4 ("the search slice, gated by server 4.1/2.3"). With server
4.1/4.2 merged, the gate's server half is met, and 7.4's first line needs
`SearchService` to exist — the client is the seam 7.4 consumes, and a client
built without its consumer is the speculative build DD-140 rejects.

**Decision.** Land the typed search client on both sides of the wire now, as
data-layer only: `AtlasClient.search` (CL-13) and, in
`libs/angular/aurelius-atlas-data-access`, `SearchService` (APC-11,
`search.service.ts`) with the search DTO cluster (`atlas-search.ts`, APC-03's
hand-mirror of `aurelius_atlas_model/discovery.py`). No screen calls it: the
browse landing's affordances, the header search bar, and the results screen stay
7.4's. The GET searches send the Java defaults (a false flag, a `0` page) as
their absence, matching the server routes' `flag`/`java_number` reading; the
POST searches send the parameters as the body `validate_basic_search_parameters`
/ `validate_quick_search_parameters` validate.

**Alternatives.** (a) Wait for 7.4 and build the client inside it — refused:
7.4 is a UI slice (the results screen redesign), and bundling the wire contract
into it makes its review carry both; (b) generate the TS DTOs from the Python
models — deferred with the same open question as the typedef cluster's hand-sync
(APC-03), one mechanism for all DTOs is better than one per cluster.

**Consequences.** 7.4 consumes `SearchService` directly; the webapp's e2e stack
already runs the real server behind the proxy (DD-142), so a 7.4 flow test needs
no new wiring. The two DTO clusters (`atlas-search.ts`,
`aurelius_atlas_model/discovery.py`) join the hand-sync list in
`aurelius-atlas-data-access/AGENTS.md`. The Python side is proven against the
container (`apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_search_e2e.py`);
the Angular side is proven against `HttpTestingController` — the e2e proof of a
search through the proxy lands with 7.4's screen.

### DD-222. The Python apps emit the stable HTTP semantic conventions

- **Status:** Accepted
- **Increment:** cross-cutting (telemetry; no Atlas REST semantics — no roadmap row, DD-210's pattern)
- **Date:** 2026-10-26

**Context.** The webapp → server → Elasticsearch trace (7.18/7.19) carried two
HTTP conventions at once. The browser leg (JS SDK 2.12) and elasticsearch-py's
native spans emit the stable set (`http.request.method`, `url.full`,
`db.system.name` — the latter stable natively since 8.13, DD-210); the
FastAPI/ASGI leg (instrumentation 0.66b1) emits the old set by default
(`http.method`, `http.url`, `http.status_code`, `net.peer.*`). Every
span-attribute filter written against the stable names silently misses the
request spans — the exact trap DD-210's ES-span probe steps around by
matching `db.system.name` only. The same split lands on metrics: the RED
panels read the old `http_server_duration_milliseconds` (ms), which the
instrumentor stops reporting under the opt-in.

**Decision.** All five Python apps set the standard
`OTEL_SEMCONV_STABILITY_OPT_IN=http` (value `http`, not `http/dup` —
the old set is dropped, not doubled). It is a bare `OTEL_*` name
(third-party-runtime consumer, the root `AGENTS.md` env rule) set in two
places per app: the `Dockerfile` `ENV` (the e2e/prod image) and the
project `.env`/`.env.enc` (`nx serve`, whose process environment Nx
builds from the project env). The FastAPI RED dashboard moves with it in
the same change: `http_server_request_duration_seconds` (stable; the SDK
emits seconds, the ms panels multiply the quantiles by 1000),
`http_server_response_body_size_bytes`, labels `http_route` /
`http_response_status_code`; `http_server_active_requests` keeps its name
(the panel uses a bare `sum()`; the stable label set is a subset). The
SSE exclusion also fixes a stale route: the old `http_target!="/sse"`
never matched the real route `/entities/sse` (the router mounts it under
its prefix), so the p95-excl-SSE panel silently included stream
durations. The server e2e store-span probe (DD-210) gains the convention
pin: the request span must carry `http.request.method=GET` and none of
`http.method`/`http.url`/`http.status_code`.

**Alternatives.** (a) `http/dup` — refused: it doubles span attributes
and metrics series forever; the migration it exists for has no second
consumer here (the collector pipeline and every dashboard in-repo are
updated in this change, and no external consumer reads these series).
(b) Set the opt-in in code (the instrumentor constructors accept no
equivalent; the SDK reads it once at first instrumentation, and the
apps' composition roots instrument at import-adjacent time) — refused:
env is the mechanism the standard defines, and `nx serve`/image/dashboards
stay declarative. (c) Leave the server legacy and rewrite the ES-span
filters to old names — refused: the stable set is where OTel has
standardised (the JS browser SDK and elasticsearch-py are already
there), and one trace carrying one convention is the point.

**Consequences.** Server and auxiliary-app spans drop
`http.url`/`http.status_code`/`net.peer.*` (nothing in-repo filters on
them; the webapp/frontend/keycloak dashboards read web-vital, Micrometer,
and resource attributes only — verified). Metric history is split at the
flip: the old `http_server_duration_milliseconds` series stop, the new
ones start (dev dashboards, acceptable; Grafana's time range covers the
gap). The active-requests gauge loses its `http_host`/`http_server_name`
labels (the stable set is method+scheme; the panel is a bare sum). The
server e2e probe is the regression gate: a dropped `ENV` in an image
fails the store-span test with a named message. The 8.x aux apps carry
the same ENV pair for symmetry — their spans join the stable set on the
next trace they ride (the 8.2 chain, DD-210). Tempo's search by
`resource.*` and the Grafana Explore panels are unaffected (resource
attributes are not part of the HTTP semconv switch).

### DD-223. E2E suites never restart shared dev infra; layout parity leaves e2e

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure)
- **Date:** 2026-10-27

**Decision.** An e2e suite may read and write the shared `dev/*` services, but it
must **never restart** them: no `docker compose down`/`up`, no container cycling,
on a stack other suites ride. Writes stay allowed when namespaced and self-cleaned
(the webapp's uuid-prefixed indices, the server's `scenario_*` writes, the example
apps' fixture rows). Concretely:

- `aurelius-atlas-store-es` e2e drops its ESD-04 restart-persistence test — the
  only test in the fleet that took the shared dev Elasticsearch down and up
  mid-suite. The rule moves to the increment spec as deliberately untested: the
  named-volume behaviour is verified by review, and the healthcheck (DD-008)
  covers the "stack comes back up" half. With no restart left in the suite, its
  `parallelism: false` pin (project.json) is deleted — store-es e2e now runs
  beside every other task.
- The rationalisation sweep that rides along: the ESD-03 credential-hygiene test
  moves from store-es e2e to a unit test (`tests/test__dev_elasticsearch_config.py`
  — it inspects committed files, never a running store; the `test` target decrypts
  the dev project's `.env` first), and the two FastAPI-framework probes in
  fastapi-example e2e (`/docs`, `/openapi.json` — they assert FastAPI defaults, not
  Aurelius behaviour, and carried no `covers` rule) are deleted.
- Layout-parity pins leave the webapp e2e suite (with the user's directive:
  interactions are what e2e guards, layout is what unit/visual tests guard). Eight
  tests go: the navbar logo box, the body type/ink, the type ramp, the chrome-band
  palette, the accent ramp, footer-below-the-fold, the landing container inset, and
  the dark-OS light pin. Their checks land in the webapp's Vitest component specs
  (`header.component.spec.ts`, `footer.component.spec.ts`, app/shell template
  structure) as class/token/attribute assertions — the parts a jsdom browser can
  verify — while the computed-pixel measurements (Bulma ramp values, band heights,
  bounding boxes) are dropped: they pinned the demo at parity-establishing time and
  can only fail on CSS refactorings, not on behaviour. The interaction half of the
  burger-menu test (click, dropdown, logout entry) stays in e2e; only its CSS pins
  go. A Storybook visual-test setup for the webapp (it has no `storybook` target
  today) is a follow-up increment, not part of this change.

**Reason.** CI runs `nx affected -t test e2e` in parallel, and the fleet rides the
shared `dev/*` services. ESD-04's dev-ES down/up races every suite mid-flight —
lost-connection failures are on record (the `parallelism: false` pin was that
outage's scar tissue, and it serialised the suite forever after). The fix is to
remove the restart, not to isolate every writer: a per-suite store stack was built
and verified in this cycle (ES ×3, Postgres ×1) and rejected as over-correction —
the dev stores' standing data is a debug aid, namespaced writes are already the
convention, and one restart-test does not justify four extra cold boots per CI run.
The proof half is the same story: tests that assert framework defaults (`/docs`
returns 200) or demo-measured pixels (navbar height 68px, ink `#4a4a4a`) can only
fail for non-Aurelius reasons, and they are the slowest to debug when they do.

**Alternatives.** (a) Suite-owned stores for every writer (the shape this session
built and verified: store-es/webapp/server on their own ES, fastapi-example on its
own Postgres) — refused on the user's direction: the ban is on restarts, writes are
fine, and four cold store boots per CI run is a lot of boot to buy what namespaced
writes already provide. The work is preserved in this branch's history if a suite
ever needs isolation (the suite-stack compose recipe — dev image, node config
mounted read-only, DD-216 certs, openssl healthcheck — is on record).
(b) Keep ESD-04 with a global serialisation — refused: `parallelism: false` taxes
the whole fleet forever to run one test, and the dev-ES restart is the exact race
the pin documents. (c) Move the layout pins to Storybook visual tests now —
refused as scope: the webapp has no storybook target, and porting eight computed-
style pins to a visual harness is its own increment; the Vitest component specs
cover the structure that jsdom can see, the pixels return with the storybook slice.

**Consequences.** store-es e2e runs in parallel (one serialised suite gone); the
dev Elasticsearch is never cycled mid-suite, so co-scheduled suites stop losing
connections. ESD-04 is the fleet's first explicitly untested rule, with the note in
the increment spec carrying why. The webapp e2e suite drops eight tests (~135 →
127 collected, all browsers) and the shell's computed-style coverage moves to unit
specs as structural assertions; a true visual-parity harness waits on a webapp
Storybook slice. The dev stores' data survives e2e runs (writes are namespaced and
self-cleaned, and the webapp glossary purge rides its own uuid-prefixed types).
`AGENTS.md` gains all three rules: no restarts, prove Aurelius behaviour not
framework defaults, guard interactions not layout.

### DD-224. The webapp e2e signs in once per browser and replays the session

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure; follows DD-223's time audit)
- **Date:** 2026-10-27

**Decision.** The webapp suite's `authenticated` fixture no longer runs the
Keycloak form login per test. A session fixture signs in **once per browser**,
saves the context as a Playwright `storage_state` (the realm's SSO cookie,
`KEYCLOAK_IDENTITY`), and every test now gets its **own context seeded from that
state**: the SPA boots with `check-sso` and the silent-iframe redirect (APC-05),
so a pre-authed context mints its own 60s access tokens from the stored SSO
session — the login form never opens. The fixture watches the boot: navbar →
signed in; login form (session died — e.g. the resilience logout test ends the
realm session, RSL-02) → run the form login and refresh the shared state, so
the next test replays from a live session again. The per-test context keeps
cookies/storage/cache isolated exactly as the per-test login left them.

**Reason.** The slow-e2e diagnosis: the suite's ~37 authenticated tests per
browser each paid a full Keycloak sign-in (~1.5s of form fill, redirect and
token exchange) — ~60% of the suite's wall time and the fleet's biggest single
cost. The realm's SSO session (30-minute idle window, refreshed by every test's
visit) plus the SPA's silent check-sso is exactly the mechanism the reuse rides:
it is the flow a real returning user takes, so the fixture now proves the SSO
path end to end as part of every test.

**Alternatives.** (a) Keep the per-test login — refused: it is the cost this
decision exists to remove. (b) One shared context for the whole session —
refused: tests mutate storage/cookies (locale, settings panel, theme); isolation
stays, only the session is shared. (c) Mint tokens by REST and inject them —
refused: keycloak-js keeps its tokens in JS memory, not storage; the
storage_state path is the browser's own session story and needs no injection
hack. (d) Test-only Keycloak config with longer token lifetimes — refused: it
drifts from the dev realm every suite rides.

**Consequences.** The suite measured 1.28s/test after the change vs 2.24s before
(full matrix, all browsers): the webapp e2e drops from ~4m to ~2m20. The realm's
60s access token and 30-minute SSO window bound the suite: ~4 minutes of
sessions fit with room, and the self-heal covers the tail. The state file lives
under pytest's tmp path — cookies only, never the user's password. The
resilience suite's logout test (which ends the realm session and re-signs-in by
form) runs on the shared state and proves the recovery path in-suite.

### DD-225. E2E containers export spans every second so Tempo probes land sooner

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure; follows DD-224's time audit)
- **Date:** 2026-10-27

**Decision.** The OTLP-emitting app services in the e2e compose stacks (the
server stack's `aurelius-atlas-server`, the webapp stack's `atlas-server`, the
lineage chain's `data2model` and `lineage-model`) set
`OTEL_BSP_SCHEDULE_DELAY: "1000"`, and the Tempo read-back probe loops (server
store-ride, lineage chain, webapp stamping/ingest) poll every 1s instead of
every 3s. Deadlines stay as they were (60–120s).

**Reason.** The probes ride `BatchSpanProcessor`, which the apps construct with
no arguments — its 5000ms schedule delay is the floor under every read-back:
the first poll that can succeed lands ≥5s after the request, Tempo's block
ingest adds 1–3s, and the 3s sleeps then quantise arrival to ~6–9s. The floor
is the exporter, not the polling, and the SDK reads
`OTEL_BSP_SCHEDULE_DELAY` from the environment when the processor is built, so
the compose env reaches it with no code change. The key stays bare (`OTEL_*` is
a third-party consumer, per the env-prefix rule) and rides the e2e compose
only: prod images keep the SDK default.

**Alternatives.** (a) Keep the 3s sleeps — refused: they were tuned to a 5s
floor the fleet no longer has, and each quantises 1–3s of latency per probe per
browser. (b) Force an export per request (a `SimpleSpanProcessor` under test)
— refused: it changes the pipeline the suite exercises. (c) Shorten the
deadlines — refused: the deadlines are the failure budget, not the expected
path.

**Consequences.** Measured solo: the server store-ride probe 12.2s → 6.2s
(suite 31.9s → 28.8s), the lineage chain probe 6.1s → 1.0s, the webapp suite
2m36s → 2m08s (its probes ride three browsers). The 84.6s server-dashboard
number from the same audit needed no fix: it is contention, not the test —
measured clean, the dashboard pair is 7.2s + 0.8s. Export cadence rises (dev
containers only, negligible collector load); probes fail only on real
ingest loss.

### DD-226. The dev stacks' restart windows are unbounded

- **Status:** Accepted
- **Increment:** cross-cutting (dev-stack wiring; rides the CI pipeline, no roadmap row)
- **Date:** 2026-10-26

**Context.** DD-195 chose `restart: on-failure:15` for the collector and DD-202 extended
the pattern to the slice metrics-pullers, reasoning that 15 attempts ≈ 6 minutes spans any
Keycloak boot and the bound keeps a permanently broken stack loud. Both halves proved
wrong under the CI e2e fan-out (run 40292544843). The attempt count burns out in ~6
minutes — Docker's backoff doubles per _attempt_ (100 ms → 60 s ceiling), so six minutes
of failing is 15 attempts, not 6 minutes of wall clock — and Keycloak's TLS listener is
not reliably up that fast when the fan-out shares one 4-vCPU node and the Elasticsearch
stack boots last. When the budget expires Docker stops restarting the container
_permanently_, and the failure is silent: ESD-06 polled Prometheus for 420 s against a
puller that had given up for good, reviving one second after the test gave up (the
green/red history of that rule — green 40279621021/40282797027/40289090955, red
40286077875/40292544843 — was this race, not the poll budget). The loud-exit property
also proved illusory: `compose up --wait` gates on the healthcheck, and a
restarting-then-dead container never reports healthy, so the bound exits on the final
crash exactly when the unbounded form keeps trying through it.

**Decision.** All four dev composes (`dev/elasticsearch`, `dev/keycloak`,
`dev/postgres`, `dev/observability`) carry unbounded `restart: on-failure` on
every container whose readiness depends on Keycloak — the collector and the
metrics-pullers. This supersedes the bounded-restart half of DD-195 (the awaited
readiness — `up --wait` + healthchecks — stands) and the `restart: on-failure:15`
detail of DD-202. Loudness moves from the restart count to the state Docker
reports: a permanently bad config sits in a visible `restarting` loop, in
`docker compose ps` and in the compose `up --wait` that never returns healthy.

**Consequences.** Keycloak readiness is no longer raced: the 60 s backoff ceiling
lands a puller within a minute of the issuer coming up, at any cold-start delay, so
ESD-06's budget measures ES metrics latency (its stated subject) instead of Docker's
restart arithmetic. The cost of the unbounded form is that a permanently broken puller
retries forever — visible, not loud; acceptable for dev stacks, where the same loop is
the normal boot shape during Keycloak's startup.

### DD-227. The store-es e2e suite is removed: it evaluated the dev environment, not production

- **Status:** Accepted
- **Increment:** cross-cutting (test strategy; follows DD-223, DD-225)
- **Date:** 2026-10-27

**Decision.** `libs/python/aurelius-atlas-store-es/e2e/` is deleted: ESD-01,
ESD-02, ESD-05 and ESD-06 lose their automated tests. The rules stay specified
in the 0-2 increment; the dev stack carries them — `up --wait` gates on the
compose healthchecks (ESD-01), every app's e2e suite reaches the store over
verified HTTPS with credentials (ESD-02 in the production path), heap and puller
wiring are config under review (ESD-05, ESD-06). ESD-03 (credential hygiene)
remains a unit test in `tests/`; ESD-04 was already untested by DD-223's choice.

**Reason.** The suite asserted the dev environment's state, not the library's
production behaviour — the same bar DD-223 set for the FastAPI `/docs` probes.
The shape-A runner made the cost concrete: the ESD-06 metrics test burned its
full 420s budget and failed the pipeline (run 40465196293) while the ES
metrics-puller sat in DD-226's unbounded restart backoff waiting on Keycloak —
a dev-stack readiness race, charged to the test suite, blocking production
work. A test whose green state is "the dev box is warm" is a flake generator;
what the store library must prove is in its unit/container tests (STO-01 to
STO-08) and in the apps' suites, which ride the real code path against this
store.

**Alternatives.** (a) Keep it with a larger budget — refused: the 420s fix was
already tuning a test that should not exist. (b) Keep ESD-02/ESD-05 as e2e
against the dev store — refused: the server e2e suite proves TLS + auth + store
round-trips from the Atlas side, on the production client path. (c) Move the
suite to CI infra validation — refused: dev-stack health is the compose
healthchecks' job, already wired to `up --wait`.

**Consequences.** CI's longest e2e suite disappears (7 min worst case, 0s
green — the ESD-06 poll dominated it); the 420s `METRICS_TIMEOUT_SECONDS`
leaves with the suite. The traceability report gains four explicitly-untested
rules beside ESD-04, with this entry as the note. The dev/elasticsearch puller
and its DD-226 restart posture stay — Grafana reads them; only the CI assertion
on their warm-up is gone.

### DD-228. Dev-posture tests leave the suites: the sweep of DD-223's rule, applied

- **Status:** Accepted
- **Increment:** cross-cutting (test strategy; follows DD-223, DD-225, DD-227)
- **Date:** 2026-10-27

**Decision.** Six e2e tests are removed: the webapp suite's
`test__browser_facing_tls_verifies_against_ca`,
`test__collector_accepts_the_dev_plaintext_issuer`,
`test__collector_accepts_the_shared_ingest_token`,
`test__collector_publishes_are_loopback_pinned` and
`test__producers_keep_flowing_with_the_token`, and the frontend-example suite's
`test__browser_facing_tls_verifies_against_ca`. Their conftest support leaves
with them (`plaintext_service_token`, `collector_container` and the dev issuer
constants). The rules they pinned — CIA-03, CIA-07, CIA-10, CIA-11 and
SHL-11's TLS half — keep their specs, with an "untested by choice" note where
each acceptance list named the test.

**Reason.** DD-223's rule — e2e proves Aurelius behaviour, not the dev box —
applied as a sweep. Each cut test asserted dev deployment posture: a
certificate chain signed by the workspace mkcert CA, the collector's
127.0.0.1 port publishes, the plaintext :8080 Keycloak listener only the dev
browser uses, the shared ingest token's dev-only legacy leg, and the dev
pullers' liveness read through the Docker API. None of it exists in production.
Two of them (the loopback-pin, the producers-flow) were also the suite's
flake-prone container-internals tests — the same family DD-227 deleted at the
store-es end. The proofs that ride shipped config stay: the CIA-01/06/08
credential rejects, the browser/service-leg accepts, the proxy paths, the CSP.

**Alternatives.** (a) Move them to a CI "infra validation" suite — refused:
the dev stack's readiness is the compose healthchecks' job (DD-226), and a
separate infra suite is where flakes go to be ignored. (b) Keep CIA-07's
producers-flow as the telemetry canary — refused: Grafana's stack dashboard
shows the pullers live, and every producer's own suite going green proves its
export; a 90 s log-poll on the dev box proves less. (c) Keep the TLS test,
verify against the container's own CA — refused: the CA is the workspace's, so
the chain proves dev wiring by construction.

**Consequences.** The webapp e2e drops from 36 to 31 tests per browser (the
two container-internals tests carried 120 s/90 s poll floors); the
frontend-example suite from 17 to 16. Four CIA rules and SHL-11's TLS half join
the fleet's explicitly-untested list, each with its note in the increment spec
that owns it — the ledger DD-223 started, and the shape-A runner's first
failure (DD-227's ESD-06) is exactly the flake class this sweep thins.

### DD-229. The shape-A tail overlaps, the test graph shares its daemon

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; follows the shape-A consolidation)
- **Date:** 2026-10-27

**Context.** Run 40471177041 — the first fully green shape-A pipeline — spent
38m 26s: tests 16m 59s (Nx: 9m 22s recoverable, default parallelism 3 against
the container's 6 CPUs), Sonar 13m 28s (Nx: 85 % recoverable — the 25 scanners
queue on the SonarQube Cloud server and idle the node), and fixed costs the
serialised graph left on the table: docker-build (60 s) waits behind every
test although images depend on source, the node_modules cache save re-uploads
~40 s after a hit, and Storybook+Chromatic (2 m) wait behind sonar's queue.

**Decision.** Three overlaps in the single job, no new jobs: docker-build
joins the test step's graph (`affected -t test e2e docker-build`) at
`--parallel=5` — one CPU stays headroom for the e2e stacks' containers, which
share this cgroup; the Storybook build launches in the background of the
sonar step (detached with `setsid` — the runner kills each step's process
tree at the step boundary, so a plain `&` dies there) and an "Await
Storybook build" step joins its exit code after sonar, keeping the verdict;
the cache save runs only on a restore miss. Sonar keeps its position —
coverage, lcov and sarif must exist — and the overlap exploits its waiting.

**Alternatives.** (a) A parallel `storybook` job — refused: the consolidation
to one job (shape A) is the point of the migration, and a second job pays pod
startup plus a second daemon to save what the background build saves for
free. (b) `--parallel=6` — the e2e composes' Keycloak/Elasticsearch/Tempo
containers compete in the same cgroup; 5 leaves them a core. (c) Scoping
Sonar engines per project (`sonar.javascript.file.suffixes=` etc.) —
deferred: real, but it changes what Sonar analyses; it deserves its own
measurement, not a ride-along.

**Consequences.** Expected 38m 26s → ~33m: ~1 min from the build overlap,
up to 5m 21s from parallelism (Nx's estimate; contention caps the real
recovery), ~2 min from storybook-under-sonar, ~40 s from the conditional
save. The Storybook log moves to `storybook.log`, echoed at the join —
failures appear at the await step, not live. If `--parallel=5` turns out to
inflate e2e contention past what it recovers, the knob is one flag.

### DD-230. Parallelism stays at the default, the scanner cache moves to the PVC

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; supersedes DD-229's parallelism clause)
- **Date:** 2026-10-27

**Context.** DD-229's `--parallel=5` run (40486044342) failed two unit
suites and got slower: the store-es suite's testcontainers Elasticsearch
missed its 180 s health window, a fastapi auth fixture read-timed out, and
the critical path grew 7m 37s → 10m 35s (run 17m 36s). Nx's "recoverable
time" assumes tasks idle on CPU; here the 6-CPU cgroup is already spent on
compose-stack JVMs (Elasticsearch, Keycloak, Tempo) and pytest workers, so
the fifth lane buys queueing, not throughput. The same week's sonar
measurement (store-es, local scanner): paired A/B runs of the as-is config
vs engine-scoped suffixes (JS/TS/CSS/YAML/JSON/XML emptied) averaged 39.2 s
vs 39.0 s — no effect. The 3.8 s → 0.2 s "plugin download" saving claimed
earlier was a cold-vs-warm cache artifact: the scanner's download cache
(~382 MB — the cloud engine jar, a JRE, 13 plugin jars, content-addressed
under `~/.sonar`) is identical for both configs; SonarCloud ships the full
bundle to the CLI regardless of project languages. What the cache does
explain is the CI sonar step's shape: the first task per pod pays the cold
bootstrap (run 40471177041: otel:sonar 109 s vs ~15 s steady-state) because
HOME is the container layer, wiped on every runner-pod boot, while uv/npm/
pre-commit caches live on PVC subPaths (arc-shapea-values.yaml).

**Decision.** (a) The test step keeps DD-229's docker-build graft at Nx's
default parallelism — one flag, DD-229's consequence named it. (b) The
scanner cache joins the PVC subPath set: `SONAR_USER_HOME=/var/cache/ci/sonar`
in the runner command, a `.ci-cache/sonar` mount, dir created by cache-init
— every pod's first sonar task stops paying ~94 s of jar downloads, and the
first pod boot pays them once. (c) Sonar engine scoping is measured away:
the suffix knobs are NOT added to any sonar-project.properties, retracting
the store-es trial before it shipped.

**Alternatives.** (a) Keep `--parallel=5` with longer testcontainers
timeouts — refused: DD-222..228 spent a week deleting exactly this flake
class, and tuning a timeout to feed a lane Nx cannot fill is backwards.
(b) actions/cache for `~/.sonar` — refused: the PVC subPaths are the
established shape-A pattern for toolchain caches (no cache-server
round-trip, warm across pods by construction). (c) Bake `~/.sonar` into the
runner image — refused for now: the image rebuild cadence is slower than
SonarCloud's plugin rotation, and stale cache entries are re-fetched by
content hash anyway; the PVC gets the same warmth with no skew.

**Consequences.** The parallelism clause of DD-229 is retired (the overlaps
survive — this run's own failures were unit tests, not the grafted builds).
The sonar step's per-pod floor drops ~94 s; the engine-scoping idea retires
with paired-run evidence, and DD-229's "85 % recoverable" sonar figure is
re-read as the server queue, which no scanner flag fixes — future sonar
tuning starts from the CI per-task times, not local guesses. The values
change lands on the next `infra/arc/install.sh` run (helm upgrade evicts
in-flight runner pods — run it between jobs).

### DD-231. Teardown downs the compose stacks: prune only sweeps corpses

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; repairs DD-229's teardown step)
- **Date:** 2026-10-27

**Context.** The shape-A teardown step names its purpose in its own
comment — Keycloak/Postgres/Elasticsearch/observability hold ~8 Gi of the
node's memory and the scan/sonar tail must not pay for it. It never
happened: `docker container prune -f` sweeps only STOPPED containers, and
the suites leave their stacks Up, so every run's teardown deleted exactly
one corpse — the 28.67 kB testcontainers ryuk (runs 40471177041,
40486044342 and 40489544189 each report the same single container) — while
the ~8 Gi rode through docker-build, the vuln scan, sonar and Chromatic on
a node capped at 11 Gi.

**Decision.** The teardown iterates `docker compose ls --all -q` and runs
`docker compose --project-name <p> down -v --remove-orphans` per project —
the same project-name pattern the diagnostics step uses — keeping the prune
pair behind it as the sweeper for non-compose strays (ryuk, anonymous
volumes). `down` deletes containers, named volumes and networks; images
stay, so the scan's daemon-read and the warm base-layer store are untouched
(unchanged from the prune semantics).

**Alternatives.** (a) `docker stop $(docker ps -q)` — kills the stacks
bluntly, with no per-project attribution in the log; refused for the
readable footprint ("Tearing down compose project: …"). (b) Each suite
downs its own stack — refused: the suites share the `dev/*` stacks
(the E2E suite rule, DD-223), and a suite stopping one mid-graph evicts its
neighbours. (c) Leave it — refused: the tail's memory pressure is the
cgroup's, and sonar and Storybook pay it.

**Consequences.** The scan/sonar/Chromatic tail runs with the stacks' ~8 Gi
free; the teardown step grows from 1 s to the seconds a four-stack `down`
takes, naming each project as it goes. The stopped-container foreclosure
the old comment guarded (run 40231127680) carries over unchanged. The
step's log is the verification: it names each project it downs, and the
prune tail stops reporting one 28.67 kB corpse as the step's whole output.

### DD-232. The CI pipeline is a fan-out DAG; the pool is per-pod emptyDir

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; supersedes DD-229's single-job clause)
- **Date:** 2026-10-27

**Context.** The single shape-A job (38m 04s green, run 40501485238) is
two workloads stitched serially: the test phase (~17 min of CPU/RAM
saturation — e2e suites plus compose-stack JVMs) and the sonar step
(13m 28s wall, ~85% of it SonarCloud _server_ queue — 2m 4s of scanner,
DD-230's re-read). One job on one 6-CPU cgroup can overlap them only by
the DD-229 setsid dance, which hides Storybook, not sonar. The pool
forbade splitting: the 50 Gi cache PD is ReadWriteOnce, so
`arc-shapea-values.yaml` pins `maxRunners: 1` — a second runner pod
cannot mount the work volume, and the docs recorded "a job on a second
node starts cold". A spike scale set (own helm release, prod untouched)
with an emptyDir work volume and `maxRunners: 2` measured the two open
questions (run 40520070483, probes 14:20:02Z→14:23:09Z and
14:20:03Z→14:23:59Z): two jobs on the pool label run CONCURRENTLY on
separate pods; per-pod markers on the work volume stay per-pod (no
shared state); JIT pod boot is 15–17 s on a warm node (a cold node pays
~3 min pulling the 546 MB runner image); and a cold daemon pulls the two
heaviest dev-stack images in 48 s, the second in 0.0 s once the node has
the layers (GKE image-cache sharing). Node facts measured at the same
time: 3 × (4 CPU / 13.6 Gi allocatable), so pod _requests_ of 1 CPU/4 Gi
let three runner pods pack on ONE node — anti-affinity, not requests, is
what spreads them.

**Decision.** (a) `ci.yaml` becomes a fan-out DAG: `validate` (checkout,
install, pre-commit --all-files, decrypt, unit `test`, coverage upload)
gates three concurrent jobs — `e2e` (the `e2e` + `docker-build` graph,
diagnostics, DD-231 teardown), `scan-sonar` (image rebuild from the
buildcache, trivy, sarif, `sonar`), and `chromatic` (Storybook build +
publish). Scan and sonar co-locate in one job: the sarif handoff stays
on the work volume. (b) Cross-job state rides artifacts (coverage
upload/download) or rebuilds (GHCR buildcache images) — jobs never share
files through the volume. (c) The pool: the RWO PD retires; the work
volume becomes a per-pod 20 Gi `emptyDir` (warm within a pod — caches,
image stores, registry auth survive between jobs; cold across pods —
48 s worst measured). `minRunners: 2` (warm pair: fan-out jobs start in
~15 s; a cold-node start pays the image pull), `maxRunners: 3` (the
three fan-out jobs), a PREFERRED pod anti-affinity on
`kubernetes.io/hostname` (spreads across nodes; packing degrades
gracefully where `required` would deadlock a queue), requests stay
1 CPU/4 Gi (limits 6 CPU/11 Gi), and the cluster autoscaler ceiling goes
2 → 3 nodes.

**Alternatives.** (a) Per-pod PDs via a StorageClass — dead before the
spike: ARC builds job pods from `template.spec`, with no StatefulSet and
no `volumeClaimTemplates` (chart 0.15.1), so per-runner PVCs need an
external provisioner webhook. (b) Filestore (RWX) shared cache — blocked
by billing-account policy (on record). (c) Keep the single job and
parallelise inside it — exhausted: DD-229/230 measured the in-job
overlaps and the parallelism knob; the serial test→sonar wall is the
server queue, which only a second job (running _while_ the first waits)
dissolves. (d) `requiredDuringScheduling` anti-affinity — refused: three
nodes is the steady state, not a guarantee; a job queued forever while
the autoscaler provisions is worse than a packed pod.

**Consequences.** Wall-time target: 38 min → ~26–28 min: validate ~7 min,
then the longest fan-out branch (e2e ~17 min with its own stacks,
scan-sonar ~15 min mostly server-queue). Measured on the first run
(40531441140, green): **27m 48s** — validate 8m 55s gates chromatic
3m 46s, scan-sonar 16m 20s (sonar 11m 12s of server queue, 2m 49s the
buildcache rebuild) and e2e 17m 42s (15m 32s of suites) on three pods;
the e2e job is the critical path, 2m 19s off the sonar branch. The
DD-229 setsid/await dance retires with the single job. Each job pays
checkout+install (~2 min, node_modules from the cache server) — the
fork's price, ~3×. The `e2e` job is now the pipeline's only stack owner,
so DD-231's teardown is a single named step, not a tail. Caches are
per-pod: a pod respawn cold-starts uv/npm/sonar/docker once (48 s–2 min),
the warm pair absorbs it. Next free DD: 233.

### DD-233. The toolchain caches bridge pod churn through the cache server

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; repairs DD-232's cache-warmth assumption)
- **Date:** 2026-10-27

**Context.** DD-232 recorded that per-pod emptyDir caches make a pod
respawn cold "once (48 s–2 min), the warm pair absorbs it". The fan-out
pool churns pods constantly — scale-in after every run, helm deploys,
preemptions — so a `validate` landing on a never-seen pod is the norm.
Measured on run 40538065508 (warm run, fresh pod): the pre-commit step
spent 66 s re-`Installing environment` for its seven hook repos
(talisman's Go build alone ~40 s) before the first hook ran — step time
181 s where the RWO-PD single job (a pod alive for weeks, caches hot)
spent 83 s; hook _execution_ is identical in both (96 s). The install
step pays the same tax on uv's side (~25 s of wheel re-downloads;
npm does not — node_modules rides the cache server and restores in
~10 s). The old pipeline's "4 s python / 20s node" warmth was the PD's
weeks-long pod life, not a better mechanism.

**Decision.** Bridge the cold-pod gap through the existing in-cluster
`actions/cache` server (the same backend node_modules uses, LAN speed,
OIDC-scoped): `validate` restores uv (keyed `uv.lock`) and pre-commit
(keyed `.pre-commit-config.yaml`) and saves both on miss — single
writer, the node_modules shape; the three fan-out jobs restore uv;
`scan-sonar` restores/saves the SonarScanner jar cache (DD-230's ~94 s
per-pod bootstrap, save after the analysis since the jars land during
it). The emptyDir stays the warm tier _within_ a pod; the cache server
is the cross-pod tier. Keying on the config files makes every cache
rebuild exactly-once per version bump.

**Alternatives.** (a) Pin runner pods warm (higher `minRunners`) —
refused: absorbs some churn, pays idle pods for all of it, and helm
deploys evict anyway. (b) Return to a shared RWX volume — Filestore is
blocked by billing-account policy (on record). (c) Bake the caches
into the runner image — refused for the same reasons as DD-230's
`~/.sonar` bake (rotation cadence), and the config-keyed caches
self-invalidate where image layers go stale.

**Consequences.** Cold-pod validate drops ~66 s (pre-commit envs) and
~25 s (uv wheels); scan-sonar's first-run sonar bootstrap drops ~94 s
on a fresh pod. First run per key version pays the build (the
save-on-miss upload, ~1 min for the uv cache at LAN speed) and every
pod everywhere rides the artifact after. The cache server PD (20 Gi,
LRU at 90 %) grows by uv (~2–3 Gi) + pre-commit (~0.5 Gi) + sonar
(~0.4 Gi) — headroom verified against the 18 Gi eviction line. The
"4 s/20 s" memory is restored where it applies (warm installs on any
pod); the ephemeral-tree rule is untouched. Next free DD: 234.

Measured (run 40549779734, fixed fleet, all caches warm on the server):
all restores hit and extract clean (zero `Cannot utime`), validate's
pre-commit step 181s -> **82s** (the old always-warm PD pod was 83s -
parity), uv install 26s, scan-sonar 16m 20s -> **12m 2s** (the sonar
jar cache rides the bridge too), validate 8m 55s -> **7m 0s**, full
pipeline 27m 48s -> **25m 48s** with the e2e suites now the critical
path. The restore step's metadata bug (subPath mount roots stay
root-owned under fsGroup - k8s applies it to volume roots only;
cache-init chowns them now) shipped in the same change.

### DD-247. Journal writes do not wait for a refresh

- **Status:** Proposed
- **Increment:** cross-cutting (no roadmap row; found by 5.2a's e2e)
- **Date:** 2026-10-30

**Decision.** The journal entry's write, its commit and its delete (DD-046) no longer carry
`refresh="wait_for"`; the entity bulk, the restores and the audit append keep it (DD-237, ENS-11). Recovery
lists the journal's entries by a search, as before, and acts on each as a real-time `get` by its write id
reads it now: an entry already deleted, or still within its lease, is left alone. This supersedes DD-237's
choice for the journal only; the rest of DD-237 stands.

**Reason.** On the dev store every entity write cost about 2.8 s: four writes each waiting for a refresh
(about 1 s each with the default refresh interval), three of them the journal's. A glossary write is several
entity and relationship writes, so creating a child category took 9 s and deleting a glossary 18 s, past the
e2e client's timeout. DD-237 kept the journal's refresh for recovery, which "reads entries written moments
before"; but recovery acts only on entries whose 60-second lease has passed, long after the index's own
refresh has made them searchable, and the real-time `get` closes the remaining gap: a listing that lags an
entry's commit or delete cannot make recovery undo a write that finished. With the change a write costs about
0.9 s on the dev store.

**Alternatives.** A shorter refresh interval: every write still pays for refreshes no reader needs. Trimming
the glossary's writes: helps one feature, and departs from Atlas's sequence of writes.

**Consequences.** A journal entry may be missing from a search for up to the refresh interval after it is
written; nothing but recovery searches it. ENS-11's text names the journal as unrefreshed.

### DD-253. The chart-contract suite lives at the workspace root and renders with the helm CLI

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** The chart-contract pytest suite lives at the workspace root
(`tests/`, owned by the root `aurelius-atlas` project through an explicit
`test` target in the root `project.json`). It renders each chart with the
`helm template` CLI in a subprocess and asserts the rendered manifests —
settings keys, Secret references and shapes, certificate SANs, probe shapes,
pg_hba lines, the realm byte-equality — instead of unit-testing template
helpers. The suite skips when `helm` is absent (it ships in the devcontainer
and the CI runner, so in CI it never skips).

**Reason.** A chart is a YAML generator and its contract is the rendered
manifest; testing the manifests is testing the contract (CHT-06's gate only
proves the render _succeeds_ — 10.2 makes the first time real containers
appear in the output, so the output's _content_ needs guarding). No `dev/*`
chart owner is a Python package and none may become one (their `project.json`
files are chart-owner stubs), and the contract spans the umbrella plus the
component charts at once — the root is the only project above that seam. The
`helm` CLI is the only faithful renderer; a Python re-implementation of
Helm's template engine does not exist and a `helm`-library shim would drift.
Rendering in a session-scoped fixture keeps the suite at ~2 s.

**Alternatives.** (a) Colocate under each chart's `tests/` as pytest files —
rejected: the chart owners have no `test` target (they are not Python
projects) and the umbrella↔component joins (Secret names a component consumes,
the issuer reference) have no single chart to live in. (b) Rely on the
`helm-template` render gate plus review — rejected: DD-294's trial showed
renders that pass lint while producing crash-looping pods; the invariants need
assertions. (c) Make the root project a uv member — rejected: `.` already is
the workspace itself; adding the tests as a package would churn
`uv sync`/release for a suite with no import surface. The root `project.json`
is what enables a target here, and with it the python plugin also infers a
root `typecheck` (`uv run pyright .`) — harmless (nothing in CI targets it;
every package is type-checked at home) and left in place.

**Consequences.** Chart edits key the target's cache through
`inputs: helm/**, dev/*/helm/**`, so any chart change re-runs the suite in CI
(the root project is affected via the umbrella's implicitDependencies anyway).
The suite is the pattern 10.3 extends when the app charts land; the
`covers`-marker rule ids (CHT-10..19) give `aurelius-atlas-trace check` the
spec-to-test map. Next free DD: 254.

### DD-254. Deploy-time credential generation lands in 10.2 with publish and rotation in 10.4

- **Status:** Accepted
- **Increment:** 10.2 (re-sliced from 10.4's share of DD-287)
- **Date:** 2026-10-28

**Decision.** The umbrella's deploy-time credential generation (DD-287's
mechanism: `randAlphaNum 32` for every empty value, `lookup`-preserve across
upgrades, values-supplied wins, one Secret per consumer, none committed)
ships in 10.2 — but only the five Secrets its workloads consume:
`<release>-elasticsearch` (elastic-password), `-keycloak-admin` (user/password),
`-keycloak-database` (user/password, shared by Keycloak and the bundled
Postgres), `-keycloak-users` (writer-password/reader-password), and
`-otel-clients` (OTEL_INGEST_CLIENT_SECRET). Each renders only while its
consumer chart is enabled. 10.4 keeps the rest of DD-287's promise: the
remaining secrets (the collector legacy token and the observability slice's
credentials, the webapp's edge token), the chart OCI-publish polish, and the
operator runbook around retrieval and rotation.

**Reason.** 10.2's acceptance is "the stateful pods reach Ready on a cluster"
— every one of them reads a generated Secret at boot (CHT-13/16), so the
generation is not separable from the workloads that consume it: without it,
the increment's own hand check would need out-of-band Secrets, exactly the
trial-fixup shape DD-294 called out as the thing acceptance must not need.
The five are also the complete set no other increment needs earlier. The
10.4-only parts stay in 10.4 because their consumers (collector, webapp edge)
land there.

**Alternatives.** (a) Ship all of DD-287's secrets now — rejected: a Secret
with no consumer is dead config that 10.3/10.4 would re-shape anyway; (b)
keep generation in 10.4 and hand-generate for the hand check — rejected: the
`lookup`-preserve pattern is subtle and untested-by-CI until real upgrades
run (10.5); deferring it also defers its first real exercise past its own
increment.

**Consequences.** The umbrella's `secrets.*` values block is the operator's
supply surface; the component charts consume strictly by `<release>-<purpose>`
names (their `*SecretName` values bring your own, which skips generation —
the chart renders the consumer regardless, pointing wherever told). The
collector legacy Secret gains a composed `otel-header` key (the
`"Authorization=Bearer <token>"` pair) when 10.3/10.4 wires its consumers —
env values cannot concat from a `secretKeyRef`, so the composition belongs in
the Secret, not the chart. Next free DD: 255.

### DD-255. The coredump agent ships as its own image project

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** The Elasticsearch coredump-agent jar (the no-op javaagent that
absorbs the fatal `java_lang` dump attempt on GKE, dev/elasticsearch's
workaround) ships as a real image — `aurelius-atlas-elasticsearch-agent`
(`tools/es-coredump-agent/`, a `dhi.io/busybox` base plus the committed jar) —
and the store's StatefulSet mounts it as an init container copying the jar to
an emptyDir the JVM's `-javaagent` flag reads. The jar itself stays committed
(`coredump-noop.jar`, 1.9 KB, byte-stable; `build.sh` regenerates it) and a
chart-contract test pins the image reference and the flag.

**Reason.** The alternative shape — embedding the jar's bytes in a chart
ConfigMap — hides a shipped binary artifact from every supply-chain control
this workspace already runs for images: the SBOM (CycloneDX), the vulnerability
scan (`docker-vuln-scan`), the cosign sign/attest/verify chain
(publish.yaml), and the registry ACL. An image flows all of them for free the
moment it exists as a project (the docker plugin infers the eight targets from
the `Dockerfile` alone; publish.yaml's `run-many -t docker-publish` picks it up
with no wiring). It also keeps the chart honest: a ConfigMap jar makes every
install carry the bytes; an image reference makes the store chart depend on a
versioned, signed artifact like every other workload.

**Alternatives.** (a) ConfigMap-embedded base64 jar — rejected above (supply
chain), plus a 1.9 KB binary blob in chart values-review. (b) Bake the jar
into a custom ES image — rejected: forks the hardened `dhi.io` store image and
re-creates the maintenance the hardened image exists to avoid. (c) Drop the
agent in-cluster (hope GKE's `vm.max_map_count` story differs) — rejected: the
procfs write is the same node behaviour DD-008's CI lessons recorded; the agent
is what makes ES 9.x boot there.

**Consequences.** The image builds in CI (`affected -t docker-build`), is
published and signed with every release like any other, and takes
`global.image`'s registry/namespace so a mirror deployment redirects it. The
busybox base pins `1.37` (no `latest` tag exists on the hardened image). The
chart's `agent.image.tag` defaults to the appVersion chain like the store's
own image. Next free DD: 256.

### DD-256. The realm is a byte-copy chart asset and its placeholders resolve in Keycloak

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** The Aurelius realm (`master.json`, the 2 580-line identity
configuration) is a chart _asset_: `dev/keycloak/helm/files/master.json`, a
byte-copy of the dev import `dev/keycloak/import/master.json`, rendered into
the realm ConfigMap verbatim (`.Files.Get`). Helm performs no substitution in
it. Its `${DEV_USER_WRITER_PASSWORD}` / `${DEV_USER_READER_PASSWORD}` /
`${OTEL_INGEST_CLIENT_SECRET}` placeholders resolve at import time inside
Keycloak itself — the JVM's own
`-Dkeycloak.migration.replace-placeholders=true` flag (already the dev
compose's mechanism, DD-196) fed from the container's environment, which the
chart fills from the generated Secrets. A chart-contract test byte-compares
the asset against the dev import every run (the drift guard).

**Reason.** The dev import file is the single authored source (every dev/e2e
realm edit lands there first); Helm-substituting the placeholders would fork
that source per environment. More than drift, the decisive fact is
reproducibility: a Helm-rendered `randAlphaNum` secret appears twice in one
render (the realm ConfigMap and the Secret), and `lookup` cannot protect the
ConfigMap side — a pod rescheduled later gets a realm baked with yesterday's
rendered value while the Secret holds today's, a boot-order-dependent
credential mismatch. Keeping the file byte-identical to what dev already
imports proves the chart path and the dev path carry the same realm, and
Keycloak's placeholder resolution — the mechanism the dev stack runs today —
is the same one that resolves from the Secret-fed env.

**Alternatives.** (a) `tpl`/substitution over the file in-chart — rejected:
the double-`randAlphaNum` race above, plus the file's 2.5 KB of `${env:...}`-
adjacent JSON full of braces Helm would have to be told to ignore. (b)
Generate the realm from chart values — rejected: forks the source and loses
every realm edit; the file is the API. (c) A CI check comparing the copy
instead of a test — rejected: the chart-contract suite is the established
place for render-time invariants (DD-253); a byte-compare there runs on the
same gate.

**Consequences.** Editing the dev import requires re-running the byte-copy
(`cp dev/keycloak/import/master.json dev/keycloak/helm/files/master.json`) and
the test fails until it is done — deliberate: the two files may only differ in
the same commit. The browser-facing redirect URIs in the realm stay
localhost-only for now; per-environment redirects are 10.3's webapp work and
will extend the asset (or a values-driven patch) then, not by Helm-substituting
secrets. Next free DD: 257.

### DD-257. Stateful workloads run as their image's declared uid, with fsGroup for volumes

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** Every stateful workload of the platform charts pins its
container to the uid the image itself declares — Elasticsearch 1000,
Keycloak 65532, Postgres 70 — with `runAsNonRoot: true`, matching
`runAsGroup`, and `fsGroup` set to the same uid for the mounted volumes.
The chart sets no `runAsUser: 0` anywhere and relies on no privilege drop
in the image. `fsGroup` is the in-cluster equivalent of the compose
stacks' one-shot `volume-init` chown: the kubelet group-owns the
provisioned volume at the fsGroup gid, so the dynamic-provisioner path
needs no init-container root.

**Reason.** Found in the 10.2 minikube hand check, not on the drawing
board. The first install crashlooped both stateful pods: Elasticsearch
exited with `can not run elasticsearch as root` (its JVM refuses uid 0 in
`initializeNatives`), and Keycloak's re-augmentation failed with
`AccessDeniedException` on `/opt/keycloak/lib/quarkus/transformed-bytecode.
jar` because the pod ran uid 1000 while the image owns that tree at 65532.
The charts had inherited a belief from the dev compose comments — that the
store image boots as root and drops privilege via `gosu` before exec'ing
the JVM, so the pod should run as root. That is upstream Elastic's image;
the hardened `dhi.io` images have no root stage at all: the ES entrypoint
is `umask 0002` then exec, its `Config.User` is `1000`, and Keycloak's is
`65532` (Postgres 70). The image's declared user is the only correct
`runAsUser`, and the hand check is the level (of the three in `AGENTS.md`)
that catches a wrong one.

**Alternatives.** (a) `runAsUser: 0` + hope for a gosu drop — rejected:
crashes the store outright, and giving root to pods that never need it
violates the hardening posture the images exist for. (b) Omit
`podSecurityContext` and inherit the image user — rejected:
`runAsNonRoot` must be explicit for the posture to be checkable, and
`fsGroup` must be set explicitly or dynamically-provisioned volumes mount
root-owned against the wrong gid. (c) An init container that chowns as uid
0 (the compose's `volume-init` shape, kept) — rejected in-cluster:
`fsGroup` does the same job without granting any container root.

**Consequences.** The chart-contract suite pins each workload's uid
against the image's declared user (`test__runs_as_image_uid_with_fs_group`
in both stateful suites), so a base-image uid change fails the gate with a
pointer to this entry. Compose comments claiming a root-entrypoint boot
describe upstream images, not `dhi.io` ones — they are corrected where
10.2 touched them, and any future chart copies the uid from
`docker inspect`, never from prose. Next free DD: 258.

### DD-258. A bundled database dates its consumer with a wait-init and its own probe SANs

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** Two facts the compose siblings state outright and the first
chart port lost, both caught by the 10.2 minikube hand check. (1) The
Keycloak pod waits for the bundled database: a `wait-for-postgres` init
container (bundled flavor only) retries a TCP dial of the database's
headless Service until it answers — the Kubernetes port of the compose's
`depends_on: postgres-keycloak: condition: service_healthy`, which has no
direct equivalent because Kubernetes never gates one pod's start on another
pod's readiness. (2) The database's Certificate carries `127.0.0.1` as an
IP SAN next to the service-name DNS SANs: the `verify-full` `pg_isready`
probes dial `127.0.0.1` (the compose healthcheck's own target, and the dev
`tls.json` lists the address for exactly this), and `verify-full` compares
the dialled host against the SANs — without the loopback entry the probes
can never pass, the pod never turns Ready, and the headless Service never
publishes an endpoint for Keycloak's JDBC URL to resolve.

**Reason.** The first install deadlocked the pair exactly along those two
missing facts: Keycloak logged `UnknownHostException: atlas-keycloak-postgres`
(it started before the database was reachable and prod mode exits on the
JDBC failure), while Postgres sat Ready-in-name-but-0/1 because its startup
probe failed hostname verification against a certificate that could not
amever validate the address it was probed at. The init's wait is
transitive on TLS correctness — the headless Service publishes the pod only
after the pod's own verify-full probe passes, so a successful dial already
proves the database serving verified TLS. bash's `/dev/tcp` is the shape
the compose's Keycloak healthcheck uses and needs no client tool added to
the hardened image.

**Alternatives.** (a) A `startupProbe` failure-threshold budget on Keycloak
instead of the init — rejected: prod-mode `kc.sh` exits on the first JDBC
failure, so probes cannot ride out the race; the restart loop only
re-rolls the dice, which is what made the deadlock look random. (b) Have
the probes dial the service name instead of loopback — rejected: during a
pod's own NotReady phase its endpoint is unpublished, so a readiness probe
addressed through the Service could fail on its own not-ready status —
loopback is the only address that answers the instant Postgres itself is
up, which is why the compose (and every Postgres guide) probes `127.0.0.1`.
(c) `publishNotReadyAddresses` on the database Service — rejected: that
would hand consumers a dial target before the database accepts connections,
replacing the deadlock with a worse silent race.

**Consequences.** The chart-contract suite pins both: the init container
present under bundled and absent under external, and the Certificate's
`ipAddresses: [127.0.0.1]`. A future cluster-ca path that issues per-SAN
certificates must keep the loopback entry as long as the probes dial
loopback. Next free DD: 259.

### DD-259. The chart-managed trust root is a namespaced self-signed issuer chain

- **Status:** Accepted
- **Supersedes:** the issuer shape in DD-286
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** `global.trust.createIssuer=true` (the default posture) builds
the cluster trust root as a three-resource chain in the app namespace: a
self-signed bootstrap `Issuer` signs exactly one `isCA: true` `Certificate`
whose Secret is the trust root (its name is `global.trust.caSecretName`,
defaulting to `<issuerRef.name>-ca`); a `ca`-type `Issuer` of that Secret —
the object every `Certificate` names in `issuerRef` — then signs every leaf.
Because every leaf descends from the one CA, the `ca.crt` cert-manager
places in each leaf Secret is the same root everywhere, and the file each
consumer pins verifies every peer's certificate. The chain is namespaced
(`Issuer`), so the umbrella's default `issuerRef.kind` becomes `Issuer`
(the component charts' standalone defaults follow); a `ClusterIssuer` stays
valid only for bring-your-own issuers (`createIssuer=false`, gke.yaml),
whose CA is off-cluster and installed via `caBundle` as before. DD-286's
decision stands in full except this issuer-shape clause.

**Reason.** The 10.2 hand check: a fresh minikube install reached Ready for
the store and the database but Keycloak refused its JDBC TLS with `PKIX
path validation failed`. The leaf Secrets told the story — the Keycloak
and database certificates were signed by two different CAs, which is what
a bare `selfSigned` issuer means: cert-manager generates a fresh private
key for every Certificate it self-signs, so "the issuer's CA" is a
per-certificate secret that cannot exist. DD-286's prose always assumed a
shared root ("a private root is the default, so the cluster's trust set is
closed and enumerable") — the implementation shipped in 10.1 contradicted
its own consequence. The namespacing is cert-manager's own constraint,
verified on the cluster before the charts changed: a `ClusterIssuer` reads
its CA Secret from cert-manager's namespace (`ErrGetKeyPair` otherwise),
while a `Certificate` can only write its Secret to its own namespace — the
chart can therefore never hand a `ClusterIssuer` a CA it created.

**Alternatives.** (a) Keep the self-signed `ClusterIssuer` and have each
consumer trust the issuer per leaf (mount every peer's `ca.crt`) —
rejected: N² trust material, renewed on every certificate rotation, and
it still cannot express "verify the name I dial" across independently
minted roots. (b) Make the chain a `ClusterIssuer` pair and copy the CA
Secret into cert-manager's namespace — rejected: the chart would write
into another system's namespace and race its garbage collection. (c)
Generate the CA key in the chart (a Helm-rendered private key in a
Secret) — rejected: the key lands in the release history and every
`helm get`, the exact posture DD-287 exists to avoid; cert-manager's
bootstrap chain keeps the key in its own secret with rotation built in.

**Consequences.** Three objects instead of one for the default posture;
the chart-contract suite renders and pins the whole chain (bootstrap spec,
root `isCA` + bootstrap issuerRef, CA Issuer spec, leaf refs `kind:
Issuer`), and the leaf certificates in the minikube hand check now share
one CA fingerprint. A CA rotation is cert-manager-renewal-driven and hits
the boot-time CA readers (store, Keycloak) — DD-286's restart-hook
consequence, still owed by 10.3. GKE overlays with `createIssuer=false`
are unaffected. Next free DD: 260.

### DD-260. Keycloak's management interface is TLS in prod mode, probes included

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** Keycloak's three probes address the management port over
**HTTPS** (`httpGet.scheme: HTTPS`), and the startup budget is 30×10s
(300s). Prod mode puts TLS on the management interface as well as the
browser one — the same keypair serves both — so there is no plaintext
listener anywhere in the chart's posture (`KC_HTTP_ENABLED=false` is a
chart-contract assertion), and a plaintext probe can only ever fail. The
budget covers what the cluster measures: `kc.sh start` re-augments the
Quarkus runtime into the container's image filesystem on every new
container (the PVC holds the realm and cache, not the augmented
runtime-layer), which on minikube's CPU took ~165s end to end.

**Reason.** The last hand-check failure, and the subtlest: the trust fixes
worked (realm import ran over JDBC TLS, bootstrap completed in ~2.5s after
a 165s boot) yet the pod restarted eleven times. kubelet logged
`Get "http://…:9000/health/ready": EOF` — the dev healthcheck's plaintext
`/dev/tcp/localhost/9000` probe shape was copied from the compose, where it
works only because dev runs the plaintext listener as ADR 039's named
relaxation. The chart renders prod posture, and an HTTP probe against a TLS
port gets an EOF — the pod's container then died on a
startup-probe-threshold kill seconds after finishing its work. The widened
budget is the same measurement: the earlier 180s (the compose's
`start_period`) left 15 seconds of margin against a cold start, and a
kill-then-reaugment loop (each restart pays the augmentation again) looked
exactly like a broken chart.

**Alternatives.** (a) `KC_HTTP_ENABLED=true` and a plaintext management
listener in-cluster — rejected: the compose's relaxation is named and
scoped to dev (ADR 039); a chart posture that exists to be the hardened
shape does not open a second plaintext port. (b) TCP probes instead of
HTTP — rejected: they'd pass on a listening socket whose health checks are
failing (the compose's HTTP-shape probe exists for the checks); TLS HTTP
probes cost kubelet nothing extra. (c) Pinning the probes' certificate
verification to the cluster CA — not an option kubelet offers (HTTPS
probes ignore certificate validation), and the right one: a liveness
channel is an escape hatch, not a trust surface.

**Consequences.** The probe scheme is a values knob
(`probes.scheme`, default HTTPS) rather than a template literal. The
augmentation cost is per-container, so a rollout or reschedule always
pays it: the readiness gate plus the 300s budget absorb it; a future
image that ships the augmented runtime (a custom build) can shrink the
budget. The chart-contract test pins the HTTPS scheme and a startup
budget of at least 300s. Next free DD: 261.

### DD-261. The two-hop edge names both client-IP trust hops

- **Status:** Accepted
- **Increment:** 10.3a
- **Date:** 2026-10-28

**Decision.** In-cluster the browser path is Gateway → webapp nginx →
server, and both proxy hops are named in values: the webapp's nginx gains a
`realip` block (`set_real_ip_from` from `nginx.trustedProxyCIDRs`, the
Gateway's network, an environment value) resolving `X-Forwarded-For` to the
browser before the `limit_req` geo bucket and the access log key on it; the
server's `FORWARDED_ALLOW_IPS` takes the webapp's network. Both default to
no-trust (loopback / empty) in a stock render; the environment overlays name
their clusters' pod CIDRs (`10.244.0.0/16` on minikube). The nginx change
lands in the app's own `nginx.conf.template` (with a placeholder the chart
resolves), keeping the chart's byte-copy and the e2e mirror one contract —
the e2e stack is one hop and sets no trusted proxies, so its behaviour is
unchanged.

**Reason.** DD-238's rate-limiter design rests on one fact: "the browser
cannot spoof the TCP address nginx sees" — true when nginx is the front
door. The Gateway API edge (DD-285) makes the browser's TCP address, as
nginx sees it, the Gateway's. Left unnamed, every browser behind the gateway
shares one `limit_req` bucket (the Gateway's address, inside the RFC1918
geo allowlist → the limiter disables entirely: requests with an empty key
are not accounted), and the server's access log/peer attributes key on the
wrong pod. That is not a hypothetical deployment shape; it is the product's
default edge. DD-238's consequence line ("deployments that front the server
with something other than the webapp nginx get no limiter") anticipated a
foreign front end, not this one in front of the nginx itself.

**Alternatives.** (a) Keep nginx's TCP-trust and let the geo allowlist
swallow the gateway — rejected: it silently disables the only browser rate
limiter in the product (DV-87's alert-drawer UX would fire against one
shared bucket, or never fire). (b) Trust `X-Forwarded-For` unconditionally —
rejected: DD-238 rejected the same for the one-hop case (spoofable when the
hop is not pinned); pinning it to the gateway network is exactly the
correction that makes the header trustworthy. (c) Have Envoy do the
limiting (local rate-limit policy at the edge) — rejected for now:
it forks the limiter from the tested contract (`e2e/config/nginx.conf`,
DD-142/238's pair), and the webapp's allowlist semantics (internal callers
exempt) are geo-based, which the edge would have to re-implement. Recorded
as a 10.5+ candidate if per-edge limiting earns its keep.

**Consequences.** The `realip` placeholder joins the template contract
(the ninth `AURELIUS_ATLAS_WEBAPP_*` name becomes ten); the chart-contract
suite pins the render against both CIDR-list defaults. A GKE overlay names
its alias IP range; a deployment whose Gateway runs outside the pod network
names its own. The server-side setting exists today (`forwarded_allow_ips`,
DD-238); only the rendering is new here.

### DD-262. The webapp nginx config resolves at pod start, not at Helm render

- **Status:** Accepted
- **Increment:** 10.3a
- **Date:** 2026-10-28

**Decision.** The webapp chart ships the nginx config as a ConfigMap of a
chart _asset_ — `helm/files/nginx.conf.template`, a byte-copy of the app's
`nginx.conf.template` (drift-guarded by a byte-compare test) — and a
`resolve-nginx-config` init container (the same webapp image, POSIX `sh` +
`sed`) substitutes the `${AURELIUS_ATLAS_WEBAPP_*}` placeholders from the
container's environment into an emptyDir that nginx reads at
`/etc/nginx/conf.d`. Helm performs no substitution; the image is unchanged
(it ships the raw template and fails loudly at parse, the Dockerfile's
contract). The hardened `dhi.io/nginx` base has neither `envsubst` nor
`bash` — the upstream image's `/docker-entrypoint.d/` 20-envsubst machinery
is not in it — hence the chart-side init container rather than an
entrypoint convention.

**Reason.** The template's ninth placeholder is
`${AURELIUS_ATLAS_WEBAPP_OTEL_INGEST_TOKEN}` — a _generated_ credential.
Rendering it Helm-side means the chart must expand
`lookup(-collector-legacy)` into the ConfigMap, and that is DD-256's
forbidden shape with a different secret: a Helm-rendered `randAlphaNum`
appearing in both the Secret and a ConfigMap, where `lookup` protects only
the Secret side — a pod rescheduled after a values edit gets yesterday's
bearer baked into its config while the Secret holds today's. Resolving at
pod start from the mounted Secret is the pattern the increment already
runs: Keycloak's realm placeholders resolve inside the process, fed from
the environment the chart fills from the generated Secret (DD-256). The
remaining placeholders (upstream names, resolver, origins, CA path) carry
no secret, but they resolve the same way — one mechanism, one contract,
byte-identical to the e2e stack's config-modulo-values.

**Alternatives.** (a) `tpl`/substitution over the file at render —
rejected: the double-generation race above. (b) Bake a filled config with
`envsubst` at image build — rejected: freezes environment values into the
image (the same environment deploys many clusters; CHT-04). (c) Fork an
nginx image with `envsubst` — rejected: the hardened image exists to not
carry GNU gettext. (d) Ship the template untouched and let nginx fail at
parse — rejected: that is the _bare container's_ deliberate failure, not a
deployable's.

**Consequences.** `tests/test__charts_webapp.py` byte-compares the asset
against `apps/aurelius-atlas-webapp/nginx.conf.template` every run; editing
the template requires re-copying. The init container's `sed` handles
exactly the `AURELIUS_ATLAS_WEBAPP_` name prefix; a template placeholder
outside it resolves to nothing loudly (a `grep` for unresolved `${` fails
the init before nginx starts). Next free DD: 263.

### DD-263. BackendTLSPolicy renders the v1 `caCertificateRefs` list

- **Status:** Accepted
- **Increment:** 10.3a
- **Date:** 2026-10-28

**Decision.** The umbrella's `httproutes.yaml` renders each TLS backend's
`BackendTLSPolicy` at `apiVersion: gateway.networking.k8s.io/v1` with
`validation.caCertificateRefs` — a _list_ of `{group, kind, name}` refs to the
trust CA Secret (which carries `ca.crt`) — plus `validation.hostname` set to
the Service name (SNI and the per-Certificate SAN check). It does not render
the `v1alpha3`/singular-`caCertRef` shape.

**Reason.** The minikube hand check caught the first render server-side
applying as `.spec.validation.caCertRef: field not declared in schema`: the
standard Gateway API CRD bundle (v1.6.1 experimental, installed per the
runbook) declares only the v1 `validation` fields; `v1alpha3` with the
singular ref is not in that schema at all. Envoy Gateway 1.9.3's
`BackendTLSSettings` docs confirm the v1 shape works end to end, including a
single Secret ref with the CA in `ca.crt`. The keycloak round-trip through the
Gateway then completed with the policy Accepted.

**Alternatives.** (a) Install the `gateway.networking.x-k8s.io` experimental
bundle to get `v1alpha3` — rejected: a whole extra CRD set for a field the
stable API already has. (b) Drop CA pinning and trust the proxy's system
store — rejected: CHT-30's whole point is the Gateway verifies the leaf the
same way an in-cluster client does.

**Consequences.** `tests/test__charts_edge.py` pins the apiVersion and the
list form; a future Gateway API upgrade needs no chart change. Next free DD: 264.

### DD-264. The webapp's emptyDirs mount below the image's symlink baked-in paths

- **Status:** Accepted
- **Increment:** 10.3a
- **Date:** 2026-10-28

**Decision.** The webapp chart's writable-path emptyDirs mount at
`/run/nginx`, `/var/lib/nginx/tmp` (not `/var/lib/nginx`), and
`/var/log/nginx`. The chart's nginx-upstream placeholder defaults are cluster
FQDNs (`<svc>.<ns>.svc.cluster.local`) rather than short Service names.

**Reason.** The minikube hand check caught the webapp CrashLooping twice over.
(1) The `dhi.io/nginx` image bakes `/var/lib/nginx/logs` and
`/var/lib/nginx/modules` as symlinks into `/var/log/nginx` and
`/usr/lib/nginx/modules`; an emptyDir over `/var/lib/nginx` hides them, and
`load_module modules/ngx_otel_module.so` then dlopens a path that no longer
exists — nginx exits at boot. Mounting at `/var/lib/nginx/tmp` covers nginx's
only real compiled-in writable need there (the temp dirs) while the image's
own `logs`/`modules` symlinks survive (the `/var/log/nginx` emptyDir still
covers the logs path; `/etc/passwd`'s home is `/home/nginx`, unused). (2) Once
booting, the `/api` leg 502'd: the template's `proxy_pass` is a variable,
which forces nginx's stub `resolver` (the template sets it from
`${..._DNS_RESOLVER}`), and that resolver never applies `resolv.conf`'s
search list — a short name like `atlas-server` fails with `Host not found`.
The peer Certificates carry the `.svc.cluster.local` SAN, so the FQDN default
fixes resolution and keeps `proxy_ssl_name` verification (DD-286) intact.

**Alternatives.** (a) `postStart`/init `ln -s` into the mounted emptyDir —
rejected: the chart would re-enact the image's filesystem contract. (b)
Non-variable `proxy_pass` (static upstream) — rejected: the template is
shared with the compose stack, where the variable form is needed for the
resolver-based OTel leg, and DD-262 keeps chart and compose configs
byte-identical. (c) Values-level FQDN overrides only in
`environments/*.yaml` — rejected: the defaults are the common case and must
work unaided (CHT-04).

**Consequences.** `tests/test__charts_webapp.py` pins the three mountPaths
and the FQDN placeholder defaults. Compose is unaffected (its `nginx.conf`
is static and docker's DNS handles short names there). Next free DD: 265.

### DD-265. The issuer's public name resolves inside the cluster too (split-horizon)

- **Status:** Accepted
- **Increment:** 10.3b
- **Date:** 2026-10-29

**Decision.** The public issuer host (`keycloak.<domain>`) is made resolvable
_in-cluster_ as well: the runbook's cluster setup gains one CoreDNS entry
(rewrite `keycloak.<domain>` → `atlas-keycloak.<ns>.svc.cluster.local` — the
cluster port of dev's per-producer `extra_hosts`, DD-202), and the Keycloak
chart's Service gains a `443 → https` port so the public URL's implicit port
dials. Keycloak's configuration is unchanged (`KC_HOSTNAME` stays the bare
public host — the hostname-v2 options are not enabled) and no consumer
changes: the collector's `oidc` extension, the apps' `AUTH_SERVER_URL`, the
OTLP token URLs, and the pullers' `token_url` all keep the public URL and now
resolve it locally. The collector keeps one `issuer_url` (no `jwks_url`
split). The hand check pins that a mint through the Gateway and a mint
through the Service yield the same `iss`.

**Reason.** The cluster must answer 10.2's deferred "how do in-cluster
producers reach the issuer" question, and a live probe against the 10.3a
hand-check cluster pinned the constraints. Keycloak (26.7, hostname v1,
`KC_HOSTNAME` bare, `KC_PROXY_HEADERS=xforwarded`) resolves the emitted
issuer from the _Host header_: a request with `Host: keycloak.atlas.test`
mints `iss=https://keycloak.atlas.test/realms/master`; one with the Service
FQDN as Host mints `iss=https://atlas-keycloak.atlas.svc.cluster.local/realms/
master` — a different issuer, permanently embedded in every token it
produces (runbook §0). So in-cluster consumers cannot simply dial the Service
name: they would fork the issuer per dial-path. The discovery document makes
it worse: it hands out a `jwks_uri` that follows the same Host, and the
auth library (and every OIDC client) _follows_ it — a Service-FQDN fetch
returns a jwks_uri that only makes sense on the dial path it came from. The
one shape where every consumer keeps its configuration and every token keeps
the canonical `iss` is making the public name resolvable both outside
(the Gateway route, browsers) and inside (CoreDNS → Service, pods), i.e.
split-horizon DNS — and that is precisely the mechanism the dev stack
already runs: `keycloak.localhost` is in every producer's hosts file
(Docker's `extra_hosts`) so the single issuer name resolves wherever it is
dialled. A real deployment's DNS does the same naturally (`atlas.test` is
the operator's domain, its internal view points at the cluster); on a dev
cluster the CoreDNS entry is the explicit form, and it is a documented
cluster prerequisite beside cert-manager and the GatewayClass.
The Service's second port exists because `https://keycloak.<domain>/`
dials 443 and the public URL must carry no port for the canonical `iss`
(Host-with-port → issuer-with-port).

**Alternatives.** (a) The hostname-v2 split (`KC_HOSTNAME_URL` +
`--hostname-backchannel-dynamic`): Keycloak's own answer to internal-vs-
public URLs — rejected: it makes the _claim_ path-dependent (the
backchannel's issuer follows the dial name per request), and the probe
showed even v1's port handling varies by dial path (:8443 appears in `iss`
whenever the Host header carries it), so the permanent claim would fork
per producer. (b) A per-consumer fetch/claim split (the collector's native
`jwks_url`, a new option in `aurelius-atlas-auth` to fetch JWKS at the
Service while checking the public `iss`, Service-FQDN token URLs in every
chart): rejected — it touches the auth library, three aux apps' settings,
the pullers, and the collector to work around a DNS gap the cluster owns,
and any future discovery-following component (Grafana/Tempo OIDC, the
server's own auth when it lands) inherits the same surgery. (c) A headless
ExternalName Service for the public name: Services answer at
`<name>.<ns>.svc.cluster.local`, never at a bare host — impossible.
(d) `hostAliases` per pod: wants an IP (Service ClusterIP is unknown at
render time). (e) Route in-cluster mints through the Gateway (hairpin via
Envoy with a Host rewrite): rejected — httpx/http clients cannot present
`Host: keycloak.<domain>` over a Service-IP connection without bespoke
transports, and Envoy hairpins every internal token mint.

**Consequences.** The runbook gains the CoreDNS step (the minikube line:
`kubectl -n kube-system edit cm coredns`, a `rewrite name` stanza); the
hand check scripts it and the `helm upgrade` pins it.
`tests/test__charts_keycloak.py` pins the Service's `443 → https` port and
the unchanged `KC_HOSTNAME`. The dashboard/contract rule stays honest: one
realm, one issuer URL, two horizons of DNS for the same name — the same
sentence the dev compose already tells.

### DD-266. Scrape with static configs and slice-owned puller Deployments

- **Status:** Accepted
- **Increment:** 10.3b
- **Date:** 2026-10-29

**Decision.** 10.2's deferred scrape question is answered with the compose's
shape, not Kubernetes-native service discovery: the Prometheus ConfigMap
keeps the five dev jobs (`prometheus`, `otel-collector` with the
native-histogram protocol pins, `otel-collector-internal`, `loki`, `tempo`)
retargeted to this chart's Service names, and the Elasticsearch and Keycloak
charts each gain a `metrics-puller` Deployment gated on `telemetry.enabled` —
the contrib collector image, a ConfigMap port of the slice's dev
`metrics-puller.yaml`, the dev `service.name` values kept verbatim
(`dev-elasticsearch`, `keycloak-infra`). No `ServiceMonitor`/`PodMonitor`
resources anywhere; no sidecar pullers.

**Reason.** The accepted Grafana dashboards pin `exported_job` values
(`dev-elasticsearch`, `keycloak-infra`, `keycloak`, …) that came from the
pullers' `service.name` upserts, and 10.2's spec committed to
"cluster-native scraping" only as a prediction, not a contract. A
Prometheus-Operator install contradicts the deployment reference's component
list (the stack is five images, and the Operator is a sixth with its own
CRDs); static scrape configs are what the working reference already runs and
what the stack dashboard's `job="otel-collector"` pins assume. Puller-as-
Deployment (not sidecar) keeps 10.2's store charts' statefulsets untouched
— including the CHT-18 template-hash checksums — and gives each puller its
own restart/rollout blast radius, which is what the dev `restart:
on-failure` + ESD-06 lesson (a wedged puller starves the store's telemetry
silently) asks for as a separate unit. Keeping the dev `service.name` values
is deliberate (DD-265's one-contract rule): a dashboard must not fork per
environment, and `dev-` reads as the metric-family name the dashboards were
accepted with, not as a lie about the environment (that's
`deployment.environment.name`, DD-268).

**Alternatives.** (a) `ServiceMonitor`s via Prometheus Operator — rejected
above (component budget, CRD surface, dashboards' job pins). (b) Puller as
a second container in each store pod — rejected: store rollout churn, and
the store's probes/checksums now include a telemetry concern. (c) Rename
`service.name`s to environment-neutral values and edit the dashboards —
rejected: the dashboards are the accepted surface (this increment's own
byte-copy drift guards treat them as frozen); a values-level
`service.name` override is available for a deployment that wants its own
attribution. (d) Scrape Elasticsearch/Postgres with Prometheus' native
`elasticsearch`/`postgres_exporter` jobs — rejected: needs an exporter
image not in the stack, and the OTel `elasticsearch`/`postgresql` receivers
already produce the series the dashboards query.

**Consequences.** `test__charts_elasticsearch.py`/
`test__charts_keycloak.py` grow a puller render (gated off by default — the
dev compose remains the dev shape); the puller ConfigMaps are structurally
compared against the dev YAMLs (CHT-34's pin, same pattern). The umbrella
enables `telemetry.enabled` on both store charts so a stock install gets
store metrics. `dev/postgres`'s standalone puller stays compose-only — that
slice is not an umbrella component. Next free DD: 267.

### DD-267. Grafana's admin password is a generated Secret and the login form stays disabled

- **Status:** Accepted (the login-form-stays-disabled clause superseded by
  [DD-276](#dd-276-grafana-logs-in-through-the-realm-with-a-request-derived-root-url))
- **Increment:** 10.3b
- **Date:** 2026-10-29

**Decision.** The umbrella generates `<release>-grafana-admin` (user +
password, the lookup/values/fresh-`randAlphaNum` CHT-19 pattern) and the
observability chart joins it into `GF_SECURITY_ADMIN_USER` /
`GF_SECURITY_ADMIN_PASSWORD` when `grafana.adminPasswordSecret` is unset
(default) or names a Secret to use. The login form stays disabled
(`GF_AUTH_DISABLE_LOGIN_FORM=true`) exactly as in dev, so the deployed
posture is anonymous-Viewer read access and the admin credential is held in
the Secret for the operator to use through whatever authenticated path the
environment opens later. A deployment that brings its own Secret points
`adminPasswordSecret` at it and the umbrella generates nothing.

**Reason.** The values contract already reserved the hook ("the default
posture is kubectl port-forward"), and the CHT-19 pattern — one generated
Secret per credential, preserved across upgrades, never rendered into any
ConfigMap — is what every other credential in this system follows (DD-254).
The alternative in dev (no admin password at all, Grafana's `admin`/`admin`
default) is what R5 forbids shipping, and enabling the login form would put
a password-authenticated surface behind the `grafana.<domain>` route (10.3a
CHT-32) that has no Keycloak front — the edge's OIDC auth filter covers the
atlas host, not this one, and bolting auth onto the observability host is
its own increment-sized decision, not a side effect of turning the stack on.
Keeping the form disabled matches the accepted dev contract: anonymous Viewer
is the posture; the generated admin exists so the instance is never
ship-default-credentialed.

**Alternatives.** (a) `adminPassword` in values plaintext — rejected: R5,
and the chart's whole secrets story is generation + joins. (b) No admin at
all — rejected: Grafana still boots `admin`/`admin` internally and the form
being off is the only thing gating it; the operator needs a real credential
to re-enable it deliberately. (c) Route Grafana through Keycloak now —
rejected as scope: the edge's auth filter pattern exists, but wiring it is
an edge change with its own rules (10.4's polish list has the candidates).

**Consequences.** `helm/templates/secret-grafana.yaml` (or the existing
secret template's sibling block) renders the pair only when
`atlas-observability.enabled` and `grafana.enabled`; the observability test
pins the `valueFrom` joins. Turning `GF_AUTH_DISABLE_LOGIN_FORM` off in a
values overlay is the documented way to expose admin, with the Secret
retrieved per the runbook's `kubectl get secret` line. Next free DD: 268.

### DD-268. The cluster's deployment environment is named by values, not baked as development

- **Status:** Accepted
- **Increment:** 10.3b
- **Date:** 2026-10-29

**Decision.** The collector's `resource` processor upserts
`deployment.environment.name` from `collector.deploymentEnvironment`
(default `cluster`); the dev compose's ConfigMap keeps `development`
untouched. Producers contribute no environment attribute of their own (the
OTel SDK defaults stay unset — the charts render no `OTEL_DEPLOYMENT_*`
env); the collector is the single place the attribute is stamped, in every
deployment shape.

**Reason.** The dev config's `development` value is an environment
statement, not pipeline semantics — every rule CHT-34 copies (receivers,
processors, pipelines) is environment-free except this one line, and the
charts' contract is "the dev config's shape with the environment slots
computed" (the observability values file's own comment). Baking
`development` into a cluster install would make Tempo/ Loki's data lie about
where it came from, and an operator filtering panels by environment would
have to fork the ConfigMap — the drift DD-253's suite exists to prevent.
Defaulting to `cluster` keeps a stock install honest with zero values; the
attribute's consumer contract (the OTel semantic convention, and panels that
group by it) is unaffected. A producer-side `OTEL_RESOURCE_ATTRIBUTES`
route was the other shape: rejected because then every chart would stamp
the same environment string (eight places instead of one) and any mismatch
between them silently splits the panels' filters.

**Alternatives.** (a) `deployment.environment.name` from the umbrella's
release/environment values (e.g. `global.environment`) — considered; kept
chart-local as `collector.deploymentEnvironment` because the collector is
the stamper and there is no second consumer of the concept yet; promote it
to `global.*` when a second one appears. (b) Producer-side env — rejected
above. (c) Omit the attribute in-cluster — rejected: Tempo's
`deployment.environment` search facets and the resource processors'
matching depend on a value existing.

**Consequences.** The CHT-34 structural test compares dev vs cluster configs
everywhere except this attribute's value (the one slot the test knows to
allow); a values-level override is the documented fork. Next free DD: 269.

### DD-269. The boot-gate image is curl, not busybox: wget cannot handshake Keycloak's TLS

- **Status:** Accepted
- **Increment:** 10.3b

**Context.** The hand check's first live boot left the three `issuer-wait` init
containers spinning forever with the issuer healthy: busybox's `wget`
(`--no-check-certificate`) fails Keycloak's TLS listener with `got bad TLS
record (len:0) while expecting handshake record` / `Connection reset by peer`
against a server openssl, python, and curl all complete handshakes to
(TLS 1.2 and 1.3, ECDHE-RSA-AES256-GCM-SHA384 and TLS_AES_256_GCM_SHA384).
The uClibc busybox TLS stack is the failing side, and it fails on every
attempt — an init loop with a fixed `sleep` would never end, so a workload
whose whole job is "wait for the issuer" blocks the collector, the server
puller, and the Keycloak puller forever.

**Decision.** The issuer-wait init ships as `dhi.io/curl:8` (uid 65532, as
busybox did) with `curl -sSf --insecure --retry 0 --retry-connrefused
--retry-delay 5 <well-known>` — an infinite native retry, no `sh` needed
(the hardened curl image has no shell), exit 0 the moment the realm answers.

**Alternatives.** (a) A richer init image with a shell (alpine-class) —
rejected: one more base image to harden for a six-line poll, and the retry
semantics are identical. (b) A TCP-only wait (`nc -z`) — rejected: a listening
socket does not mean the realm's JWKS endpoint answers, and the OIDC extension
reads exactly that endpoint (DD-195's race is an HTTP-level one). (c) Keep
busybox, retry the init from Kubernetes instead of in-process — rejected: a
backoff-waiting Pod is exactly what the init container exists to prevent
(DD-298's lesson applies to crash-looping inits too).

**Consequences.** CHT-37's rule text names the image honestly; the chart tests
pin `dhi.io/curl:8` and the command shape (no shell, `--retry-connrefused`).
The `--insecure` flag stays scoped to a boot gate (the collector verifies the
issuer CA-pinned, DD-216). Next free DD: 270.

### DD-270. The webapp serves TLS behind the gateway: the last plaintext hop closes

- **Status:** Accepted
- **Increment:** 10.3c
- **Date:** 2026-10-29

**Context.** DD-285 shaped the webapp's listener as plaintext behind the
gateway, and `helm/templates/httproutes.yaml` gave it no BackendTLSPolicy.
The trust analysis of the OTel/API flows found the one inversion between the
dev stacks and the cluster: the e2e nginx already listens `8080 ssl` with the
project's mkcert leaf (`apps/aurelius-atlas-webapp/e2e/config/nginx.conf`),
so the shipped chart was weaker than the tested dev shape. From 7.3 the
browser's bearer token and per-user OTLP pushes arrive at the Gateway, whose
HTTPS listener terminates there — and would then cross the gateway→nginx hop
in plaintext, one hop before the same token's TLS-verified `/api/` proxy
(whose comment names exactly that threat). The invariant "user tokens never
cross plaintext" (ADR 039) needs the hop closed before the tokens flow.

**Decision.** The webapp's nginx listener serves TLS: the shipped template
gains `listen 8080 ssl` with `ssl_certificate`/`ssl_certificate_key` from two
new placeholders (the contract grows ten → twelve, CHT-25 amended in place —
PR #159 is still in review). The chart ships a `Certificate` following the
server's pattern (CHT-22: SANs = the Service and its FQDNs, issued by the
umbrella's CA issuer; `tls.certSecretName` brings your own and renders
nothing), mounts the leaf whole beside the trust root, and flips its probes
to HTTPS. The umbrella's `edge.listeners` helper flips the webapp entry's
`tlsBackend` to true, so `httproutes.yaml` renders the third
`BackendTLSPolicy` — CA-pinned via `caCertificateRefs`, SNI = the Service
name = the SAN — with no template change of its own. Grafana stays the lone
plaintext backend (anonymous Viewer, login disabled, DD-267): nothing
secret-bearing crosses its hop, and DD-285's clause stands scoped to it.
DD-285's gateway choice is untouched — this supersedes only its
plaintext-backend clause.

**Alternatives.** (a) Leave it until 7.3 — rejected: the e2e stack already
runs TLS nginx (the cluster should not ship weaker than the test rig), and
landing it beside the auth wiring bundles two unrelated slices. (b) mTLS to
the webapp — rejected: the Gateway API `BackendTLS` validation is
CA-and-SNI; client certificates would need Envoy Gateway BackendAuth policies
for an identity the app layer already carries (DD-285's mesh argument).
(c) Reuse the `<release>-edge-tls` leaf — rejected: its SANs are the browser
hosts, not the Service name; the BackendTLSPolicy hostname check is the
Service name (CHT-22's rule, as for every other backend).

**Consequences.** CHT-23's and CHT-25's rule text in the 10.3a spec amend in
place (unmerged); CHT-30's "plaintext backends (webapp) none" becomes
Grafana-only. The webapp's placeholder count is twelve; the byte-copy drift
guard covers the new template. The probes are HTTPS (kubelet skips
verification — liveness, not trust, DD-260's lesson). A cluster upgrade to
this chart is an atomic umbrella `helm upgrade`: the BackendTLSPolicy and the
TLS listener ship together, so there is no window where Envoy dials TLS into
a plaintext listener or plaintext into a TLS one.
Next free DD: 271.

### DD-271. Network-policy ownership: the umbrella deny-all and the chart's additive allows

- **Status:** Accepted
- **Increment:** 10.6
- **Date:** 2026-10-29

**Context.** The pre-pentest review's H2 found the cluster shape flat: any
pod in the namespace could dial any other pod's every port, so one webapp
compromise walked to Elasticsearch's 9200, Keycloak's 8443, and the telemetry
backends without a credential check at the network layer. Kubernetes
`NetworkPolicy` is the native fix, but its semantics — policies are additive
allows and a namespace is default-open until some policy selects a pod —
make _ownership_ the design question: a single umbrella-owned policy set
would have to enumerate every chart's ports (a central registry the component
charts don't have, against ADR 057's per-chart ownership), and one default
rendered per chart would make a chart's `networkPolicy.enabled=false` a
namespace-wide open — the opposite of the surgical switch operators need.

**Decision.** Two owners, never overlapping (CHT-60/72): the umbrella renders
exactly one namespace-wide deny (`<release>-deny-all-ingress`,
`podSelector: {}`, no rules) and the browser-edge allows for its own
listeners; every chart renders only additive ingress allows for the pods it
owns, gated by its own `networkPolicy.enabled`. Disabling a chart's switch
narrows allows, never the deny — no component can open the namespace, and no
component chart ever needs to know the namespace contract exists. Peers join
by **pod** labels (`app.kubernetes.io/name`/`instance`/`component`, CHT-70),
not Service names: the name rule the Services use is the same rule, and the
`networkPolicy.peers.<peer>` overrides exist because the Service-name joins
(`atlas.service` et al.) rename Services and must never feed a selector. The
peer sets are the full call graph read off the renders (who actually dials
whom, DD-265's split-horizon included), so every rule names a real caller —
lineage-model and validate-entity get no ingress policy because nothing dials
them (CHT-66), and Grafana's only allow is the gateway's when its host is
enabled (CHT-69).

**Alternatives.** (a) One umbrella-owned policy list — rejected: centralises
every chart's port knowledge in the umbrella, exactly what ADR 057 split up,
and a component renamed by values silently breaks a rule it does not own.
(b) Per-chart default-deny policies — rejected: overlapping denies compose to
the intersection and a chart's disable switch becomes namespace-wide
foot-gun. (c) CiliumNetworkPolicy / egress rules — rejected: a CRD
dependency for a posture Kubernetes v1 covers, and egress restriction is a
cluster-policy decision (the compose dev shape runs with no policies at all;
CHT-73 keeps Ingress-only so both shapes stay honest). (d) AdminNetworkPolicy
— rejected: out of the chart's namespace scope entirely.

**Consequences.** The umbrella and every chart carry a
`networkPolicy.yaml`; the contract suite names CHT-60..73 with the exact
peer sets and ports so a widened rule breaks a named rule, not a snapshot.
Kubelet probes and `kubectl port-forward` ride the CNI's node path and are
policy-exempt — documented (CHT-71), which is what keeps the collector's
13133 and Keycloak's 9000 rule-free. A cluster upgrade applies the deny the
moment it rolls: charts that ship a policy whose caller the operator has
customised need the `peers` override set before the upgrade, and the hand
check (10.5 script) boots the full umbrella under the policies before the
leg round-trip runs. Next free DD: 272.

### DD-272. The edge allow's source is a knob with an all-namespaces default

- **Status:** Accepted
- **Increment:** 10.6
- **Date:** 2026-10-29

**Context.** The gateway edge policies (CHT-61) admit the Gateway's data
plane to the browser backends' container ports. The obvious `from` is the
data plane's namespace by label — but the placement is not the chart's fact:
Envoy Gateway ships its data plane wherever its own install puts it
(`controlPlane.namespace`), the managed alternatives (GKE, AKS, Istio
ingress) name it their own, and the dev kind/minikube shapes may co-locate
it. A wrong pin does not fail loudly: the HTTPRoutes stay green, the Gateway
programs, and every browser request black-holes at the network layer —
exactly the class of failure the pentest would report as a foot-gun.

**Decision.** `networkPolicy.gatewayNamespaces` (list, default `[]`). Empty —
the shipped default — renders `namespaceSelector: {}` (every namespace):
the browser backends are already public through the Gateway, so an
all-namespaces source adds no exposure the edge does not already have —
the in-cluster peers of a browser backend are no closer to a secret than a
browser is (the webapp proxies only through the server's own auth). A
non-empty list pins: one `namespaceSelector` per name matched on
`kubernetes.io/metadata.name`, and only those namespaces admit. The runbook
names the pin as the production hardening step; the chart cannot read the
Gateway's placement from inside the release.

**Alternatives.** (a) Default to `ingress-gateway` (Envoy Gateway's default
namespace) — rejected: right for one install recipe, silently wrong for the
managed platforms, and the failure mode (black-holed edge) is invisible in
the HTTPRoute tests. (b) Discover the data plane from the cluster at render
— rejected: `helm template` has no cluster, and an `lookup`-based default
makes the render untestable (the contract suite renders offline, CHT-06).
(c) No knob at all, always all-namespaces — rejected: operators on a
multi-tenant cluster lose the hardening path entirely.

**Consequences.** The stock install's edge policies say "any namespace", which
reads alarming in a security review until DD-272 is cited — the spec and
`helm/values.yaml` comment carry the pointer. The pin test (CHT-61) renders
the single-namespace spellings so the knob is a contract, not a suggestion.
A future environment overlay (helm/environments/) may set the pin per
platform once the placement facts are on record.
Next free DD: 273.

### DD-273. Two identity realms: hardened `aurelius-atlas` for clusters, `master` as the dev escape hatch

- **Status:** Accepted
- **Increment:** 10.7
- **Date:** 2026-10-30

**Context.** The pre-pentest review's H3: the cluster authenticated the whole
system against Keycloak's own `master` admin realm, because
`dev/keycloak/import/master.json` — built for the compose/e2e browser-login
rig (localhost origins, ROPC password grant, demo users, Keycloak's admin
clients with `webOrigins: ["+"]`) — was also the chart's only realm asset.
Splitting the shapes raises the question of what the prod asset is made of.
Stripping master's export down to the app surface looked attractive until
its composites were checked: `default-roles-master` composites the
account/realm-management client roles, so a pruned export either keeps dead
references or breaks import, and no offline check can prove which — there is
no running Java-Atlas-style reference Keycloak here, and the cluster shape
only ever boots for real in the 10.5 hand check.

**Decision.** Two assets, two shapes (CHT-75, CHT-78). The cluster's realm is
the minimally-authored `files/aurelius-atlas.json`: exactly the
application-facing surface — the `aurelius` public client (with its
`aurelius-write` client role), the seven `otel-*` service accounts, and the
`otel-ingest` scope — with the H3 hardening applied and no seeded users;
Keycloak recreates its built-in clients, scopes, flows, and roles when it
creates the realm, so the file never carries or references them.
`files/master.json` stays exactly as DD-256 made it (byte-copy of the dev
import, drift guard running): the dev compose and the four `e2e/` suites keep
importing `master` with its localhost origins, ROPC, and demo users — the
browser-login conveniences the Playwright suites need — and `realm.name:
master` remains the documented cluster escape hatch that loads it byte-for-
byte. The demo-user plumbing (the umbrella's `<release>-keycloak-users`
Secret, the StatefulSet's `DEV_USER_*` env) is gated on the master realm
(CHT-80): a stock install provisions no people.

**Alternatives.** (a) One realm for everything, hardened — rejected: it
breaks the dev login rig (Playwright's ROPC grants and localhost origins are
the suite's contract, DD-206's shape) and drags dev into the first-boot
hostname pin. (b) A pruned export of master as the prod asset — rejected as
unverifiable offline (composite transplant, above). (c) Seed prod users from
values — rejected: a cluster realm with no users is the pentest-clean shape;
operator provisioning through the admin console is the normal path, and
placeholder-fed demo identities in a prod chart re-create the finding.

**Consequences.** The CHT-79 structural-parity test is the two-asset drift
guard: the otel-* clients and the otel-ingest scope must equal their dev
peers and the aurelius client may differ only in the hardened fields, so an
identity change in dev must be mirrored in the prod asset or named in its
commit. The two shapes are deliberate (DV-112): a reviewer comparing the dev
stack's login behaviour to the cluster's should expect them to differ.

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

### DD-276. Grafana logs in through the realm, with a request-derived root URL

- **Status:** Accepted (supersedes DD-267's login-form-stays-disabled clause)
- **Increment:** 10.8
- **Date:** 2026-10-31

**Context.** Enabling the login (H4) has an operator cost DD-267 named
obliquely: its reason paragraph said enabling the form would put a
password surface behind a route with no Keycloak front — 10.8 removes that
objection by putting Keycloak in front. The other half of DD-267 (the
generated `-grafana-admin` Secret, never ship-defaulted) stands untouched
and keeps its env joins; it becomes account recovery rather than a dormant
credential.

**Decision.** `GF_AUTH_*` swaps anonymous-off/login-form-on/OAuth-on
(CHT-84); `GF_SERVER_ROOT_URL` **stays unset** and the client's
`redirectUris` carry both `https://__GRAFANA_HOST__/login/generic_oauth` and
`http://localhost:3000/login/generic_oauth` (CHT-82). Grafana derives the
redirect from the request Host header when root_url is unset, so
`kubectl port-forward` to the pod — the documented default access path —
completes the full OIDC round-trip through Keycloak at the public issuer
URL, while a browser reaching `grafana.<domain>` (if exposed) round-trips
through the same client. The localhost entry is a fixed dev/operator URI,
not a wildcard: an attacker who cannot land a browser on `localhost:3000` of
the operator's machine cannot use it.

**Alternatives.** (a) Pin `GF_SERVER_ROOT_URL` to `https://grafana.<domain>`
— rejected: it breaks the port-forward path (Grafana would redirect the
browser to a host that isn't listening) and pins the pod to one hostname;
the umbrella's `hosts.grafana.enabled=false` default makes the request-
derived form the correct general shape. (b) The `+` wildcard redirect —
rejected: CHT-77 forbids `+` in a cluster asset, and a wildcard on a
confidential client is the open-redirect shape the realm was hardened
against. (c) A second `grafana-dev` client for the localhost path —
rejected: one client, two exact URIs is less surface and one row of drift.

**Consequences.** DD-267's table row and body carry the partial-supersession
annotation; its generated-Secret half is unchanged. Keycloak's 8443 dialer
set gains the Grafana pod (CHT-86) — the token exchange and JWKS fetches are
new real traffic and the full-dialer-set philosophy (CHT-62) admits them
without a flag. A render with `global.hosts.grafana.host` set to something
unreachable still logs in fine over port-forward; the host entry is inert
allow-list filler (CHT-82), not a dependency.
Next free DD: 277.

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

### DD-278. Third-party digests committed, own images stay tags; charts sign

- **Status:** Accepted
- **Increment:** 10.10
- **Date:** 2026-10-31

**Context.** The pre-pentest triage's M9: every chart image renders by
mutable tag, and published OCI charts are unsigned while their images are
keyless-signed (publish.yaml). A registry compromise, a mirror substitution,
or a retagged upstream silently changes what installs. A first design
sketch pinned _everything_: committed digests for the thirteen third-party
values plus a publish-time bake resolving each Aurelius image's digest into
the chart tree before `helm package`. The bake is what this entry rejects.

**Decision.** Three calls, the second at the user's explicit direction
("uncomplicate our pipeline by only pinning digests for third-party
images"):

1. **Every image block gains a `digest` field; the helpers make it win.**
   `<base>@<digest>` when set, `<base>:<tag>` otherwise — whatever produced
   the tag (appVersion chain, chart default, `global.image.tag`). Puller and
   issuer-wait images move from inline `printf "%s:%s"` joins to named
   helpers so they get the same branch (CHT-92).
2. **Only third-party digests are committed; Aurelius images stay tags.**
   The risk a digest answers is _someone else changing what a tag means_.
   The nine dhi.io pins carry committed digests (CHT-93); a weekly drift
   guard (CHT-96) fails when a tag bump forgets its digest refresh. Our own
   six images are written only by publish.yaml — after signing and
   verifying — and the published chart version that references them is
   itself immutable (OCI refuses re-push) and cosign-signed, so installing
   chart version X provably names this release's images. The bake would
   pin the release to itself a second time, at the cost of a publish-time
   rewrite of the chart tree (a workflow-local mutation invisible to
   review, whose output no CI render ever reproduces). Their `digest`
   fields stay `""` — a live operator override, not decoration (CHT-94).
3. **Charts sign like containers.** `helm-sign`/`helm-verify` join the helm
   plugin's inferred targets (DD-290's mechanism) against
   `ghcr.io/aureliusenterprise/charts/<chart>:<version>`, keyless, with
   `docker-verify`'s identity/issuer regexp contract; publish.yaml runs the
   pair right after `helm-publish` (CHT-95).

**Alternatives.** (a) Full bake (the first sketch) — rejected per 2; with
it went `tools/images/bake_digests.py` and the publish bake step, descoped
mid-increment. (b) Committed Aurelius digests bumped by the release itself
— rejected: every release would dirty the chart tree with a digest of its
own predecessor, and CI renders would trail the registry. (c) Dependabot
for the third-party pins — rejected as mechanism: its `docker` ecosystem
does not parse Helm values; the drift guard's refresh PR is the equivalent
flow. (d) `helm provenance` (.prov packages) instead of cosign — rejected:
cosign is what the image chain already uses, one identity/issuer contract
to audit, and the sign target rides the OCI artifact `helm push` already
uploads.

**Consequences.** A stock install pulls nine immutable third-party images
and a signature-verifiable chart; admission enforcement (policy rejecting
unverified images at the cluster) stays an operator follow-up named in the
runbook. The umbrella guard (CHT-97) classifies every rendered image as
Aurelius-tag or committed-pin, so an unpinned new image fails CI without a
registry call, and a pin that drifts from `conftest.PINNED` fails loudly.
`digest: ""` fields in the six Aurelius blocks look like dead config to a
newcomer; CHT-94 and the values comments carry the why. Next free DD: 279.

### DD-279. Edge hardening, two-stack loopback guard, CI fork posture

- **Status:** Accepted
- **Increment:** 10.11
- **Date:** 2026-10-31

**Context.** The pentest backlog's Low residue after 10.6–10.10: the webapp
edge serves the SPA over TLS with no HSTS, keeps the resolved nginx config
(which embeds the legacy ingest bearer) on disk, and proxies `/otel/`
unthrottled; Prometheus/Loki/Tempo and the dev store still publish on
`0.0.0.0`; and the CI queue treats the members-only-PR policy as a GitHub
setting rather than code, with one `concurrency` group shared by public
deploys and PR previews and ARC runner images floating on mutable tags.

**Decision.** Four calls, the third's shape decided mid-increment at the
user's direction:

1. **The tmpfs is scoped to the secret.** Only `nginx-conf` gets
   `emptyDir.medium: Memory` (CHT-98); the pid/temp/log emptyDirs stay
   disk-backed. RAM is charged per pod and the threat is the bearer, not
   emptyDirs in general. HSTS rides the same placeholder mechanism as the
   realip block — the chart renders the _whole_ `add_header` directive into
   `${AURELIUS_ATLAS_WEBAPP_HSTS_HEADER}` (CHT-99), so the e2e/compose
   shapes resolve it to nothing and the fail-loud guard keeps the contract
   closed at thirteen. The `/otel/` limiter is browser-sized deliberately
   (`atlas_otel`, 600 r/m, burst 100) in both twins — a test-sized zone
   would throttle the suite's own traffic (CHT-100).
2. **The loopback guard enforces two stacks, not the world** (CHT-101).
   `tests/test__dev_stack.py` scans only `dev/observability` and
   `dev/elasticsearch` compose files. A first sketch swept all of `dev/*`;
   the sweep surfaced Keycloak's issuer ports (e2e consumers dial
   `keycloak.localhost` via `extra_hosts: host-gateway`, so a loopback bind
   detaches every app e2e suite) and the template Postgres (its host port
   is the examples' `serve` database — host processes, not containers).
   Both need a compose-network rework, not a `127.0.0.1:` prefix: they are
   **named deferrals** in the spec, and the guard's file set is the honest
   enforceable set rather than an allowlist-shaped lie.
3. **Fork posture lives in the workflows** (CHT-102). Every
   `pull_request`-triggered job in `ci.yaml` and the PR-docs job gain the
   same-repo guard (`head.repo.full_name == github.repository`, ORed with
   `event_name != 'pull_request'` where a job also rides pushes). The
   members-only policy is a repo setting a future settings-sync could
   relax; the runners mount age keys, so the boundary is worth two lines
   per job. Docs `concurrency` splits by scope: `docs-public` (main/tag/
   delete) vs `docs-pr-<number>` per PR — no `cancel-in-progress` on the
   PR group because `mike deploy --push` is a git transaction.
   ARC: the third-party `actions-runner` cache-init image is digest-pinned
   in values; `CI_SHAPEA_IMAGE_TAG` accepts a `sha256:` digest and
   `install.sh` joins it with `@` (own images stay tags per DD-278).
4. **The Trivy SARIF stays one-hopped** — declined at the user's direction:
   the scan already feeds SonarQube, whose quality gate fails the build; a
   second surface (GitHub code scanning) for identical findings splits the
   triage queue instead of shortening it. CODEOWNERS declined the same way
   (enforces nothing without org plan support). Both stay in the spec's
   not-delivered list with the reasoning.

**Alternatives.** (a) Whole-`dev/*` loopback sweep — rejected per 2; the
deferrals are named and dated, not hidden. (b) `permissions: contents:
read` on PR jobs instead of `if:` guards — insufficient: the age keys ride
step env from decrypted `.env.enc`, and a fork PR would still exfiltrate
via build output. (c) tmpfs for every emptyDir — rejected per 1. (d) A
per-PR concurrency group with `cancel-in-progress: true` — rejected: two
previews of one PR racing `mike deploy --push` corrupt the gh-pages
branch; queueing (no cancel) is correct for a git transaction.

**Consequences.** The webapp ConfigMap asset carries an
`${AURELIUS_ATLAS_WEBAPP_HSTS_HEADER}` placeholder no render may leave
unresolved — the chart suite pins the thirteen-name contract, and the
twin byte-identity test keeps `helm/files/nginx.conf.template` honest.
Dev hosts with tooling that reached 9090/3100/3200 or 9200 over a LAN
interface must re-point at the box's address; contributor-guide ports
table says so. The fork guard means external contributions run only the
lint/render jobs until the policy question is settled — accepted. The
Keycloak/Postgres loopback deferrals are open items with a named blocker
(compose-network rework) for a future increment. Next free DD: 280.

### DD-281. The container-outage and edge-flood e2e proofs retire; the shipped limiter stays

- **Status:** Accepted
- **Increment:** 10.5 (rollout step 0)
- **Date:** 2026-11-02

**Context.** The 10.5 rollout (DD-280) moves the e2e suites onto the
Helm/minikube lane, and three scenarios have no lane to migrate to. RSL-01
(webapp suite) and RSL-02 (lineage chain) stop and start **compose
containers** through the docker SDK, found by compose labels
(`com.docker.compose.project`); a minikube pod has no counterpart to that
handle, and rebuilding the arrangement on `kubectl delete pod` + restart
buy back two browser-visible symptoms — a bell badge after a 502, an
Atlas-shaped 502 body — that the unit suites already pin in-process (7.7's
`HttpTestingController` alert chain, 8.5's fake-transport LM-12 suite).
SRV-09's rate-limit test is worse: it proves the bucket by outspending it,
which works only because `e2e/config/nginx.conf` ships a **test-sized**
twin (60r/m burst 20) the live-flood can overflow in seconds; the shipped
browser-sized bucket (300r/m burst 100, geo-allowlisted so suite traffic
passes unlimited) is unprovable through a live flood at suite speed on any
lane, and the cluster edge adds a second limiter layer on top.

**Decision.** Delete the three proofs, in both lanes, and retire their
rule ids rather than park them as skips:

- `test__aurelius_atlas_webapp_resilience.py` keeps only the RSL-03
  logout round-trip (browser-only, migrates cleanly in 10.5c); its outage
  fixture, docker-SDK helpers, and RSL-01 test go.
- `test__aurelius_atlas_lineage_model_resilience_e2e.py` goes whole; its
  `covers` markers also named LM-12 and CL-30, which stay pinned by the
  scenarios files and the client suites.
- `test__aurelius_atlas_webapp_rate_limit.py` goes whole, and with it the
  test-sized `atlas_api` zone in `e2e/config/nginx.conf` (a bucket with no
  test keeps no config). RSL-03 and the `atlas_otel` zone (CHT-100,
  chart-guarded) stay.

**What stands.** The shipped limiter itself is untouched: both
`nginx.conf.template` copies (image + helm byte-copy), the geo/map key
pair, `limit_req_status 429`, DV-87, and the chart-render guards. SRV-09
retires as an _e2e rule_ — the config remains part of the product, guarded
where it is deterministic to guard (rendered manifests), and no longer
where it was only ever provable against a fixture-sized twin.

**Consequences.** 9.1 narrows to RSL-03; 9.3's limiter row carries the
retirement note; the conversion index rows for 9.1/9.3 and the lineage
conftest's timeout rationale follow. docker-py leaves the direct-use
column (its two consumers were these files; it stays installed as a
testcontainers transitive). The step runs **before** the suite migrations
so the shared lane library (10.5b) never has to carry an outage-orchestration
API nobody intends to use.

Next free DD: 282.

### DD-282. Chart misconfig scans ride the Sonar hop as project-level issues

- **Status:** Accepted
- **Increment:** 10.11 follow-on (helm hardening)
- **Date:** 2026-10-31

**Context.** The helm charts are in decent shape and the ask was to hunt
for small misconfigurations. A Trivy `config` pass over the nine charts
(their real renders, below) surfaces 206 findings (28 HIGH / 66 MED /
112 LOW); every HIGH is a dev-only workload — the store, Keycloak + its
Postgres, the observability stack, the metrics pullers — no Aurelius app
chart. SonarCloud already ingests the per-app image-vuln SARIF
(`docker-vuln-scan -c sarif` → `sonar.sarifReportPaths`, scan and sonar
co-located in CI's `scan-sonar` job for exactly that handoff); the natural
move is to give the chart findings the same hop instead of a new surface
(the 10.11 DD-279 decision keeps Trivy one-hopped — Sonar is the surface).

**Decision.** Three calls:

1. **Plugin target, not a script.** `helm-config-scan` joins the helm
   plugin's inferred set (`json` default for humans, `sarif` config for
   CI, `exit-code 0` — the gate lives in the quality gate, not the task),
   mirroring `docker-vuln-scan`'s configuration shape. CI's scan step
   extends in place (`-t docker-vuln-scan helm-config-scan -c sarif`);
   both SARIFs share the `vuln-reports` artifact. The target needs the
   explicit-executor form: Nx silently DROPS a `command:`-sugar target
   carrying `configurations` (verified against the graph — the target
   vanishes).
2. **Scan the real `helm template` render, not Trivy's helm renderer.**
   Two silent-skip traps, both verified. Trivy renders charts with DEFAULT
   values, and the CHT-02 required-guards fire there — a guarded chart then
   scans zero targets, which reads as clean. Worse, Trivy's own renderer
   cannot run `.Files.Get` (the keycloak chart's realm asset), so even with
   test values passed it SKIPs that chart outright — the `--helm-values`
   flag fixed six of nine but left keycloak invisible. The robust shape:
   render with real `helm template` (test values when the chart ships
   them, exactly as `helm-template` does — handles both guards and
   `.Files.Get`), write the manifests to `{projectRoot}/.helm-rendered.yaml`,
   and `trivy config` the file. Because the SARIF is project-level either
   way (locations dropped), scanning the render costs nothing in
   attribution.
3. **Project-level issues, no scope change.** The SARIF's jq filter drops
   every result's `locations` and the run's `originalUriBaseIds`, so
   Sonar imports findings as project-level issues (documented
   location-less behaviour). The alternative — rewrite URIs
   workspace-relative and add `helm/` to `sonar.sources` — would run the
   YAML analyzer over the Go templates (the same files prettier/check-yaml
   already exclude) and its line numbers are whole-container stanza
   regions anyway. The SARIF stays HIGH/CRITICAL-only: the LOW/MED backlog
   (KSV-0011 CPU limits — often deliberate, KSV-0125 ghcr untrusted-registry
   false positive, KSV-0013 `:latest` — a default-values render artefact,
   the release pins `appVersion`) would enter the new-issues gate as noise
   before triage; it graduates by editing the severity list, not by
   `.trivyignore`.

**Scope.** Only the five app charts have Sonar projects; their
`sonar-project.properties` gain the second comma-delimited SARIF path.
The umbrella and the three dev charts (where every HIGH lives) have no
Sonar project yet — their scans run in CI and their SARIFs reach the
artifact only; Sonar projects for them are a later decision.

**HIGH baseline (render-scan, all nine).** Five app charts: 0. Dev
elasticsearch 2, keycloak 3, observability 6, umbrella 17 (the umbrella
supersets the dev charts' workloads — its render is the deployed shape).
Every HIGH is KSV-0014 (`readOnlyRootFilesystem` unset/false) on a
dev-only workload — the store, Keycloak + its Postgres, the observability
stack, the metrics pullers — or KSV-0109 (a puller ConfigMap holding a
`${env:…}` password/secret slot). None touches an Aurelius app chart.

**Consequences.** `helm-misconfigs.json` and `.helm-rendered.yaml` join
the gitignored scan-report set (`*.sarif` was already ignored). The
plugin gained a sixth target; `helm/AGENTS.md`'s adding-a-chart list names
it. The findings are triage items, not gate failures: KSV-0109's
`${env:…}` references are placeholders (the real secret arrives as env
from a Secret — R5), and KSV-0014's puller containers can likely take a
read-only root with an emptyDir; the stateful workloads (store, Keycloak,
Postgres, observability) write to their data dirs and a read-only root is
a per-workload decision with a `tests/values.test.yaml` render guard. Both
are follow-ups; nothing enters a quality gate today because the app charts
are clean at HIGH. Next free DD: 283.

### DD-283. One chart per component under an umbrella, published as OCI artifacts

- **Status:** Superseded by DD-290 (the `charts/` residence; one-chart-per-
  component, umbrella, and OCI publish stand)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** Deployment lives in a top-level `charts/` tree: one chart per
deployable component (`atlas-server`, `atlas-webapp`, `atlas-data2model`,
`atlas-lineage-model`, `atlas-validate-entity`, `atlas-elasticsearch`,
`atlas-keycloak`, `atlas-observability`), a Helm library chart `atlas-common`
for the shared helpers, and the umbrella `aurelius-atlas` that composes them.
A component chart owns its component's runtime contract (port, probes,
`AURELIUS_ATLAS_*` settings, trust mounts); the umbrella owns the edge, the
trust issuers, the shared secrets, and the `global.*` values contract. Charts
publish to `oci://ghcr.io/aureliusenterprise/charts` in the release.

**Reason.** ADR 057. The increment that changes a component is the one that
knows its ports and probes, so ownership sits at the component (R3); the
combination that CI proves is one install of the umbrella (R4); a registry
artifact under the release's number, in the registry the images use, with the
credentials CI already has, is the smallest addition to the delivery plane
(R7). `charts/` as one tree keeps chart-to-chart edges — the common library,
the umbrella's pins — visible in one place, and each project's `AGENTS.md`
points at its chart.

**Alternatives.** (a) `apps/<app>/chart/` — one step more local, and it
interleaves the docker plugin's `**/Dockerfile` glob with a `**/Chart.yaml`
glob in the same directories; the deployable unit is a chart, and the app tree
is organised by conversion increment, not by deployment. (b) One monolithic
chart — R3's failure, the file where component knowledge goes stale.
(c) Charts in their own repositories — R2's failure, and ADR 001's; a
component change and its chart change stop being one commit. (d) Kustomize —
no chart artifact to publish (R7) and env-var text substitution where the
components need typed, validated values.

**Consequences:** `charts/AGENTS.md` carries the chart conventions the way
`libs/python/AGENTS.md` carries the library recipes. The example apps get no
chart — they leave with 6.4 (DD-019). The dashboard is not a chart: it is
copied into the server image (`/application/dashboard`, DD-018). Publishing
order becomes load-bearing (subcharts before the umbrella, DD-288). Next free
DD: 241.

### DD-284. Helm targets are inferred from `Chart.yaml` by a plugin mirroring `docker.ts`

- **Status:** Superseded by DD-293 (the inference and the plugin stand; the
  separate `<chart>-chart` PROJECT does not — targets merge onto the owner)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** `tools/plugins/helm.ts` infers, for every `charts/**/Chart.yaml`,
an Nx project named `<chart>-chart` (tagged `helm`) with `helm-lint`,
`helm-template` (`local`/`ci` configurations) and `helm-publish`
(`--namespace oci://ghcr.io/aureliusenterprise/charts`, `version` default
`local`, publish `latest`, CI passes `--version $VERSION`) — the option,
configuration, and metadata shape of `tools/plugins/docker.ts`.

**Reason.** ADR 021 (a technology joins by recipe: discovered, gated,
releasable, removable in one pass) and DD-283's R7. Inference makes charts
graph-visible, so `nx affected -t helm-lint` gates a chart change and
`nx run-many -t helm-publish` releases them — the same two commands that
already carry images. The docker plugin is the house pattern; a second shape
for the same job costs review attention.

**Alternatives.** (a) One root `helm` project looping charts in a shell script
— invisible to `affected`, no per-chart cache, no per-chart target to compose.
(b) A `project.json` in each chart — nine manifests to keep in step, where one
plugin file infers all nine. (c) `@nx/kubernetes` — it generates kustomize
scaffolding, not Helm targets.

**Consequences.** The validate job adds `nx affected -t helm-lint helm-template`
(level 0: no cluster, no registry, no SOPS key — helm 4.3.1 is in the dev
container, which is the CI runner image, so nothing installs). Release
grouping picks chart projects into the version plan (DD-288). The plugin's
commands are helm 4 flags; a helm 3 operator can lint the charts but the
publish path assumes helm 4's OCI push. Next free DD: 242.

### DD-285. The edge is Gateway API, not ingress-nginx

- **Status:** Accepted
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** The umbrella renders the edge as Gateway API resources: one
`Gateway` and one `HTTPRoute` per host (`atlas.<domain>` → webapp,
`keycloak.<domain>` → Keycloak, optional dashboard and Grafana hosts), with
`gateway.className` a value (Envoy Gateway on minikube, the provider's
implementation on a managed cluster). No ingress-nginx, no ingress-level
instrumentation, no service mesh.

**Reason.** ingress-nginx retires in March 2026 — best-effort maintenance
until then, no security fixes after (kubernetes.io, 2025-11-11) — so building
the deployment on it starts a migration on day one. Gateway API is the
successor and is the portable choice by construction: the chart names an API,
the cluster names an implementation, which is R1 in one line. The policy the
edge used to be chosen for already lives one hop in: the webapp's nginx owns
the browser rate limit (DD-238) and the `/api/` tracing export (DD-239), and
it is tested by the e2e suites.

**Alternatives.** (a) ingress-nginx — retired; its snippet annotations are the
security debt the retirement names. (b) Traefik, Kong, Moov — capable, and
each makes its own CRDs and policy vocabulary a chart dependency, so
portability costs a value per controller; as a GatewayClass implementation
each is a value swap. (c) LoadBalancer Services only — two browser-reachable
hosts (webapp, Keycloak) on one address needs host routing. (d) Istio —
a mesh sidecar model replaces the pinned-CA trust the components ship with
(ADR 039, DD-234) and adds a data plane to operate for a policy set already
implemented in nginx.

**Consequences.** A GatewayClass is a cluster prerequisite, installed by the
install script and named in the runbook (10.4). TLS terminates at the gateway
and the webapp→server hop stays TLS (DD-286's per-service certificates).
Routing stays coarse: one host to one service, because the webapp's `/api/`
and `/otel/` proxy is the tested data path (DD-142) — the gateway does not
duplicate it. Next free DD: 243.

### DD-286. TLS trust is cert-manager issuers; each pinned CA is a ConfigMap of the trust root

- **Status:** Accepted (the default issuer's shape superseded by
  [DD-259](#dd-259-the-chart-managed-trust-root-is-a-namespaced-self-signed-issuer-chain))
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** The umbrella owns the trust model: an issuer reference
(`global.issuerRef`, a self-signed `ClusterIssuer` by default, swappable for
ACME, a provider CA, or an existing chain) and one `Certificate` per
browser host and per in-cluster service, with the SAN sets the consumers
verify (service DNS names for internal hops, the host names for the edge).
The CA every consumer pins by file — `ELASTICSEARCH_CA_CERTS`, nginx
`proxy_ssl_trusted_certificate`, `AUTH_CA_FILE`, `OTEL_*_CA_FILE`, the store's
`tls/ca.pem` — is supplied as a ConfigMap of the issuer's CA, mounted at the
path the chart names, through a helper in `atlas-common`.

**Reason.** ADR 039 declares TLS at every hop and the components enforce it:
the server refuses to start without key, cert, and CA (SRV-06, DD-234), and
nginx, Keycloak, Elasticsearch, and the collector each pin a CA file. So the
chart must deliver files, not secrets alone. cert-manager is the one mechanism
that produces a leaf and its `ca.crt` on every cluster, minikube included
(R1, R6), with rotation built in. The dev CA cannot travel: `tools/tls/certgen.sh`
is mkcert-root based, mode-644 keys, and its header forbids shipping `certs/`.

**Alternatives.** (a) Bring-your-own TLS secrets — the chart stays dumb and
every environment hand-produces eight leaf certificates with eight SAN sets and
renews them by hand; R6's failure is that no test catches a wrong SAN.
(b) SPIFFE or mesh-issued identities — a third identity system beside Keycloak
and the `otel-*` client credentials (ADR 007, ADR 013). (c) Plaintext in-cluster
hop-by-hop — refused by ADR 039: a declared arrangement, not an assumed property.

**Consequences.** cert-manager is a prerequisite of every cluster (install
script, runbook). Consumers that read the CA at boot (Elasticsearch, Keycloak)
need a restart hook when the CA rotates — recorded for 10.2/10.3. A private
root is the default, so the cluster's trust set is closed and enumerable;
swapping `issuerRef` to ACME changes the browser certificates only, because
internal consumers pin the internal issuer's CA. Next free DD: 244.

### DD-287. The umbrella owns shared secrets, generated at install and preserved on upgrade

- **Status:** Accepted
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** Every credential the system needs at runtime is produced by one
umbrella template from one `secrets.*` values block and written as plain
`Secret`s, one per consumer: the store's `elastic` password, Keycloak's
bootstrap admin and database credentials, the `otel-*` client secret the realm
shares, the two demo users, and the collector's legacy-leg token. A value
supplied in values wins; a value absent is generated (`randAlphaNum`) and
**preserved across upgrades** by reading the live Secret (`lookup`) before
generating. The webapp's ingest token is the legacy-leg token, documented as
browser-reachable — a public ingest endpoint's constant, not a confidential
credential.

**Reason.** R5 (no secret in the artifact) and R6 (a fresh minikube install
with no prepared secrets must reach a running system). The preserve step is
not decoration: regenerating the store's password on upgrade bricks the system
of record, and the first install of a generated secret is the only moment the
value exists. That the browser leg's token is public follows from DD-239 — the
edge exports on the legacy leg from the browser's request path, so the value
travels where an attacker with a page load can read it; the honest model is an
OTLP ingest DSN, and the audit trail is the OIDC legs (7.17/7.18).

**Alternatives.** (a) The repo's SOPS `.env.enc` — those files are per-project
dev defaults readable by every developer's age key (ADR 008); production
credentials in them inherit that audience. (b) External Secrets Operator or a
cloud secret manager — the right answer for a deployment that runs one, so the
chart consumes plain `Secret` names and leaves the door open (option in the
runbook, 10.4) rather than binding the chart to a backend. (c) helm-secrets /
sops in the operator's path — adds a CLI and an age-key distribution problem
to the install.

**Consequences.** `helm uninstall` deletes the credentials, so the runbook
names the backup duty with ADR 026/028 and the rotation procedure (10.4);
retrieval is `kubectl get secret -o jsonpath`. Talisman and pre-commit see no
secrets because none are committed. A deployment that wants per-environment
secrets in its own store sets them in values and gets the same preservation.
Next free DD: 245.

### DD-288. The umbrella pins its component charts to its own version; chart version equals release version

- **Status:** Accepted
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** Every chart's `version` is the release's semver and its
`appVersion` the image tag. The umbrella's `dependencies` pin each component
chart to `=` its own version and resolve them from the OCI repository, so
`helm install aurelius-atlas` on a deployment's machine pulls exactly the set
CI tested. `publish.yaml` publishes subcharts before the umbrella.

**Reason.** ADR 019's one number must name a shippable combination, and CHT-07
is the chart half of that promise: a range (`>=1.2.0`) resolves to "the newest
of each", which is a combination no pipeline ever ran. Pin-equal makes mixing
impossible and makes the release the unit of deployment, the same argument
that gives the images one tag.

**Alternatives.** (a) Caret/range pins — the drift generator this decision
exists to refuse. (b) `file://` dependencies only — the umbrella would carry
tarballs and a component chart could not be installed standalone from the
registry (a deployment standing up Keycloak alone for a staging test).
(c) Independent chart versioning — a chart fix ships without a release, so
"the release" stops naming what runs; R2's failure, and the one ADR 019
forbids.

**Consequences.** Charts join the release group, so Nx release bumps them with
the rest (DD-284); a chart-only fix costs a release — the deliberate price of
R2, and the same price the images already pay. Development installs can use
the local tree (umbrella `file://` dependencies behind a values switch) so
chart hacking needs no publish; publish ordering is subcharts → umbrella,
checked by the verify step 10.4 adds. Next free DD: 246.

### DD-289. The chart gate renders each chart's own values files; the release refreshes Chart.lock

- **Status:** Accepted
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** `helm-template` renders a chart once per values file it ships —
`tests/values.test.yaml` and each `environments/*.yaml` overlay — as separate
`helm template` invocations, never as one stacked command. The chart
projects' `afterAllProjectsVersioned` refreshes the umbrella's `Chart.lock`
with `helm dep update` after a release writes the new versions.

**Reason.** Stacked (`-f a.yaml -f b.yaml`) renders only the umbrella's
combination; a component chart's own overlay pair (test values + environment)
is a combination no deployment runs, and stacking every chart's files in one
command hides which file breaks. Separate renders name the failing file. The
lock refresh exists because `Chart.lock` records the resolved dependency
versions and a digest over them: a release that bumps the component charts
leaves it stale, and only helm computes the digest — the tree is flushed to
disk by the time the hook runs, so `helm dep update` is the only writer that
can produce a valid lock.

**Alternatives.** (a) One stacked render — fails the naming-the-file goal and
makes a component chart's CI green without its own contract ever rendering.
(b) Gitignore `Chart.lock` — helm's own contract wants the lock committed
(`helm dep build` verifies against it); an unlocked install resolves
dependencies at install time, which is DD-288's drift generator re-opened.
(c) A `helm-lock` Nx target — a release-time action, not a developer one; the
version-actions hook fires exactly when the lock goes stale.

**Consequences.** The gate's task count grows with the values files a chart
ships (20 tasks for 11 charts today); every chart that gains an overlay gains
a render. The lock refresh runs in `nx release version` only (a dry run
skips it, and the `--dry-run` flag's tree is empty), so the version commit
carries a valid lock. The plugin's target command is generated at graph-build
time from the files on disk — adding an overlay changes the task's command,
which is a cache miss. Next free DD: 247.

### DD-290. Component charts live next to their projects; helpers are chart-local

- **Status:** Accepted (supersedes DD-283's `charts/` residence; its
  one-chart-per-component split, the umbrella, and the OCI publish stand;
  the umbrella's `charts/` residence is superseded by DD-292)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** Each component chart lives in a `helm/` directory inside the
project it deploys — `apps/<app>/helm/` for the five apps,
`dev/<name>/helm/` for the three infrastructure components. `charts/` keeps
the umbrella `aurelius-atlas` only: it is the one chart with no owning
project. The two library charts (`atlas-common`, `atlas-aux-api`) are
deleted: their helpers are expanded into each chart's own
`templates/_helpers.tpl` and template files, keeping the naming convention
(`<chart>.fullname`, `<chart>.labels`, …). The umbrella reaches its
components through `file://../../apps/…/helm` dependencies; names, pins
(CHT-07), and OCI artifacts are unchanged.

**Reason.** The chart's owner is the project's owner: a change to a
component's ports, settings env, or probes rides the same PR as the code it
deploys, and the PR's diff shows the blast radius (workload + chart) in one
place. A library chart is a component with no runtime — nothing runs it,
nothing deploys it, and every consumer sits in the same repo — the
artificial-abstraction shape this workspace's module rule rejects. 10.1's
gate measured the shared surface as small (mostly `required:` guards), so
the copies are cheap; DD-283's "chart-to-chart edges in one place" is the
umbrella's `Chart.yaml` (the single join) plus the naming convention. The
Nx plugin infers targets from a `**/Chart.yaml` glob, so the move is a
tooling non-event — zero plugin changes.

**Alternatives.** (a) Keep the `charts/` tree (DD-283) — the ownership map
lives only in docs, and contributors must know to visit a sibling tree.
(b) Keep `atlas-common` as the only library — the shared helpers stay
shared, at the cost of every chart depending on a project that runs
nothing; the convention dedupes what a library would share.
(c) Name the directory `chart/` — `helm/` is unambiguous (the Helm
convention, parallel to `docker/`-style folders) and reads as the deploy
toolchain of the project.

**Consequences.** Each owning project's `AGENTS.md` documents its chart
(layout bullet + a Helm-chart section); `charts/AGENTS.md` covers the
umbrella and the shared conventions/gotchas. Component charts are
dependency-free, so their `Chart.lock` files are gone; the umbrella's lock
regenerates with 8 entries. The prettier/check-yaml template excludes and
the gitignore dependency-tarball rules widen from `charts/*/…` to
`**/helm/…`. The gate keeps its task count (the libraries contributed two
lint tasks). The aux-API deployment/service shape now exists three times
(verified byte-identical at the copy); the three charts may drift on
purpose — the convention, not code, is the dedupe. Next free DD: 248.

### DD-291. The Chart.yaml is the chart's whole Nx identity; no chart project.json

- **Status:** Superseded by DD-293 (the no-`project.json` rule and the
  everything-from-`Chart.yaml` rule stand; the separate `<chart>-chart` PROJECT
  — the plugin's `name` field — does not)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** A chart ships no `project.json`. The helm plugin reads
everything it needs from `Chart.yaml` itself: the project **name**
(`<chart>-chart`, from the `name:` field — the same name Helm gives the
packaged artifact), `projectType: application`, the `helm` tag, the release
`versionActions`, and — for the umbrella — the `implicitDependencies` that
drive `helm-publish`'s cascade, derived from the `dependencies:` block.
DD-284's inference claim becomes literally true: the chart directory is
`Chart.yaml`, `values.yaml`, `templates/`, `tests/`, and nothing else.

**Reason.** The `project.json` files existed only to carry four fields the
plugin could derive, and each was a second statement of a fact `Chart.yaml`
already states: the chart name (`name:` = the artifact name = the project
name base), the dependency edges (the umbrella's `dependencies:` = the
cascade graph = the CHT-07 pins). Two sources of one fact is the drift the
conversion workflow bans. The naming suffix is load-bearing, not cosmetic:
without it, nine folders all named `helm` would derive colliding project
names, and the release's pin lookup (`<project>-chart → chart name`) needs
the mapping — deriving it from `Chart.yaml name:` keeps chart and project
names equal by construction.

**Alternatives.** (a) Keep the nine `project.json` files — nine manifests
echoing facts the manifest of record already carries (DD-284's own
rejected alternative (b)). (b) Folder-derived project names
(`apps-aurelius-atlas-server-helm`) — stable but verbose, collides on plain
`helm` folders, and breaks the `<chart>-chart` naming the CI invocations,
docs, and the release pin lookup use. (c) Name the projects from the
owning app (`aurelius-atlas-server`) — the chart is a distinct artifact
with its own version and OCI repository; the `-chart` suffix keeps the
image project and the chart project addressable apart.

**Consequences.** Adding a chart is files only: `Chart.yaml` + values +
templates + test values (+ the umbrella's dependency row) — nothing to
register. Removing a slice removes one file fewer. The plugin gained two
small line-parsers (`name:`, `dependencies[].name`) in
chart-yaml-version-actions.ts's no-YAML-library style; the umbrella's
dependency list is now load-bearing for the publish cascade as well as for
install. Next free DD: 249.

### DD-292. The umbrella sits at the workspace root: `helm/`

- **Status:** Accepted (supersedes DD-290's clause that the umbrella is the
  only resident of `charts/`; the component-chart placement and the
  no-library-charts rule stand, and DD-283 is superseded the same way)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** The umbrella chart `aurelius-atlas` lives in `helm/` at the
workspace root; the `charts/` directory is gone. The chart tree is now one
shape: every chart in the repo is a `helm/` directory — the component charts
next to their projects (DD-290), the umbrella at the root. The umbrella's
`file://` dependencies shorten one level (`file://../apps/<app>/helm`), and
its lock is `helm/Chart.lock`.

**Reason.** DD-290 moved every component chart to its owner; the umbrella
has no owning project — it deploys the whole system — so its place is the
root. It also completes the naming convention: the chart is the Helm
toolchain of "the workspace project", exactly as `apps/<app>/helm/` is of
an app. A single-chart directory named `charts/` (plural, one entry) was a
vestige of the tree DD-290 dismantled.

**Alternatives.** (a) Keep `charts/aurelius-atlas/` — DD-290's rationale
applied verbatim: an owning scope exists (the workspace), the folder is
just `helm/` at root, and the residual `charts/` tree exists only for the
umbrella. (b) `helm/aurelius-atlas/` (chart name inside the root dir) —
one directory deeper than needed; a chart directory is one chart, and
`helm/` at root already says whose.

**Consequences.** The plugin needs zero changes (the `**/Chart.yaml` glob
finds the root chart; the Nx project root becomes `helm`). The release
lock-refresh hook targets `helm/Chart.lock`. The prettier/check-yaml/
gitignore patterns converge on `**/helm/{templates,charts}/` — the
`charts/aurelius-atlas/...` special cases are deleted, not widened. The
`.helmignore-shared` template moves to `helm/.helmignore-shared`. Next
free DD: 250.

### DD-293. Helm targets merge onto the owning project: a chart is not a project

- **Status:** Accepted (supersedes DD-284 and DD-291: the plugin's inference
  and the no-`project.json` rule stand, the separate `<chart>-chart` projects
  do not)
- **Increment:** 10.1
- **Date:** 2026-10-28

**Decision.** The helm plugin keys its `createNodes` result at the chart's
OWNER root — the chart dir's parent (`apps/<app>/helm` → `apps/<app>`; the
root `helm` → `.`) — so Nx shallow-merges `helm-lint`/`helm-template`/
`helm-publish` and the `helm` tag onto the existing project node. No `*-chart`
project exists. The plugin sets no `name` (a node's name belongs to the first
plugin that claims its root, helm runs before the ecosystem plugins, and
naming here would rename the owner) and no `projectType`. The umbrella's
dependency edges become `implicitDependencies` on the OWNING projects,
resolved by following each `dependencies[]` `repository: file://` path to the
chart dir and reading the owner's name (project.json, pyproject.toml,
package.json). Release: every chart owner points `release.version.versionActions`
at the composite module (`tools/plugins/chart-yaml-version-actions.ts`), which
versions the owner's ecosystem manifest AND its `helm/Chart.yaml`, re-pins the
umbrella (dependency entries are looked up through the owner name), and
refreshes `helm/Chart.lock` — wired from `python.ts` for the uv projects
(which overwrites the plugin's same-valued field), from `project.json` for the
dev charts, from the plugin at the root project.

**Reason.** The nine `*-chart` projects were graph noise: one chart per
project already (DD-290), so the chart project and the app project share a
root, a release bump, a CI run, and an owner. A chart change touched two graph
nodes; `nx affected -t helm-lint` listed a project no one navigates to, and
each app's target list carried `helm-*` beside its own `build`/`test` under a
name no one types. Merging by parent root is Nx's documented merge (a
same-root inference result adds targets to the existing node), the
project.json-override layer is untouched, and CI is target-based (`affected
-t helm-lint helm-template`, `run-many -t helm-publish`) so it sees no change.
The chart tree, the CHT rules, the pin-equal release (DD-288), and the OCI
artifact are untouched — only the graph shape.

**Alternatives.** (a) Keep the chart projects (DD-284/DD-291) — a stable name
per artifact, addressable apart from the image; paid in graph noise and split
`affected` output. (b) Folder-derived owner names — not available: `name` is
first-plugin-wins, helm runs early, and the plugin has no project-name map in
the v1 context; the parent's name comes from its own manifests, read the same
way the release's pin lookup reads them. (c) Keep the chart projects and alias
them in `nx.json` — an artificial abstraction the tree rejects (DD-290).

**Consequences.** Release needed a composite: chart version writes, umbrella
pin refresh, and the lock hook all lived on the chart projects' version-actions
and now run on the owners' — the composite extends `@nxlv/python`'s actions for
pyproject owners, treats `Chart.yaml` as the manifest for chart-only owners,
and maps umbrella pins by owner name through the `repository:` paths (the
dependency parser reads entries, not line-adjacent pairs, so a `repository:`
after `version:` resolves). The `-chart` suffix and its pin-lookup convention
are gone — the chart name lives only in `Chart.yaml`/`repository:`. `npx nx
show project aurelius-atlas-server` lists the chart targets. The release
dry-run keeps its shape: 9 Chart.yaml writes + 8 umbrella pin updates. Docs'
per-chart commands become `npx nx run <owner>:helm-template`. The dev charts'
`project.json` swap noop actions for the composite (their chart is their
version manifest). Next free DD: 251.

### DD-294. The minikube trial findings in the aux charts land in 10.3

- **Status:** Accepted
- **Increment:** 10.1 (trial) · fixed in 10.3
- **Date:** 2026-10-28

**Decision.** A trial `helm install` of the umbrella on minikube (the three aux
APIs — the only real workloads 10.1 ships — with locally built images and
self-signed `kubernetes.io/tls` Secrets) surfaced two defects in the aux
charts' rendered Deployments. Neither is fixed in 10.1; both are scheduled
into 10.3, where the app charts get their real workload wiring:

1. **The CA file has no backing store.** The aux charts' default settings env
   points `AUTH_CA_FILE`/`OTEL_CA_FILE` at `/etc/aurelius-atlas/tls/ca.crt`,
   but the TLS volume mounts only a `kubernetes.io/tls` Secret — which carries
   only `tls.crt`/`tls.key` — so a spec-conformant install crash-loops at boot
   on pydantic's `path_not_file`. The `tls.caConfigMap`/`tls.caPath` values the
   charts already declare are dead: the Deployment template never reads them.
   10.3 wires the mount for real — cert-manager issues each service's
   Certificate from the self-signed ClusterIssuer (DD-286) and the issuer's
   `ca.crt` reaches the pod through the declared CA value (Secret or
   ConfigMap), and the settings default and the mount become consistent.
2. **lineage-model cannot boot its own defaults.** `atlas_base_url` and
   `data2model_url` are required settings with no defaults, and the chart
   renders neither, so the rendered Deployment always fails validation. 10.3
   sets them from the in-cluster joins (`https://<server-svc>:21000/`,
   `https://<data2model-svc>:21001/` — the sibling Service the same chart
   renders), the same increment that wires the OTEL endpoints the values
   comments already promise.

**Reason.** 10.1's stated boundary is the foundation: charts render, lint,
version, and publish, and the acceptance gate is render-level (CHT-06). Both
fixes are workload-wiring changes — a trust mount and a settings join — and
the trial shows the aux charts were skipped over by the render gate exactly
where 10.3's scope line already says they get filled in (the three auxiliary
APIs, CHT-20..34). Fixing them under 10.1 would land half the trust model
(no cert-manager yet) and duplicate 10.3's edits.

**Alternatives.** (a) Fix the CA mount now with a plain-Secret `ca.crt` key —
wrong shape: the real CA arrives with cert-manager in 10.3/10.4 and the key
would be re-plumbed. (b) Give the lineage-model settings chart defaults —
wrong owner: those URLs are deployment joins like `AUTH_SERVER_URL`, not
component constants, and deriving them in-chart before the server chart has a
Service (10.3) would be guesswork.

**Consequences.** 10.3's spec must carry both as rules (CA mount for every TLS
app; lineage-model upstream URLs) with render assertions, and its minikube
install must boot the aux Deployments with no out-of-band values — the
`/tmp`-style overrides this trial needed (an extra `ca.crt` in the TLS Secret,
an `extraEnv` file for the two URLs) are the acceptance test's negative space.
The trial itself passed otherwise: install/upgrade reached `deployed`, all
three rollouts went Ready on the HTTPS `/liveness` probes, and the derived
`AUTH_SERVER_URL` matched the overlay domain. Next free DD: 252.

### DD-295. Chart-track id collisions with main renumber above both ranges

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the rebase of the 10.x chart
  track onto the 4.3–6.1 merges, PRs #157–#191)
- **Date:** 2026-11-01

**Decision.** The 4.3–6.1 track on main (DSL, lineage, glossaries, auth) and
the 10.x chart track branched at DD-239/DV-87 and minted ids in parallel:
main took DD-240..251 and DV-88..109, the chart track took DD-240..252 (12
colliding ids — the same numbers, different decisions) plus DV-88/89 in its
10.7/10.8 increments, its children continuing at DD-253..282. The rebase
renumbers the **chart side of the collision**: DD-240..251 → DD-283..294 in
ascending order, and DV-88/89 → DV-112/113 — and this entry (DD-295) records
it. Main's ids keep their numbers. The chart track's DD-252..282 already sit
above both ranges and are untouched; the 10.1 chain citation `DD-240..252`
becomes the explicit list `DD-298, DD-283..294`. The citation sweep rewrote
every chart spec, doc, chart template, plugin comment, CI workflow, and test
on the chart side; DD-177 is the precedent for the method.

**Reason.** Main's 4.3–6.1 decisions are merged and cited by merged code —
they are the accepted record, and the ledger's rule (numbers are never reused,
accepted entries are never edited) protects them. The chart track is the
in-progress side of the same ledger, so it is the side allowed to move;
moving 12+2 ids in one mechanical, reviewable sweep costs less than living
with ids that mean two things. The new range starts above the chart track's
own DD-282, so the track's later ids keep their citations.

**Consequences.** The rebase of the chart chain onto main is conflict-free
for the id ledger: the two tracks occupy disjoint ranges. Every pre-rebase
commit message cites the OLD numbers — commit history is not rewritten
further, and this appendix is the lookup from a commit's citation to the
merged record.

| Old    | New    | Old    | New    | Old    | New    |
| ------ | ------ | ------ | ------ | ------ | ------ |
| DD-240 | DD-283 | DD-245 | DD-288 | DD-250 | DD-293 |
| DD-241 | DD-284 | DD-246 | DD-289 | DD-251 | DD-294 |
| DD-242 | DD-285 | DD-247 | DD-290 | DV-88  | DV-112 |
| DD-243 | DD-286 | DD-248 | DD-291 | DV-89  | DV-113 |
| DD-244 | DD-287 | DD-249 | DD-292 | —      | —      |

**Addendum (2026-11-01, this merge).** 4.5 (#194) then minted main’s `DD-252`
and `DV-110`, so ids this entry left in place collided: they move to `DD-298`
and `DV-112`, and the paired `DV-111` shifts with it to `DV-113` — one sweep,
same rule. Chart `DD-252` → `DD-298`, `DV-110/111` → `DV-112/113`; main keeps
`DD-252` and `DV-110`.

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

### DD-298. A stuck pending-install release is cleared by uninstall

- **Status:** Accepted
- **Increment:** 10.1 (trial)
- **Date:** 2026-10-28

**Decision.** The runbook's install/upgrade sections warn: `helm install
--wait` (or `--atomic`) against a workload that never reaches Ready — a
crash-loop, a missing Secret — burns the full `--timeout` and leaves the
release `pending-install`; every later `helm upgrade` then fails with
"another operation (install/upgrade/rollback) is in progress" until `helm
uninstall` clears it. Fix the cause, inspect with `helm history`, and
uninstall rather than waiting the release out.

**Reason.** Observed twice in the trial of DD-294: the first install timed out
on the crash-looping aux pods and the stuck release blocked the fix-and-retry
path with a confusing error unrelated to the actual defect. It is helm's
documented behaviour, not a chart bug, so it belongs in the runbook, and
mid-roadmap installs (subcharts that render no workloads yet, workloads whose
wiring lands in a later increment) are exactly when an operator meets it.

**Consequences.** The runbook gains the note and the `helm history` /
`helm uninstall` recovery lines; 10.5's install script scripts the recovery
(guard the wait with a pre-flight, or clean up on timeout) rather than
discovering it again. Next free DD: 253.

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

## Moved entries

The entries moved next to the increment they record. The record is the truth; the status
here is a copy of the one at the time of the move. New entries go to the increment's
`design.md`, never here.

| #      | Decision                                                                                                           | Status           | Design record                                                                          |
| ------ | ------------------------------------------------------------------------------------------------------------------ | ---------------- | -------------------------------------------------------------------------------------- |
| DD-001 | Reference is Apache Atlas 2.4.0, and both dashboards are served                                                    | Accepted         | `specs/0-1-adopt-template/design.md`                                                   |
| DD-002 | Atlas code lives in aurelius-atlas projects split by layer                                                         | Accepted         | `specs/0-1-adopt-template/design.md`                                                   |
| DD-003 | Template projects are renamed to the aurelius-atlas prefix                                                         | Accepted         | `specs/0-1-adopt-template/design.md`                                                   |
| DD-004 | The SPA keeps tokens in memory and renews them silently                                                            | Accepted         | `specs/0-1-adopt-template/design.md`                                                   |
| DD-005 | The store uses the official async Elasticsearch client                                                             | Proposed         | `libs/python/aurelius-atlas-store-es/specs/0-2-elasticsearch-infrastructure/design.md` |
| DD-006 | Development and tests run Elasticsearch with security on                                                           | Proposed         | `dev/elasticsearch/specs/0-2-elasticsearch-infrastructure/design.md`                   |
| DD-007 | The Elasticsearch test fixture ships with the store library                                                        | Proposed         | `libs/python/aurelius-atlas-store-es/specs/0-2-elasticsearch-infrastructure/design.md` |
| DD-008 | A yellow cluster is healthy                                                                                        | Proposed         | `libs/python/aurelius-atlas-store-es/specs/0-2-elasticsearch-infrastructure/design.md` |
| DD-009 | Traceability is checked from collected markers, not from a test run                                                | Proposed         | `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`        |
| DD-010 | The traceability check covers Atlas code from increment 0.2 on                                                     | Proposed         | `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`        |
| DD-011 | The test report is generated from JUnit, coverage and trace files                                                  | Proposed         | `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`        |
| DD-012 | Parity scenarios are YAML files run as parametrised pytest tests                                                   | Proposed         | `libs/python/aurelius-atlas-parity/specs/0-4-parity-harness/design.md`                 |
| DD-013 | A scenario response is compared exactly, except at declared paths                                                  | Proposed         | `libs/python/aurelius-atlas-parity/specs/0-4-parity-harness/design.md`                 |
| DD-014 | Scenario facts reach the report as test properties                                                                 | Proposed         | `libs/python/aurelius-atlas-trace/specs/0-4-parity-harness/design.md`                  |
| DD-015 | The server is a FastAPI application with one router per Atlas resource                                             | Proposed         | `apps/aurelius-atlas-server/specs/0-5-server-skeleton/design.md`                       |
| DD-016 | The server does not start without its store                                                                        | Proposed         | `apps/aurelius-atlas-server/specs/0-5-server-skeleton/design.md`                       |
| DD-017 | The dashboards are vendored unchanged and built with dart-sass on Node 24                                          | Proposed         | `apps/aurelius-atlas-dashboard/specs/0-6-dashboards/design.md`                         |
| DD-018 | The server serves the dashboards from the API's origin                                                             | Proposed         | `apps/aurelius-atlas-server/specs/0-6-dashboards/design.md`                            |
| DD-019 | The template examples stay until the plan is done                                                                  | Proposed         | `apps/aurelius-atlas-server/specs/0-6-dashboards/design.md`                            |
| DD-020 | Typedef models are Pydantic models that read and write Atlas's JSON                                                | Proposed         | `libs/python/aurelius-atlas-model/specs/1-1-typedef-models/design.md`                  |
| DD-021 | Set-valued fields keep each name once, in first-seen order                                                         | Proposed         | `libs/python/aurelius-atlas-model/specs/1-1-typedef-models/design.md`                  |
| DD-022 | Typedef timestamps are aware datetimes, written as epoch milliseconds                                              | Proposed         | `libs/python/aurelius-atlas-model/specs/1-1-typedef-models/design.md`                  |
| DD-023 | Atlas errors live in the model library                                                                             | Proposed         | `libs/python/aurelius-atlas-typesystem/specs/1-2-type-registry/design.md`              |
| DD-024 | The registry is updated on a transient copy under a re-entrant lock                                                | Proposed         | `libs/python/aurelius-atlas-typesystem/specs/1-2-type-registry/design.md`              |
| DD-025 | The type system ports the definition side only                                                                     | Proposed         | `libs/python/aurelius-atlas-typesystem/specs/1-2-type-registry/design.md`              |
| DD-026 | Dynamic attributes and search lookups wait for their increments                                                    | Proposed         | `libs/python/aurelius-atlas-typesystem/specs/1-3-type-hierarchies/design.md`           |
| DD-027 | Derived type sets keep first-seen order                                                                            | Proposed         | `libs/python/aurelius-atlas-typesystem/specs/1-3-type-hierarchies/design.md`           |
| DD-028 | The type definitions are one Elasticsearch document                                                                | Proposed         | `libs/python/aurelius-atlas-core/specs/1-4-typedef-store/design.md`                    |
| DD-029 | Server processes share the type definitions through the document's version                                         | Proposed         | `libs/python/aurelius-atlas-core/specs/1-4-typedef-store/design.md`                    |
| DD-030 | The store asks the entity store whether a type is in use                                                           | Proposed         | `libs/python/aurelius-atlas-core/specs/1-4-typedef-store/design.md`                    |
| DD-031 | The patch records live in the typedef document                                                                     | Proposed         | `libs/python/aurelius-atlas-core/specs/1-5-builtin-models/design.md`                   |
| DD-032 | The built-in models are vendored unchanged and read from a directory                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/1-5-builtin-models/design.md`                   |
| DD-033 | Start-up loading is one change per model file and per patch                                                        | Proposed         | `libs/python/aurelius-atlas-core/specs/1-5-builtin-models/design.md`                   |
| DD-034 | Lists of type definitions are sorted by name                                                                       | Proposed         | `apps/aurelius-atlas-server/specs/1-6-types-rest/design.md`                            |
| DD-035 | Type scenarios create what they read and delete it at their end                                                    | Proposed         | `apps/aurelius-atlas-server/specs/1-6-types-rest/design.md`                            |
| DD-036 | Start-up loading tries a raced change again                                                                        | Proposed         | `apps/aurelius-atlas-server/specs/1-6-types-rest/design.md`                            |
| DD-037 | Instance models are one module per Java class                                                                      | Proposed         | `libs/python/aurelius-atlas-model/specs/2-1-entity-models/design.md`                   |
| DD-038 | Attribute values stay plain JSON values until their types read them                                                | Proposed         | `libs/python/aurelius-atlas-model/specs/2-1-entity-models/design.md`                   |
| DD-039 | One Atlas JSON codec reads floats as decimals and writes them with their digits                                    | Proposed         | `libs/python/aurelius-atlas-model/specs/2-1-value-types/design.md`                     |
| DD-040 | Java values are held as the Python values closest to them                                                          | Proposed         | `libs/python/aurelius-atlas-typesystem/specs/2-1-value-types/design.md`                |
| DD-041 | The type system is one module per Java type class too                                                              | Proposed         | `libs/python/aurelius-atlas-typesystem/specs/2-1-value-types/design.md`                |
| DD-042 | A validity period without a time zone is in UTC                                                                    | Proposed         | `libs/python/aurelius-atlas-typesystem/specs/2-1-value-types/design.md`                |
| DD-043 | Entities are documents of one index, their attributes under qualified names                                        | Proposed         | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md`                     |
| DD-044 | A GUID is a random UUID                                                                                            | Proposed         | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md`                     |
| DD-045 | Unique values are reserved by create-only documents                                                                | Proposed         | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md`                     |
| DD-046 | A multi-entity write is all or nothing, through a journal                                                          | Proposed         | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md`                     |
| DD-047 | Entities are written conditionally on their Elasticsearch version                                                  | Proposed         | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md`                     |
| DD-048 | A type is in use while the entity index holds one of it                                                            | Proposed         | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md`                     |
| DD-049 | Attribute values are stored normalised; a struct inline, a reference as a GUID                                     | Proposed         | `apps/aurelius-atlas-server/specs/2-3-entity-read-rest/design.md`                      |
| DD-050 | Relationship attributes read empty until relationships are stored                                                  | Superseded by DD | `apps/aurelius-atlas-server/specs/2-3-entity-read-rest/design.md`                      |
| DD-051 | Entity reads are tested on entities written through the store until 2.4                                            | Proposed         | `apps/aurelius-atlas-server/specs/2-3-entity-read-rest/design.md`                      |
| DD-052 | A request is mapped in memory and written once; a lost race runs it again                                          | Proposed         | `apps/aurelius-atlas-server/specs/2-4-entity-write-rest/design.md`                     |
| DD-053 | Relationship attribute values are resolved, but stored only as legacy attributes until 3.1                         | Superseded by DD | `apps/aurelius-atlas-server/specs/2-4-entity-write-rest/design.md`                     |
| DD-054 | Dynamic attributes are evaluated in first-seen dependency order                                                    | Proposed         | `apps/aurelius-atlas-server/specs/2-4-entity-write-rest/design.md`                     |
| DD-055 | Scenarios name what they create with a per-run value                                                               | Proposed         | `apps/aurelius-atlas-server/specs/2-4-entity-write-rest/design.md`                     |
| DD-056 | An entity write also removes documents, journaled like the others                                                  | Proposed         | `libs/python/aurelius-atlas-core/specs/2-5-delete-semantics/design.md`                 |
| DD-057 | Entities referring to one are found through an indexed field of GUIDs                                              | Proposed         | `libs/python/aurelius-atlas-core/specs/2-5-delete-semantics/design.md`                 |
| DD-058 | A stored reference stands for an edge: active for a delete, deleted for a purge                                    | Proposed         | `libs/python/aurelius-atlas-core/specs/2-5-delete-semantics/design.md`                 |
| DD-059 | The delete type and its override are server settings                                                               | Proposed         | `apps/aurelius-atlas-server/specs/2-5-delete-semantics/design.md`                      |
| DD-060 | The owned-reference cascade moves from 3.2 to 2.5                                                                  | Proposed         | `libs/python/aurelius-atlas-core/specs/2-5-delete-semantics/design.md`                 |
| DD-061 | Relationships are documents of their own index, listed by both ends                                                | Proposed         | `libs/python/aurelius-atlas-core/specs/3-1-relationship-instances/design.md`           |
| DD-062 | An entity write also writes relationships, all or nothing                                                          | Proposed         | `libs/python/aurelius-atlas-core/specs/3-1-relationship-instances/design.md`           |
| DD-063 | 3.1 is split into relationship instances and relationship attributes                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/3-1-relationship-instances/design.md`           |
| DD-064 | Relationship attribute values are relationships                                                                    | Proposed         | `libs/python/aurelius-atlas-core/specs/3-1-relationship-attributes/design.md`          |
| DD-065 | A relationship keeps one array index, the last writer's                                                            | Proposed         | `libs/python/aurelius-atlas-core/specs/3-1-relationship-attributes/design.md`          |
| DD-066 | Relationship attributes are mapped in memory and written with the entities                                         | Proposed         | `libs/python/aurelius-atlas-core/specs/3-1-relationship-attributes/design.md`          |
| DD-067 | Delete cascades follow owned relationships from 3.1b                                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/3-1-relationship-attributes/design.md`          |
| DD-068 | Owned entities an update drops are deleted through a view of the request                                           | Proposed         | `libs/python/aurelius-atlas-core/specs/3-2-ownership-cascades/design.md`               |
| DD-069 | A reference to a deleted entity stands for a deleted edge when reviving                                            | Proposed         | `libs/python/aurelius-atlas-core/specs/3-2-ownership-cascades/design.md`               |
| DD-070 | Classification instances are documents of their own index, listed by their entity                                  | Proposed         | `libs/python/aurelius-atlas-core/specs/3-3-direct-classifications/design.md`           |
| DD-071 | An entity write also writes classification instances, all or nothing                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/3-3-direct-classifications/design.md`           |
| DD-072 | The propagation defaults are Atlas's defaults                                                                      | Proposed         | `libs/python/aurelius-atlas-core/specs/3-3-direct-classifications/design.md`           |
| DD-073 | 3.3 is split into direct classifications and the bulk associator                                                   | Proposed         | `libs/python/aurelius-atlas-core/specs/3-3-direct-classifications/design.md`           |
| DD-074 | `bulk/headers` moves to 3.5                                                                                        | Proposed         | `libs/python/aurelius-atlas-core/specs/3-3-bulk-classifications/design.md`             |
| DD-075 | A propagated classification is listed by the entities it reaches                                                   | Proposed         | `libs/python/aurelius-atlas-core/specs/3-4-classification-propagation/design.md`       |
| DD-076 | The entities a classification reached are found through an indexed field                                           | Proposed         | `libs/python/aurelius-atlas-core/specs/3-4-classification-propagation/design.md`       |
| DD-077 | Propagation runs within the request until 3.4b                                                                     | Proposed         | `libs/python/aurelius-atlas-core/specs/3-4-classification-propagation/design.md`       |
| DD-078 | 3.4 is split into propagation and propagation tasks                                                                | Proposed         | `libs/python/aurelius-atlas-core/specs/3-4-classification-propagation/design.md`       |
| DD-079 | Tasks are documents of their own index, written with the change that records them                                  | Proposed         | `libs/python/aurelius-atlas-core/specs/3-4-propagation-tasks/design.md`                |
| DD-080 | Every server process runs tasks, each claimed with a lease                                                         | Proposed         | `libs/python/aurelius-atlas-core/specs/3-4-propagation-tasks/design.md`                |
| DD-081 | Tasks are enabled by a server setting, on by default                                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/3-4-propagation-tasks/design.md`                |
| DD-082 | Audit events are documents of their own index, written after the change                                            | Proposed         | `libs/python/aurelius-atlas-core/specs/3-5-entity-audit/design.md`                     |
| DD-083 | Audit events keep Atlas's event keys and their order                                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/3-5-entity-audit/design.md`                     |
| DD-084 | The entity writer tells a change notifier what it changed                                                          | Proposed         | `libs/python/aurelius-atlas-core/specs/3-5-entity-audit/design.md`                     |
| DD-085 | Classification events are collected in the request and recorded after its write                                    | Proposed         | `libs/python/aurelius-atlas-core/specs/3-5-classification-audit/design.md`             |
| DD-086 | Tag propagation records the propagations a request added and removed                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/3-5-classification-audit/design.md`             |
| DD-087 | Basic search is split into entity and classification search                                                        | Proposed         | `libs/python/aurelius-atlas-core/specs/4-1-entity-search/design.md`                    |
| DD-088 | Entity attributes are searched in typed search fields named after their defining type                              | Proposed         | `libs/python/aurelius-atlas-core/specs/4-1-entity-search/design.md`                    |
| DD-089 | A search is a query of the entity documents, ordered by creation when no sort is given                             | Proposed         | `libs/python/aurelius-atlas-core/specs/4-1-entity-search/design.md`                    |
| DD-090 | A classification search finds instances first, then the entities listing them                                      | Proposed         | `libs/python/aurelius-atlas-core/specs/4-1-classification-search/design.md`            |
| DD-091 | Free text is split from quick search                                                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/4-2-free-text/design.md`                        |
| DD-092 | String search fields carry an analysed text sub-field, searched with Atlas's weights                               | Proposed         | `libs/python/aurelius-atlas-core/specs/4-2-free-text/design.md`                        |
| DD-093 | Facets are aggregations of the search's own query                                                                  | Proposed         | `libs/python/aurelius-atlas-core/specs/4-2-quick-search/design.md`                     |
| DD-094 | Suggestions are terms aggregations of the text sub-fields                                                          | Proposed         | `libs/python/aurelius-atlas-core/specs/4-2-quick-search/design.md`                     |
| DD-126 | The webapp is a new project, not the Aurelius app upgraded in place                                                | Proposed         | `apps/aurelius-atlas-webapp/specs/7-0-webapp-foundation/design.md`                     |
| DD-127 | Signals replace the custom store; each slice owns its state                                                        | Proposed         | `apps/aurelius-atlas-webapp/specs/7-0-webapp-foundation/design.md`                     |
| DD-128 | Aurelius dictionaries become XLIFF, migrated whole, with the JSON as fixture                                       | Proposed         | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md`                          |
| DD-129 | Google Analytics and clickstream are dropped, not ported                                                           | Proposed         | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md`                          |
| DD-130 | The webapp's config is a typed AppConfig, and `environment.ts` is not ported                                       | Proposed         | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md`                          |
| DD-131 | Webapp purity is a checked gate, not a review convention                                                           | Proposed         | `apps/aurelius-atlas-webapp/specs/7-0-webapp-foundation/design.md`                     |
| DD-132 | The wildcard fallback redirects to the destination, not through the root                                           | Proposed         | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md`                          |
| DD-133 | Operational telemetry lands with 7.1; the auth wiring stays with 7.3                                               | Proposed         | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md`                          |
| DD-134 | The design-system slice ports the in-use components, not the library                                               | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md`                     |
| DD-135 | Component services dissolve into signal state; nothing is ported as a store                                        | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md`                     |
| DD-136 | Shared chrome strings are localisation units keyed by the legacy dictionary paths                                  | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md`                     |
| DD-137 | The purity gate is made executable over `libs/angular`                                                             | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md`                     |
| DD-138 | The Storybook preview loads `@angular/localize/init`                                                               | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md`                     |
| DD-139 | The client owns the base URL; the proxy forwards the prefix untouched                                              | Proposed         | `libs/angular/aurelius-atlas-data-access/specs/7-3-api-client-auth/design.md`          |
| DD-140 | The REST client ports the live surface; the search client is redesigned in 7.4                                     | Proposed         | `libs/angular/aurelius-atlas-data-access/specs/7-3-api-client-auth/design.md`          |
| DD-141 | Auth is guarded at the app root; the bearer token is stated inert until 6.1                                        | Proposed         | `apps/aurelius-atlas-webapp/specs/7-3-api-client-auth/design.md`                       |
| DD-142 | The webapp e2e stack runs the real Atlas server behind the proxy                                                   | Proposed         | `apps/aurelius-atlas-webapp/specs/7-3-api-client-auth/design.md`                       |
| DD-143 | The landing page is ported statically; search affordances and Shell chrome join the search slice                   | Proposed         | `apps/aurelius-atlas-webapp/specs/7-5-browse-landing/design.md`                        |
| DD-144 | i18n ids carry no description suffix; the bridge key must equal the extracted id                                   | Proposed         | `apps/aurelius-atlas-webapp/specs/7-5-browse-landing/design.md`                        |
| DD-145 | The Shell chrome is ported search-free; the root composes header and footer                                        | Proposed         | `apps/aurelius-atlas-webapp/specs/7-11-shell-chrome/design.md`                         |
| DD-146 | Session chrome injects the keycloak-js `Keycloak` instance, not keycloak-angular's `KeycloakService`               | Accepted         | `apps/aurelius-atlas-webapp/specs/7-11-shell-chrome/design.md`                         |
| DD-147 | Dev Keycloak users carry `default-roles-master` explicitly                                                         | Accepted         | `apps/aurelius-atlas-webapp/specs/7-11-shell-chrome/design.md`                         |
| DD-148 | The Aurelius brand lands on Bulma 1 tokens, light-forced, legacy metrics pinned                                    | Accepted         | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md`                |
| DD-149 | Critical-CSS inlining is off: the zoneless CSR app never swaps the print sheet                                     | Accepted         | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md`                |
| DD-150 | The sticky footer is the legacy rule verbatim; page content sits on Bulma's grid                                   | Accepted         | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md`                |
| DD-151 | The brand re-emits Bulma 0.9.4's text ramp, not just the body metrics                                              | Accepted         | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md`                |
| DD-152 | The accent ramp: primary stays Bulma teal, the accents take the Bootstrap map                                      | Proposed         | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md`                |
| DD-153 | The mobile burger chrome: grey burger, blended dropdowns, legacy logout anchor                                     | Proposed         | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md`                |
| DD-154 | The entity card emits `entityClicked`; the caller navigates                                                        | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-13-ui-components-details/design.md`            |
| DD-155 | The select is one field with a `searchRequested` output                                                            | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-13-ui-components-details/design.md`            |
| DD-156 | The brand ships a dark ink ramp on Bulma's dark hosts                                                              | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-13-ui-components-details/design.md`            |
| DD-157 | The drawer is a new ui-lib component, not a Modal or a dropdown                                                    | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-158 | The telemetry switch stops exports immediately and starts them on reload                                           | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-159 | The theme choice is applied pre-render; SHM-01's light pin is superseded by a light default                        | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-160 | Settings are a facade over one owner service per category                                                          | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-161 | Settings are browser-scoped localStorage; server-side persistence is the follow-up slice                           | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-162 | The drawer animates in and out; the layer's life is the exit animation's                                           | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-163 | The drawer styles itself with fallbacks; Bulma's modal tokens are `.modal`-scoped                                  | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-164 | The Appearance picker is the ui-lib Select; the Select gains `searchVisible`                                       | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-165 | About shows one version; the server is not fetched                                                                 | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-166 | The settings panel is a routed overlay in the `drawer` aux outlet                                                  | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-167 | Settings-drawer polish: lit gear, scheme-following band, Browser-default picker, `.label` headings                 | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-168 | The navbar follows the scheme: the dark slate band                                                                 | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-169 | Settings headings are the controls' accessible names                                                               | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-170 | The active locale is filled with the Aurelius blue                                                                 | Accepted         | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md`                       |
| DD-171 | The alerts store groups by a quiet window                                                                          | Accepted         | `apps/aurelius-atlas-webapp/specs/7-15-alerts-drawer/design.md`                        |
| DD-172 | The app's ErrorHandler chains: alert, then trace                                                                   | Accepted         | `apps/aurelius-atlas-webapp/specs/7-15-alerts-drawer/design.md`                        |
| DD-173 | The HTTP reporter: 5xx and network failures on /api                                                                | Accepted         | `apps/aurelius-atlas-webapp/specs/7-15-alerts-drawer/design.md`                        |
| DD-174 | The bell: severity badge and ring, one outlet                                                                      | Accepted         | `apps/aurelius-atlas-webapp/specs/7-15-alerts-drawer/design.md`                        |
| DD-175 | AlertList and Badge are ui-lib presentational components                                                           | Accepted         | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md`                    |
| DD-176 | The chip's pinned pair; Clear all in the drawer head                                                               | Accepted         | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md`                    |
| DD-180 | The inbox bar: severity chips, read tracking, Clear all in the bar                                                 | Accepted         | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md`                    |
| DD-181 | The drawer's body is the scroll container                                                                          | Accepted         | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md`                    |
| DD-182 | The inbox bar is one joined group, severity-coloured, ramp order                                                   | Accepted         | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md`                    |
| DD-183 | The inbox bar is one height: the count badge is compacted                                                          | Accepted         | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md`                    |
| DD-184 | The void chip: an empty severity greys out                                                                         | Accepted         | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md`                    |
| DD-185 | Show all is gone: the bar's shape never shifts                                                                     | Accepted         | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md`                    |
| DD-186 | Entity details arrives as a routed skeleton; its data spine joins 2.3                                              | Proposed         | `apps/aurelius-atlas-webapp/specs/7-6-entity-details/design.md`                        |
| DD-187 | The entity client is built test-first against the Atlas wire format                                                | Proposed         | `apps/aurelius-atlas-webapp/specs/7-6-entity-details/design.md`                        |
| DD-188 | One API base: the client's URLs all ride the API_BASE_URL token                                                    | Accepted         | `apps/aurelius-atlas-webapp/specs/7-6-entity-details/design.md`                        |
| DD-189 | The details chip is the classification chip; its sources project in                                                | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-16-ui-components-details-ii/design.md`         |
| DD-190 | The type-name badge is extracted from entity-card                                                                  | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-16-ui-components-details-ii/design.md`         |
| DD-191 | Details navigation is a shell; the scroll directive stays app-side                                                 | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-16-ui-components-details-ii/design.md`         |
| DD-192 | The count bar is section-stats: one component, two call sites                                                      | Proposed         | `libs/angular/aurelius-atlas-ui/specs/7-16-ui-components-details-ii/design.md`         |
| DD-193 | Collector ingest is authenticated in two legs: user JWTs for browsers, a shared token for services                 | Proposed         | `dev/observability/specs/7-17-collector-ingest-auth/design.md`                         |
| DD-194 | The collector stamps the verified user onto the telemetry: `enduser.id`                                            | Accepted         | `dev/observability/specs/7-17-collector-ingest-auth/design.md`                         |
| DD-195 | The collector rides out Keycloak's boot: bounded restart, awaited readiness                                        | Accepted         | `dev/observability/specs/7-17-collector-ingest-auth/design.md`                         |
| DD-196 | The service leg graduates to per-service identity: Keycloak client-credentials JWTs, azp-stamped                   | Proposed         | `libs/python/aurelius-atlas-otel/specs/7-18-collector-ingest-identity/design.md`       |
| DD-197 | The auxiliary APIs share one foundation: the OTel and auth libs                                                    | Proposed         | `libs/python/aurelius-atlas-auth/specs/8-0-auxiliary-api-foundation/design.md`         |
| DD-198 | The 8.x ports are pandas-free: pydantic rule models, plain row maps                                                | Proposed         | `apps/aurelius-atlas-data2model/specs/8-1-data2model-api/design.md`                    |
| DD-199 | App unit tests clear the injected `.env` prefix in an autouse fixture                                              | Accepted         | `apps/aurelius-atlas-data2model/specs/8-1-data2model-api/design.md`                    |
| DD-200 | The 8.2 proxy app injects its upstream HTTP client; the e2e Atlas is a canned-file server                          | Accepted         | `apps/aurelius-atlas-lineage-model/specs/8-2-lineage-model-api/design.md`              |
| DD-201 | The 8.3 mock ships as module data; the verifier is injectable                                                      | Accepted         | `apps/aurelius-atlas-validate-entity/specs/8-3-validate-entity-api/design.md`          |
| DD-202 | One issuer world: producers mint on the TLS listener, the collector validates both                                 | Accepted         | `dev/observability/specs/7-18-collector-ingest-identity/design.md`                     |
| DD-203 | The wire contract lives in a client library; the app imports it                                                    | Accepted         | `libs/python/aurelius-atlas-server-client/specs/8-4-api-client-libraries/design.md`    |
| DD-204 | Clients are async httpx with an injectable transport, and read no env                                              | Accepted         | `libs/python/aurelius-atlas-server-client/specs/8-4-api-client-libraries/design.md`    |
| DD-205 | The client's `httpx.AsyncClient` is provided externally                                                            | Accepted         | `libs/python/aurelius-atlas-server-client/specs/8-4-api-client-libraries/design.md`    |
| DD-206 | The lineage-model's upstream breakers live in the app, on pybreaker's `calling()` seam                             | Accepted         | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-207 | The lineage-model app follows the example app's provider/route layout                                              | Proposed         | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-208 | The lineage flow lives in the route; the chain class is dissolved                                                  | Proposed         | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-209 | data2model and validate-entity follow the example app's provider/route layout                                      | Proposed         | `apps/aurelius-atlas-data2model/specs/8-1-data2model-api/design.md`                    |
| DD-210 | Telemetry goes native: the OTel SDK replaces the logfire shell                                                     | Proposed         | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-211 | httpx2 replaces httpx across the HTTP surface                                                                      | Proposed         | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-212 | The 8.x apps' app/scenario test modules carry their package name                                                   | Accepted         | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-213 | The lineage guid is a UUID on every typed surface                                                                  | Accepted         | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-218 | 7.4 splits in two, and the search bar lands in the hero; the list is infinite scroll                               | Accepted         | `apps/aurelius-atlas-webapp/specs/7-4a-search-results/design.md`                       |
| DD-219 | The results URL carries the query only                                                                             | Accepted         | `apps/aurelius-atlas-webapp/specs/7-4a-search-results/design.md`                       |
| DD-220 | The demo pass restores the search screens' legacy chrome: title, typography, shell and plate                       | Accepted         | `apps/aurelius-atlas-webapp/specs/7-4a-search-results/design.md`                       |
| DD-221 | The empty query lists every entity through the `_ALL_ENTITY_TYPES` marker                                          | Accepted         | `apps/aurelius-atlas-webapp/specs/7-4a-search-results/design.md`                       |
| DD-234 | TLS material is a required setting: the server never serves plaintext                                              | Accepted         | `apps/aurelius-atlas-server/specs/9-2-server-hardening/design.md`                      |
| DD-235 | A 5xx answer is opaque and carries the trace id as `requestId`                                                     | Accepted         | `apps/aurelius-atlas-server/specs/9-2-server-hardening/design.md`                      |
| DD-236 | Security response headers are a pure-ASGI middleware split on `/api` path                                          | Accepted         | `apps/aurelius-atlas-server/specs/9-2-server-hardening/design.md`                      |
| DD-237 | Index refresh moves from reads to writes: writes carry `refresh=wait_for`, no read path refreshes                  | Accepted         | `libs/python/aurelius-atlas-core/specs/9-3-search-cost-client-ip/design.md`            |
| DD-238 | The browser rate limit lives at the nginx edge, not in the server; private ranges are allowlisted                  | Accepted         | `apps/aurelius-atlas-server/specs/9-3-search-cost-client-ip/design.md`                 |
| DD-239 | The webapp's nginx exports `/api/` spans on the collector's legacy leg; the module builds in the image's dev-stage | Accepted         | `apps/aurelius-atlas-webapp/specs/9-4-edge-tracing/design.md`                          |
| DD-240 | The DSL parser is generated from Atlas's own grammar                                                               | Proposed         | `libs/python/aurelius-atlas-dsl/specs/4-3-dsl-parser/design.md`                        |
| DD-241 | The parse tree is handed on as typed, immutable nodes                                                              | Proposed         | `libs/python/aurelius-atlas-dsl/specs/4-3-dsl-parser/design.md`                        |
| DD-242 | A DSL query is composed into the basic search's filter tree                                                        | Proposed         | `libs/python/aurelius-atlas-core/specs/4-4-dsl-entities/design.md`                     |
| DD-243 | DSL traversals and projections are evaluated in steps                                                              | Proposed         | `libs/python/aurelius-atlas-core/specs/4-4-dsl-projections/design.md`                  |
| DD-244 | Saved searches wait for authentication                                                                             | Accepted         | `libs/python/aurelius-atlas-core/specs/4-5-saved-searches/design.md`                   |
| DD-245 | Lineage walks the relationships of the process edges                                                               | Proposed         | `libs/python/aurelius-atlas-core/specs/5-1-lineage/design.md`                          |
| DD-246 | Glossary objects are entities written through the entity and relationship stores                                   | Proposed         | `libs/python/aurelius-atlas-core/specs/5-2-glossaries-and-categories/design.md`        |
| DD-248 | An entity's meanings are read from its listed relationships                                                        | Proposed         | `libs/python/aurelius-atlas-core/specs/5-2-term-assignment/design.md`                  |
| DD-249 | Uploaded files are read with python-multipart, openpyxl and xlrd                                                   | Proposed         | `libs/python/aurelius-atlas-core/specs/5-2-glossary-import/design.md`                  |
| DD-250 | The server authenticates requests itself against the identity provider                                             | Proposed         | `apps/aurelius-atlas-server/specs/6-1-authentication/design.md`                        |
| DD-251 | Browser sessions are kept in the server's memory                                                                   | Proposed         | `apps/aurelius-atlas-server/specs/6-1-authentication/design.md`                        |
| DD-252 | DataAccess carries every model object through a registry of DTOs                                                   | Proposed         | `libs/python/aurelius-atlas-core/specs/4-5-saved-searches/design.md`                   |
| DD-300 | Four fixed roles of the server's client grant Atlas's privileges                                                   | Proposed         | `apps/aurelius-atlas-server/specs/6-2-authorization/design.md`                         |
| DD-301 | The stores check through the authorizer they are given                                                             | Proposed         | `apps/aurelius-atlas-server/specs/6-2-authorization-entities/design.md`                |

> [!NOTE]
> DD-095 to DD-125 and DD-280 were never written. The first band went unused when the
> `feat/api-client-libraries` branch renumbered its entries to DD-180 and above (DD-179);
> DD-280's 10.5 step took its decisions in the 10.x specs without a record. Those numbers
> stay unused.
