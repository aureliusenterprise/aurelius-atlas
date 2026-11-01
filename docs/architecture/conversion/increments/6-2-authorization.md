# 6.2a Authorization: the authorizer, types and admin

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-300, DV-114, DV-115; removes DV-105; relies on ADR 038 (accepted with 6.2c), DD-250

What a user may do is decided in one place (ADR 038): the server's authorizer grants Atlas's privileges by
four roles of the server's client in the identity provider. Granting and revoking a role there is the one act
that changes what a user may do. This first part of 6.2 builds the authorizer, reports the session's
permissions, and checks the type definitions and the admin purge as Atlas does. Entities, classifications,
labels, business metadata, relationships and the glossary follow in 6.2b; search results and lineage are
scrubbed in 6.2c.

## Scope

| Endpoint                                                                          | Needs                                       |
| --------------------------------------------------------------------------------- | ------------------------------------------- |
| `POST /api/atlas/v2/types/typedefs`                                               | `TYPE_CREATE` of each definition            |
| `PUT /api/atlas/v2/types/typedefs`                                                | `TYPE_UPDATE` of each definition            |
| `DELETE /api/atlas/v2/types/typedefs`, `typedef/name/{name}`                      | `TYPE_DELETE` of each definition            |
| `GET /api/atlas/v2/types/typedef/...`, `{kind}def/name/...`, `{kind}def/guid/...` | `TYPE_READ` of the definition               |
| `PUT /api/atlas/admin/purge`                                                      | `ADMIN_PURGE`                               |
| `GET /api/atlas/admin/session`                                                    | reports `ENTITY_CREATE` and `ENTITY_UPDATE` |

In `aurelius-atlas-server`, `authorization` (Atlas's privileges, the roles that grant them, `verify_access`);
the user's roles in `authentication`; the checks in the type and admin routes. In `aurelius-atlas-auth`, the
token's roles of a client, public. In `dev/keycloak`, the four roles, their holders and the webapp's scope.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AUZ-01 | A user's roles are the roles of the server's client (`auth_client_id`) in their token, `resource_access.<client>.roles`; a browser session's are those of its access token                                                                                                                                                                                                                                                                                                                                                                   |
| AUZ-02 | `atlas-read` grants `TYPE_READ`, `ENTITY_READ` and `ENTITY_READ_CLASSIFICATION`; `atlas-write` grants `ENTITY_CREATE`, `ENTITY_UPDATE`, `ENTITY_DELETE`, the classification, label and business metadata privileges and `RELATIONSHIP_ADD`, `RELATIONSHIP_UPDATE`, `RELATIONSHIP_REMOVE`; `atlas-types` grants `TYPE_CREATE`, `TYPE_UPDATE`, `TYPE_DELETE` and, as Atlas's simple authorizer adds, `TYPE_READ`; `atlas-admin` grants `ADMIN_EXPORT`, `ADMIN_IMPORT`, `ADMIN_PURGE` and `ADMIN_AUDITS`. No role grants anything else (DD-300) |
| AUZ-03 | A request without the privilege it needs is answered 403 `UNAUTHORIZED_ACCESS`, `<user> is not authorized to perform <action>`, the action Atlas's text of the check                                                                                                                                                                                                                                                                                                                                                                         |
| AUZ-04 | Creating, updating or deleting type definitions needs the privilege for each, checked in the order of the request's kinds (enums, structs, classifications, entities, relationships, business metadata), as `create entity-def <name>`, `update entity-def <name>`, `delete entity-def <name>`; reading one definition by name or GUID needs `TYPE_READ`, `read type <name or GUID>`. Listing definitions and their headers needs none                                                                                                       |
| AUZ-05 | Purging entities needs `ADMIN_PURGE`, `purge entity: guids=<guids>`                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| AUZ-06 | The session's `atlas.entity.create.allowed` and `atlas.entity.update.allowed` say whether the user holds `ENTITY_CREATE` and `ENTITY_UPDATE`                                                                                                                                                                                                                                                                                                                                                                                                 |

## Java origin

Apache Atlas `release-2.4.0`:

- `authorization/.../authorize/AtlasPrivilege.java`, `AtlasAuthorizationUtils.java` (`verifyAccess`,
  `isAccessAllowed`), `simple/AtlasSimpleAuthorizer.java` (`TYPE_READ` with any type privilege)
- `repository/.../store/graph/v2/Atlas*DefStoreV2.java`: the type checks and their texts
- `repository/.../store/graph/AtlasTypeDefGraphStore.java`: `read type`
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `purgeByIds`
- `webapp/.../web/resources/AdminResource.java`: `getUserProfile`'s permissions

## Deviations

- **DV-105** is removed: the session reports the user's entity permissions.
- **DV-114:** permissions are four fixed roles of the server's client in the identity provider, not a policy
  of regular expressions over types, entities and classifications (`atlas-simple-authz-policy.json`, Ranger).
- **DV-115:** a type request without the privilege is refused before the definitions are validated; Atlas
  validates them first, so an invalid definition from such a user answers its validation error there.

## Acceptance

- `apps/aurelius-atlas-server/tests/` — AUZ-01 to AUZ-06 with tokens of each role and of none.
- `apps/aurelius-atlas-server/e2e/` — the parity scenarios as the dev realm's writer, who holds every role; the
  reader refused a type definition.
- `uv run aurelius-atlas-trace check`.
