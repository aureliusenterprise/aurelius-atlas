# 20.1 Design decisions

## DD-812 — The client's view family: methods, not a generic request escape hatch

- **Status:** accepted
- **Date:** 2026-08-01
- **Relates to:** CL-11, CL-13, AVW-04, AVR-08, AVR-10, DD-562, DD-591

The suite needs three view routes, and `AtlasClient` has none of them. The cheapest change is a generic
`request()` on the client, and the e2e files keep their JSON dictionaries. That is the shape the suite has
today with a different spelling, and it proves nothing about the client.

The client gains three typed methods on a `view` namespace instead (`view.search`, `view.read`, `view.save`).
The server already ships the models: `EntityView` and `EntityCard` live in `aurelius-atlas-model`, so the
client reuses them whole (CL-10, DD-309) and adds nothing new to parse. The one shape the model library does
not carry is the search door's request, because that door lives in the server app (`routes/view_search.py`).
The client's `aurelius.py` states it (DD-562's rule for Aurelius-only shapes), mirroring the server model the
same way `SemanticSearchParameters` mirrors its twin. The answer is typed too: `cards` arrive as
`EntityCard` models, so the suite compares fields, not dictionary keys.

`view.save` takes the view dict the caller holds. The read door answers `EntityView`, which the suite edits
and sends back; a save that re-validates into `EntityView` first would drop the one key the door reads and
the model does not carry — `meanings`, which the wire view never answers (the door only acts on a caller who
sets it). So `save` sends what it was given, like `aurelius.validate_quality_rule` does, and answers the
parsed `EntityView`. The stale case (AVW-04) cannot ride `AtlasClientError`: its body has no
`{errorCode, errorMessage}` twin for the embedded `view`, and CL-04's `info` keeps exactly its two fields. A
subclass `ViewVersionConflictError` carries the stored view, parsed, and stays an `AtlasClientError`, so a
caller that catches the base still catches it (CL-04 unchanged). The subclass matches the route: the server
raises its own `ViewVersionConflictError` for exactly this body.

## DD-813 — Six carriers keep raw requests

- **Status:** accepted
- **Date:** 2026-08-01
- **Relates to:** ECL-01, LOD-01..03, SCN-05, ECU-02..04, DSH, CIA-07, AUT-04, DD-223

ECL-01 says the suite calls through the client. Six places keep raw `httpx` on purpose, because moving them
would change what the test measures, need a client feature the suite does not want, or ask the client's error
to carry more than CL-04 gives it:

1. **The parity runner** (`aurelius-atlas-parity`) drives JSON stages written for the Atlas wire. It takes an
   `httpx.AsyncClient` and posts the stage bodies raw. Rebuilding it on typed models rewrites the runner, and
   its job (SCN-05, ADR 052) is the wire itself.
2. **The session teardown** (`cleanup.remove`) runs after the loop closes, with a sync `httpx.Client`. The
   client is async-only, and a session fixture has no loop to run it on. It keeps its sync client (ECU-02,
   ECU-03).
3. **The load mix** (`load.atlas_mix`, `load.drive`) measures the server's latency, and every request is a
   timed sample (LOD-02). Typed parsing on every response adds CPU the measurement must not count. The mix
   and its driver keep the raw client. The test's own seed and clean-up — not timed — do move to the client.
4. **The dashboard browser probes** ride Playwright's page and request API. Their subject is the browser's
   own redirects, and `httpx` does not run them at all.
5. **The trace probe** sends one hand-made `traceparent` header per request and asserts on Tempo's spans
   (CIA-07). The client carries only the bearer header, and a per-request header escape hatch exists to
   bend the client into a shape no consumer uses. The probe's repeated GET stays raw.
6. **The bearer-challenge probe** asserts on the 401's `www-authenticate` header (AUT-04). CL-04 gives a
   raised `AtlasClientError` its status and its parsed body, and nothing else of the response — not the
   headers. A client method cannot answer that assertion, and growing the error to carry the whole response
   would bend CL-04 for one test. The probe's anonymous GET stays raw; the writer's session read of the same
   test moves to the client.

## DD-814 — Migrated tests name client methods in covers, like CL-13

- **Status:** accepted
- **Date:** 2026-08-01
- **Relates to:** ECL-02, ADR 056, DD-307

ADR 056 puts the rule id on the test, and the trace check maps the `covers` paths to the code the test
exercises. When a test moved to the client, the old version of this suite kept naming the route function, so
the client method the test really exercised went unnamed. The search suite (CL-13) fixed that by naming the
client methods. This increment extends that convention to every migrated test (ECL-02): the covers list
names the `AtlasClient` methods the request travels through, and keeps naming the route or core function
whose rule is still under test. The matrix in `libs/python/aurelius-atlas-server-client/specs/` is unchanged
for the Atlas routes; the view family is a new module there with its own table (DD-307's rule that a route
module has a spec).

## DD-815 — `AtlasSessionInfo` gains the two entity permission flags

- **Status:** accepted
- **Date:** 2026-08-01
- **Relates to:** CLW-13, ADM-05, AUZ-06, DD-203

The dashboards suite reads `atlas.entity.create.allowed` off the session body to prove the reader may not
write (AUZ-06). The client's `AtlasSessionInfo` (CL-10) was written from Java's session object before the
server answered the flags, so it lacks them and the suite cannot read them through the client.

The client's model gains the two fields as `entity_create_allowed` and `entity_update_allowed`, with the
`atlas.entity.*.allowed` aliases the route answers with, exactly as the server's `AtlasSessionProfile` states
them. Nothing else of Java's session profile moves over: the client carries what its callers read (CL-10),
and the other flags have no caller today.
