# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-244. Saved searches wait for authentication

- **Status:** Accepted
- **Increment:** 4.5
- **Date:** 2026-10-30

**Decision.** Increment 4.5 (saved searches and the user profile) follows 6.1 (authentication) instead of
preceding 5.1. The roadmap keeps its number; 5.1 lineage is the next increment. The user chose this on
2026-10-30.

**Reason.** Atlas owns every saved search by the logged-in user: `addSavedSearch` sets the owner from the
request's user, `getSavedSearches` defaults to that user, and reading, updating, deleting and executing a
search check ownership (`checkSavedSearchOwnership`). Until 6.1 the server has no user (DV-04, DV-06); porting
4.5 now would need a temporary owner, a deviation 6.1 would have to undo, and ownership checks that test
nothing.

**Alternatives.** One anonymous owner until 6.1: the endpoints sooner, the checks trivially passing. An owner
taken from a request header until 6.1: testable checks, but a spoofable identity to remove later.

**Consequences.** `search/saved*` stays unanswered until after 6.1; the dashboards' saved-search menus fail
until then, as they did before.

### DD-252. DataAccess carries every model object through a registry of DTOs

- **Status:** Proposed
- **Increment:** 4.5
- **Date:** 2026-11-01

**Decision.** `DataAccess` moves out of the glossary's module into `data_access`, generic over a registry of
data transfer objects by the object's class, as Atlas's `DataAccess` and `DTORegistry` are. A DTO names the
entity type, makes the object's entities (its own first, then those it refers to) and reads the object back
from its entity and the entities read with it, and gives the unique attributes a new object is found by. The
glossary's three DTOs and the user profile's two register there; each service builds its `DataAccess` from its
registry.

**Reason.** 4.5 stores the user profile and its saved searches as Atlas does, as internal entities read and
written like the glossary's objects (DD-246). Atlas has one `DataAccess` for both; a second copy for profiles
would duplicate the save, load, type and deletion checks the glossary's already has.

**Alternatives.** A profile store written apart: the same checks twice. One registry of every DTO: services
would carry DTOs they never use.

**Consequences.** The glossary's `DataAccess` is `glossary_data_access`; its tests name the generic methods.
