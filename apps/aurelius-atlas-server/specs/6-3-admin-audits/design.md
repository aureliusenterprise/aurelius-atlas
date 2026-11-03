# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-308. Admin audits are written unchecked, through a request context bound per request

- **Status:** Proposed
- **Increment:** 6.3c3
- **Date:** 2026-11-02

**Decision.** The server binds each request's user, client address and start time in a context variable of the
core (`request_context`), inside the authentication. The admin audit service reads it, as Atlas's
`AtlasAuditService` reads its thread-local `RequestContext`, and writes its entries without a privilege check.
The two endpoints that read the entries read through the request's authorizer, as entity reads. A catalogue
whose registry lacks `__AtlasAuditEntry` keeps no admin audits.

**Reason.** Admin audits are written deep inside changes that do not carry the request: the type definition
store's listeners, a purge, the start of the server. Passing the user and client down every call would change
many signatures for one consumer; a context variable follows the request through its tasks as a thread-local
follows a Java request. The writes are unchecked for the reason of DD-307: under our fixed roles an
administrator need not hold the entity privileges. The base model, which defines the entry type, is always
loaded by the server; the unit tests' catalogues without it then work unchanged.

**Alternatives.** Passing a `user` and `client` to each audited call: explicit, but it reaches the typedef store,
the model loader and the patch handlers. Failing writes without the type: faithful to Atlas, which always has
it, but every test without the base model would need it.

**Consequences.** Code that writes admin audits outside a request (the start, the models' loading) names the
process's login user, as Atlas does. A future change that runs work in a new task keeps the context
only when the task is started from the request.

### DD-316. The start's typedef audits are held and written in one write after the models load

- **Status:** Proposed
- **Increment:** 6.3c3
- **Date:** 2026-11-03

**Decision.** The server loads the models with a `BufferedTypeDefAuditListener` in place of the plain
`TypeDefAuditListener`. The buffered listener is told every typedef change the load makes, exactly as ADA-03
asks, and makes each change's audit entries at the time of the change. It keeps those entries instead of
writing them, and writes them all in one write when the load is done (`flush`, before `SERVER_START`). The
service method behind that write is `AtlasAuditService.add_all`, which passes every entry as an entity of one
`createOrUpdate`. After `flush` the listener writes each later change at once, as its parent does.

**Reason.** A store write carries `refresh=wait_for` (DD-237), so each write costs about a refresh of the
index. One write per typedef change adds about 200 such waits to a cold start — measured at 198 seconds of
audits inside a 210 second start — which is longer than the image's health check budget (a 10 second start
period and three 30 second retries). The container is then declared unhealthy and every server and webapp e2e
test fails at its fixture. A warm store hides this: a loaded store creates no new definitions, so the load
audits nothing and the start is quick. Only a cold Elasticsearch (CI, a fresh dev store) shows it.

**Alternatives.** Registering the audit listener after the load: one line, but it breaks ADA-03, which says
the models at the start are told to the change listeners, and the existing test that the start's audit holds
the base model. Raising the health check's `start_period`: a band-aid that leaves a real two-minute start in
production, and a slower catalogue would break it again. Making the start's writes skip the refresh: faster,
but a later start step that reads an audit would not see it, and no start step needs to.

**Consequences.** The entries a cold start writes are the same set ADA-03 requires — one per change, same
parameters, result and count, same start time — only written together at the end instead of one each. Their
write order among themselves is the order the load made them. A cold start now does three audit writes (the
models' in one, `SERVER_START` and `SERVER_STATE_ACTIVE`), against about 208 before.
