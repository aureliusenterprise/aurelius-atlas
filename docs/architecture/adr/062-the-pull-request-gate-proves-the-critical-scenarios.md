# 062. The pull-request gate proves the critical scenarios and waits for the rest

- **Status:** Proposed
- **Date:** 2026-11-12
- **Deciders:** Aurelius Enterprise

## Decision

We will run the acceptance-critical end-to-end scenarios on every pull request,
and move the rest of the suite to the merge run and the weekly scan. Every
scenario carries one of four criticality levels, and a guard test refuses any
scenario that carries none. A pull request no longer waits for the whole suite,
and a path that left the gate stays proven within hours on main and within a
week in full.

## Context

The end-to-end job is the slow half of the pipeline, and the pool of CI
runners is capped at three. On a busy day, pull requests queue behind each
other, and the wait teaches people to distrust the gate rather than to trust
the code. The 2026-11 contention record made the cost concrete: two suites
failed on pull requests and passed on a quiet main run, because the runner was
shared, not because the product broke. Running every scenario on every pull
request buys assurance the change rarely needs, at a delivery speed the team
pays for on every change.

The product also has parts that change at different speeds. The spine (the
store, search, the details screens) carries the catalogue's trust and breaks
loudly. Young screens, capacity probes, and fragile service-shape probes carry
less trust and fail for environmental reasons more often. Treating all of them
as one gate forces the weakest probe to set the price of every merge.

## Requirements

- R1: A change that breaks the catalogue's core answers (store, search, the
  shipped screens) fails before it merges.
- R2: Every scenario still runs on a known cadence, so nothing goes unproven
  forever.
- R3: A break outside the gate becomes visible on main within hours, not days.
- R4: The classification is written where a reviewer sees it, and a scenario
  cannot join the suite unclassified.
- R5: The weekly proof keeps the full suite, including the browsers and the
  capacity claims that the shared pull-request runner cannot honour.
- R6: The team keeps one definition of the gate, as ADR 014 requires: local
  runs stay whole, and the cadence belongs to CI, not to the test files.

## Alternatives

- **Keep everything on the pull request (do nothing).** It fails the pressure
  it exists to answer: the queue and the flakes stay, and the lesson of the
  contention record repeats.
- **Mark only the slow or flaky tests to skip them.** A skip list is an
  unranked list. It answers "what is slow", never "what matters", so the next
  removal has no rule to appeal to. The four levels and the score pair (impact
  times likelihood) give the removal a rule.
- **Run the full suite on every pull request but in parallel across more
  runners.** The pool is capped at three by cost. A wider pool is the other
  way to buy the same wall time, and it was refused with the cap.
- **Split the pull-request gate by touched area alone.** `nx affected` already
  does this, and it misses the point: a documentation change already skips the
  untouched suites. What stays is a change to the spine, which deserves the
  spine's proof, not the capacity probe's.

## Tradeoffs

- **Positive:** the pull-request job drops roughly a third of its wall time,
  releases its runner sooner, and drains the queue across parallel pull
  requests. The gate's failures get more signal from contention.
- **Negative:** a break on a non-critical path reaches main before it fails.
  The window is hours: the push-to-main run adds the next level back, and the
  weekly scan repeats everything. The review of any reclassification must
  accept that window explicitly.
- **Neutral / follow-ups:** the weekly scan becomes the full suite's home and
  gains duty value. Its manual dispatch is the on-demand cadence for the
  lowest level. Each increment's review decides whether a new scenario starts
  inside the gate. The mechanism, the matrix, and the per-component scores are
  in the [CI test tiers plan](../platform/ci-test-tiers-plan.md).
