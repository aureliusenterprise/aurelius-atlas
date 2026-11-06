# Design Log

The archive of the technical decisions made during the conversion that are too implementation-specific for an ADR but must not be lost: storage layout, identifiers, query translation, test tooling. Business-level decisions are ADRs in [Architecture Decisions](<https://aureliusenterprise.github.io/fix-all-types-roots/architecture/adr/index.md>).

Each new entry lives in the `design.md` of the increment that makes it, next to that increment's spec ([ADR 051](<https://aureliusenterprise.github.io/fix-all-types-roots/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)); where, is what the [Moved entries](<#moved-entries>) index keeps per number. This page holds the entries written before that layout (DD-001 to DD-094, DD-126 to DD-176, DD-180 to DD-213, DD-218 to DD-221, DD-234 to DD-246, DD-248 to DD-279, DD-282 to DD-294, DD-296 to DD-301 are moved out; what is listed below stays): it is read-only history. Nothing is appended here.

## Rules

- Entries are numbered `DD-NNN`, consecutively across the repository; numbers are never reused, and an unused number (see the note under [Moved entries](<#moved-entries>)) stays unused.
- Statuses: **Proposed** → **Accepted**, then optionally **Superseded by DD-NNN**.
- An accepted entry is never edited except its status line. A changed decision is a new entry that supersedes the old one.
- Every entry names the increment that introduced it, and lives next to that increment's spec: `<project>/specs/N-M-slug/design.md`.
- An increment that makes a decision adds its entry in the same pull request.

## Entry template

```
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

| \# | Decision | Increment | Status |
| --- | --- | --- | --- |
| [DD-177](<#dd-177-the-parallel-tracks-colliding-dddv-ids-renumber-to-the-7x8x-side>) | The parallel tracks' colliding DD/DV ids renumber to the 7.x/8.x side | — | Accepted |
| [DD-178](<#dd-178-the-merge-resolves-the-opentelemetry-version-split-to-the-1451066b1-set>) | The merge resolves the OpenTelemetry version split to the 1.45.1/0.66b1 set | — | Accepted |
| [DD-179](<#dd-179-the-branchs-second-collision-band-renumbers-above-mains-tail>) | The branch's second collision band renumbers above main's tail | — | Accepted |
| [DD-214](<#dd-214-the-test-suite-review-of-2026-10-24-scopes-the-hardening-increments>) | The test suite review of 2026-10-24 scopes the hardening increments | cross-cutting | Accepted |
| [DD-215](<#dd-215-the-ci-pipeline-drops-the-traceability-check-and-report>) | The CI pipeline drops the traceability check and report; the tools stay as local aids | cross-cutting | Accepted |
| [DD-216](<#dd-216-stacks-own-the-tls-material-they-mount>) | Stacks own the TLS material they mount | cross-cutting | Accepted |
| [DD-217](<#dd-217-the-search-client-lands-on-both-sides-of-the-wire-ahead-of-74>) | The search client lands on both sides of the wire, ahead of 7.4 | cross-cutting | Accepted |
| [DD-226](<#dd-226-the-dev-stacks-restart-windows-are-unbounded>) | The dev stacks' restart windows are unbounded: an attempt budget burns out before Keycloak is up | cross-cutting | Accepted |
| [DD-227](<#dd-227-the-store-es-e2e-suite-is-removed-it-evaluated-the-dev-environment-not-production>) | The store-es e2e suite is removed: it evaluated the dev environment, not production | cross-cutting | Accepted |
| [DD-228](<#dd-228-dev-posture-tests-leave-the-suites-the-sweep-of-dd-223s-rule-applied>) | Six dev-posture e2e tests are removed: they asserted the dev box's deployment state, not shipped behaviour | cross-cutting | Accepted |
| [DD-229](<#dd-229-the-shape-a-tail-overlaps-the-test-graph-shares-its-daemon>) | Shape-A wall-time tuning: docker-build rides the test graph, sonar overlaps Storybook, cache save on miss | cross-cutting | Accepted |
| [DD-230](<#dd-230-parallelism-stays-at-the-default-the-scanner-cache-moves-to-the-pvc>) | Nx parallelism stays at the default (5 regressed); the SonarScanner download cache moves to the PVC; engine scoping measured away | cross-cutting | Accepted |
| [DD-231](<#dd-231-teardown-downs-the-compose-stacks-prune-only-sweeps-corpses>) | CI teardown downs every compose stack: prune only sweeps stopped containers, so the stacks rode through the tail | cross-cutting | Accepted |
| [DD-232](<#dd-232-the-ci-pipeline-is-a-fan-out-dag-the-pool-is-per-pod-emptydir>) | CI splits into validate then {e2e, scan-sonar, chromatic} on a 3-pod pool; the RWO cache PD retires for per-pod emptyDir | cross-cutting | Accepted |
| [DD-233](<#dd-233-the-toolchain-caches-bridge-pod-churn-through-the-cache-server>) | Fan-out pods churn: uv/pre-commit/sonar caches bridge across pods on the cache server (cold-pod tax measured away) | cross-cutting | Accepted |
| [DD-247](<#dd-247-journal-writes-do-not-wait-for-a-refresh>) | Journal writes do not wait for a refresh | cross-cutting | Proposed |
| [DD-295](<#dd-295-chart-track-id-collisions-with-main-renumber-above-both-ranges>) | Chart-track id collisions with main renumber above both ranges | — | Accepted |
| [DD-302](<#dd-302-business-attributes-are-stored-among-the-entitys-attributes-under-their-qualified-names>) | Business attributes are stored among the entity's attributes under their qualified names | 5.3 | Proposed |

### DD-177. The parallel tracks' colliding DD/DV ids renumber to the 7.x/8.x side

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into `feat/api-client-libraries`, PR \#143)
- **Date:** 2026-10-24

**Decision.** The 2.x/3.x track (server spine, entity store, relationships, classifications, tasks, audits) and the 7.x/8.x track (webapp shell, aux APIs, client libraries) branched at DD-036/DV-10 and minted ids in parallel: main took DD-037..089 and DV-11..46, the branch took DD-037..088 (51 ids, the same numbers, different decisions) and DV-11..27. The merge renumbers the **branch side above both ranges**: DD-037..088 → DD-126..176 and DV-11..27 → DV-47..61 in ascending order — DV-18/DV-22 included, to DV-62/DV-63, because main's DD-049 retired its own DV-18/DV-22 rows and retired numbers are never reused — and this entry (DD-177) records it. Main's ids keep their numbers. The citation sweep rewrote every spec, doc, code comment, scenario, `.env` comment, and trace marker on the branch side; a chain whose members renumber non-consecutively becomes an explicit list (`DD-059/062` → `DD-148, DD-151`).

**Reason.** Main's 2.x decisions are merged and cited by merged code — they are the accepted record, and the ledger's rule (numbers are never reused, accepted entries are never edited) protects them. The branch's specs are the in-progress side of the same ledger, so it is the side allowed to move; moving 51+17 ids in one mechanical, reviewable sweep costs less than living with ids that mean two things. The branch's non-colliding ids stay: DD-089..125 is untouched, and the new range starts above main's DD-089 with room for this entry. DD-065 is main's alone (the branch mints no DD-065).

**Consequences.** The merge of main into the branch is conflict-free for the id ledger: the two tracks occupy disjoint ranges. The mapping table (branch old → new) is this entry's appendix, below; every pre-merge commit message cites the OLD numbers — commit history is not rewritten, and the appendix is the lookup from a commit's citation to the merged record. The design-log and deviations tables are sorted by number, so the renumbered entries interleave with main's by position only after the merge sorts them; within the branch the sweep is in-place (ascending order). The untracked dev `.env` files (decrypted from the renumbered `.env.enc` comments) refresh on the next `nx decrypt`.

| Old | New | Old | New | Old | New |
| --- | --- | --- | --- | --- | --- |
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
| DD-051 | DD-140 | DD-071 | DD-159 | DV-11 | DV-47 |
| DD-052 | DD-141 | DD-072 | DD-160 | DV-12 | DV-48 |
| DD-053 | DD-142 | DD-073 | DD-161 | DV-13 | DV-49 |
| DD-054 | DD-143 | DD-074 | DD-162 | DV-14 | DV-50 |
| DD-055 | DD-144 | — | — | DV-15 | DV-51 |
| — | — | — | — | DV-16 | DV-52 |
| DV-17 | DV-53 | DV-21 | DV-56 | DV-25 | DV-59 |
| DV-18 | DV-62 | DV-22 | DV-63 | DV-26 | DV-60 |
| DV-19 | DV-54 | DV-23 | DV-57 | DV-27 | DV-61 |
| DV-20 | DV-55 | DV-24 | DV-58 | — | — |

DD-065 is main's alone (the branch mints no DD-065), and the branch's DD-089..125 sit above main's range — both untouched.

### DD-178. The merge resolves the OpenTelemetry version split to the 1.45.1/0.66b1 set

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into `feat/api-client-libraries`, PR \#143)
- **Date:** 2026-10-24

**Decision.** The merged `uv.lock` is re-resolved to one OpenTelemetry set: the OTLP exporter and SDK at 1.45.1, the instrumentation family (core, asgi, fastapi, httpx, logging, system-metrics) at 0.66b1 — main's set. The text merge had kept the branch's `opentelemetry-instrumentation-logging`/ `-system-metrics` at 0.65b0 under main's `opentelemetry-instrumentation` 0.66b1, and 0.65b0 pins the core at `==0.65b0`: the four app Docker builds fail `ResolutionImpossible`. The two otel seam tests follow the 1.45.1 exporter's internals: the ingest session moved from `OTLPSpanExporter._session` to `._client._transport._session`, and the metric exporter's resolved headers from `._headers` to `._client._headers`.

**Reason.** Main's lock is the accepted record (DD-177), and the pins are exact-equality inside the instrumentation family — a mixed set is not a solution pip can install, so the merged lock must resolve to one generation. The seam tests assert the wiring through the exporter's private structure (their declared purpose: the session/headers the ingest pipeline attaches); re-pointing them at the moved attributes keeps the same assertion on the same object graph.

**Consequences.** `nx run-many -t test e2e -c ci` is green again for the otel lib and the four Docker builds. The exporter's private attributes are not a public API: the tests are pinned to the locked version, and a future OTel bump must re-point them the same way. No production code changed — `build_otlp_pipeline` passes `session=` through the constructor, which is public in both versions.

### DD-179. The branch's second collision band renumbers above main's tail

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into `feat/api-client-libraries`, PR \#143)
- **Date:** 2026-10-24

**Decision.** Round 1 (DD-177) planned to main's DD-089 and DV-46; main's tail is DD-090 and DV-47 (the classification-search entry and row, 4.1). The merge of main's ledger keyed by id and kept HEAD, dropping main's DD-090 entry and DV-47 row; this entry restores both, and renumbers the branch's second band above main's tail and above DD-177/DD-178: DD-090..125 → DD-180..214 (the branch mints no DD-104, so the shift is not uniform) and DV-47..63 → DV-64..80, with the citation sweep over every spec, doc, code comment, scenario, `.env` comment, and trace marker on the branch side. The mapping table is this entry's appendix.

**Reason.** The same as DD-177: main's ids are the accepted record cited by merged code, and the ledger's rule (numbers are never reused, accepted entries are never edited) protects them; the in-progress side moves. The band DD-090..125 minted above DD-088 because main's tail was DD-089 when it was minted — main kept minting, and the merge proved the tail moved.

**Consequences.** The id ranges of the two tracks are disjoint: main DD-001..090 / DV-1..47, the branch DD-126..176, DD-180..214 / DV-64..80. Every pre-merge commit message cites the OLD numbers; DD-177's and this entry's appendices are the lookup. The untracked dev `.env` files refresh on the next `nx decrypt`.

| Old | New | Old | New | Old | New |
| --- | --- | --- | --- | --- | --- |
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
| DD-100 | DD-190 | DD-114 | DD-203 | DV-47 | DV-64 |
| DD-101 | DD-191 | DD-115 | DD-204 | DV-48 | DV-65 |
| DD-102 | DD-192 | — | — | DV-49 | DV-66 |
| — | — | — | — | DV-50 | DV-67 |
| — | — | — | — | DV-51 | DV-68 |
| — | — | — | — | DV-52 | DV-69 |
| — | — | — | — | DV-53 | DV-70 |
| — | — | — | — | DV-54 | DV-71 |
| — | — | — | — | DV-55 | DV-72 |
| — | — | — | — | DV-56 | DV-73 |
| — | — | — | — | DV-57 | DV-74 |
| — | — | — | — | DV-58 | DV-75 |
| — | — | — | — | DV-59 | DV-76 |
| — | — | — | — | DV-60 | DV-77 |
| — | — | — | — | DV-61 | DV-78 |
| — | — | — | — | DV-62 | DV-79 |
| — | — | — | — | DV-63 | DV-80 |

### DD-214. The test suite review of 2026-10-24 scopes the hardening increments

- **Status:** Accepted
- **Increment:** cross-cutting (rides the delivery docs; no roadmap row — the hardening increments 8.6/8.7/7.19/9.1 carry their own rows when specified)
- **Date:** 2026-10-24

**Context.** Development added tests ad hoc per increment. A workspace-wide review (all apps, all Python libraries, all frontend projects, both e2e suites) measured coverage and scored every suite against the five non-happy flow categories (input/validation, business rule/auth, infrastructure, interrupted/async, edge-case). Findings: infrastructure failure testing is a house strength (lineage-model, store-es, auth); the systematic holes are mid-request infra failures (server, core), frontend session lifecycle and error UX breadth (7 of 71 webapp-side specs assert an HTTP error), the client libraries' response-shape failures (2xx-with-garbage-body, timeout vs connect error), and data2model's view-edge/dynamic-view engine paths (0%). No coverage threshold exists in CI, and the Python libraries' `coverage.xml` is generated in CI only, not committed.

**Decision.** The review's findings, verdicts, ranked deferred backlog, and template-code exemptions are recorded in [Test Suite Review](<https://aureliusenterprise.github.io/fix-all-types-roots/architecture/platform/delivery/testing-review/index.md>), kept as a dated review page (reviews record, they do not drift). Four hardening increments proceed from it, one PR each, spec-first. The review's first finding about the ledger: **the failure semantics are almost all already specified — the tests are what is missing** (DTM-04/06/07 state the view-edge and dynamic-view paths at 0% coverage; LM-07/11/12/13 state the transport-failure, fast-fail, and outage-counting behaviours; CL-04/05/06 state the client failure contract; APC-04/05, ALR-04/05, SHC-05 state the frontend's). The increments therefore cite the existing ids, and mint new ones only where a finding names behaviour no rule states: **8.6** aux API failure hardening (proves DTM/LM/VE ids, adds negative parity scenarios), **8.7** client failure contract (adds CL-08 — a 2xx body that fails its model is the contract failing, not succeeding; proves CL-04/05/06), **7.19** frontend failure UX (proves APC/ALR/SPL/SHC ids; the example app's editor has no increment spec, its tests carry plain names), **9.1** resilience e2e with targeted container-stopping scenarios (the only new prefix, `RSL`). Coverage enforcement stays where it is: the SonarQube quality gate — no `--cov-fail-under`, no Vitest `coverage.thresholds`, no new CI flag. The server-spine findings (mid-request store failure, concurrent store writes) are explicitly deferred to the 2.x track as ranked backlog \#1, not dropped.

**Reason.** The gate already measures coverage (the `-c ci` configs write `coverage.xml`/`lcov.info`, CI uploads them, `nx affected -t sonar` feeds Sonar, whose quality gate fails on low levels — including new-code coverage, which ratchets naturally with every hardening PR); a second local flag would duplicate the gate and fight ADR 014's "defined once, runs everywhere". The priority split (frontend / aux APIs / clients first) follows where the representativeness gaps bite the conversion's next increments; the server spine's mid-request failures pair with 2.2's entity-store work, which changes those same call paths.

**Alternatives.** (a) A per-project coverage ratchet in the Nx python plugin and Vitest configs — refused, see Reason (and the user's call of this date). (b) One workspace-wide coverage floor — refused: the template baseline is heterogeneous and a uniform floor would punish the vendored dashboard and the example apps. (c) Destructive failure-injection e2e as a nightly resilience suite — refused for now in favour of a small number of targeted scenarios inside the existing per-PR e2e suites (≤2 min budget each), the same realism bar as ADR 012.

**Consequences.** The review page is the reference for "what was known on this date"; its numbers are a snapshot, the trace report stays the live system of record. Rule-id reservations: **CL-08** (8.7's one new rule) and `RSL-01…` (9.1); the other increments cite existing ids — minting new ids for already-specified behaviour would fork the ledger. The fastapi-example, `sdk`'s aws/msal/logger, aurelius-atlas-example, and the dashboard are exempted from hardening (matching the trace check's `exclude-projects` and DD-017). Phase ordering: 8.6 and 8.7 parallel, 7.19 parallel, 9.1 after 8.6 and 7.19.

### DD-215. The CI pipeline drops the traceability check and report

- **Status:** Accepted
- **Increment:** cross-cutting (rides the CI pipeline; no roadmap row)
- **Date:** 2026-10-24

**Context.** Increment 0.3 wired [ADR 049](<https://aureliusenterprise.github.io/fix-all-types-roots/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>) into the pipeline: the `validate` job runs `aurelius-atlas-trace check` (collection only, no test runs) and the `test` job builds an HTML trace report from the JUnit, coverage, and trace files. The check proves that a test *names* a function or rule id; it never runs anything. The desired behaviour of every increment is already encoded in its unit tests, which the pipeline runs, so the gate restates what the suites prove. Keeping the declarations true across the whole surface — TypeScript citations, end-to-end claims, rules whose proof lives in another repo — turned into bookkeeping that fails CI without indicating a missing test.

**Decision.** `.github/workflows/ci.yaml` drops both steps: the `validate` job no longer runs `aurelius-atlas-trace check`, and the `test` job no longer runs `aurelius-atlas-trace report` or uploads the `test-report` artifact. What blocks a merge is a failing test. The trace lib, the `covers` marker, and the `--trace-json` plumbing stay in the repo as local tools and a code-review convention — `nx test`/`nx e2e` keep writing the files, and anyone can run `check` or `report` themselves. Coverage enforcement is unchanged: the SonarQube quality gate ([DD-214](<#dd-214-the-test-suite-review-of-2026-10-24-scopes-the-hardening-increments>)). Parity scenarios keep their citation discipline ([ADR 052](<https://aureliusenterprise.github.io/fix-all-types-roots/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)) and the parity lib keeps its own checks — that is how expected behaviour is justified, not a trace gate. The business-level decision is [ADR 056](<https://aureliusenterprise.github.io/fix-all-types-roots/architecture/adr/056-behaviour-is-proven-by-executed-tests-not-by-a-trace-gate/index.md>), which supersedes ADR 049; `DD-009` (the record: `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`), `DD-010` (the record: `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`), and `DD-011` (the record: `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md`) describe the tools, which remain, so they stand as written.

**Alternatives.** (a) Widen the gate to prove the gaps away (TypeScript citations, end-to-end markers, seams for cross-repo rules) — refused: more mechanism proving declarations, no executed behaviour. (b) Keep the check as a non-blocking warning — refused: an unenforced gate is documentation nobody reads, and the noise stays. (c) Delete the trace lib as a slice now — refused: the marker is a useful review pointer and removing it would rewrite every test's metadata for no gain; it is removable later as one slice.

**Consequences.** The pipeline is smaller and says only what it can prove. The per-change published trace report is gone; reviewers read the tests and the coverage report. Increment specs that list `aurelius-atlas-trace check` in their "gates" describe the verification the increment was accepted with — they are dated records, not promises about current CI, and are not edited.

### DD-216. Stacks own the TLS material they mount

- **Status:** Accepted
- **Increment:** cross-cutting (e2e wiring; no roadmap row)
- **Date:** 2026-10-25

**Context.** The webapp's e2e stack runs the real Atlas server behind the nginx `/api/` proxy ( `DD-142` (the record: `apps/aurelius-atlas-webapp/specs/7-3-api-client-auth/design.md` )), and the server container mounted `apps/aurelius-atlas-server/certs` — the server project's own material, because its leaf carries the `aurelius-atlas-server` SAN nginx verifies against. The webapp's `e2e` target declared the server's `docker-build` and the dev stacks' `up` as `dependsOn` but not the server's `certgen` : Nx's compose plugin infers `certgen` from the compose **owner's** `tls.json` (tools/plugins/docker-compose.ts), so a sibling project's `certs/` mount is invisible to it. When the devcontainer was rebuilt, mkcert regenerated its root CA and every project self-healed its own material on its next `certgen` — the server's stayed signed by the old CA, its server container failed Elasticsearch TLS verification, exited 3 during `docker compose up --wait` , and every webapp e2e test errored at fixture setup.

**Decision.** The stack mounts only its owning project's certs. `tls.json` for the webapp gains an `aurelius-atlas-server` service (the same SANs the server project issues: the service name, localhost, 127.0.0.1), so the webapp's own `certgen` — already a `dependsOn` of `e2e` and `serve`, and auto-wired by the compose plugin's rule — generates the leaf the server container wears. `e2e/docker-compose.yaml` mounts `../certs` for it, and no cross-project `certgen` dependency is needed. The CA bundle is the shared mkcert root, so the server's verification of the dev Elasticsearch, the collector, and Keycloak is unchanged; the dev server (`nx serve aurelius-atlas-server`) still presents the server project's own leaf.

**Alternatives.** (a) Declare `{projects: ["aurelius-atlas-server"], target: "certgen"}` on the webapp's `e2e` — the pattern PR \#143 used for lineage-model → data2model, and correct: it keeps one issuer per identity. Refused for the webapp because the mount is part of the webapp's e2e stack, and a stack should carry its own material: with the `dependsOn`, "the webapp project needs the server project's certs" is a fact recorded only in a mount string, and certgen stays a target whose trigger (the devcontainer rebuild) lives outside the project that consumes it. (b) Have `certgen.sh` refresh every project's material — refused: a project's target writing into other projects breaks the slice ownership ADR 002 relies on. (c) Teach the compose plugin to parse volume mounts and auto-add the owning project's `certgen` — deferred; it generalises the inference rule but adds plugin magic for a pattern (stacks that embed a sibling's image) the explicit `dependsOn`/manifest already covers.

**Consequences.** `nx e2e aurelius-atlas-webapp` is self-sufficient for TLS: a fresh container rebuilds the webapp's `certs/` (server leaf included) before compose starts. Two projects now issue a leaf for the `aurelius-atlas-server` name — the server's for its own stacks, the webapp's for the e2e stack — which is dev-only identity, gitignored and never shipped (ADR 006); `apps/aurelius-atlas-server/certs` is no longer read by the webapp stack. The same audit swept the workspace's other two cross-project cert mounts (the only ones beyond this): the observability collector pinned its OIDC `issuer_ca_path` to the webapp's CA copy mounted at `/dev-ca`, which no target produced — it now verifies the issuer against its own `certs/ca.pem` (the mkcert root is shared workspace-wide, byte-identical copies), so the mount and its producer disappear together. The lineage-model e2e stack mounted data2model's certs behind an explicit cross-project `certgen` `dependsOn` (PR \#143 — the pattern this entry's alternative (a)); it now follows this entry's decision: `tls.json` gains the `aurelius-atlas-data2model` service, the stack mounts `../certs`, and the cross-project `certgen` `dependsOn` is gone (its `docker-build` stays — the image is data2model's artifact). After this, no compose file mounts another project's `certs/`: every stack's TLS material is generated by the stack owner's own `certgen`, matching the frontend-example, whose `tls.json` already listed all three services its e2e stack hosts.

### DD-217. The search client lands on both sides of the wire, ahead of 7.4

- **Status:** Accepted
- **Increment:** cross-cutting (the 8.4 client family and the 7.3 Angular client; no roadmap row)
- **Date:** 2026-10-26

**Context.** Increments 4.1/4.2 gave the server the discovery routes (`/api/atlas/v2/search/**`), and the Python client gained them as `AtlasClient.search` (CL-13, the 8.4 family). On the frontend, 7.3 deliberately ported only the surface the server implemented then (DD-140), leaving every search call to 7.4 ("the search slice, gated by server 4.1/2.3"). With server 4.1/4.2 merged, the gate's server half is met, and 7.4's first line needs `SearchService` to exist — the client is the seam 7.4 consumes, and a client built without its consumer is the speculative build DD-140 rejects.

**Decision.** Land the typed search client on both sides of the wire now, as data-layer only: `AtlasClient.search` (CL-13) and, in `libs/angular/aurelius-atlas-data-access`, `SearchService` (APC-11, `search.service.ts`) with the search DTO cluster (`atlas-search.ts`, APC-03's hand-mirror of `aurelius_atlas_model/discovery.py`). No screen calls it: the browse landing's affordances, the header search bar, and the results screen stay 7.4's. The GET searches send the Java defaults (a false flag, a `0` page) as their absence, matching the server routes' `flag`/`java_number` reading; the POST searches send the parameters as the body `validate_basic_search_parameters` / `validate_quick_search_parameters` validate.

**Alternatives.** (a) Wait for 7.4 and build the client inside it — refused: 7.4 is a UI slice (the results screen redesign), and bundling the wire contract into it makes its review carry both; (b) generate the TS DTOs from the Python models — deferred with the same open question as the typedef cluster's hand-sync (APC-03), one mechanism for all DTOs is better than one per cluster.

**Consequences.** 7.4 consumes `SearchService` directly; the webapp's e2e stack already runs the real server behind the proxy (DD-142), so a 7.4 flow test needs no new wiring. The two DTO clusters (`atlas-search.ts`, `aurelius_atlas_model/discovery.py`) join the hand-sync list in `aurelius-atlas-data-access/AGENTS.md`. The Python side is proven against the container (`apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_search_e2e.py`); the Angular side is proven against `HttpTestingController` — the e2e proof of a search through the proxy lands with 7.4's screen.

### DD-222. The Python apps emit the stable HTTP semantic conventions

- **Status:** Accepted
- **Increment:** cross-cutting (telemetry; no Atlas REST semantics — no roadmap row, DD-210's pattern)
- **Date:** 2026-10-26

**Context.** The webapp → server → Elasticsearch trace (7.18/7.19) carried two HTTP conventions at once. The browser leg (JS SDK 2.12) and elasticsearch-py's native spans emit the stable set (`http.request.method`, `url.full`, `db.system.name` — the latter stable natively since 8.13, DD-210); the FastAPI/ASGI leg (instrumentation 0.66b1) emits the old set by default (`http.method`, `http.url`, `http.status_code`, `net.peer.*`). Every span-attribute filter written against the stable names silently misses the request spans — the exact trap DD-210's ES-span probe steps around by matching `db.system.name` only. The same split lands on metrics: the RED panels read the old `http_server_duration_milliseconds` (ms), which the instrumentor stops reporting under the opt-in.

**Decision.** All five Python apps set the standard `OTEL_SEMCONV_STABILITY_OPT_IN=http` (value `http`, not `http/dup` — the old set is dropped, not doubled). It is a bare `OTEL_*` name (third-party-runtime consumer, the root `AGENTS.md` env rule) set in two places per app: the `Dockerfile` `ENV` (the e2e/prod image) and the project `.env`/`.env.enc` (`nx serve`, whose process environment Nx builds from the project env). The FastAPI RED dashboard moves with it in the same change: `http_server_request_duration_seconds` (stable; the SDK emits seconds, the ms panels multiply the quantiles by 1000), `http_server_response_body_size_bytes`, labels `http_route` / `http_response_status_code`; `http_server_active_requests` keeps its name (the panel uses a bare `sum()`; the stable label set is a subset). The SSE exclusion also fixes a stale route: the old `http_target!="/sse"` never matched the real route `/entities/sse` (the router mounts it under its prefix), so the p95-excl-SSE panel silently included stream durations. The server e2e store-span probe (DD-210) gains the convention pin: the request span must carry `http.request.method=GET` and none of `http.method`/`http.url`/`http.status_code`.

**Alternatives.** (a) `http/dup` — refused: it doubles span attributes and metrics series forever; the migration it exists for has no second consumer here (the collector pipeline and every dashboard in-repo are updated in this change, and no external consumer reads these series). (b) Set the opt-in in code (the instrumentor constructors accept no equivalent; the SDK reads it once at first instrumentation, and the apps' composition roots instrument at import-adjacent time) — refused: env is the mechanism the standard defines, and `nx serve`/image/dashboards stay declarative. (c) Leave the server legacy and rewrite the ES-span filters to old names — refused: the stable set is where OTel has standardised (the JS browser SDK and elasticsearch-py are already there), and one trace carrying one convention is the point.

**Consequences.** Server and auxiliary-app spans drop `http.url`/`http.status_code`/`net.peer.*` (nothing in-repo filters on them; the webapp/frontend/keycloak dashboards read web-vital, Micrometer, and resource attributes only — verified). Metric history is split at the flip: the old `http_server_duration_milliseconds` series stop, the new ones start (dev dashboards, acceptable; Grafana's time range covers the gap). The active-requests gauge loses its `http_host`/`http_server_name` labels (the stable set is method+scheme; the panel is a bare sum). The server e2e probe is the regression gate: a dropped `ENV` in an image fails the store-span test with a named message. The 8.x aux apps carry the same ENV pair for symmetry — their spans join the stable set on the next trace they ride (the 8.2 chain, DD-210). Tempo's search by `resource.*` and the Grafana Explore panels are unaffected (resource attributes are not part of the HTTP semconv switch).

### DD-223. E2E suites never restart shared dev infra; layout parity leaves e2e

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure)
- **Date:** 2026-10-27

**Decision.** An e2e suite may read and write the shared `dev/*` services, but it must **never restart** them: no `docker compose down`/`up`, no container cycling, on a stack other suites ride. Writes stay allowed when namespaced and self-cleaned (the webapp's uuid-prefixed indices, the server's `scenario_*` writes, the example apps' fixture rows). Concretely:

- `aurelius-atlas-store-es` e2e drops its ESD-04 restart-persistence test — the only test in the fleet that took the shared dev Elasticsearch down and up mid-suite. The rule moves to the increment spec as deliberately untested: the named-volume behaviour is verified by review, and the healthcheck (DD-008) covers the "stack comes back up" half. With no restart left in the suite, its `parallelism: false` pin (project.json) is deleted — store-es e2e now runs beside every other task.
- The rationalisation sweep that rides along: the ESD-03 credential-hygiene test moves from store-es e2e to a unit test (`tests/test__dev_elasticsearch_config.py` — it inspects committed files, never a running store; the `test` target decrypts the dev project's `.env` first), and the two FastAPI-framework probes in fastapi-example e2e (`/docs`, `/openapi.json` — they assert FastAPI defaults, not Aurelius behaviour, and carried no `covers` rule) are deleted.
- Layout-parity pins leave the webapp e2e suite (with the user's directive: interactions are what e2e guards, layout is what unit/visual tests guard). Eight tests go: the navbar logo box, the body type/ink, the type ramp, the chrome-band palette, the accent ramp, footer-below-the-fold, the landing container inset, and the dark-OS light pin. Their checks land in the webapp's Vitest component specs (`header.component.spec.ts`, `footer.component.spec.ts`, app/shell template structure) as class/token/attribute assertions — the parts a jsdom browser can verify — while the computed-pixel measurements (Bulma ramp values, band heights, bounding boxes) are dropped: they pinned the demo at parity-establishing time and can only fail on CSS refactorings, not on behaviour. The interaction half of the burger-menu test (click, dropdown, logout entry) stays in e2e; only its CSS pins go. A Storybook visual-test setup for the webapp (it has no `storybook` target today) is a follow-up increment, not part of this change.

**Reason.** CI runs `nx affected -t test e2e` in parallel, and the fleet rides the shared `dev/*` services. ESD-04's dev-ES down/up races every suite mid-flight — lost-connection failures are on record (the `parallelism: false` pin was that outage's scar tissue, and it serialised the suite forever after). The fix is to remove the restart, not to isolate every writer: a per-suite store stack was built and verified in this cycle (ES ×3, Postgres ×1) and rejected as over-correction — the dev stores' standing data is a debug aid, namespaced writes are already the convention, and one restart-test does not justify four extra cold boots per CI run. The proof half is the same story: tests that assert framework defaults (`/docs` returns 200) or demo-measured pixels (navbar height 68px, ink `#4a4a4a`) can only fail for non-Aurelius reasons, and they are the slowest to debug when they do.

**Alternatives.** (a) Suite-owned stores for every writer (the shape this session built and verified: store-es/webapp/server on their own ES, fastapi-example on its own Postgres) — refused on the user's direction: the ban is on restarts, writes are fine, and four cold store boots per CI run is a lot of boot to buy what namespaced writes already provide. The work is preserved in this branch's history if a suite ever needs isolation (the suite-stack compose recipe — dev image, node config mounted read-only, DD-216 certs, openssl healthcheck — is on record). (b) Keep ESD-04 with a global serialisation — refused: `parallelism: false` taxes the whole fleet forever to run one test, and the dev-ES restart is the exact race the pin documents. (c) Move the layout pins to Storybook visual tests now — refused as scope: the webapp has no storybook target, and porting eight computed- style pins to a visual harness is its own increment; the Vitest component specs cover the structure that jsdom can see, the pixels return with the storybook slice.

**Consequences.** store-es e2e runs in parallel (one serialised suite gone); the dev Elasticsearch is never cycled mid-suite, so co-scheduled suites stop losing connections. ESD-04 is the fleet's first explicitly untested rule, with the note in the increment spec carrying why. The webapp e2e suite drops eight tests (\~135 → 127 collected, all browsers) and the shell's computed-style coverage moves to unit specs as structural assertions; a true visual-parity harness waits on a webapp Storybook slice. The dev stores' data survives e2e runs (writes are namespaced and self-cleaned, and the webapp glossary purge rides its own uuid-prefixed types). `AGENTS.md` gains all three rules: no restarts, prove Aurelius behaviour not framework defaults, guard interactions not layout.

### DD-224. The webapp e2e signs in once per browser and replays the session

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure; follows DD-223's time audit)
- **Date:** 2026-10-27

**Decision.** The webapp suite's `authenticated` fixture no longer runs the Keycloak form login per test. A session fixture signs in **once per browser**, saves the context as a Playwright `storage_state` (the realm's SSO cookie, `KEYCLOAK_IDENTITY`), and every test now gets its **own context seeded from that state**: the SPA boots with `check-sso` and the silent-iframe redirect (APC-05), so a pre-authed context mints its own 60s access tokens from the stored SSO session — the login form never opens. The fixture watches the boot: navbar → signed in; login form (session died — e.g. the resilience logout test ends the realm session, RSL-02) → run the form login and refresh the shared state, so the next test replays from a live session again. The per-test context keeps cookies/storage/cache isolated exactly as the per-test login left them.

**Reason.** The slow-e2e diagnosis: the suite's \~37 authenticated tests per browser each paid a full Keycloak sign-in (\~1.5s of form fill, redirect and token exchange) — \~60% of the suite's wall time and the fleet's biggest single cost. The realm's SSO session (30-minute idle window, refreshed by every test's visit) plus the SPA's silent check-sso is exactly the mechanism the reuse rides: it is the flow a real returning user takes, so the fixture now proves the SSO path end to end as part of every test.

**Alternatives.** (a) Keep the per-test login — refused: it is the cost this decision exists to remove. (b) One shared context for the whole session — refused: tests mutate storage/cookies (locale, settings panel, theme); isolation stays, only the session is shared. (c) Mint tokens by REST and inject them — refused: keycloak-js keeps its tokens in JS memory, not storage; the storage\_state path is the browser's own session story and needs no injection hack. (d) Test-only Keycloak config with longer token lifetimes — refused: it drifts from the dev realm every suite rides.

**Consequences.** The suite measured 1.28s/test after the change vs 2.24s before (full matrix, all browsers): the webapp e2e drops from \~4m to \~2m20. The realm's 60s access token and 30-minute SSO window bound the suite: \~4 minutes of sessions fit with room, and the self-heal covers the tail. The state file lives under pytest's tmp path — cookies only, never the user's password. The resilience suite's logout test (which ends the realm session and re-signs-in by form) runs on the shared state and proves the recovery path in-suite.

### DD-225. E2E containers export spans every second so Tempo probes land sooner

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure; follows DD-224's time audit)
- **Date:** 2026-10-27

**Decision.** The OTLP-emitting app services in the e2e compose stacks (the server stack's `aurelius-atlas-server`, the webapp stack's `atlas-server`, the lineage chain's `data2model` and `lineage-model`) set `OTEL_BSP_SCHEDULE_DELAY: "1000"`, and the Tempo read-back probe loops (server store-ride, lineage chain, webapp stamping/ingest) poll every 1s instead of every 3s. Deadlines stay as they were (60–120s).

**Reason.** The probes ride `BatchSpanProcessor`, which the apps construct with no arguments — its 5000ms schedule delay is the floor under every read-back: the first poll that can succeed lands ≥5s after the request, Tempo's block ingest adds 1–3s, and the 3s sleeps then quantise arrival to \~6–9s. The floor is the exporter, not the polling, and the SDK reads `OTEL_BSP_SCHEDULE_DELAY` from the environment when the processor is built, so the compose env reaches it with no code change. The key stays bare (`OTEL_*` is a third-party consumer, per the env-prefix rule) and rides the e2e compose only: prod images keep the SDK default.

**Alternatives.** (a) Keep the 3s sleeps — refused: they were tuned to a 5s floor the fleet no longer has, and each quantises 1–3s of latency per probe per browser. (b) Force an export per request (a `SimpleSpanProcessor` under test) — refused: it changes the pipeline the suite exercises. (c) Shorten the deadlines — refused: the deadlines are the failure budget, not the expected path.

**Consequences.** Measured solo: the server store-ride probe 12.2s → 6.2s (suite 31.9s → 28.8s), the lineage chain probe 6.1s → 1.0s, the webapp suite 2m36s → 2m08s (its probes ride three browsers). The 84.6s server-dashboard number from the same audit needed no fix: it is contention, not the test — measured clean, the dashboard pair is 7.2s + 0.8s. Export cadence rises (dev containers only, negligible collector load); probes fail only on real ingest loss.

### DD-226. The dev stacks' restart windows are unbounded

- **Status:** Accepted
- **Increment:** cross-cutting (dev-stack wiring; rides the CI pipeline, no roadmap row)
- **Date:** 2026-10-26

**Context.** DD-195 chose `restart: on-failure:15` for the collector and DD-202 extended the pattern to the slice metrics-pullers, reasoning that 15 attempts ≈ 6 minutes spans any Keycloak boot and the bound keeps a permanently broken stack loud. Both halves proved wrong under the CI e2e fan-out (run 40292544843). The attempt count burns out in \~6 minutes — Docker's backoff doubles per *attempt* (100 ms → 60 s ceiling), so six minutes of failing is 15 attempts, not 6 minutes of wall clock — and Keycloak's TLS listener is not reliably up that fast when the fan-out shares one 4-vCPU node and the Elasticsearch stack boots last. When the budget expires Docker stops restarting the container *permanently*, and the failure is silent: ESD-06 polled Prometheus for 420 s against a puller that had given up for good, reviving one second after the test gave up (the green/red history of that rule — green 40279621021/40282797027/40289090955, red 40286077875/40292544843 — was this race, not the poll budget). The loud-exit property also proved illusory: `compose up --wait` gates on the healthcheck, and a restarting-then-dead container never reports healthy, so the bound exits on the final crash exactly when the unbounded form keeps trying through it.

**Decision.** All four dev composes (`dev/elasticsearch`, `dev/keycloak`, `dev/postgres`, `dev/observability`) carry unbounded `restart: on-failure` on every container whose readiness depends on Keycloak — the collector and the metrics-pullers. This supersedes the bounded-restart half of DD-195 (the awaited readiness — `up --wait` + healthchecks — stands) and the `restart: on-failure:15` detail of DD-202. Loudness moves from the restart count to the state Docker reports: a permanently bad config sits in a visible `restarting` loop, in `docker compose ps` and in the compose `up --wait` that never returns healthy.

**Consequences.** Keycloak readiness is no longer raced: the 60 s backoff ceiling lands a puller within a minute of the issuer coming up, at any cold-start delay, so ESD-06's budget measures ES metrics latency (its stated subject) instead of Docker's restart arithmetic. The cost of the unbounded form is that a permanently broken puller retries forever — visible, not loud; acceptable for dev stacks, where the same loop is the normal boot shape during Keycloak's startup.

### DD-227. The store-es e2e suite is removed: it evaluated the dev environment, not production

- **Status:** Accepted
- **Increment:** cross-cutting (test strategy; follows DD-223, DD-225)
- **Date:** 2026-10-27

**Decision.** `libs/python/aurelius-atlas-store-es/e2e/` is deleted: ESD-01, ESD-02, ESD-05 and ESD-06 lose their automated tests. The rules stay specified in the 0-2 increment; the dev stack carries them — `up --wait` gates on the compose healthchecks (ESD-01), every app's e2e suite reaches the store over verified HTTPS with credentials (ESD-02 in the production path), heap and puller wiring are config under review (ESD-05, ESD-06). ESD-03 (credential hygiene) remains a unit test in `tests/`; ESD-04 was already untested by DD-223's choice.

**Reason.** The suite asserted the dev environment's state, not the library's production behaviour — the same bar DD-223 set for the FastAPI `/docs` probes. The shape-A runner made the cost concrete: the ESD-06 metrics test burned its full 420s budget and failed the pipeline (run 40465196293) while the ES metrics-puller sat in DD-226's unbounded restart backoff waiting on Keycloak — a dev-stack readiness race, charged to the test suite, blocking production work. A test whose green state is "the dev box is warm" is a flake generator; what the store library must prove is in its unit/container tests (STO-01 to STO-08) and in the apps' suites, which ride the real code path against this store.

**Alternatives.** (a) Keep it with a larger budget — refused: the 420s fix was already tuning a test that should not exist. (b) Keep ESD-02/ESD-05 as e2e against the dev store — refused: the server e2e suite proves TLS + auth + store round-trips from the Atlas side, on the production client path. (c) Move the suite to CI infra validation — refused: dev-stack health is the compose healthchecks' job, already wired to `up --wait`.

**Consequences.** CI's longest e2e suite disappears (7 min worst case, 0s green — the ESD-06 poll dominated it); the 420s `METRICS_TIMEOUT_SECONDS` leaves with the suite. The traceability report gains four explicitly-untested rules beside ESD-04, with this entry as the note. The dev/elasticsearch puller and its DD-226 restart posture stay — Grafana reads them; only the CI assertion on their warm-up is gone.

### DD-228. Dev-posture tests leave the suites: the sweep of DD-223's rule, applied

- **Status:** Accepted
- **Increment:** cross-cutting (test strategy; follows DD-223, DD-225, DD-227)
- **Date:** 2026-10-27

**Decision.** Six e2e tests are removed: the webapp suite's `test__browser_facing_tls_verifies_against_ca`, `test__collector_accepts_the_dev_plaintext_issuer`, `test__collector_accepts_the_shared_ingest_token`, `test__collector_publishes_are_loopback_pinned` and `test__producers_keep_flowing_with_the_token`, and the frontend-example suite's `test__browser_facing_tls_verifies_against_ca`. Their conftest support leaves with them (`plaintext_service_token`, `collector_container` and the dev issuer constants). The rules they pinned — CIA-03, CIA-07, CIA-10, CIA-11 and SHL-11's TLS half — keep their specs, with an "untested by choice" note where each acceptance list named the test.

**Reason.** DD-223's rule — e2e proves Aurelius behaviour, not the dev box — applied as a sweep. Each cut test asserted dev deployment posture: a certificate chain signed by the workspace mkcert CA, the collector's 127.0.0.1 port publishes, the plaintext :8080 Keycloak listener only the dev browser uses, the shared ingest token's dev-only legacy leg, and the dev pullers' liveness read through the Docker API. None of it exists in production. Two of them (the loopback-pin, the producers-flow) were also the suite's flake-prone container-internals tests — the same family DD-227 deleted at the store-es end. The proofs that ride shipped config stay: the CIA-01/06/08 credential rejects, the browser/service-leg accepts, the proxy paths, the CSP.

**Alternatives.** (a) Move them to a CI "infra validation" suite — refused: the dev stack's readiness is the compose healthchecks' job (DD-226), and a separate infra suite is where flakes go to be ignored. (b) Keep CIA-07's producers-flow as the telemetry canary — refused: Grafana's stack dashboard shows the pullers live, and every producer's own suite going green proves its export; a 90 s log-poll on the dev box proves less. (c) Keep the TLS test, verify against the container's own CA — refused: the CA is the workspace's, so the chain proves dev wiring by construction.

**Consequences.** The webapp e2e drops from 36 to 31 tests per browser (the two container-internals tests carried 120 s/90 s poll floors); the frontend-example suite from 17 to 16. Four CIA rules and SHL-11's TLS half join the fleet's explicitly-untested list, each with its note in the increment spec that owns it — the ledger DD-223 started, and the shape-A runner's first failure (DD-227's ESD-06) is exactly the flake class this sweep thins.

### DD-229. The shape-A tail overlaps, the test graph shares its daemon

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; follows the shape-A consolidation)
- **Date:** 2026-10-27

**Context.** Run 40471177041 — the first fully green shape-A pipeline — spent 38m 26s: tests 16m 59s (Nx: 9m 22s recoverable, default parallelism 3 against the container's 6 CPUs), Sonar 13m 28s (Nx: 85 % recoverable — the 25 scanners queue on the SonarQube Cloud server and idle the node), and fixed costs the serialised graph left on the table: docker-build (60 s) waits behind every test although images depend on source, the node\_modules cache save re-uploads \~40 s after a hit, and Storybook+Chromatic (2 m) wait behind sonar's queue.

**Decision.** Three overlaps in the single job, no new jobs: docker-build joins the test step's graph (`affected -t test e2e docker-build`) at `--parallel=5` — one CPU stays headroom for the e2e stacks' containers, which share this cgroup; the Storybook build launches in the background of the sonar step (detached with `setsid` — the runner kills each step's process tree at the step boundary, so a plain `&` dies there) and an "Await Storybook build" step joins its exit code after sonar, keeping the verdict; the cache save runs only on a restore miss. Sonar keeps its position — coverage, lcov and sarif must exist — and the overlap exploits its waiting.

**Alternatives.** (a) A parallel `storybook` job — refused: the consolidation to one job (shape A) is the point of the migration, and a second job pays pod startup plus a second daemon to save what the background build saves for free. (b) `--parallel=6` — the e2e composes' Keycloak/Elasticsearch/Tempo containers compete in the same cgroup; 5 leaves them a core. (c) Scoping Sonar engines per project (`sonar.javascript.file.suffixes=` etc.) — deferred: real, but it changes what Sonar analyses; it deserves its own measurement, not a ride-along.

**Consequences.** Expected 38m 26s → \~33m: \~1 min from the build overlap, up to 5m 21s from parallelism (Nx's estimate; contention caps the real recovery), \~2 min from storybook-under-sonar, \~40 s from the conditional save. The Storybook log moves to `storybook.log`, echoed at the join — failures appear at the await step, not live. If `--parallel=5` turns out to inflate e2e contention past what it recovers, the knob is one flag.

### DD-230. Parallelism stays at the default, the scanner cache moves to the PVC

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; supersedes DD-229's parallelism clause)
- **Date:** 2026-10-27

**Context.** DD-229's `--parallel=5` run (40486044342) failed two unit suites and got slower: the store-es suite's testcontainers Elasticsearch missed its 180 s health window, a fastapi auth fixture read-timed out, and the critical path grew 7m 37s → 10m 35s (run 17m 36s). Nx's "recoverable time" assumes tasks idle on CPU; here the 6-CPU cgroup is already spent on compose-stack JVMs (Elasticsearch, Keycloak, Tempo) and pytest workers, so the fifth lane buys queueing, not throughput. The same week's sonar measurement (store-es, local scanner): paired A/B runs of the as-is config vs engine-scoped suffixes (JS/TS/CSS/YAML/JSON/XML emptied) averaged 39.2 s vs 39.0 s — no effect. The 3.8 s → 0.2 s "plugin download" saving claimed earlier was a cold-vs-warm cache artifact: the scanner's download cache (\~382 MB — the cloud engine jar, a JRE, 13 plugin jars, content-addressed under `~/.sonar`) is identical for both configs; SonarCloud ships the full bundle to the CLI regardless of project languages. What the cache does explain is the CI sonar step's shape: the first task per pod pays the cold bootstrap (run 40471177041: otel:sonar 109 s vs \~15 s steady-state) because HOME is the container layer, wiped on every runner-pod boot, while uv/npm/ pre-commit caches live on PVC subPaths (arc-shapea-values.yaml).

**Decision.** (a) The test step keeps DD-229's docker-build graft at Nx's default parallelism — one flag, DD-229's consequence named it. (b) The scanner cache joins the PVC subPath set: `SONAR_USER_HOME=/var/cache/ci/sonar` in the runner command, a `.ci-cache/sonar` mount, dir created by cache-init — every pod's first sonar task stops paying \~94 s of jar downloads, and the first pod boot pays them once. (c) Sonar engine scoping is measured away: the suffix knobs are NOT added to any sonar-project.properties, retracting the store-es trial before it shipped.

**Alternatives.** (a) Keep `--parallel=5` with longer testcontainers timeouts — refused: DD-222..228 spent a week deleting exactly this flake class, and tuning a timeout to feed a lane Nx cannot fill is backwards. (b) actions/cache for `~/.sonar` — refused: the PVC subPaths are the established shape-A pattern for toolchain caches (no cache-server round-trip, warm across pods by construction). (c) Bake `~/.sonar` into the runner image — refused for now: the image rebuild cadence is slower than SonarCloud's plugin rotation, and stale cache entries are re-fetched by content hash anyway; the PVC gets the same warmth with no skew.

**Consequences.** The parallelism clause of DD-229 is retired (the overlaps survive — this run's own failures were unit tests, not the grafted builds). The sonar step's per-pod floor drops \~94 s; the engine-scoping idea retires with paired-run evidence, and DD-229's "85 % recoverable" sonar figure is re-read as the server queue, which no scanner flag fixes — future sonar tuning starts from the CI per-task times, not local guesses. The values change lands on the next `infra/arc/install.sh` run (helm upgrade evicts in-flight runner pods — run it between jobs).

### DD-231. Teardown downs the compose stacks: prune only sweeps corpses

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; repairs DD-229's teardown step)
- **Date:** 2026-10-27

**Context.** The shape-A teardown step names its purpose in its own comment — Keycloak/Postgres/Elasticsearch/observability hold \~8 Gi of the node's memory and the scan/sonar tail must not pay for it. It never happened: `docker container prune -f` sweeps only STOPPED containers, and the suites leave their stacks Up, so every run's teardown deleted exactly one corpse — the 28.67 kB testcontainers ryuk (runs 40471177041, 40486044342 and 40489544189 each report the same single container) — while the \~8 Gi rode through docker-build, the vuln scan, sonar and Chromatic on a node capped at 11 Gi.

**Decision.** The teardown iterates `docker compose ls --all -q` and runs `docker compose --project-name <p> down -v --remove-orphans` per project — the same project-name pattern the diagnostics step uses — keeping the prune pair behind it as the sweeper for non-compose strays (ryuk, anonymous volumes). `down` deletes containers, named volumes and networks; images stay, so the scan's daemon-read and the warm base-layer store are untouched (unchanged from the prune semantics).

**Alternatives.** (a) `docker stop $(docker ps -q)` — kills the stacks bluntly, with no per-project attribution in the log; refused for the readable footprint ("Tearing down compose project: …"). (b) Each suite downs its own stack — refused: the suites share the `dev/*` stacks (the E2E suite rule, DD-223), and a suite stopping one mid-graph evicts its neighbours. (c) Leave it — refused: the tail's memory pressure is the cgroup's, and sonar and Storybook pay it.

**Consequences.** The scan/sonar/Chromatic tail runs with the stacks' \~8 Gi free; the teardown step grows from 1 s to the seconds a four-stack `down` takes, naming each project as it goes. The stopped-container foreclosure the old comment guarded (run 40231127680) carries over unchanged. The step's log is the verification: it names each project it downs, and the prune tail stops reporting one 28.67 kB corpse as the step's whole output.

### DD-232. The CI pipeline is a fan-out DAG; the pool is per-pod emptyDir

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; supersedes DD-229's single-job clause)
- **Date:** 2026-10-27

**Context.** The single shape-A job (38m 04s green, run 40501485238) is two workloads stitched serially: the test phase (\~17 min of CPU/RAM saturation — e2e suites plus compose-stack JVMs) and the sonar step (13m 28s wall, \~85% of it SonarCloud *server* queue — 2m 4s of scanner, DD-230's re-read). One job on one 6-CPU cgroup can overlap them only by the DD-229 setsid dance, which hides Storybook, not sonar. The pool forbade splitting: the 50 Gi cache PD is ReadWriteOnce, so `arc-shapea-values.yaml` pins `maxRunners: 1` — a second runner pod cannot mount the work volume, and the docs recorded "a job on a second node starts cold". A spike scale set (own helm release, prod untouched) with an emptyDir work volume and `maxRunners: 2` measured the two open questions (run 40520070483, probes 14:20:02Z→14:23:09Z and 14:20:03Z→14:23:59Z): two jobs on the pool label run CONCURRENTLY on separate pods; per-pod markers on the work volume stay per-pod (no shared state); JIT pod boot is 15–17 s on a warm node (a cold node pays \~3 min pulling the 546 MB runner image); and a cold daemon pulls the two heaviest dev-stack images in 48 s, the second in 0.0 s once the node has the layers (GKE image-cache sharing). Node facts measured at the same time: 3 × (4 CPU / 13.6 Gi allocatable), so pod *requests* of 1 CPU/4 Gi let three runner pods pack on ONE node — anti-affinity, not requests, is what spreads them.

**Decision.** (a) `ci.yaml` becomes a fan-out DAG: `validate` (checkout, install, pre-commit --all-files, decrypt, unit `test`, coverage upload) gates three concurrent jobs — `e2e` (the `e2e` + `docker-build` graph, diagnostics, DD-231 teardown), `scan-sonar` (image rebuild from the buildcache, trivy, sarif, `sonar`), and `chromatic` (Storybook build + publish). Scan and sonar co-locate in one job: the sarif handoff stays on the work volume. (b) Cross-job state rides artifacts (coverage upload/download) or rebuilds (GHCR buildcache images) — jobs never share files through the volume. (c) The pool: the RWO PD retires; the work volume becomes a per-pod 20 Gi `emptyDir` (warm within a pod — caches, image stores, registry auth survive between jobs; cold across pods — 48 s worst measured). `minRunners: 2` (warm pair: fan-out jobs start in \~15 s; a cold-node start pays the image pull), `maxRunners: 3` (the three fan-out jobs), a PREFERRED pod anti-affinity on `kubernetes.io/hostname` (spreads across nodes; packing degrades gracefully where `required` would deadlock a queue), requests stay 1 CPU/4 Gi (limits 6 CPU/11 Gi), and the cluster autoscaler ceiling goes 2 → 3 nodes.

**Alternatives.** (a) Per-pod PDs via a StorageClass — dead before the spike: ARC builds job pods from `template.spec`, with no StatefulSet and no `volumeClaimTemplates` (chart 0.15.1), so per-runner PVCs need an external provisioner webhook. (b) Filestore (RWX) shared cache — blocked by billing-account policy (on record). (c) Keep the single job and parallelise inside it — exhausted: DD-229/230 measured the in-job overlaps and the parallelism knob; the serial test→sonar wall is the server queue, which only a second job (running *while* the first waits) dissolves. (d) `requiredDuringScheduling` anti-affinity — refused: three nodes is the steady state, not a guarantee; a job queued forever while the autoscaler provisions is worse than a packed pod.

**Consequences.** Wall-time target: 38 min → \~26–28 min: validate \~7 min, then the longest fan-out branch (e2e \~17 min with its own stacks, scan-sonar \~15 min mostly server-queue). Measured on the first run (40531441140, green): **27m 48s** — validate 8m 55s gates chromatic 3m 46s, scan-sonar 16m 20s (sonar 11m 12s of server queue, 2m 49s the buildcache rebuild) and e2e 17m 42s (15m 32s of suites) on three pods; the e2e job is the critical path, 2m 19s off the sonar branch. The DD-229 setsid/await dance retires with the single job. Each job pays checkout+install (\~2 min, node\_modules from the cache server) — the fork's price, \~3×. The `e2e` job is now the pipeline's only stack owner, so DD-231's teardown is a single named step, not a tail. Caches are per-pod: a pod respawn cold-starts uv/npm/sonar/docker once (48 s–2 min), the warm pair absorbs it. Next free DD: 233.

### DD-233. The toolchain caches bridge pod churn through the cache server

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; repairs DD-232's cache-warmth assumption)
- **Date:** 2026-10-27

**Context.** DD-232 recorded that per-pod emptyDir caches make a pod respawn cold "once (48 s–2 min), the warm pair absorbs it". The fan-out pool churns pods constantly — scale-in after every run, helm deploys, preemptions — so a `validate` landing on a never-seen pod is the norm. Measured on run 40538065508 (warm run, fresh pod): the pre-commit step spent 66 s re-`Installing environment` for its seven hook repos (talisman's Go build alone \~40 s) before the first hook ran — step time 181 s where the RWO-PD single job (a pod alive for weeks, caches hot) spent 83 s; hook *execution* is identical in both (96 s). The install step pays the same tax on uv's side (\~25 s of wheel re-downloads; npm does not — node\_modules rides the cache server and restores in \~10 s). The old pipeline's "4 s python / 20s node" warmth was the PD's weeks-long pod life, not a better mechanism.

**Decision.** Bridge the cold-pod gap through the existing in-cluster `actions/cache` server (the same backend node\_modules uses, LAN speed, OIDC-scoped): `validate` restores uv (keyed `uv.lock`) and pre-commit (keyed `.pre-commit-config.yaml`) and saves both on miss — single writer, the node\_modules shape; the three fan-out jobs restore uv; `scan-sonar` restores/saves the SonarScanner jar cache (DD-230's \~94 s per-pod bootstrap, save after the analysis since the jars land during it). The emptyDir stays the warm tier *within* a pod; the cache server is the cross-pod tier. Keying on the config files makes every cache rebuild exactly-once per version bump.

**Alternatives.** (a) Pin runner pods warm (higher `minRunners`) — refused: absorbs some churn, pays idle pods for all of it, and helm deploys evict anyway. (b) Return to a shared RWX volume — Filestore is blocked by billing-account policy (on record). (c) Bake the caches into the runner image — refused for the same reasons as DD-230's `~/.sonar` bake (rotation cadence), and the config-keyed caches self-invalidate where image layers go stale.

**Consequences.** Cold-pod validate drops \~66 s (pre-commit envs) and \~25 s (uv wheels); scan-sonar's first-run sonar bootstrap drops \~94 s on a fresh pod. First run per key version pays the build (the save-on-miss upload, \~1 min for the uv cache at LAN speed) and every pod everywhere rides the artifact after. The cache server PD (20 Gi, LRU at 90 %) grows by uv (\~2–3 Gi) + pre-commit (\~0.5 Gi) + sonar (\~0.4 Gi) — headroom verified against the 18 Gi eviction line. The "4 s/20 s" memory is restored where it applies (warm installs on any pod); the ephemeral-tree rule is untouched. Next free DD: 234.

Measured (run 40549779734, fixed fleet, all caches warm on the server): all restores hit and extract clean (zero `Cannot utime`), validate's pre-commit step 181s -\> **82s** (the old always-warm PD pod was 83s - parity), uv install 26s, scan-sonar 16m 20s -\> **12m 2s** (the sonar jar cache rides the bridge too), validate 8m 55s -\> **7m 0s**, full pipeline 27m 48s -\> **25m 48s** with the e2e suites now the critical path. The restore step's metadata bug (subPath mount roots stay root-owned under fsGroup - k8s applies it to volume roots only; cache-init chowns them now) shipped in the same change.

### DD-247. Journal writes do not wait for a refresh

- **Status:** Proposed
- **Increment:** cross-cutting (no roadmap row; found by 5.2a's e2e)
- **Date:** 2026-10-30

**Decision.** The journal entry's write, its commit and its delete (DD-046) no longer carry `refresh="wait_for"`; the entity bulk, the restores and the audit append keep it (DD-237, ENS-11). Recovery lists the journal's entries by a search, as before, and acts on each as a real-time `get` by its write id reads it now: an entry already deleted, or still within its lease, is left alone. This supersedes DD-237's choice for the journal only; the rest of DD-237 stands.

**Reason.** On the dev store every entity write cost about 2.8 s: four writes each waiting for a refresh (about 1 s each with the default refresh interval), three of them the journal's. A glossary write is several entity and relationship writes, so creating a child category took 9 s and deleting a glossary 18 s, past the e2e client's timeout. DD-237 kept the journal's refresh for recovery, which "reads entries written moments before"; but recovery acts only on entries whose 60-second lease has passed, long after the index's own refresh has made them searchable, and the real-time `get` closes the remaining gap: a listing that lags an entry's commit or delete cannot make recovery undo a write that finished. With the change a write costs about 0.9 s on the dev store.

**Alternatives.** A shorter refresh interval: every write still pays for refreshes no reader needs. Trimming the glossary's writes: helps one feature, and departs from Atlas's sequence of writes.

**Consequences.** A journal entry may be missing from a search for up to the refresh interval after it is written; nothing but recovery searches it. ENS-11's text names the journal as unrefreshed.

### DD-281. The container-outage and edge-flood e2e proofs retire; the shipped limiter stays

- **Status:** Accepted
- **Increment:** 10.5 (rollout step 0)
- **Date:** 2026-11-02

**Context.** The 10.5 rollout (DD-280) moves the e2e suites onto the Helm/minikube lane, and three scenarios have no lane to migrate to. RSL-01 (webapp suite) and RSL-02 (lineage chain) stop and start **compose containers** through the docker SDK, found by compose labels (`com.docker.compose.project`); a minikube pod has no counterpart to that handle, and rebuilding the arrangement on `kubectl delete pod` + restart buy back two browser-visible symptoms — a bell badge after a 502, an Atlas-shaped 502 body — that the unit suites already pin in-process (7.7's `HttpTestingController` alert chain, 8.5's fake-transport LM-12 suite). SRV-09's rate-limit test is worse: it proves the bucket by outspending it, which works only because `e2e/config/nginx.conf` ships a **test-sized** twin (60r/m burst 20) the live-flood can overflow in seconds; the shipped browser-sized bucket (300r/m burst 100, geo-allowlisted so suite traffic passes unlimited) is unprovable through a live flood at suite speed on any lane, and the cluster edge adds a second limiter layer on top.

**Decision.** Delete the three proofs, in both lanes, and retire their rule ids rather than park them as skips:

- `test__aurelius_atlas_webapp_resilience.py` keeps only the RSL-03 logout round-trip (browser-only, migrates cleanly in 10.5c); its outage fixture, docker-SDK helpers, and RSL-01 test go.
- `test__aurelius_atlas_lineage_model_resilience_e2e.py` goes whole; its `covers` markers also named LM-12 and CL-30, which stay pinned by the scenarios files and the client suites.
- `test__aurelius_atlas_webapp_rate_limit.py` goes whole, and with it the test-sized `atlas_api` zone in `e2e/config/nginx.conf` (a bucket with no test keeps no config). RSL-03 and the `atlas_otel` zone (CHT-100, chart-guarded) stay.

**What stands.** The shipped limiter itself is untouched: both `nginx.conf.template` copies (image + helm byte-copy), the geo/map key pair, `limit_req_status 429`, DV-87, and the chart-render guards. SRV-09 retires as an *e2e rule* — the config remains part of the product, guarded where it is deterministic to guard (rendered manifests), and no longer where it was only ever provable against a fixture-sized twin.

**Consequences.** 9.1 narrows to RSL-03; 9.3's limiter row carries the retirement note; the conversion index rows for 9.1/9.3 and the lineage conftest's timeout rationale follow. docker-py leaves the direct-use column (its two consumers were these files; it stays installed as a testcontainers transitive). The step runs **before** the suite migrations so the shared lane library (10.5b) never has to carry an outage-orchestration API nobody intends to use.

Next free DD: 282.

### DD-295. Chart-track id collisions with main renumber above both ranges

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the rebase of the 10.x chart track onto the 4.3–6.1 merges, PRs \#157–\#191)
- **Date:** 2026-11-01

**Decision.** The 4.3–6.1 track on main (DSL, lineage, glossaries, auth) and the 10.x chart track branched at DD-239/DV-87 and minted ids in parallel: main took DD-240..251 and DV-88..109, the chart track took DD-240..252 (12 colliding ids — the same numbers, different decisions) plus DV-88/89 in its 10.7/10.8 increments, its children continuing at DD-253..282. The rebase renumbers the **chart side of the collision**: DD-240..251 → DD-283..294 in ascending order, and DV-88/89 → DV-112/113 — and this entry (DD-295) records it. Main's ids keep their numbers. The chart track's DD-252..282 already sit above both ranges and are untouched; the 10.1 chain citation `DD-240..252` becomes the explicit list `DD-298, DD-283..294`. The citation sweep rewrote every chart spec, doc, chart template, plugin comment, CI workflow, and test on the chart side; DD-177 is the precedent for the method.

**Reason.** Main's 4.3–6.1 decisions are merged and cited by merged code — they are the accepted record, and the ledger's rule (numbers are never reused, accepted entries are never edited) protects them. The chart track is the in-progress side of the same ledger, so it is the side allowed to move; moving 12+2 ids in one mechanical, reviewable sweep costs less than living with ids that mean two things. The new range starts above the chart track's own DD-282, so the track's later ids keep their citations.

**Consequences.** The rebase of the chart chain onto main is conflict-free for the id ledger: the two tracks occupy disjoint ranges. Every pre-rebase commit message cites the OLD numbers — commit history is not rewritten further, and this appendix is the lookup from a commit's citation to the merged record.

| Old | New | Old | New | Old | New |
| --- | --- | --- | --- | --- | --- |
| DD-240 | DD-283 | DD-245 | DD-288 | DD-250 | DD-293 |
| DD-241 | DD-284 | DD-246 | DD-289 | DD-251 | DD-294 |
| DD-242 | DD-285 | DD-247 | DD-290 | DV-88 | DV-112 |
| DD-243 | DD-286 | DD-248 | DD-291 | DV-89 | DV-113 |
| DD-244 | DD-287 | DD-249 | DD-292 | — | — |

**Addendum (2026-11-01, this merge).** 4.5 (\#194) then minted main’s `DD-252` and `DV-110`, so ids this entry left in place collided: they move to `DD-298` and `DV-112`, and the paired `DV-111` shifts with it to `DV-113` — one sweep, same rule. Chart `DD-252` → `DD-298`, `DV-110/111` → `DV-112/113`; main keeps `DD-252` and `DV-110`.

### DD-302. Business attributes are stored among the entity's attributes under their qualified names

- **Status:** Proposed
- **Increment:** 5.3b
- **Date:** 2026-11-01

**Decision.** An entity's business attribute values are kept in its stored document's `attributes`, each under the attribute's qualified name, `<business metadata>.<attribute>`, mapped as an entity attribute's value is (`EntityMapper`). Reads collect them per business metadata from the entity type's business attributes.

**Reason.** Atlas keeps them as vertex properties of exactly that name, beside the entity's own attributes, and maps them with `mapAttribute`. A business metadata's name is a type name, so its qualified names cannot collide with an entity attribute's (`<entity type>.<attribute>`). Keeping them in `attributes` means every write that copies an entity's attributes keeps them, as Atlas's entity updates leave them, and the search fields can be built from them as from the entity's own attributes when business metadata becomes searchable.

**Alternatives.** A separate `businessAttributes` object in the document: closer to the REST shape, but each write path would have to carry it across, and the values would need their own mapping and indexing.

**Consequences.** Removing a business metadata type leaves values of its qualified names in stored documents; Atlas leaves its vertex properties too. Nothing reads them without the type.

## Moved entries

The entries moved next to the increment they record. The record is the truth; the status here is a copy of the one at the time of the move. New entries go to the increment's `design.md`, never here.

| \# | Decision | Status | Design record |
| --- | --- | --- | --- |
| DD-001 | Reference is Apache Atlas 2.4.0, and both dashboards are served | Accepted | `specs/0-1-adopt-template/design.md` |
| DD-002 | Atlas code lives in aurelius-atlas projects split by layer | Accepted | `specs/0-1-adopt-template/design.md` |
| DD-003 | Template projects are renamed to the aurelius-atlas prefix | Accepted | `specs/0-1-adopt-template/design.md` |
| DD-004 | The SPA keeps tokens in memory and renews them silently | Accepted | `specs/0-1-adopt-template/design.md` |
| DD-005 | The store uses the official async Elasticsearch client | Proposed | `libs/python/aurelius-atlas-store-es/specs/0-2-elasticsearch-infrastructure/design.md` |
| DD-006 | Development and tests run Elasticsearch with security on | Proposed | `dev/elasticsearch/specs/0-2-elasticsearch-infrastructure/design.md` |
| DD-007 | The Elasticsearch test fixture ships with the store library | Proposed | `libs/python/aurelius-atlas-store-es/specs/0-2-elasticsearch-infrastructure/design.md` |
| DD-008 | A yellow cluster is healthy | Proposed | `libs/python/aurelius-atlas-store-es/specs/0-2-elasticsearch-infrastructure/design.md` |
| DD-009 | Traceability is checked from collected markers, not from a test run | Proposed | `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md` |
| DD-010 | The traceability check covers Atlas code from increment 0.2 on | Proposed | `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md` |
| DD-011 | The test report is generated from JUnit, coverage and trace files | Proposed | `libs/python/aurelius-atlas-trace/specs/0-3-test-report-traceability/design.md` |
| DD-012 | Parity scenarios are YAML files run as parametrised pytest tests | Proposed | `libs/python/aurelius-atlas-parity/specs/0-4-parity-harness/design.md` |
| DD-013 | A scenario response is compared exactly, except at declared paths | Proposed | `libs/python/aurelius-atlas-parity/specs/0-4-parity-harness/design.md` |
| DD-014 | Scenario facts reach the report as test properties | Proposed | `libs/python/aurelius-atlas-trace/specs/0-4-parity-harness/design.md` |
| DD-015 | The server is a FastAPI application with one router per Atlas resource | Proposed | `apps/aurelius-atlas-server/specs/0-5-server-skeleton/design.md` |
| DD-016 | The server does not start without its store | Proposed | `apps/aurelius-atlas-server/specs/0-5-server-skeleton/design.md` |
| DD-017 | The dashboards are vendored unchanged and built with dart-sass on Node 24 | Proposed | `apps/aurelius-atlas-dashboard/specs/0-6-dashboards/design.md` |
| DD-018 | The server serves the dashboards from the API's origin | Proposed | `apps/aurelius-atlas-server/specs/0-6-dashboards/design.md` |
| DD-019 | The template examples stay until the plan is done | Proposed | `apps/aurelius-atlas-server/specs/0-6-dashboards/design.md` |
| DD-020 | Typedef models are Pydantic models that read and write Atlas's JSON | Proposed | `libs/python/aurelius-atlas-model/specs/1-1-typedef-models/design.md` |
| DD-021 | Set-valued fields keep each name once, in first-seen order | Proposed | `libs/python/aurelius-atlas-model/specs/1-1-typedef-models/design.md` |
| DD-022 | Typedef timestamps are aware datetimes, written as epoch milliseconds | Proposed | `libs/python/aurelius-atlas-model/specs/1-1-typedef-models/design.md` |
| DD-023 | Atlas errors live in the model library | Proposed | `libs/python/aurelius-atlas-typesystem/specs/1-2-type-registry/design.md` |
| DD-024 | The registry is updated on a transient copy under a re-entrant lock | Proposed | `libs/python/aurelius-atlas-typesystem/specs/1-2-type-registry/design.md` |
| DD-025 | The type system ports the definition side only | Proposed | `libs/python/aurelius-atlas-typesystem/specs/1-2-type-registry/design.md` |
| DD-026 | Dynamic attributes and search lookups wait for their increments | Proposed | `libs/python/aurelius-atlas-typesystem/specs/1-3-type-hierarchies/design.md` |
| DD-027 | Derived type sets keep first-seen order | Proposed | `libs/python/aurelius-atlas-typesystem/specs/1-3-type-hierarchies/design.md` |
| DD-028 | The type definitions are one Elasticsearch document | Proposed | `libs/python/aurelius-atlas-core/specs/1-4-typedef-store/design.md` |
| DD-029 | Server processes share the type definitions through the document's version | Proposed | `libs/python/aurelius-atlas-core/specs/1-4-typedef-store/design.md` |
| DD-030 | The store asks the entity store whether a type is in use | Proposed | `libs/python/aurelius-atlas-core/specs/1-4-typedef-store/design.md` |
| DD-031 | The patch records live in the typedef document | Proposed | `libs/python/aurelius-atlas-core/specs/1-5-builtin-models/design.md` |
| DD-032 | The built-in models are vendored unchanged and read from a directory | Proposed | `libs/python/aurelius-atlas-core/specs/1-5-builtin-models/design.md` |
| DD-033 | Start-up loading is one change per model file and per patch | Proposed | `libs/python/aurelius-atlas-core/specs/1-5-builtin-models/design.md` |
| DD-034 | Lists of type definitions are sorted by name | Proposed | `apps/aurelius-atlas-server/specs/1-6-types-rest/design.md` |
| DD-035 | Type scenarios create what they read and delete it at their end | Proposed | `apps/aurelius-atlas-server/specs/1-6-types-rest/design.md` |
| DD-036 | Start-up loading tries a raced change again | Proposed | `apps/aurelius-atlas-server/specs/1-6-types-rest/design.md` |
| DD-037 | Instance models are one module per Java class | Proposed | `libs/python/aurelius-atlas-model/specs/2-1-entity-models/design.md` |
| DD-038 | Attribute values stay plain JSON values until their types read them | Proposed | `libs/python/aurelius-atlas-model/specs/2-1-entity-models/design.md` |
| DD-039 | One Atlas JSON codec reads floats as decimals and writes them with their digits | Proposed | `libs/python/aurelius-atlas-model/specs/2-1-value-types/design.md` |
| DD-040 | Java values are held as the Python values closest to them | Proposed | `libs/python/aurelius-atlas-typesystem/specs/2-1-value-types/design.md` |
| DD-041 | The type system is one module per Java type class too | Proposed | `libs/python/aurelius-atlas-typesystem/specs/2-1-value-types/design.md` |
| DD-042 | A validity period without a time zone is in UTC | Proposed | `libs/python/aurelius-atlas-typesystem/specs/2-1-value-types/design.md` |
| DD-043 | Entities are documents of one index, their attributes under qualified names | Proposed | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md` |
| DD-044 | A GUID is a random UUID | Proposed | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md` |
| DD-045 | Unique values are reserved by create-only documents | Proposed | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md` |
| DD-046 | A multi-entity write is all or nothing, through a journal | Proposed | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md` |
| DD-047 | Entities are written conditionally on their Elasticsearch version | Proposed | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md` |
| DD-048 | A type is in use while the entity index holds one of it | Proposed | `libs/python/aurelius-atlas-core/specs/2-2-entity-store/design.md` |
| DD-049 | Attribute values are stored normalised; a struct inline, a reference as a GUID | Proposed | `apps/aurelius-atlas-server/specs/2-3-entity-read-rest/design.md` |
| DD-050 | Relationship attributes read empty until relationships are stored | Superseded by DD | `apps/aurelius-atlas-server/specs/2-3-entity-read-rest/design.md` |
| DD-051 | Entity reads are tested on entities written through the store until 2.4 | Proposed | `apps/aurelius-atlas-server/specs/2-3-entity-read-rest/design.md` |
| DD-052 | A request is mapped in memory and written once; a lost race runs it again | Proposed | `apps/aurelius-atlas-server/specs/2-4-entity-write-rest/design.md` |
| DD-053 | Relationship attribute values are resolved, but stored only as legacy attributes until 3.1 | Superseded by DD | `apps/aurelius-atlas-server/specs/2-4-entity-write-rest/design.md` |
| DD-054 | Dynamic attributes are evaluated in first-seen dependency order | Proposed | `apps/aurelius-atlas-server/specs/2-4-entity-write-rest/design.md` |
| DD-055 | Scenarios name what they create with a per-run value | Proposed | `apps/aurelius-atlas-server/specs/2-4-entity-write-rest/design.md` |
| DD-056 | An entity write also removes documents, journaled like the others | Proposed | `libs/python/aurelius-atlas-core/specs/2-5-delete-semantics/design.md` |
| DD-057 | Entities referring to one are found through an indexed field of GUIDs | Proposed | `libs/python/aurelius-atlas-core/specs/2-5-delete-semantics/design.md` |
| DD-058 | A stored reference stands for an edge: active for a delete, deleted for a purge | Proposed | `libs/python/aurelius-atlas-core/specs/2-5-delete-semantics/design.md` |
| DD-059 | The delete type and its override are server settings | Proposed | `apps/aurelius-atlas-server/specs/2-5-delete-semantics/design.md` |
| DD-060 | The owned-reference cascade moves from 3.2 to 2.5 | Proposed | `libs/python/aurelius-atlas-core/specs/2-5-delete-semantics/design.md` |
| DD-061 | Relationships are documents of their own index, listed by both ends | Proposed | `libs/python/aurelius-atlas-core/specs/3-1-relationship-instances/design.md` |
| DD-062 | An entity write also writes relationships, all or nothing | Proposed | `libs/python/aurelius-atlas-core/specs/3-1-relationship-instances/design.md` |
| DD-063 | 3.1 is split into relationship instances and relationship attributes | Proposed | `libs/python/aurelius-atlas-core/specs/3-1-relationship-instances/design.md` |
| DD-064 | Relationship attribute values are relationships | Proposed | `libs/python/aurelius-atlas-core/specs/3-1-relationship-attributes/design.md` |
| DD-065 | A relationship keeps one array index, the last writer's | Proposed | `libs/python/aurelius-atlas-core/specs/3-1-relationship-attributes/design.md` |
| DD-066 | Relationship attributes are mapped in memory and written with the entities | Proposed | `libs/python/aurelius-atlas-core/specs/3-1-relationship-attributes/design.md` |
| DD-067 | Delete cascades follow owned relationships from 3.1b | Proposed | `libs/python/aurelius-atlas-core/specs/3-1-relationship-attributes/design.md` |
| DD-068 | Owned entities an update drops are deleted through a view of the request | Proposed | `libs/python/aurelius-atlas-core/specs/3-2-ownership-cascades/design.md` |
| DD-069 | A reference to a deleted entity stands for a deleted edge when reviving | Proposed | `libs/python/aurelius-atlas-core/specs/3-2-ownership-cascades/design.md` |
| DD-070 | Classification instances are documents of their own index, listed by their entity | Proposed | `libs/python/aurelius-atlas-core/specs/3-3-direct-classifications/design.md` |
| DD-071 | An entity write also writes classification instances, all or nothing | Proposed | `libs/python/aurelius-atlas-core/specs/3-3-direct-classifications/design.md` |
| DD-072 | The propagation defaults are Atlas's defaults | Proposed | `libs/python/aurelius-atlas-core/specs/3-3-direct-classifications/design.md` |
| DD-073 | 3.3 is split into direct classifications and the bulk associator | Proposed | `libs/python/aurelius-atlas-core/specs/3-3-direct-classifications/design.md` |
| DD-074 | `bulk/headers` moves to 3.5 | Proposed | `libs/python/aurelius-atlas-core/specs/3-3-bulk-classifications/design.md` |
| DD-075 | A propagated classification is listed by the entities it reaches | Proposed | `libs/python/aurelius-atlas-core/specs/3-4-classification-propagation/design.md` |
| DD-076 | The entities a classification reached are found through an indexed field | Proposed | `libs/python/aurelius-atlas-core/specs/3-4-classification-propagation/design.md` |
| DD-077 | Propagation runs within the request until 3.4b | Proposed | `libs/python/aurelius-atlas-core/specs/3-4-classification-propagation/design.md` |
| DD-078 | 3.4 is split into propagation and propagation tasks | Proposed | `libs/python/aurelius-atlas-core/specs/3-4-classification-propagation/design.md` |
| DD-079 | Tasks are documents of their own index, written with the change that records them | Proposed | `libs/python/aurelius-atlas-core/specs/3-4-propagation-tasks/design.md` |
| DD-080 | Every server process runs tasks, each claimed with a lease | Proposed | `libs/python/aurelius-atlas-core/specs/3-4-propagation-tasks/design.md` |
| DD-081 | Tasks are enabled by a server setting, on by default | Proposed | `libs/python/aurelius-atlas-core/specs/3-4-propagation-tasks/design.md` |
| DD-082 | Audit events are documents of their own index, written after the change | Proposed | `libs/python/aurelius-atlas-core/specs/3-5-entity-audit/design.md` |
| DD-083 | Audit events keep Atlas's event keys and their order | Proposed | `libs/python/aurelius-atlas-core/specs/3-5-entity-audit/design.md` |
| DD-084 | The entity writer tells a change notifier what it changed | Proposed | `libs/python/aurelius-atlas-core/specs/3-5-entity-audit/design.md` |
| DD-085 | Classification events are collected in the request and recorded after its write | Proposed | `libs/python/aurelius-atlas-core/specs/3-5-classification-audit/design.md` |
| DD-086 | Tag propagation records the propagations a request added and removed | Proposed | `libs/python/aurelius-atlas-core/specs/3-5-classification-audit/design.md` |
| DD-087 | Basic search is split into entity and classification search | Proposed | `libs/python/aurelius-atlas-core/specs/4-1-entity-search/design.md` |
| DD-088 | Entity attributes are searched in typed search fields named after their defining type | Proposed | `libs/python/aurelius-atlas-core/specs/4-1-entity-search/design.md` |
| DD-089 | A search is a query of the entity documents, ordered by creation when no sort is given | Proposed | `libs/python/aurelius-atlas-core/specs/4-1-entity-search/design.md` |
| DD-090 | A classification search finds instances first, then the entities listing them | Proposed | `libs/python/aurelius-atlas-core/specs/4-1-classification-search/design.md` |
| DD-091 | Free text is split from quick search | Proposed | `libs/python/aurelius-atlas-core/specs/4-2-free-text/design.md` |
| DD-092 | String search fields carry an analysed text sub-field, searched with Atlas's weights | Proposed | `libs/python/aurelius-atlas-core/specs/4-2-free-text/design.md` |
| DD-093 | Facets are aggregations of the search's own query | Proposed | `libs/python/aurelius-atlas-core/specs/4-2-quick-search/design.md` |
| DD-094 | Suggestions are terms aggregations of the text sub-fields | Proposed | `libs/python/aurelius-atlas-core/specs/4-2-quick-search/design.md` |
| DD-126 | The webapp is a new project, not the Aurelius app upgraded in place | Proposed | `apps/aurelius-atlas-webapp/specs/7-0-webapp-foundation/design.md` |
| DD-127 | Signals replace the custom store; each slice owns its state | Proposed | `apps/aurelius-atlas-webapp/specs/7-0-webapp-foundation/design.md` |
| DD-128 | Aurelius dictionaries become XLIFF, migrated whole, with the JSON as fixture | Proposed | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md` |
| DD-129 | Google Analytics and clickstream are dropped, not ported | Proposed | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md` |
| DD-130 | The webapp's config is a typed AppConfig, and `environment.ts` is not ported | Proposed | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md` |
| DD-131 | Webapp purity is a checked gate, not a review convention | Proposed | `apps/aurelius-atlas-webapp/specs/7-0-webapp-foundation/design.md` |
| DD-132 | The wildcard fallback redirects to the destination, not through the root | Proposed | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md` |
| DD-133 | Operational telemetry lands with 7.1; the auth wiring stays with 7.3 | Proposed | `apps/aurelius-atlas-webapp/specs/7-1-webapp-shell/design.md` |
| DD-134 | The design-system slice ports the in-use components, not the library | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md` |
| DD-135 | Component services dissolve into signal state; nothing is ported as a store | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md` |
| DD-136 | Shared chrome strings are localisation units keyed by the legacy dictionary paths | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md` |
| DD-137 | The purity gate is made executable over `libs/angular` | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md` |
| DD-138 | The Storybook preview loads `@angular/localize/init` | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-2-design-system/design.md` |
| DD-139 | The client owns the base URL; the proxy forwards the prefix untouched | Proposed | `libs/angular/aurelius-atlas-data-access/specs/7-3-api-client-auth/design.md` |
| DD-140 | The REST client ports the live surface; the search client is redesigned in 7.4 | Proposed | `libs/angular/aurelius-atlas-data-access/specs/7-3-api-client-auth/design.md` |
| DD-141 | Auth is guarded at the app root; the bearer token is stated inert until 6.1 | Proposed | `apps/aurelius-atlas-webapp/specs/7-3-api-client-auth/design.md` |
| DD-142 | The webapp e2e stack runs the real Atlas server behind the proxy | Proposed | `apps/aurelius-atlas-webapp/specs/7-3-api-client-auth/design.md` |
| DD-143 | The landing page is ported statically; search affordances and Shell chrome join the search slice | Proposed | `apps/aurelius-atlas-webapp/specs/7-5-browse-landing/design.md` |
| DD-144 | i18n ids carry no description suffix; the bridge key must equal the extracted id | Proposed | `apps/aurelius-atlas-webapp/specs/7-5-browse-landing/design.md` |
| DD-145 | The Shell chrome is ported search-free; the root composes header and footer | Proposed | `apps/aurelius-atlas-webapp/specs/7-11-shell-chrome/design.md` |
| DD-146 | Session chrome injects the keycloak-js `Keycloak` instance, not keycloak-angular's `KeycloakService` | Accepted | `apps/aurelius-atlas-webapp/specs/7-11-shell-chrome/design.md` |
| DD-147 | Dev Keycloak users carry `default-roles-master` explicitly | Accepted | `apps/aurelius-atlas-webapp/specs/7-11-shell-chrome/design.md` |
| DD-148 | The Aurelius brand lands on Bulma 1 tokens, light-forced, legacy metrics pinned | Accepted | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md` |
| DD-149 | Critical-CSS inlining is off: the zoneless CSR app never swaps the print sheet | Accepted | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md` |
| DD-150 | The sticky footer is the legacy rule verbatim; page content sits on Bulma's grid | Accepted | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md` |
| DD-151 | The brand re-emits Bulma 0.9.4's text ramp, not just the body metrics | Accepted | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md` |
| DD-152 | The accent ramp: primary stays Bulma teal, the accents take the Bootstrap map | Proposed | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md` |
| DD-153 | The mobile burger chrome: grey burger, blended dropdowns, legacy logout anchor | Proposed | `apps/aurelius-atlas-webapp/specs/7-12-theme-branding-layout/design.md` |
| DD-154 | The entity card emits `entityClicked`; the caller navigates | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-13-ui-components-details/design.md` |
| DD-155 | The select is one field with a `searchRequested` output | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-13-ui-components-details/design.md` |
| DD-156 | The brand ships a dark ink ramp on Bulma's dark hosts | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-13-ui-components-details/design.md` |
| DD-157 | The drawer is a new ui-lib component, not a Modal or a dropdown | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-158 | The telemetry switch stops exports immediately and starts them on reload | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-159 | The theme choice is applied pre-render; SHM-01's light pin is superseded by a light default | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-160 | Settings are a facade over one owner service per category | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-161 | Settings are browser-scoped localStorage; server-side persistence is the follow-up slice | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-162 | The drawer animates in and out; the layer's life is the exit animation's | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-163 | The drawer styles itself with fallbacks; Bulma's modal tokens are `.modal`-scoped | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-164 | The Appearance picker is the ui-lib Select; the Select gains `searchVisible` | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-165 | About shows one version; the server is not fetched | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-166 | The settings panel is a routed overlay in the `drawer` aux outlet | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-167 | Settings-drawer polish: lit gear, scheme-following band, Browser-default picker, `.label` headings | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-168 | The navbar follows the scheme: the dark slate band | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-169 | Settings headings are the controls' accessible names | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-170 | The active locale is filled with the Aurelius blue | Accepted | `apps/aurelius-atlas-webapp/specs/7-14-settings-panel/design.md` |
| DD-171 | The alerts store groups by a quiet window | Accepted | `apps/aurelius-atlas-webapp/specs/7-15-alerts-drawer/design.md` |
| DD-172 | The app's ErrorHandler chains: alert, then trace | Accepted | `apps/aurelius-atlas-webapp/specs/7-15-alerts-drawer/design.md` |
| DD-173 | The HTTP reporter: 5xx and network failures on /api | Accepted | `apps/aurelius-atlas-webapp/specs/7-15-alerts-drawer/design.md` |
| DD-174 | The bell: severity badge and ring, one outlet | Accepted | `apps/aurelius-atlas-webapp/specs/7-15-alerts-drawer/design.md` |
| DD-175 | AlertList and Badge are ui-lib presentational components | Accepted | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md` |
| DD-176 | The chip's pinned pair; Clear all in the drawer head | Accepted | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md` |
| DD-180 | The inbox bar: severity chips, read tracking, Clear all in the bar | Accepted | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md` |
| DD-181 | The drawer's body is the scroll container | Accepted | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md` |
| DD-182 | The inbox bar is one joined group, severity-coloured, ramp order | Accepted | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md` |
| DD-183 | The inbox bar is one height: the count badge is compacted | Accepted | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md` |
| DD-184 | The void chip: an empty severity greys out | Accepted | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md` |
| DD-185 | Show all is gone: the bar's shape never shifts | Accepted | `libs/angular/aurelius-atlas-ui/specs/7-15-alerts-drawer/design.md` |
| DD-186 | Entity details arrives as a routed skeleton; its data spine joins 2.3 | Proposed | `apps/aurelius-atlas-webapp/specs/7-6-entity-details/design.md` |
| DD-187 | The entity client is built test-first against the Atlas wire format | Proposed | `apps/aurelius-atlas-webapp/specs/7-6-entity-details/design.md` |
| DD-188 | One API base: the client's URLs all ride the API\_BASE\_URL token | Accepted | `apps/aurelius-atlas-webapp/specs/7-6-entity-details/design.md` |
| DD-189 | The details chip is the classification chip; its sources project in | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-16-ui-components-details-ii/design.md` |
| DD-190 | The type-name badge is extracted from entity-card | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-16-ui-components-details-ii/design.md` |
| DD-191 | Details navigation is a shell; the scroll directive stays app-side | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-16-ui-components-details-ii/design.md` |
| DD-192 | The count bar is section-stats: one component, two call sites | Proposed | `libs/angular/aurelius-atlas-ui/specs/7-16-ui-components-details-ii/design.md` |
| DD-193 | Collector ingest is authenticated in two legs: user JWTs for browsers, a shared token for services | Proposed | `dev/observability/specs/7-17-collector-ingest-auth/design.md` |
| DD-194 | The collector stamps the verified user onto the telemetry: `enduser.id` | Accepted | `dev/observability/specs/7-17-collector-ingest-auth/design.md` |
| DD-195 | The collector rides out Keycloak's boot: bounded restart, awaited readiness | Accepted | `dev/observability/specs/7-17-collector-ingest-auth/design.md` |
| DD-196 | The service leg graduates to per-service identity: Keycloak client-credentials JWTs, azp-stamped | Proposed | `libs/python/aurelius-atlas-otel/specs/7-18-collector-ingest-identity/design.md` |
| DD-197 | The auxiliary APIs share one foundation: the OTel and auth libs | Proposed | `libs/python/aurelius-atlas-auth/specs/8-0-auxiliary-api-foundation/design.md` |
| DD-198 | The 8.x ports are pandas-free: pydantic rule models, plain row maps | Proposed | `apps/aurelius-atlas-data2model/specs/8-1-data2model-api/design.md` |
| DD-199 | App unit tests clear the injected `.env` prefix in an autouse fixture | Accepted | `apps/aurelius-atlas-data2model/specs/8-1-data2model-api/design.md` |
| DD-200 | The 8.2 proxy app injects its upstream HTTP client; the e2e Atlas is a canned-file server | Accepted | `apps/aurelius-atlas-lineage-model/specs/8-2-lineage-model-api/design.md` |
| DD-201 | The 8.3 mock ships as module data; the verifier is injectable | Accepted | `apps/aurelius-atlas-validate-entity/specs/8-3-validate-entity-api/design.md` |
| DD-202 | One issuer world: producers mint on the TLS listener, the collector validates both | Accepted | `dev/observability/specs/7-18-collector-ingest-identity/design.md` |
| DD-203 | The wire contract lives in a client library; the app imports it | Accepted | `libs/python/aurelius-atlas-server-client/specs/8-4-api-client-libraries/design.md` |
| DD-204 | Clients are async httpx with an injectable transport, and read no env | Accepted | `libs/python/aurelius-atlas-server-client/specs/8-4-api-client-libraries/design.md` |
| DD-205 | The client's `httpx.AsyncClient` is provided externally | Accepted | `libs/python/aurelius-atlas-server-client/specs/8-4-api-client-libraries/design.md` |
| DD-206 | The lineage-model's upstream breakers live in the app, on pybreaker's `calling()` seam | Accepted | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-207 | The lineage-model app follows the example app's provider/route layout | Proposed | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-208 | The lineage flow lives in the route; the chain class is dissolved | Proposed | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-209 | data2model and validate-entity follow the example app's provider/route layout | Proposed | `apps/aurelius-atlas-data2model/specs/8-1-data2model-api/design.md` |
| DD-210 | Telemetry goes native: the OTel SDK replaces the logfire shell | Proposed | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-211 | httpx2 replaces httpx across the HTTP surface | Proposed | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-212 | The 8.x apps' app/scenario test modules carry their package name | Accepted | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-213 | The lineage guid is a UUID on every typed surface | Accepted | `apps/aurelius-atlas-lineage-model/specs/8-5-lineage-model-circuit-breakers/design.md` |
| DD-218 | 7.4 splits in two, and the search bar lands in the hero; the list is infinite scroll | Accepted | `apps/aurelius-atlas-webapp/specs/7-4a-search-results/design.md` |
| DD-219 | The results URL carries the query only | Accepted | `apps/aurelius-atlas-webapp/specs/7-4a-search-results/design.md` |
| DD-220 | The demo pass restores the search screens' legacy chrome: title, typography, shell and plate | Accepted | `apps/aurelius-atlas-webapp/specs/7-4a-search-results/design.md` |
| DD-221 | The empty query lists every entity through the `_ALL_ENTITY_TYPES` marker | Accepted | `apps/aurelius-atlas-webapp/specs/7-4a-search-results/design.md` |
| DD-234 | TLS material is a required setting: the server never serves plaintext | Accepted | `apps/aurelius-atlas-server/specs/9-2-server-hardening/design.md` |
| DD-235 | A 5xx answer is opaque and carries the trace id as `requestId` | Accepted | `apps/aurelius-atlas-server/specs/9-2-server-hardening/design.md` |
| DD-236 | Security response headers are a pure-ASGI middleware split on `/api` path | Accepted | `apps/aurelius-atlas-server/specs/9-2-server-hardening/design.md` |
| DD-237 | Index refresh moves from reads to writes: writes carry `refresh=wait_for`, no read path refreshes | Accepted | `libs/python/aurelius-atlas-core/specs/9-3-search-cost-client-ip/design.md` |
| DD-238 | The browser rate limit lives at the nginx edge, not in the server; private ranges are allowlisted | Accepted | `apps/aurelius-atlas-server/specs/9-3-search-cost-client-ip/design.md` |
| DD-239 | The webapp's nginx exports `/api/` spans on the collector's legacy leg; the module builds in the image's dev-stage | Accepted | `apps/aurelius-atlas-webapp/specs/9-4-edge-tracing/design.md` |
| DD-240 | The DSL parser is generated from Atlas's own grammar | Proposed | `libs/python/aurelius-atlas-dsl/specs/4-3-dsl-parser/design.md` |
| DD-241 | The parse tree is handed on as typed, immutable nodes | Proposed | `libs/python/aurelius-atlas-dsl/specs/4-3-dsl-parser/design.md` |
| DD-242 | A DSL query is composed into the basic search's filter tree | Proposed | `libs/python/aurelius-atlas-core/specs/4-4-dsl-entities/design.md` |
| DD-243 | DSL traversals and projections are evaluated in steps | Proposed | `libs/python/aurelius-atlas-core/specs/4-4-dsl-projections/design.md` |
| DD-244 | Saved searches wait for authentication | Accepted | `libs/python/aurelius-atlas-core/specs/4-5-saved-searches/design.md` |
| DD-245 | Lineage walks the relationships of the process edges | Proposed | `libs/python/aurelius-atlas-core/specs/5-1-lineage/design.md` |
| DD-246 | Glossary objects are entities written through the entity and relationship stores | Proposed | `libs/python/aurelius-atlas-core/specs/5-2-glossaries-and-categories/design.md` |
| DD-248 | An entity's meanings are read from its listed relationships | Proposed | `libs/python/aurelius-atlas-core/specs/5-2-term-assignment/design.md` |
| DD-249 | Uploaded files are read with python-multipart, openpyxl and xlrd | Proposed | `libs/python/aurelius-atlas-core/specs/5-2-glossary-import/design.md` |
| DD-250 | The server authenticates requests itself against the identity provider | Proposed | `apps/aurelius-atlas-server/specs/6-1-authentication/design.md` |
| DD-251 | Browser sessions are kept in the server's memory | Proposed | `apps/aurelius-atlas-server/specs/6-1-authentication/design.md` |
| DD-252 | DataAccess carries every model object through a registry of DTOs | Proposed | `libs/python/aurelius-atlas-core/specs/4-5-saved-searches/design.md` |
| DD-253 | The chart-contract suite lives at the workspace root (`tests/`) and asserts rendered manifests via the `helm` CLI | Accepted | `helm/specs/10-2-stateful-platform/design.md` |
| DD-254 | The umbrella's `randAlphaNum` + `lookup` credential generation ships in 10.2; retrieval/rotation polish stays in 10.4 | Accepted | `helm/specs/10-2-stateful-platform/design.md` |
| DD-255 | The ES coredump agent ships as the `aurelius-atlas-elasticsearch-agent` image, not a ConfigMap-embedded jar | Accepted | `helm/specs/10-2-stateful-platform/design.md` |
| DD-256 | The realm is a byte-copy chart asset rendered verbatim; its `${...}` placeholders resolve in Keycloak, never by Helm | Accepted | `helm/specs/10-2-stateful-platform/design.md` |
| DD-257 | Each stateful pod pins its hardened image's declared uid (ES 1000, KC 65532, PG 70) with `fsGroup` for volumes — no privilege drop | Accepted | `helm/specs/10-2-stateful-platform/design.md` |
| DD-258 | Keycloak waits for the bundled Postgres via an init container (the compose `depends_on: service_healthy` port); the DB cert carries the probe's loopback SAN | Accepted | `helm/specs/10-2-stateful-platform/design.md` |
| DD-259 | The default trust root is a namespaced self-signed-issuer chain (bootstrap → CA Certificate → CA issuer); a bare self-signed ClusterIssuer mints a per-certificate root (partially supersedes DD-286) | Accepted | `helm/specs/10-2-stateful-platform/design.md` |
| DD-260 | Prod-mode Keycloak serves TLS on the management port; probes are HTTPS and the startup budget covers the per-container re-augmentation | Accepted | `helm/specs/10-2-stateful-platform/design.md` |
| DD-261 | The Gateway in front of the webapp makes DD-238's TCP-trust assumption false: realip from the gateway network, forwarded\_allow\_ips from values | Accepted | `helm/specs/10-3-app-edge-charts/design.md` |
| DD-262 | The nginx ConfigMap is a byte-copy asset; its placeholders (incl. the ingest bearer) resolve at pod start in an init container, never at Helm render | Accepted | `helm/specs/10-3-app-edge-charts/design.md` |
| DD-263 | The edge BackendTLSPolicy renders the stable v1 `caCertificateRefs` list — the experimental `v1alpha3` singular ref is not in the standard CRD bundle | Accepted | `helm/specs/10-3-app-edge-charts/design.md` |
| DD-264 | Writable emptyDirs mount below the nginx image's symlinked paths; upstream placeholder defaults are cluster FQDNs because the stub resolver ignores search domains | Accepted | `helm/specs/10-3-app-edge-charts/design.md` |
| DD-265 | Split-horizon issuer: a runbook CoreDNS entry resolves `keycloak.<domain>` to the Keycloak Service (which gains a 443 port); Keycloak and every consumer keep the public URL, so the issuer claim is one value in both horizons | Accepted | `helm/specs/10-3b-observability-chart/design.md` |
| DD-266 | The cluster answers 10.2's deferred scrape question the compose's way: Prometheus static configs over chart Services, plus ES/Keycloak `metrics-puller` Deployments; no Prometheus Operator | Accepted | `helm/specs/10-3b-observability-chart/design.md` |
| DD-267 | Grafana gets an umbrella-generated `-grafana-admin` Secret; with `adminPasswordSecret` unset the dev anonymous-Viewer-only posture (login disabled) stands unchanged | Accepted | `helm/specs/10-3b-observability-chart/design.md` |
| DD-268 | The collector's `deployment.environment.name` comes from values (default `cluster`); the dev compose keeps `development` — environment, not drift | Accepted | `helm/specs/10-3b-observability-chart/design.md` |
| DD-269 | The issuer-wait init ships as `dhi.io/curl` with native retry; busybox wget resets against Keycloak's TLS, and the hardened curl image has no shell for a loop | Accepted | `helm/specs/10-3b-observability-chart/design.md` |
| DD-270 | The webapp's listener serves TLS and the umbrella adds its BackendTLSPolicy; the last plaintext backend hop closes (supersedes DD-285's plaintext-backend clause) | Accepted | `helm/specs/10-3-app-edge-charts/design.md` |
| DD-271 | The umbrella renders the namespace default-deny; each chart renders its own additive ingress allows; the two never overlap, so no switch opens the namespace (CHT-60/72) | Accepted | `helm/specs/10-6-network-segmentation/design.md` |
| DD-272 | The gateway edge allows read `networkPolicy.gatewayNamespaces`; the default admits every namespace, because a public browser edge's data-plane placement varies per cluster and a wrong pin silently black-holes the edge | Accepted | `helm/specs/10-6-network-segmentation/design.md` |
| DD-273 | Two identity realms: hardened `aurelius-atlas` for clusters, `master` as the dev escape hatch | Accepted | `dev/keycloak/specs/10-7-prod-realm/design.md` |
| DD-274 | `global.realm` as the values contract; host tokens substituted chart-side | Accepted | `helm/specs/10-7-prod-realm/design.md` |
| DD-275 | Grafana is a confidential realm RP; its client lives in the prod asset only | Accepted | `helm/specs/10-8-grafana-auth/design.md` |
| DD-276 | Grafana logs in through the realm, with a request-derived root URL | Accepted (supersedes DD-267's login-form-stays-disabled clause) | `dev/observability/specs/10-8-grafana-auth/design.md` |
| DD-277 | Per-producer ingest secrets: one realm-shaped Secret, dev stays shared | Accepted (completes DD-196's deferral) | `dev/keycloak/specs/10-9-per-producer-ingest-credentials/design.md` |
| DD-278 | Third-party digests committed, own images stay tags; charts sign | Accepted | `helm/specs/10-10-digest-pinning-chart-signing/design.md` |
| DD-279 | Edge hardening, two-stack loopback guard, CI fork posture | Accepted | `helm/specs/10-11-low-findings-hardening/design.md` |
| DD-282 | Chart misconfig scans ride the Sonar hop as project-level issues | Accepted | `helm/specs/10-11-low-findings-hardening/design.md` |
| DD-283 | One chart per component under an umbrella, published as OCI artifacts from `charts/` | Superseded by DD-290 | `helm/specs/10-1-chart-foundation/design.md` |
| DD-284 | Helm targets are inferred from `Chart.yaml` by a plugin mirroring `docker.ts` | Superseded by DD-293 | `helm/specs/10-1-chart-foundation/design.md` |
| DD-285 | The edge is Gateway API, not ingress-nginx (retired March 2026); instrumentation and Istio are out | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-286 | TLS trust is cert-manager issuers; the CA each consumer pins is a ConfigMap of the cluster trust root | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-287 | The umbrella owns shared secrets; the webapp's telemetry token is a browser-reachable public constant | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-288 | The umbrella pins its component charts to its own version; chart version equals release version, `appVersion` is the tag | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-289 | The chart gate renders each chart's own values files separately; the release refreshes Chart.lock in `afterAllProjectsVersioned` | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-290 | Component charts live in `apps/<app>/helm` / `dev/<name>/helm`; helpers are chart-local, no library charts | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-291 | The `Chart.yaml` is the chart's whole Nx identity: the plugin infers name, targets, release actions, and umbrella edges | Superseded by DD-293 | `helm/specs/10-1-chart-foundation/design.md` |
| DD-292 | The umbrella lives at `helm/` in the workspace root: the chart tree is all `helm/` directories, `charts/` is gone | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-293 | Helm targets merge onto the owning project: a chart is not a project | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-294 | The minikube trial's two aux-chart findings (unbackable CA mount, lineage-model upstream URLs) are fixed in 10.3 | Accepted | `helm/specs/10-3-app-edge-charts/design.md` |
| DD-296 | 6.1a's required server-auth settings land in the charts as issuer/realm/secret joins; the dashboards' browser leg stays dashboard-host-gated | Accepted | `helm/specs/10-12-server-auth-chart-wiring/design.md` |
| DD-297 | The aux APIs' AUTH\_REALM was a static `master` config literal; it joins `global.realm` like every other realm-bearing env (CHT-74) | Accepted | `helm/specs/10-12-server-auth-chart-wiring/design.md` |
| DD-298 | `helm install --wait` against a never-Ready workload leaves the release `pending-install` until uninstalled — runbook warns | Accepted | `helm/specs/10-1-chart-foundation/design.md` |
| DD-299 | `helm-lint` runs `helm dep update` before linting: the umbrella's gitignored subchart tarballs otherwise leave a fresh checkout without dependency values | Proposed | `helm/specs/10-12-server-auth-chart-wiring/design.md` |
| DD-300 | Four fixed roles of the server's client grant Atlas's privileges | Proposed | `apps/aurelius-atlas-server/specs/6-2-authorization/design.md` |
| DD-301 | The stores check through the authorizer they are given | Proposed | `apps/aurelius-atlas-server/specs/6-2-authorization-entities/design.md` |

> \[!NOTE\] DD-095 to DD-125 and DD-280 were never written. The first band went unused when the `feat/api-client-libraries` branch renumbered its entries to DD-180 and above (DD-179); DD-280's 10.5 step took its decisions in the 10.x specs without a record. Those numbers stay unused.
