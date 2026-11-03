# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision is a
new entry that supersedes the old one.

## Entries

### DD-307. One live-check spec per server route module

- **Status:** Proposed
- **Increment:** 8.8
- **Date:** 2026-11-02

**Decision.** The client-coverage work proceeds as a series (8.8..8.12) with one
spec per server route module: 8.8 carries the client-wide conventions, the lineage
module, and the whole-client coverage matrix; 8.9 the entity module; 8.10 the
glossary module; 8.11 the relationship module and the admin writes and tasks; 8.12
the saved searches and the DSL search. Each spec holds a **coverage matrix** —
every route of its module with its rule id and client method — and that table is
the live check a reviewer updates when the module's routes change.

**Reason.** The 2026-11-02 review found the client covering 33 of the server's 124
endpoints, because 8.4 deferred the later routes ("each adds its client methods as
it ships") and no increment after 2.x–6.x claimed them. The deferral had no owner,
no matrix, and no drift check, so the drift grew silently. A module-named spec makes
the owner of `routes/<module>.py`'s client half the same file a change to that
module touches first. 8.4 and 8.7 keep their shapes; the series starts beside them.

**Alternatives.** (a) One umbrella spec for all 91 endpoints (refused — past the
size a reviewable page holds, and every change edits one hot file). (b) Per-endpoint
specs (refused — ~91 files, most a one-row table; the module is the unit that changes
together). (c) An auto-generated matrix from FastAPI's OpenAPI schema diffed against
the client (refused for now — the server ships `openapi_url=None` (9.2's hardened
surface), and a generator is a tooling increment of its own; the hand table is the
reviewable contract this workspace's convention (8.4's generator refusal) keeps).

**Consequences.** Five spec directories land under
`libs/python/aurelius-atlas-server-client/specs/`, and the trace check reads them
through the root `specs = ["."]` walk. The root roadmap gains five rows. The lib's
`AGENTS.md` and `README.md` gain the matrix pointer when 8.8's code lands (same PR,
per convention — not in this spec PR). Each series PR updates its matrix line for
every route it ships, so an unshipped route reads open rather than missing.

### DD-308. The client's lineage prefix fixes to the server's mounted path

- **Status:** Proposed
- **Increment:** 8.8
- **Date:** 2026-11-02

**Decision.** `LINEAGE_ROOT` changes from `v2/lineage` to
`api/atlas/v2/lineage`, matching the prefix `routes/lineage.py` mounts. The
`AtlasClient.get_lineage` method becomes a thin alias of the new
`AtlasClient.lineage.get` so the 8.2 app keeps compiling; the alias raises the same
`AtlasClientError` and is removed when 8.2 moves (a follow-up note in the lib's
`AGENTS.md`, not this series).

**Reason.** 8.4 wrote the path against the legacy host it had (the Aurelius Atlas
lineage feed had no `/api/atlas` prefix on that deployment, and 8.2's e2e fixture
answers `/v2/lineage/<guid>`). The server's own feed landed under
`/api/atlas/v2/lineage` (5.1, `app.py` mounts it), so today `get_lineage` answers a
404 against this workspace's server. The other roots already carry the prefix;
lineage is the odd one out and its `AGENTS.md` note ("the paths here already mirror
it") is stale.

**Alternatives.** (a) Keep the legacy path and have callers set a base URL that
includes `api/atlas` (refused — the same client then breaks `admin`/`types`/`search`,
which carry the prefix in their own roots). (b) Fix only in the 8.2 app (refused —
the path is the contract, and DD-203 says the contract lives here).

**Consequences.** The 8.2 app's unit tests and scenario stubs match the request
path (`/v2/lineage/{guid}`) in `apps/aurelius-atlas-lineage-model/tests/`, and its
e2e `fixture-atlas` serves that path from files; they repoint to
`/api/atlas/v2/lineage/...` in 8.8's PR (a test edit, no app code). 8.2's
docker-compose fixture repoints too: its command and healthcheck, and the fixture
directory `fixtures/v2/lineage/` moves to `fixtures/api/atlas/v2/lineage/`. DV-69
stays accurate (8.2's upstream stays stubbed until its e2e repoints to the server).
`zensical build --strict` and the docstring of the client module (which cites the
old root) update in the same PR.

### DD-309. Client methods reuse `aurelius-atlas-model` bodies, never fork them

- **Status:** Proposed
- **Increment:** 8.8
- **Date:** 2026-11-02

**Decision.** Every request and response body of the series is an
`aurelius-atlas-model` class — entities, relationships, classifications, glossary
objects, saved searches, audit events, tasks, patches, export/import requests and
results, lineage info. The client adds no body models of its own. Where the server
answers bytes rather than a model (DV-36's `setClassifications` summary JSON array,
`bulk/headers`), the client returns the parsed JSON as-is or raw bytes (DD-310).

**Reason.** 8.4's CL-10 set this for typedef and search bodies ("reused whole,
never forked") and it is why 8.2's chain validates against one class on both sides
(CL-07). The series' 91 routes have their bodies in `aurelius-atlas-model` already —
the server builds its answers with their `to_json()`.

**Alternatives.** Client-side DTOs per route (refused — a second copy of every body,
the drift DD-203 exists to remove).

**Consequences.** None new: the lib already depends on `aurelius-atlas-model`, and
each spec names the model class per route in its matrix.

### DD-310. File routes cross the client as bytes, not paths

- **Status:** Proposed
- **Increment:** 8.8
- **Date:** 2026-11-02

**Decision.** A route that answers a download (the admin export ZIP, the two import
templates) returns `(bytes, content_type)` from the client; a route that takes an
upload (the admin import form, the glossary and business-metadata CSV imports) takes
a filename and `bytes` and sends a `multipart/form-data` part. The client opens no
file and reads no path.

**Reason.** Libraries read no environment and touch no disk (CL-01's rule, the
libs-python convention); the app that holds the file is the one that reads it. The
admin export answers 204 for an empty export with the option set, so the client
maps no-content to empty bytes rather than raising — the caller sees one shape.

**Alternatives.** Accept `Path` arguments and read them in the client (refused — a
library with filesystem side effects cannot run in the browser-proxy apps, and the
tests' `MockTransport` seam covers a path-free client fully). Accept a file-like
object (refused — httpx's `files=` takes bytes or (name, bytes, type) tuples; bytes
are the smallest shape that covers both callers).

**Consequences.** `AtlasClient.admin.export` and `import_data`/`import_file`, the
glossary `import` and `import_template`, and the entity business-metadata pair (8.9)
carry bytes. The `Content-Disposition` the server sets (a result-class name) is the
caller's business; the client returns the content type and the bytes.
