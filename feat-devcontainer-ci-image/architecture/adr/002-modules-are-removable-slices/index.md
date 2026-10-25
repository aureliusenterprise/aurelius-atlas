# 002\. Modules are removable as whole slices

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Aurelius Enterprise

Every module is spine (always stays) or an optional capability that leaves as a whole slice: delete its directories and the remainder works. Partial removal is not a supported state — a team takes a capability in full, or not at all.

## Decision

**Two categories, no third.** A module is part of the spine — the core that stays in every copy of this system — or it belongs to an optional capability.

**A capability owns its applications, libraries, and development infrastructure together.** Deleting it — code, wiring, configuration, documentation in one pass — leaves the remainder working. A team takes a capability in full or does not take it at all.

> [!NOTE]
>
> **What is the spine today?**
>
> The spine is listed in the root `AGENTS.md`: the server, dashboard, store, parity, and trace projects, the dev infrastructure, and the template's example apps — which stay in the spine until increment 6.4 retires them as their own slice ([DD-019](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/conversion/design-log/#dd-019-the-template-examples-stay-until-the-plan-is-done>)). The template's Kafka streaming and AWS Lambda slices and its Java tooling were the first capabilities to leave this way ([050](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)).

## Context

The repository holds a complete business system, built by one team, with nothing being removed today. It is also meant to be read and reused as a whole — the reason it lives in one repository ([001](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/001-single-monorepo/index.md>)) — and work taken from it takes a subset: a form-driven service has no use for a streaming pipeline; a serverless team's infrastructure needs differ from a long-lived-services team's.

The tension: the more capabilities the system demonstrates, the more useful it is as a reference — and the more a reader must sift to find their part.

Without a rule about how the system may be taken apart, two failure modes are open:

- **Removal by archaeology.** Someone dropping a capability discovers by trial and error which libraries, wiring, keys, and documents belong to it — and usually leaves some behind.
- **Threading.** A capability added with no rule has no reason to stay separable, so it threads a dependency through something general-purpose.

Either way the repository accumulates parts that belong to no one, and the cost of understanding it rises for everyone who reads it.

## Requirements

Any acceptable arrangement must deliver:

|  | Requirement |
| --- | --- |
| **R1** | **Complete removal by deletion.** Delete the capability's directories; no hunting for hidden wiring. |
| **R2** | **The remainder still works.** What remains builds, tests, and runs without reference to what was deleted. |
| **R3** | **Wiring is not interleaved.** Removal is deletion, not an editing task on files someone else owns. |
| **R4** | **Cheap to take back.** Adding a capability later needs no rework of what exists. |
| **R5** | **Cheap to keep true.** The rule holds with a small team, no dedicated owner per capability. |

## Alternatives

| Alternative | Why it fails |
| --- | --- |
| Free-form composition (any module, any dep) | R1, R2: no boundary at which a capability ends, so removal is a hunt through shared files. R3 outright: one capability's wiring runs through files the whole system shares. |
| Fine-grained modules, one per component | R5: keeping a graph of small modules coherent is ongoing work a small team cannot fund. R1 degrades: "which parts form the streaming capability?" stops having one answer. |
| Fork per capability combination | R2 in the direction that matters: the fork diverges, fixes stop flowing. R4: taking an improvement back is a rework of everything the fork changed. |
| Do nothing (document nothing about removal) | R1, R2 by default: the first remover discovers boundaries by breaking the build, and writes down nothing for the next one. |

## Tradeoffs

### What it buys

- A capability is taken or dropped as a unit — the system serves teams that need only part (R1, R2).
- Ownership is legible: everything belonging to a capability sits together (R3).
- The rule asks for colocated wiring, not new machinery (R5).

### What it costs

- Capabilities cannot share infrastructure freely: where two rely on one backing service, one must own it — and removing that owner strands the other.
- Some general-purpose work is duplicated rather than shared, because sharing would cut a capability in half.
- Every addition is classified core-or-optional, a judgement occasionally re-litigated.

### Watch

- Nothing in the build enforces the boundaries: the rule holds because the repository makes each capability's parts easy to see — which depends on every project documenting itself ([003](<https://aureliusenterprise.github.io/feat-devcontainer-ci-image/architecture/adr/003-every-project-documents-itself/index.md>)).
- Infrastructure shared by several capabilities is owned by the capability whose directory holds it, stated in that capability's own documentation, where a remover reads it.
- A part belongs to its capability by sitting in its directories **and** being listed in its documentation; a part that is neither is invisible to a removal sweep — a defect in that documentation, not bad luck.
