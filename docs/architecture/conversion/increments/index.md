# Increments

An increment's semantics specification lives in the project it touches: it is written before the
code ([ADR 051](../../adr/051-the-conversion-proceeds-in-specified-increments.md)) as
`<project>/specs/N-M-slug/spec.md`, with its `DD-NNN` records in `design.md` beside it. An
increment that spans two projects gets one part per project, sharing the rule table; the
increment-to-project map is [Spec Map](../spec-map.md).

The pages below are the specifications written before the move: kept here as history until their
series moves. Copy [the template](./template.md) to start a new one, add its project's `specs`
directory to the `specs` roots in the root `pyproject.toml`, and keep its status in step with the
[roadmap](../index.md#roadmap).
