# 072. The catalogue answers agents through MCP

- **Status:** Proposed
- **Date:** 2026-11-26
- **Deciders:** Aurelius Atlas maintainers

## Decision

We will expose the catalogue to AI agents through a dedicated service that speaks the
Model Context Protocol (MCP) over HTTPS, built on the FastMCP framework. The service
answers a small, deliberate set of catalogue operations — search, read, lineage, glossary,
type system, write, and the governance verdicts — and holds no catalogue logic of its own.
Agents reach the catalogue only through this front door; they are never handed Elasticsearch,
the store, or the server's private routes.

Because an agent session is a person acting through a tool, the service forwards the
caller's own credential to the catalogue rather than signing with a service identity of
its own. This is a deliberate difference from the other auxiliary APIs, and it is recorded
as such.

## Context

Catalogue users increasingly work through AI assistants: they ask questions in plain
language and expect the assistant to look records up, follow lineage, check governance,
and occasionally file a correction. The dashboard cannot serve those assistants — it is a
human interface — and neither can the raw REST API be handed out safely: it is broad, it
has no notion of "the operations an assistant may attempt", and every consumer that
learned it becomes hard to retire.

The Model Context Protocol is the common language that emerged for connecting assistants
to tools. Adopting it means any conforming client — an IDE assistant, an agent runtime, the
MCP inspector — can talk to the catalogue without bespoke glue, and we describe our
surface once instead of per consumer.

The forces in tension:

- The catalogue's public REST contract must stay stable and private from agents (ADR 046).
- A governance catalogue is sensitive: an assistant must not become a way to bypass who is
  allowed to do what (ADR 013, ADR 038).
- The surface exposed to a non-deterministic caller must be small and reviewable, not the
  whole API.
- We already port the operations this needs; a new surface must reuse them, not fork them.
- The whole system runs on one machine and ships as removable slices (ADR 002, ADR 006).

## Requirements

- **R1** An MCP-conforming client can search, read, follow lineage, consult the glossary
  and type system, write, and read verdicts without any bespoke integration code.
- **R2** The exposed surface is a named, reviewable set of operations — not the REST API
  reshaped wholesale.
- **R3** Access control is not weakened: an operation runs with the caller's authority and
  is refused without it. A missing or bad credential never reaches the store.
- **R4** No catalogue logic lives in the new surface; every operation travels through the
  existing client libraries, so behaviour cannot drift from the server.
- **R5** The surface is a removable slice: deleting it unwires cleanly (ADR 002).
- **R6** It runs and deploys like the other auxiliary services: Keycloak tokens, TLS,
  containers, one CA (ADR 039, ADR 057).

## Alternatives

- **Give agents the REST API directly.** Fails R2 and R3 — the API is far broader than any
  assistant needs, and there is no reviewable surface to point a policy at.
- **Extend the server itself to speak MCP.** Fails R5 and muddies the system of record
  (ADR 047); a protocol adapter is a separable concern, not part of the store.
- **Sign catalogue calls with the service's own identity, like the 8.x aux APIs.** Fails R3:
  an agent acts for a person, so its authority must be that person's, and writes would
  lose the acting user the server records (6.1b).
- **Build the protocol layer ourselves instead of FastMCP.** Fails R1's economy and ignores
  a mature convention we are allowed to borrow (ADR 045).

## Consequences

- A new auxiliary service joins the stack. It is a thin adapter: it can be removed without
  touching the catalogue, satisfying R5.
- We accept a framework dependency (FastMCP) at the MCP boundary. Its behaviour is confined
  to this one app.
- Forwarding the caller's token, unlike our other aux APIs, is a real asymmetry. It is
  stated as a deviation (DV-208) so a reviewer sees it next time an 8.x pattern is copied.
- The tool set becomes a second public contract to maintain, alongside the REST API. It
  must grow deliberately: each tool is named by a rule in a spec before it ships.
- The write tools open a path for an assistant to change the catalogue. They are gated on
  the same write role the dashboard requires, and the acting user is recorded as today.
