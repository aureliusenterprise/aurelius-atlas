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
