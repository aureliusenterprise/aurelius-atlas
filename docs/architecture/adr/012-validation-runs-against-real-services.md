# 012. Validation runs against real services, not substitutes

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Aurelius Enterprise

The system's behaviour is validated against the real services it uses, brought
up for the run and torn down after it. A test passing against a stub is
evidence about the stub, not the system.

## Decision

**Validation exercises the real services** — the database, the identity
provider, the event platform — brought up by the run and torn down after it.
Substitutes (stubbed services, canned responses, hand-written fakes) are not
the default path for validating behaviour.

**A test that passes against a substitute is evidence about the substitute.**
Only a test that passes against the real thing is evidence about the system,
and the organisation acts on the second kind.

## Context

The system is assembled from parts that talk to services: a service reads and
writes storage, consumers move records through a stream, a front end calls an
API that delegates admission to an identity provider. **The failures that cost
the business money live in those conversations** — a driver that behaves
differently than the client assumed, a constraint the code never expected, a
handshake only the real service enforces.

Those conversations can be exercised against the real service or a stand-in.
A stand-in starts faster and costs less per run, and carries a hidden cost:

- **It is a second implementation of the service's behaviour**, written by
  people who only know the behaviour the code already assumes. Where the
  assumption is wrong, the stand-in agrees with it — the substitute hides
  precisely the failures the test exists to catch, silently and forever.
- **It is a second codebase**, with its own bugs and its own upkeep — exactly
  the cost a small team cannot fund twice.

The decision is what behaviour is validated against, and what a passing test
is allowed to be evidence of.

## Requirements

Any acceptable arrangement must deliver:

|        | Requirement                                                                                                                      |
| ------ | -------------------------------------------------------------------------------------------------------------------------------- |
| **R1** | **A passing test is evidence about the shipped path.** The services a test exercises are production's, at the same interface.    |
| **R2** | **Fidelity does not decay in silence.** No hand-written model of a service's behaviour that can quietly disagree with it.        |
| **R3** | **Runs need no accounts or network.** The run brings the services up on the machine validating, so unattended and offline agree. |
| **R4** | **The cost stays bounded.** Real minutes and real money per run, kept small enough that validation isn't rationed.               |
| **R5** | **Cheap to keep true.** Adding a validated part is a local edit, not work spread across a maintained fake world.                 |

## Alternatives

| Alternative                            | Why it fails                                                                                                                                                                                                                                                                                  |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Substitutes everywhere                 | R2 structurally: a substitute is written from the code's own assumptions, so the two agree by construction and disagree with the service where nobody noticed. R1 for the same reason — the claim ends at the substitute's boundary. R5: the fake world must track every service it imitates. |
| Recorded traffic replayed              | R1 on the day of capture, R2 afterwards: a recording is a claim about one day, the service evolves, and the replay agrees with old behaviour in silence. R4: recordings rot and must be re-captured — the substitute's upkeep with extra steps.                                               |
| Real services hosted by the platform   | R1 outright, R3 not at all: every run needs accounts, network, and a shared mutable service, so unattended runs wait on access someone provisioned and two runs contaminate each other.                                                                                                       |
| Do nothing (each test picks its level) | R1 by default: a green suite becomes a mix of claims about the system and about substitutes, and no reader can tell which — so green stops meaning anything in particular.                                                                                                                    |

## Tradeoffs

### What it buys

- A passing test is evidence about the shipped path (R1): confidence transfers
  to production with no gap to reason about.
- There is no fake world to build or maintain, which removes a whole category of
  silent disagreement (R2, R5).
- Runs are self-contained, so the pipeline and an offline machine see the same
  result (R3).

### What it costs

- Every run pays real startup and resource cost, so validation must stay
  **targeted** — the parts a change can reach — or the cost rations the testing.
- Some services have no local equivalent at all; those runs wait on the exception
  rather than the rule.

### Watch

- A dependency that exists only as a hosted service is validated against a local
  equivalent, and drift between the two is a defect, not environment noise.
- Each such dependency needs a **named validation arrangement**. Until it has
  one, it is a hole in R1 the organisation carries knowingly.

??? question "Why not stub the expensive services?"

    Because the expensive services are where the assumptions live. A stub
    encodes what the code already believes about the service, so it validates
    the belief instead of testing it — and the day the belief is wrong is the
    day the test goes green.
