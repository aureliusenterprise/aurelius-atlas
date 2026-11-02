# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

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
