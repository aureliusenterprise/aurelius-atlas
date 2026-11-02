# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-015. The server is a FastAPI application with one router per Atlas resource

- **Status:** Proposed
- **Increment:** 0.5
- **Date:** 2026-10-17

**Decision.** `apps/aurelius-atlas-server` is a FastAPI application built like the template's example
service (settings, uvicorn entry point, logfire, hardened image), with one router module per Atlas
REST resource class (`AdminResource` → `routes/admin.py`, later `EntityREST` → `routes/entity.py`).
Atlas errors are raised as `AtlasError` and turned into the Atlas error body by one exception handler,
as `AtlasBaseExceptionMapper` does; JSON goes out as `application/json; charset=UTF-8`.

**Reason.** ADR 045's ladder: FastAPI and the example's wiring are the workspace's convention, already
gated, observed and packaged. Mirroring the Java resource classes keeps the Java map one row per class
and lets a reviewer put a router next to its Java resource.

**Alternatives.** Starlette without FastAPI: no validation or OpenAPI for the request models later
increments need. Routers per URL prefix rather than per Java class: `admin` would still be one, but
`/v2/entity` and `/v2/entity/bulk` belong to one Java class and would split.

**Consequences.** The example service is no longer the only FastAPI app; it stays until the plan is done
(DD-019). Later
increments add routers and error codes; the error handler and media type stay.

### DD-016. The server does not start without its store

- **Status:** Proposed
- **Increment:** 0.5
- **Date:** 2026-10-17

**Decision.** The server opens the Elasticsearch store in its start-up and stops with an error when the
store cannot be opened (unreachable, rejected, or not Elasticsearch 9). Once running, `readiness`
reports the store's health on every call, and `liveness` and `status` do not depend on it.

**Reason.** The store is the only system of record ([ADR 047](../../../../docs/architecture/adr/047-one-search-store-is-the-system-of-record.md));
a server without it cannot answer anything but the admin endpoints. Failing at start-up shows a wrong
setting at once ([ADR 018][a018]) and lets an
orchestrator restart the container, while readiness covers a store that goes away later.

**Alternatives.** Start without the store and retry in the background: a misconfigured server would run
and only its readiness would say so. Make liveness depend on the store: an outage of Elasticsearch would
make an orchestrator restart every server, which does not help.

**Consequences.** Start-up order matters: `nx serve` and the end-to-end tests start the dev store first.

[a018]: ../../../../docs/architecture/adr/018-settings-arrive-at-startup-through-one-channel.md
