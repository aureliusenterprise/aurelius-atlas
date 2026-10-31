# 10.11 Low-findings hardening: webapp edge, dev loopbacks, CI hygiene

- **Status:** in review
- **Pull request:** #186 (stacked on #184)
- **Records:** DD-279 (adds), DD-238 (relies on: the edge limiter's address key),
  DD-262 (relies on: the placeholder-resolved nginx config), DD-270 (relies on:
  the webapp TLS listener), DD-232 (relies on: the CI fan-out), DD-247 (relies
  on: the chart-target plugin)

## Scope

The pre-pentest triage's remaining **Low** finds, collected across both review
passes and deferred until every High/Medium shipped (H1 stays out of scope;
the probe-auth Low belongs to that auth increment, not this one). Seven
parked items, three surfaces:

- **Webapp edge (pentest 2 L1–L3).** The resolved nginx config — which
  carries the legacy ingest bearer in its `otel_exporter` block — rides a
  disk-backed `emptyDir`, so the token can land on node disk; set
  `medium: Memory`. No HSTS rides the webapp's TLS listener (the server has
  one behind a setting; the edge serving the SPA has none); stamp it with
  the same header, whole-directive-placeholder like the realip block. The
  `/otel/` proxy is the one browser-facing location without a limiter —
  `/api/` has the SRV-09 bucket — so a logged-in tab can flood the
  collector's browser leg unbounded; give it its own zone.
- **Dev stack loopbacks (pentest 1 L2, unfinished half).** The collector's
  publishes went loopback in 7.17; Prometheus/Loki/Tempo (9090/3100/3200)
  and the store's `${ELASTICSEARCH_PORT}:9200` still bind `0.0.0.0` on dev
  hosts. Every consumer reaches them on `localhost` or in-network, so
  pinning all four is zero-breakage. The guard sweeps the whole `dev/*`
  set and the Keycloak issuer (8080/8443) and the template Postgres
  surfaced as unpinned while doing it: both are **deferred** — their e2e
  consumers dial `keycloak.localhost` through `extra_hosts:
host-gateway`, and the Postgres host port is the examples' `serve`
  database, so a loopback bind needs a compose-network rework, not one
  line. The guard names the two files it enforces, not the whole set.
- **CI hygiene (pentest 1 L6a–c).** `ci.yaml` and `publish-docs-pr.yaml`
  run PRs with no same-repo guard — the members-only policy is a GitHub
  _setting_, and the PR runners are privileged with age keys in step env;
  enforce the boundary in code. The four docs workflows share one
  `concurrency` group, so a PR preview's queue slot can displace a main
  deploy's; scope the groups. The ARC runner pool's images float on
  `:latest`/`:main`; pin the third-party init by digest and make the
  platform runner's tag var digest-spellable.

**Kept with justification notes** (auditor-facing, no behaviour change):
Postgres `local all all trust` (socket-only, inside the PG pod — TCP is
TLS+scram); the store's 9300 transport port (bound, no peers single-node,
NetPol ruleless by design); Keycloak's 9000 management port (probes only,
never on a Service — the chart suite already pins the Service's ports).
Each gets its justification stated adjacent in the owning file.

This increment does **not** deliver: API authentication (H1, separate PR),
probe endpoints' 401s (rides H1), CODEOWNERS (the triage's optional item —
enforces nothing without org plan support, declined), the Trivy SARIF's
second hop to GitHub code scanning (L6d, declined: the same files already
ride to SonarQube, where the quality gate fails the build on them — a
second triage surface for identical findings splits the queue instead of
shortening it), HSTS preload (the `includeSubDomains` half only),
admission enforcement (operator posture, runbook note in 10.10), changes
to the `/api/` limiter's shape (SRV-09 stands; `/otel/` gets its own zone
beside it), or the loopback pins of Keycloak's issuer ports and the
template Postgres (named deferrals above).

## Semantics

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHT-98  | The webapp deployment's `nginx-conf` volume — the init-resolved config carrying the legacy bearer — is a tmpfs (`emptyDir.medium: Memory`). The other emptyDirs (template mount targets, pid/temp/log dirs) stay disk-backed: only the secret-bearing one earns the RAM.                                                                                                                                                                                                                                                                                                     |
| CHT-99  | The webapp nginx serves `Strict-Transport-Security: max-age=31536000; includeSubDomains` (`always`) at server scope when `nginx.hsts.enabled` (default `true`); the chart renders the whole `add_header` directive through a template placeholder (the realip-block precedent), so the compose/e2e shapes resolve it to nothing. The placeholder contract grows twelve → thirteen (init env + sed + fail-loud guard). The e2e copy stays without the header (test posture, mirroring the server's dev `HSTS_ENABLED=false`).                                                 |
| CHT-100 | The `/otel/` location carries `limit_req` on its own zone (`atlas_otel`, rate `600r/m` browser-sized, `burst=100 nodelay`, `limit_req_status 429`), keyed on the same trusted-address variable as `/api/` — behind a Gateway with `trustedProxyCIDRs` set it buckets per browser, without it per Gateway. The e2e copy carries the zone browser-sized (not test-sized): the suite's own `/otel` traffic must not throttle.                                                                                                                                                   |
| CHT-101 | The observability and store dev stacks publish on loopback only: `127.0.0.1:` on Prometheus 9090, Loki 3100, Tempo 3200 and the store's `${ELASTICSEARCH_PORT}:9200`. In-network consumers (Grafana datasources, compose DNS, the collector's exporter endpoints) are unaffected; the suites already read these on `127.0.0.1`. The guard (`tests/test__dev_stack.py`) scans those two stacks' compose files for a loopback bind on every `ports:` entry; Keycloak's issuer ports and the template Postgres are the named deferrals above.                                   |
| CHT-102 | Same-repo PR guard: every `pull_request`-triggered job in `ci.yaml` (the privileged pool, age-key env) and `publish-docs-pr.yaml` runs only when `github.event.pull_request.head.repo.full_name` equals `github.repository`. Docs `concurrency` groups are scope-split: the public-docs pushers (main, tag, delete) share `docs-public`; PR previews get a per-PR group and can no longer displace a main deploy's queue slot. ARC images: the `actions-runner` cache-init is digest-pinned; `CI_SHAPEA_IMAGE_TAG` accepts a `sha256:` digest (`@`-joined) as well as a tag. |

## Java origin

None — this increment ports no Apache Atlas behaviour. The reference is the
pre-pentest triage's Low backlog (both passes); findings closed by earlier
increments (headers/CSRF/search-cost/segmentation/realm/Grafana/creds/digests)
are named there, not here.

## Deviations

None against Atlas. The `/otel/` limiter is Aurelius-only edge policy (Atlas
has no OTLP proxy); its rate is a deliberate operational guess, browser-sized
with headroom, and the zone is named so a deployment can retune it.

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green (the chart owners).
- `tests/test__charts_webapp.py` names CHT-98 (the tmpfs volume, and that the
  sibling emptyDirs stay unmediumed), CHT-99 (the placeholder contract at
  thirteen — env, sed, guard; HSTS in the ConfigMap asset; `nginx.hsts.enabled=false`
  renders the placeholder empty; twin byte-identity still exact), and
  CHT-100 (the `/otel/` zone lines in the ConfigMap asset, and the e2e copy's
  browser-sized twin).
- `tests/test__dev_stack.py` names CHT-101: every `ports:` publish in the
  observability and store compose files carries a `127.0.0.1:` (or
  `localhost:`) bind — a plain text scan, no docker needed.
- CHT-102 is a workflow/infra change reviewed as code (the CHT-95
  precedent): graph/`actionlint`-style checks only, no test file.
- Hand check: `nx e2e aurelius-atlas-webapp` (the loopback-pinned stack under
  the real browser suite) — Level 2.
