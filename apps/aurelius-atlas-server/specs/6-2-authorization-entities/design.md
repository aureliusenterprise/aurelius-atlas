# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-301. The stores check through the authorizer they are given

- **Status:** Proposed
- **Increment:** 6.2b
- **Date:** 2026-11-01

**Decision.** The privileges and the checks live in `aurelius-atlas-core` (`authorization`): each store that
reads or writes entities and relationships for a request (`EntityWriter`, `EntityClassifications`,
`RelationshipStore`, `DataAccess` and the services built on them) takes an `Authorizer` and asks it at the
points where Atlas's entity and relationship stores call `AtlasAuthorizationUtils.verifyAccess`, with the same
action texts. The server builds one per request from its user's privileges (`Granted`, DD-300). A store built
without one is given `ALLOW_ALL`, which checks nothing. The relationship checks Atlas makes inside an entity
write (`EntityGraphMapper` creating relationship edges through `createRelationship`) are not made.

**Reason.** Atlas checks inside its stores, after it has found what a request names and before it writes; the
same placement keeps the same order of not-found and unauthorized answers, and covers the glossary and saved
searches, which write through those stores, without a check of their own. The core library knows no users or
roles; it is handed the decision. Allowing everything by default keeps the stores' own tests, the model loading
at startup and other internal writes free of a user they do not have. Under DD-300 only `atlas-write` grants
`RELATIONSHIP_ADD`, together with `ENTITY_CREATE` and `ENTITY_UPDATE`, which an entity write checks first, so
the relationship checks within it could never refuse what the entity checks allowed.

**Alternatives.** Checks in the routes before the stores run: simpler, but they would answer unauthorized for
a missing entity, and every glossary and saved-search route would need its own. A required authorizer with no
default: every internal caller and test would have to make one up.

**Consequences.** Every store a route builds must be given `authorizer(request)`; the server's tests refuse each
kind of change for a reader, which catches a route that forgets. Should roles ever grant privileges per type
(DV-111), the relationship checks inside entity writes are to be added.
