# Access Management

This page explains what a signed-in person may do, as decided by the permission record ([ADR 038](<https://aureliusenterprise.github.io/feat-e2e-cleanup/architecture/adr/038-what-a-person-may-do-is-decided-in-one-place-apart-from-who-they-are/index.md>)). Who the person is comes from the identity provider ([ADR 007](<https://aureliusenterprise.github.io/feat-e2e-cleanup/architecture/adr/007-one-shared-identity-provider/index.md>), [identity management](<https://aureliusenterprise.github.io/feat-e2e-cleanup/architecture/platform/security/identity-management/index.md>)). What they may do comes from the roles the identity provider gives them, read by one authorizer in the catalogue server. The rules and their tests are in the increment specs `6.2a` (the spec: `apps/aurelius-atlas-server/specs/6-2-authorization/spec.md`), `6.2b` (the spec: `apps/aurelius-atlas-server/specs/6-2-authorization-entities/spec.md`) and `6.2c` (the spec: `apps/aurelius-atlas-server/specs/6-2-authorization-search/spec.md`).

## The role model

Four roles of the server's client (`aurelius-atlas-server`) grant Apache Atlas's privileges (DD-300). Who holds a role is decided in the identity provider only. What a role grants is fixed in the server's `authorization` module.

| Role | Grants |
| --- | --- |
| `atlas-read` | Reading types, entities and their classifications |
| `atlas-write` | Creating, updating and deleting entities, their classifications, labels, business metadata and relationships |
| `atlas-types` | Creating, updating and deleting type definitions, and reading them |
| `atlas-admin` | Purge, export, import and the admin audits |

A person usually holds several roles. A data steward needs `atlas-read` and `atlas-write`, and a modeller also needs `atlas-types`. The roles are read from the access token's `resource_access.aurelius-atlas-server.roles`. They are mapped into the webapp client's (`aurelius`) scope, so a browser session's token carries them, as does a token the auxiliary APIs forward.

Atlas's own authorizer takes a policy file of regular expressions over types, entities and classifications. This one has four fixed roles instead (DV-114). A role grants its privileges on every type and entity or on none.

## What is checked

The checks sit where Apache Atlas 2.4.0's sit, with the same action texts:

- **Changes** — every type definition, entity, classification, relationship and glossary change, the saved searches, and the admin purge. A request without the privilege is refused with 403 `ATLAS-403-00-001`, `<user> is not authorized to perform <action>`. A missing object is reported as missing (404) before the check.
- **Reading one object** — an entity, its header, its classifications, its audit, its lineage, and one type definition. Refused in the same way.
- **Listings** — searches do not refuse: each entity the user may not read comes back scrubbed, with GUID `-1` and no attributes, classifications or meanings. Type listings leave out the definitions the user may not read.

Type definition changes are checked before the definitions are validated, where Atlas validates first (DV-115).

## Granting and revoking

Granting or withdrawing a role is one act in the identity provider's admin console, with no release of any surface (ADR 038's R2). A change takes effect with the person's next access token. A token already issued keeps its roles until it expires, at most the realm's access-token lifespan (15 minutes on clusters).

If the identity provider cannot be reached, no new token is issued and requests without a valid token are refused: the arrangement fails closed.

## Where it runs

- **Development** — the dev realm (`dev/keycloak/import/master.json`) gives `aurelius-writer` all four roles and `aurelius-reader` `atlas-read`. The parity suites run as the writer, and the authorization tests run as the reader and as users with no role.
- **Clusters** — the production realm asset carries the four roles and their scope mapping, but no users. An operator grants the roles. Until then, a fresh install refuses every catalogue request.
