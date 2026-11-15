# 15.6 The webapp's tenant

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-634 to DD-636 (here); relies on 15.1 (TEN-02 to TEN-06), 15.5a (RLM-02,
  RLM-03, DD-582)

15.5a gave the webapp's Keycloak client the organization groups mapper, and the server's own sign-in asks for
the organization scope while tenancy is on. The webapp still signed in without it, so with tenancy on its token
named no tenant and the server refused it. This increment makes the webapp sign in to one tenant, show which,
let a person in several tenants switch by signing in again, and offer its write controls by the tenant's roles.

## Scope

- `aurelius-atlas-server`: the open endpoint `GET /api/aurelius/v1/tenancy` (`routes/tenancy.py`).
- `aurelius-atlas-webapp`:
    - the tenancy read at start (`tenancy.ts`, `app.config.ts`);
    - the sign-in's scope (`app.config.ts`, `routes.ts`);
    - the tenant in the account menu, and switching (`shell/`);
    - the write controls' gate (`search/editor/can-write-entities.ts`);
    - two strings in the shell dictionary (`tests/fixtures/shell-*.json`, regenerated `src/locale/`).

Not delivered: a tenant's name beside its alias. The token carries the alias alone, and the realm's organizations
are named as their aliases (15.5b).

## Semantics

"The tenancy setting", "a token", "the tenant", "the operator organization" and "the operator role" are as in
15.1. "The answer" is the server's answer to `GET /api/aurelius/v1/tenancy`. "The webapp's tenant" is the one
organization its token names, read as TEN-02 reads it: the strings of a list, or the keys of an object.

| Id     | Rule                                                                                                                                                                                                                                                                                                                        |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TNW-01 | `GET /api/aurelius/v1/tenancy` answers without a user: `{"enabled": false}` while the tenancy setting is off, and `{"enabled": true, "operatorOrganization": …, "operatorRole": …}` while it is on (DD-636)                                                                                                                 |
| TNW-02 | The webapp reads the answer at start, after `/config.json` and before it signs in, from its own origin below the API base. An answer it can't read fails the start with the reason, as a bad `/config.json` does (SHL-02). The read is the start's, not a screen's: BRW-04 counts the landing's own `/api` calls without it |
| TNW-03 | With tenancy off, the webapp signs in, greets and gates its write controls as before: no organization scope, no tenant shown, the server client's roles                                                                                                                                                                     |
| TNW-04 | With tenancy on, a sign-in the webapp starts asks Keycloak for the scopes `openid organization`, so a person in several organizations chooses one there (DD-582)                                                                                                                                                            |
| TNW-05 | With tenancy on, the webapp remembers its tenant in the browser. Its silent check at start asks for `organization:<alias>` of the remembered tenant, else for `organization`; when Keycloak refuses it, the sign-in of TNW-04 follows, and the tenant it names is remembered (DD-634)                                       |
| TNW-06 | With tenancy on, the account menu shows the webapp's tenant, and its item "Switch tenant" signs in again as TNW-04 does, without signing out, back to the page shown. A token that names no tenant shows none (DD-635)                                                                                                      |
| TNW-07 | With tenancy on, the write controls show for a token whose tenant's groups hold `/atlas-write`, unless the user holds the operator role and the tenant isn't the operator organization; the server client's roles count for nothing. The server stays the gate (TEN-05, TEN-06, DD-636)                                     |
| TNW-08 | The menu's two strings, the tenant's label and "Switch tenant", are in the shell dictionary in English and Dutch, and the catalogue is generated from it                                                                                                                                                                    |
| TNW-09 | No answer of Apache Atlas's API changes: the endpoint is Aurelius's own                                                                                                                                                                                                                                                     |
| TNW-10 | The webapp reads no tenant from a query parameter, a path or a setting a viewer can change: the remembered alias only chooses which organization the silent check asks Keycloak for, which refuses one the person isn't a member of (ADR 063, R3)                                                                           |

## Java origin

None: Apache Atlas has no tenants (ADR 063), and the legacy Aurelius webapp had none.

## Deviations

None: no Atlas endpoint changes, and with tenancy off the webapp is as before.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_tenancy_route.py`: TNW-01, TNW-09.
- `apps/aurelius-atlas-webapp/src/app/tenancy.spec.ts`: TNW-02, TNW-05, TNW-10 (the answer read, the tenant read,
  remembered, and the scope asked for).
- `apps/aurelius-atlas-webapp/src/app/app.config.spec.ts` and `routes.spec.ts`: TNW-03, TNW-04.
- `apps/aurelius-atlas-webapp/src/app/shell/header.component.spec.ts` and `session.service.spec.ts`: TNW-06.
- `apps/aurelius-atlas-webapp/src/app/search/editor/can-write-entities.spec.ts`: TNW-07.
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts`: TNW-08.
- A run against Keycloak 26.7.4, recorded in DD-634 and DD-635.
- `nx test aurelius-atlas-webapp -c ci`, `uv run pytest apps/aurelius-atlas-server/tests` (level 0).
