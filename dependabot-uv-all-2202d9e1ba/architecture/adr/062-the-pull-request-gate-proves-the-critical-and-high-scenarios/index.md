# 062\. The pull-request gate proves the critical and high scenarios and waits for the rest

- **Status:** Proposed
- **Date:** 2026-11-12
- **Deciders:** Aurelius Enterprise

## Decision

We will run the acceptance-critical and high end-to-end scenarios on every pull request, and move the rest of the suite to the weekly scan. Every scenario carries one of four criticality levels, and a guard test refuses any scenario that carries none. The pull-request gate and the push-to-main run are the same run: the same two levels, on Chromium alone, so a merge carries no test the pull request did not already prove. Firefox and WebKit run on the weekly scan, which also carries the two lower levels. A pull request no longer waits for the whole suite, and a path that left the gate stays proven within a week.

## Context

The end-to-end job is the slow half of the pipeline, and the pool of CI runners is capped at three. On a busy day, pull requests queue behind each other, and the wait teaches people to distrust the gate rather than to trust the code. The 2026-11 contention record made the cost concrete: two suites failed on pull requests and passed on a quiet main run, because the runner was shared, not because the product broke. Running every scenario on every pull request buys assurance the change rarely needs, at a delivery speed the team pays for on every change.

The product also has parts that change at different speeds. The spine (the store, search, the details screens) carries the catalogue's trust and breaks loudly. Young screens, capacity probes, and fragile service-shape probes carry less trust and fail for environmental reasons more often. Treating all of them as one gate forces the weakest probe to set the price of every merge.

## Requirements

- R1: A change that breaks the catalogue's core answers (store, search, the shipped screens) fails before it merges.
- R2: Every scenario still runs on a known cadence, so nothing goes unproven forever.
- R3: A scenario the pull request proved does not fail for the first time on main. The two runs carry the same levels.
- R4: The classification is written where a reviewer sees it, and a scenario cannot join the suite unclassified.
- R5: The weekly proof keeps the full suite, including the browsers and the capacity claims that the shared pull-request runner cannot honour.
- R6: The team keeps one definition of the gate, as ADR 014 requires: local runs stay whole, and the cadence belongs to CI, not to the test files.

## Alternatives

- **Gate the pull request on `critical` only.** It is cheaper, but it lets a `high` break reach main and fail there for the first time. The team judged the merge surprise worse than the extra minutes, so `high` stays in the gate.
- **Mark only the slow or flaky tests to skip them.** A skip list is an unranked list. It answers "what is slow", never "what matters", so the next removal has no rule to appeal to. The four levels and the score pair (impact times likelihood) give the removal a rule.
- **Run the full suite on every pull request but in parallel across more runners.** The pool is capped at three by cost. A wider pool is the other way to buy the same wall time, and it was refused with the cap.
- **Split the pull-request gate by touched area alone.** `nx affected` already does this, and it misses the point: a documentation change already skips the untouched suites. What stays is a change to the spine, which deserves the spine's proof, not the capacity probe's.

## Tradeoffs

- **Positive:** a merge carries no test the pull request did not already prove, so the surprise a bad merge used to cause on main is gone. The gate runs one browser, so it stays well short of the full suite, and a `critical` or `high` break is caught on the change that caused it.
- **Negative:** a break on a `medium` or `low` path, or a Firefox- or WebKit- only behaviour, reaches main before it fails, and its proof is the weekly scan. Because `critical` and `high` now share every cadence, the two levels differ only in the risk score beside the marker, not in when they run. The review of any reclassification must accept that window explicitly.
- **Neutral / follow-ups:** the weekly scan becomes the full suite's home and gains duty value. Its manual dispatch is the on-demand cadence for the lowest level. Each increment's review decides whether a new scenario starts inside the gate. The mechanism, the matrix, and the per-component scores are in the [CI test tiers plan](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-2202d9e1ba/architecture/platform/ci-test-tiers-plan/index.md>).
