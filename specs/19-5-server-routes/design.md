# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-793. A closed store set answers the Atlas error, and it can ship alone

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-01.

**Decision.** The function that resolves a request's store set raises `AtlasError` when the tenant's store set
is
closed, instead of raising a bare `LookupError`. `AtlasError` already has a handler at `app.py:257`, so the
answer
becomes the Atlas error body.

**Reason.** A `LookupError` has no handler, so FastAPI answers its default 500 with no `errorCode`, and a
client
that switches on `errorCode` sees a shape no other refusal uses. One line and one test fix it, and the fix
does
not depend on any other change here, so it ships as the first commit and the first reviewable win.

**Alternatives.**

- **Add a `LookupError` handler.** That maps a generic built-in to a web shape, which hides the real problem:
  the resolver should raise the error type the API already answers.

### DD-794. Dependencies reach a route as dependencies

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-02.

**Decision.** Settings, the store set, and the authorizer reach a route through FastAPI dependencies. The
dependencies read `request.app.state` internally, so `create_app` stays the composition root.

**Reason.** Five test files change behaviour by writing `app.state.settings` because a route's real needs are
invisible from its signature. A named dependency makes the need visible and lets a test override the
dependency
instead of mutating app state behind the route's back. The bodies still read what they need; only how they get
it
changes.

**Alternatives.**

- **Pass settings and stores through every body by hand.** That is a larger diff across 33 handlers for the
  same readability, and it re-adds the parameter noise FastAPI dependencies exist to remove.

### DD-795. The entity hub stops being a hub

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-03, SVC-04.

**Decision.** The ten per-request service factories move from `routes/entity.py` to a services module, and the
Java numeric coercion moves to the module that owns the coercion rule. `routes/entity.py` keeps only handlers.

**Reason.** `routes/entity.py` is 909 lines, and eight sibling route files import helpers from it, so it is
both a
route module and a utility module at once. A change to a service factory reads as an entity-route change, and
a
route-only reader opens a file with factories and coercion in it. With the helpers out, the hub is a handler
list
and the siblings import from the module that owns each helper.

**Alternatives.**

- **Leave the helpers and add a routes/common.py that re-exports them.** The hub stays a hub, and a reader
  still cannot tell where a helper lives from its import.

### DD-796. One owner for request-body validation

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-05.

**Decision.** The four places that hand-check a request body before building a service call one validation
owner
in a `bodies` module.

**Reason.** Four near-copies of a body rule drift, and a rule written wrong in the model still ships if a copy
skips a check. One owner makes the body rule a single source that the model's own validation backs.

**Alternatives.**

- **Push every check into the pydantic model.** Some checks need the request context the model does not hold,
  so the owner stays in the request layer and calls the model.

### DD-797. One owner for the export lock

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-06.

**Decision.** The take-and-release sequence of the export lock lives in one owner, and the two places that use
it
call it.

**Reason.** A lock protocol copied twice drifts on release: one copy can release on a path the other forgets,
and
the lock leaks. One owner makes the release path single and testable.

**Alternatives.**

- **Keep two copies.** The audit found the two copies already differ on error paths, which is the drift the
  owner removes.

### DD-798. The OpenAPI model list is per app

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-07.

**Decision.** The list of models that build the OpenAPI schema (`openapi.py:26`) belongs to each app, not to a
module-level list appended at import time.

**Reason.** A module-level list grows as each app imports, so two apps' tests pollute each other's schema and
the
order of imports changes the answer. A per-app list makes each app's schema depend only on what that app
imports.

**Alternatives.**

- **Keep the global and clear it in a fixture.** A fixture that clears global state runs in an order tests do
  not control, and the schema still depends on import order.

### DD-799. The store set and the authorizer resolve once per request

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-02, SVC-08.

**Decision.** The store-set and authorizer dependencies cache their value for the life of one request, so a
route
that needs both does not resolve them twice.

**Reason.** Resolving the store set is where SVC-01's closed-store error originates, and the authorizer is
built
from the acting user. Both are per-request and both are read by several helpers, so resolving once keeps the
closed-store refusal consistent and avoids rebuilding the authorizer per helper.

**Alternatives.**

- **Resolve per use.** More work and a wider window for a helper to see a store set and an authorizer that
  came from different resolves of the same request.

### DD-800. One commit per route family

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-03, SVC-04.

**Decision.** The increment changes routes one family at a time: the entity routes, then the discovery routes,
then the glossary, lineage, relationship, and search routes. Each family is its own commit.

**Reason.** Route signatures change in thirteen files, and one commit that touches all of them is a diff a
reviewer cannot hold. One commit per family keeps each diff about one endpoint group, and a regression bisects
to
a family.

**Alternatives.**

- **One routes commit.** Faster to write and impossible to bisect when one endpoint family regresses.

### DD-801. The store-lookup fix is the first commit, and provably alone

- **Status:** Proposed
- **Increment:** 19.5
- **Date:** 2026-11-21
- **Relates to:** SVC-01, SVC-08.

**Decision.** Commit one is only DD-793: the one-line resolver change and its test. No other change rides with
it.

**Reason.** SVC-01 is the increment's only wire-answer change, and it is the change a reviewer most wants to
read
alone. Keeping it in commit one also means it can merge and ship before the rest of the increment lands, which
is
the plan's note that this line "can ship alone".

**Alternatives.**

- **Bundle SVC-01 with the dependency work.** The one behaviour change hides inside a mechanical refactor, and
  a reviewer has to dig for it.
