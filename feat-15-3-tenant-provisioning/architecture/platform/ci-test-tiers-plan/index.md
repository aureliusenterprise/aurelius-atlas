# CI Test Tiers Plan

> [!NOTE]
>
> **Plan for approval, not yet the as-built**
>
> This page is the plan to split the test suites into tiers so pull-request CI runs the acceptance-critical and high path and waits for the rest. Nothing here is implemented. On approval, the rollout steps below land as small PRs, and [Testing](<https://aureliusenterprise.github.io/feat-15-3-tenant-provisioning/architecture/platform/delivery/testing/index.md>) gains a pointer to the as-built tier rules.

Pull-request CI runs every unit test and every end-to-end test that the change affects. The end-to-end suites dominate the wall time, and most of that runtime proves paths that a pull request rarely breaks. This plan classifies every end-to-end test into one of four criticality levels, `critical`, `high`, `medium`, or `low`, and runs each level on a cadence: `critical` and `high` gate every pull request and every push to main, `medium` runs weekly, and `low` runs on demand. A guard test fails the build when a test carries no level. Classification is required, not a convention.

## The problem in numbers

| Fact | Value |
| --- | --- |
| Runner pool (Shape A, `infra/arc`) | max 3 runners, one PR fan-out can hold all 3 |
| `e2e` job wall time on the 2026-11-12 merge head | about 31 min, critical path 19 min |
| Webapp e2e suite | 46 tests x 3 browsers plus 14 more = 180 tests, about 14 min |
| Server load suite (LOD-01..03) | 8 users x 20 s of mixed ops plus setup, about 3 min |
| Unit suites (`test` targets) | milliseconds to seconds each, offline-capable |
| Weekly Scan workflow | Wednesdays 02:00 UTC, already runs `nx run-many -t test e2e -c ci` |

The two flakes from PR 329's final run (2026-11-12) sit exactly in the lower levels: the server load test fails its latency budget under CPU contention, and the webapp deep-link test times out during a cold sign-in round-trip when the runner is saturated. Both passed on the quiet-pool main run `43214878271` (12:54 UTC), so contention is the confirmed cause for each.

## The tier model

Four criticality levels, and every test names its own. The level is a risk claim, and the cadence follows from it.

| Level (`@pytest.mark.*`) | What it claims | Cadence |
| --- | --- | --- |
| `critical` | The pull request must gate on this | PR (affected), main, weekly, manual |
| `high` | A merge must not carry this broken | PR (affected), main, weekly, manual |
| `medium` | Weekly proof is enough, drift is caught | weekly Scan, manual |
| `low` | Valuable, run on purpose | manual dispatch only |

`critical` and `high` share every cadence: the pull-request gate carries both so a merge brings no test the pull request did not already prove. The two differ in the risk score beside the marker (`critical` is the spine, `high` is a severe path with a weaker backstop), not in when they run. See step 3 for how the gate stays small: pull and main run Chromium only, and the other browsers ride the weekly Scan.

Local runs are unaffected: `nx e2e <project>` applies no filter and runs the whole project suite.

### The classification guide

The level is a risk score, and the score reads two axes the way a risk matrix does: the business impact of the scenario failing, and the likelihood that it fails without an earlier signal.

**Impact** asks what a paying user or operator loses when the tested scenario is broken in production:

- **Severe**: the catalog lies or stops. Wrong or missing governance data, a broken sign-in, a lost entity. A customer cannot trust or cannot use the product.
- **Major**: a feature is wrong or missing in its own screen. Search-by-meaning returns poor cards, a quality rule misfires. The product works; one promise does not.
- **Minor**: a contained or rare path. A resilience screen, an edge tracing probe. Nobody notices until they go looking.

**Likelihood** asks how probable it is that the scenario breaks, or drifts, between one run of this test and the next, without another test catching it. Score it high, medium, or low from three signals:

- **Churn**: how often the commits touch the tested path. Recent git history per component answers this per increment.
- **Fragility**: how much the scenario depends on things the repo does not control: a second browser engine, TLS round-trips, CPU timing, a shared dev service under load.
- **No backstop**: no other test proves the same claim. A component's only-proof suite scores high here whatever its churn, because a break reaches production silently. The affected filter makes that cost nothing on other projects' pull requests.

The matrix maps the pair to the four levels:

| Impact \\ Likelihood | High | Medium | Low |
| --- | --- | --- | --- |
| Severe | `critical` | `critical` | `high` |
| Major | `high` | `high` | `medium` |
| Minor | `medium` | `medium` | `low` |

Two overrides move a test off the matrix, each with a reason in the marker's comment:

- **Cost ceiling**: a run over about 10 minutes, or one with a contention failure record, drops at least one level. A capacity fact is not a risk claim, but the pool decides what fits the gate. The load suite lives here: severe impact, low likelihood, which reads `high`, and the ceiling caps it at `medium` on the weekly Scan's dedicated runner.
- **Increment promotion**: while an increment changes a path, treat likelihood as high for its tests during the increment, then settle per the matrix. The spec review states the promotion.

Classify by the scenario the test proves, not the folder it sits in: a parity scenario is severe-impact, a resilience probe is minor. The sweep records the pair beside the marker (`impact=severe, likelihood=high`) so the next reviewer can audit the score, not just the level.

Every e2e test carries exactly one of the four markers. A guard test fails the build when one carries none (step 1 of the mechanism), and `--strict-markers` rejects a fifth one. The rollout PR classifies the existing suite in one sweep, so the tree starts complete.

> [!NOTE]
>
> **Why levels and cadences, not one gate flag**
>
> A single gate flag forces a yes-or-no choice per test. The four levels say how soon a break must be caught, and score the risk behind it. Here the `critical` and `high` levels share a cadence (both gate the pull request), so the split is about the recorded risk and the demotion rule, not about two different run times. `medium` and `low` keep the cheaper cadences: the weekly dedicated runner and an on-demand dispatch.

> [!IMPORTANT]
>
> **A subset that cannot fail is a green lie**
>
> The gate levels (`critical` and `high`) must keep every path a pull request can break, and each lower level must say what catches it later (weekly, or a human who dispatches). The file list below is the reviewable answer, and a reclassification is a reviewable change, never a side effect. The guard test makes an unclassified test a red run instead of a quiet skip.

## The per-component critical list

Unit suites (`test` targets, 40 server files, 62 webapp `.spec.ts`) stay whole in pull-request CI and stay unclassified: they always run everywhere, so a criticality marker there would decide nothing. The classification applies to `e2e` targets only.

Scores are the sweep's starting point, read off the matrix. The landed tree then went through a per-scenario audit: every marker carries its own pair, and files that mix scenario kinds split (the webapp main file spans all four levels). Counts below are test functions; parametrization adds a few runnables.

| Project | `critical` (PR + main, 85) | `high` (PR + main, 38) | `medium` / `low` (weekly / dispatch, 29 + 6) |
| --- | --- | --- | --- |
| `aurelius-atlas-server` e2e | search, scenarios (parity), the load file's percentile test (severe, churn) | cleanup, export, admin audits, restore, dashboards (severe, low churn) | mixed-load run medium (severe, low; cost-capped from `high`) |
| `aurelius-atlas-webapp` e2e | editor, search, seeded details, reader gate, the boot/sign-in proofs (16) | entry/locale routing, api proxy, config bootstrap, 404 details, banner, field rules, explore (15) | shell chrome, locale/telemetry probes, drawer resilience (24); links, footer, greeting, mistyped path (4) |
| `aurelius-atlas-core` e2e | all 19 files (severe: the store spine; churn keeps likelihood high) | none | none |
| `aurelius-atlas-embedder` | the ranking proofs (severe for the product: bad vectors poison search-by-meaning) | batch-padding and input\_type invariants (major, only proof) | refusals/model list/pinned files medium; liveness low (healthcheck backstop) |
| `aurelius-atlas-kafka-scanner` | all (7 tests; severe: only proof, young path) | none | none |
| `aurelius-atlas-lineage-model` | all (6 tests; severe: only proof, young chain) | none | none |
| `aurelius-atlas-quality-scanner` | the scan's own-identity round trip (severe: wrong scores lie in the catalog) | idempotent re-run, dry run, error entity, audit trail (severe/major, low-med churn) | none |
| `aurelius-atlas-validate-entity` | none (the aux's answers ride the webapp's banner suite) | the gate 401, seeded verdicts, rule-selection walk (major, young) | error body medium; liveness low (healthcheck backstop) |
| `aurelius-atlas-db-scanner` | all (3 tests; severe: only proof, young path) | none | none |
| `aurelius-atlas-data2model` | all (4 tests; severe: only proof, young chain) | none | none |

The webapp file's demotions name their catcher: a collector/CSP/chrome break lands on the pull request when it breaks Chromium, and on the weekly Scan otherwise (a `medium` scenario, or one that breaks only Firefox or WebKit), each with the pair beside the marker. The aux suites lost their blanket `critical` because `nx affected` already runs them only when they change; the level now states how soon a silent break must surface, per scenario.

Two rules govern future changes to this table.

- **A demotion shows its score.** Moving a test down re-reads the matrix against evidence (git churn, a runtime or contention record), and the marker comment carries the pair and the override. A catcher line says what proves it later: main, weekly, or a dispatch.
- **No browser is dropped from the weekly run.** Cutting Firefox and WebKit from the pull-request and main gate is a latency decision (step 3), and the engine-only behaviours (the history-fragment notes in the webapp e2e helpers) stay proven weekly.

The sweep in the rollout PR writes a decorator on every test function: each scenario carries its own level, so one file mixes levels freely (the server load file holds a `critical` percentile test and a `medium` mixed-load run). A module-level `pytestmark` never carries a level — a file is not one risk — and the guard test holds the line.

## The mechanism

The lever is a pytest marker filter passed to the CI step as extra arguments after `--`. No target configuration changes: the run-commands executor already appends unparsed CLI arguments to the command, quoted, and Nx passes them only to the requested target — `docker-build` rides the e2e graph as a dependency, where no pytest flags land. The `decrypt` `dependsOn` and the `envFile` wiring on every Python target stay untouched.

### 1\. Register the marker

Add to `[tool.pytest.ini_options]` in the root `pyproject.toml` and in the nine project pyprojects that own an e2e run with their own pytest block: `aurelius-atlas-server`, `-embedder`, `-lineage-model`, `-quality-scanner`, `-kafka-scanner`, `-db-scanner`, `-data2model`, `-validate-entity` (apps) and `libs/python/aurelius-atlas-core`. Each e2e run picks the closest pyproject ini, because pytest runs with `cwd` at the project root. The webapp e2e has no pyproject, so its run walks up to the root ini.

```
markers = [
    "critical: gates a pull request",
    "high: gates a merge, runs on main and weekly",
    "medium: weekly proof is enough",
    "low: on-demand only",
]
addopts = "--strict-markers"
```

The webapp e2e has no pyproject of its own, so it inherits the root ini. The `--strict-markers` option rejects a marker outside the four. It applies to the unit suites too, which is safe: the repo's other markers (`covers` from the trace plugin, plus `parametrize`, `asyncio`, `usefixtures`, `skip`) are all known to pytest, and a `--strict-markers` collection passes today.

The guard is a root test in `tests/` (`test__e2e_classification.py`): it walks every `apps/*/e2e` and `libs/python/*/e2e` file, parses it, and fails when a `test__` function does not carry exactly one of the four levels in its own decorators, when a module `pytestmark` carries a level at all, or when a test below `critical` has no score-pair comment (`impact=..., likelihood=...`, plus an override note when one applies) beside its marker. A run below the top level must show the matrix answer that earned it. The test is offline (level 0). The `validate` job runs it through a small dedicated step (`uv run pytest tests/test__e2e_classification.py`) because the root `test` target's inputs cover only the chart paths. It is the enforcement half of the scheme: an unclassified test fails the build before any cadence runs.

### 2\. Pass the level as CI step arguments

The CI step passes the marker filter after `--`, and the run-commands executor appends it to the pytest command (verified: `-m "critical or high"` survives as one quoted argument, and a task requested with `-- flags` hashes the flags, so a filtered run can never restore an unfiltered cache entry). Nx 24 configuration names were the first design — `-c ci,ci-core` — and were dropped: Nx does not merge two `-c` names, and a dependency without the named configuration silently falls to its `defaultConfiguration`, which sent `docker-build` to `local` and lost the report files.

### 3\. Trim browsers with a keyword filter

Firefox and WebKit leave the pull-request and main gate with pytest's own `-k "not webkit and not firefox"`, not with a target configuration: the webapp suite's Playwright instances carry the browser in the test id (`test__x[webkit]`), so the keyword filter drops exactly those legs (verified through the Nx target: the webapp's gate is 32 of its 180 instances, Chromium only). No scenario name contains "firefox" or "webkit", so the keywords trim browsers and nothing else. The other suites have no browser scenarios, so the filter is a no-op there. The hand-written webapp target keeps its one all-browsers command for local and weekly use. Browser trimming and criticality stay separate levers: the two browsers leave the gate for every level, independent of the marker.

### 4\. Switch the CI steps

| Step | Today | After |
| --- | --- | --- |
| `validate` "Run unit tests" | `nx affected -t test -c ci` | unchanged (units are the Sonar product), plus the guard-test step |
| `e2e` job | `nx affected -t e2e docker-build -c ci` | `nx affected -t e2e -c ci -- -m "critical or high" -k "not webkit and not firefox"` (PR and main, one command), then `nx affected -t docker-build -c ci` |
| Weekly Scan "Test all projects" | `nx run-many -t test e2e -c ci` | unchanged (full suite, all four levels, see below) |

One command serves both events: `-m "critical or high" -k "not webkit and not firefox"`. Pull and main prove the same levels on the same browser, so a merge holds no surprise and the step needs no event branch. The weekly Scan stays unfiltered, so it runs all four levels on every browser, and its manual dispatch is the `low` cadence and the release-candidate check.

Splitting `docker-build` out of the one request is required, not cosmetic: CLI flags become pytest arguments for every *requested* target, and `-m` means memory to buildx. As a dependency inside the e2e graph, `docker-build:ci` takes no flags, and the second step replays the same builds from cache.

> [!NOTE]
>
> **Why the pull-request gate carries `high` too**
>
> A `high` break that only the push-to-main run caught would fail on main for the first time, after the merge. The team judged that surprise worse than the extra minutes, so the pull request runs `high` beside `critical`. The gate is therefore not the cheapest tier split; it is the one that leaves no proven-on-PR path able to break on main. Only `medium` and `low`, and only the Firefox and WebKit legs, wait for the weekly Scan. The pull-request run and the push-to-main run are identical.

## What is lost, and the compensation

| Loss | Compensation |
| --- | --- |
| `medium` paths no longer gate the PR | weekly Scan on a dedicated runner; a `medium` break reaches main and surfaces within a week |
| Firefox/WebKit proof in PR + main CI | weekly full sweep, and the engine-specific quirks stay in code comments |
| Load budgets (LOD-03) in PR CI | weekly Scan on a dedicated runner, plus the test's own env knobs for a local harder run |
| `low` runs happen only when dispatched | manual `workflow_dispatch` on Scan, the release-candidate check, and the dispatch duty in the runbook |

Note that `high` stays in the pull-request gate. The plan first moved it to main-only, and that was reversed: the team would rather pay the extra minutes than let a `high` scenario fail on main for the first time after a merge.

Sonar coverage does not shrink. The `coverage.xml` that feeds SonarQube comes from the `test` (unit) targets, and the plan keeps those whole. The e2e targets produce no coverage today (their `ci` configuration carries junit and trace files only), so cutting e2e cannot move the Sonar number.

ADR 056 traceability is untouched. The `@pytest.mark.covers` decorators are read from source by `aurelius-atlas-trace check` and by review, not from a run. A reclassified test keeps naming its rule ids, and its executed proof refreshes on its own cadence.

## Wall-time and pool effect

On a spine pull request the e2e job runs `critical` and `high` on Chromium only: it drops two thirds of the webapp suite's browser instances (its gate is 32 of 180), the webapp's `medium` and `low` files, the server's `medium` run, and the aux suites' `medium`/`low` probes. The server gate is 67 of 68 (its suites are browser-less, so only the level filter bites there), and every core/young-path test still runs. The first week's numbers will tell the wall time; cutting the levels and two of three browsers should land near the 20 to 24 min estimate against the old about 31 min. The win is pool pressure and contention as much as raw minutes. main carries the identical command, so a merge holds no surprise and main costs no pull request any time.

## Goal 2 pilot: the two flakes ride the mechanism

The rollout PR carries the two flake decisions from PR 329 as its first classification change and its first real fix. The main run on the merge commit (`43214878271`, quiet pool) is the discriminator, and it landed green (12:54 UTC): the contention read is confirmed for both.

1. **Server load test** (`test__the_server_holds_a_mixed_load`): mark it `@pytest.mark.medium` with the cost-ceiling reason in its comment. Its p95 budget is a capacity claim that a shared runner cannot honour under contention, and the weekly Scan's dedicated runner is its honest home. The green quiet-pool run proves the contention story.
2. **Webapp deep-link test** (`test__m4i_details_render_the_seeded_sections`, the `_deep_link_lands_its_section` helper): fix the wait, do not only bump the timeout. The failure log shows the cold `goto` lands while the Keycloak sign-in callback is still round-tripping, then the 5 s expect timeout expires before the details screen renders. The suite already carries `--tracing retain-on-failure`, so pull the retained trace from the failed run before editing. The fix: after a cold details `goto`, wait for the app shell the way the sign-in fixture does (the navbar-visible wait with the 30 s budget in the webapp e2e `conftest.py`), then assert the title at the default timeout. Apply the same readiness wait to the other cold details go-to sites in the webapp suite (the bare-guid goto in the same file and the two in the person-details file) so the pattern is one helper, not a patch per test. Reproduce with the trace on: `uv run pytest e2e -k m4i_details --browser webkit` in `apps/aurelius-atlas-webapp/e2e` against the dev stack.

## Rollout

1. **PR 1 (this plan):** marker registration, the guard test, the classification sweep of the 41 e2e files (one decorator per test, 157 levels in all), the `ci.yaml` step switch, and the two Goal 2 changes. No plugin or target configuration changes. The sweep is mechanical, so the whole stays inside the 1,500-line convention.
2. **ADR (same PR):** the gate change (which tests gate a pull request) is a business-level decision, so it enters `docs/architecture/adr/` as [ADR 062](<https://aureliusenterprise.github.io/feat-15-3-tenant-provisioning/architecture/adr/062-the-pull-request-gate-proves-the-critical-and-high-scenarios/index.md>), and `delivery/testing.md` carries the tier paragraph with a pointer here.
3. **Later increments:** further reclassifications ride their increment PRs with a measured reason, per the table rules above.

## Verification for PR 1

- Level 0: in `apps/aurelius-atlas-server/e2e`, `uv run pytest . -m critical --collect-only` keeps everything but the mixed-load run, and `-m "critical or high"` keeps that percentile test too. The guard test passes only when every e2e test carries one level in its own decorators, no module `pytestmark` carries one, and each test below `critical` shows its score pair.
- Level 1: `nx test aurelius-atlas-server -c ci` stays green (units unchanged).
- Level 2: `nx e2e aurelius-atlas-webapp -c ci -- -m "critical or high" -k "not webkit and not firefox" --collect-only -q` proves the flags reach pytest through the target: 32 of 180 browser instances, and the dry run of the new gate.

## Open decisions for approval

1. \~\~The `high` cadence.\~\~ Decided: the pull-request gate carries `high` beside `critical`, so a merge holds no surprise. The two levels now share every cadence and differ only in the risk score beside the marker.
2. \~\~PR browsers.\~\~ Decided: the pull-request and main gate runs Chromium only. Firefox and WebKit are proven on the weekly Scan, so an engine-only break waits at most a week. Pull and main carry one identical command.
3. Whether the ADR lands inside PR 1 or as its own record first. It landed inside PR 1 as [ADR 062](<https://aureliusenterprise.github.io/feat-15-3-tenant-provisioning/architecture/adr/062-the-pull-request-gate-proves-the-critical-and-high-scenarios/index.md>), still Proposed until a person accepts it.
