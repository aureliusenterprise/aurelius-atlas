# 6.1b The acting user on writes

- **Status:** in progress
- **Pull request:** to follow
- **Records:** removes DV-06, DV-15 and DV-109; relies on DD-250

The second part of increment 6.1: the user a request authenticates as (6.1a) names what it writes, as Atlas's `RequestContext` user does. Type definitions, entities, relationships, classifications and glossary objects carry the user as `createdBy` and `updatedBy`, audit events as `user`, and the propagation tasks a request leaves run as it. The core already took a user for every write; this increment passes the request's.

## Scope

Every route that writes: `types/typedefs` (`POST`, `PUT`), the entity, classification, label and business attribute routes, `admin/purge`, `relationship`, the glossary routes, and the tasks they leave. The parity harness gains values a test knows before the first stage, such as `{user}`.

## Semantics

| Id | Rule |
| --- | --- |
| USR-01 | A request acts as the user it authenticated as (AUT-03); a request on an open path acts as no user |
| USR-02 | A type definition's `createdBy` is the user who created it, its `updatedBy` the user who last updated it |
| USR-03 | An entity's and a relationship's `createdBy` and `updatedBy`, a classification's change of its entity, and each audit event's `user` are the acting user's; a propagation task records it as `createdBy` and runs as it |
| USR-04 | A parity scenario's `{user}` is the user the test's client acts as, given to the run with any other known value; `{run}` stays the run's own |

## Java origin

Apache Atlas `release-2.4.0`:

- `server-api/.../RequestContext.java`: `getUser`, which the stores and listeners read
- `repository/.../store/graph/v2/EntityGraphMapper.java`, `AtlasRelationshipStoreV2.java`, `AtlasTypeDefGraphStoreV2.java`: `createdBy` and `updatedBy`
- `repository/.../audit/EntityAuditListenerV2.java`: the event's user
- `repository/.../store/graph/v2/tasks/ClassificationTask.java`: the task's `createdBy` as its user

## Deviations

- **DV-06**, **DV-15** and **DV-109** are removed: definitions, entities and audit events name the user.

## Acceptance

- `apps/aurelius-atlas-server/tests/` — USR-01 to USR-03, and every parity scenario as the user `admin`, Atlas's default user, whom its expectations name.
- `apps/aurelius-atlas-server/e2e/` — the parity scenarios as the dev realm's writer.
- `libs/python/aurelius-atlas-parity/tests/` — USR-04.
- `uv run aurelius-atlas-trace check`.
