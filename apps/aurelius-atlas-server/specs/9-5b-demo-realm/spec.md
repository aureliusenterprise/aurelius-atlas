# 9.5b The standalone stack's demo realm

- **Status:** in review
- **Pull request:** [#281](https://github.com/aureliusenterprise/aurelius-atlas/pull/281)
- **Records:** DD-366; relies on DD-363 (the standalone stack behind nginx), AUZ-01 to AUZ-03 (the server's
  roles) and AUT-10 (the further audiences)

The standalone stack signs its users in to a realm of their own, `demo`, with three users who show the
server's rights: `atlas` may do everything, `steward` reads and writes the catalogue, and `scientist` only
reads it. The dev realm `master` stays the one of `nx serve` and the e2e suites.

## Scope

The standalone stack in `apps/aurelius-atlas-server/standalone/`: the realm file `keycloak/demo.json`, which
its Keycloak imports at every start; the server's `AURELIUS_ATLAS_SERVER_AUTH_REALM`; the sample import
signing in to `demo`. The users' passwords are placeholders, filled from the dev Keycloak's `.env`
(`DEMO_USER_ATLAS_PASSWORD`, `DEMO_USER_STEWARD_PASSWORD`, `DEMO_USER_SCIENTIST_PASSWORD`), encrypted in its
`.env.enc`. The dev realm's `aurelius-atlas-server` client no longer lists the stack's addresses.

Not in scope: the dev realm's users and the chart's realm.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                    |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DMO-01 | The realm `demo` holds the confidential client `aurelius-atlas-server`, whose roles are the server's four (`atlas-read`, `atlas-write`, `atlas-types`, `atlas-admin`), and the public client `aurelius`, whose tokens carry those roles. The only sign-in return is `https://localhost:9000/atlas2/login.jsp`, and sign-out returns to `https://localhost:9000/atlas2/` |
| DMO-02 | `atlas` holds the four roles; `steward` holds `atlas-read` and `atlas-write`; `scientist` holds `atlas-read`. Each password is a placeholder of the realm file, none written in it                                                                                                                                                                                      |
| DMO-03 | The stack's Keycloak imports `demo` alone, and the server verifies its tokens; the sample import signs in to it as `atlas`, the user with `atlas-admin`                                                                                                                                                                                                                 |

## Java origin

None: Atlas's own users are a file of the simple authorizer (`users-credentials.properties`), with the roles
`ROLE_ADMIN`, `DATA_STEWARD` and `DATA_SCIENTIST` in its default policy (`atlas-simple-authz-policy.json`).
The three users are named after them; the roles they hold are the server's (AUZ-02).

## Deviations

None: the realm is the stack's, not the server's.

## Acceptance

- `tests/test__standalone_demo_realm.py`: DMO-01 to DMO-03, read from `demo.json` and the stack's compose
  file, the roles checked against `ROLE_PRIVILEGES`.
- By hand, the standalone stack: each user signs in at `https://localhost:9000/atlas2/`. `atlas` creates an
  entity and exports; `steward` creates an entity and is refused the export (403); `scientist` is refused
  both (403). Keycloak's admin console signs in to `master`, so its session no longer signs the browser in to
  the dashboards.
