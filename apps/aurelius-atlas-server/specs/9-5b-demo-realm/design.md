# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-366. The standalone stack signs in to a demo realm of its own, not the dev realm

- **Status:** Proposed
- **Increment:** 9.5b
- **Date:** 2026-11-06
- **Supersedes:** DD-363's consequence that the stack's Keycloak imports the dev realm; the rest of DD-363
  stands

**Decision.** The stack's Keycloak imports the realm `demo` from `standalone/keycloak/demo.json` and nothing
else. It holds the server's client with its four roles, the public client the sample import uses, and the
users `atlas` (every role), `steward` (`atlas-read`, `atlas-write`) and `scientist` (`atlas-read`). Their
passwords are placeholders, filled from the dev Keycloak's `.env`.

**Reason.** The dev realm is `master`, Keycloak's administration realm. In the stack, a sign-in to the admin
console at `/auth/admin/` was also a sign-in to the dashboards: the browser came back as the administrator,
who holds none of the server's roles, and the Statistics showed no entities and an empty chart without an
error. A realm of its own keeps the two sessions apart. The users show the three levels of the server's
rights, named after the roles of Atlas's simple authorizer, for a demonstration on the sample data.

**Alternatives.**

- The server's roles for the administrator: one user with every right again, and the admin console and the
  dashboards still one session.
- The demo users in the dev realm: `nx serve`, the e2e suites and the chart's realm, which must equal the dev
  import (CHT-15), would carry them too.
- Passwords written in the realm file: a demo password in the repository, against the workspace's rule that
  secrets live in `.env.enc`.

**Consequences.** `aurelius-writer` and `aurelius-reader` don't sign in to the stack; `atlas`, `steward` and
`scientist` do, with the passwords in `dev/keycloak/.env`. The dev realm's `aurelius-atlas-server` client
drops the stack's sign-in and sign-out addresses that DD-363 added.

### DD-641. The standalone stack's realm is named `atlas`, not `demo`

- **Status:** Proposed
- **Increment:** 9.5b (a change, 2026-11-16)
- **Date:** 2026-11-16
- **Supersedes:** DD-366's name of the realm, `demo`, and of its file, `demo.json`; the rest of DD-366 stands

**Decision.** The stack's Keycloak imports the realm `atlas` from `standalone/keycloak/atlas.json`, shown as
"Aurelius Atlas". The server, the webapp and the sample import sign in to it. The organization `demo`, its
users and its sample data stay as they are.

**Reason.** Since the stack serves tenants (series 15), `demo` is one of the realm's organizations. A realm of
the same name read as if it belonged to that tenant, and the admin console, the sign-in URLs and the guides
named the tenant where they meant the platform. The realm is the platform's, so it carries the product's name.

**Alternatives.**

- Keep `demo`: no change, and the realm and the tenant stay confused.
- Rename the organization instead: its users, indices and record would all move, for the same gain.

**Consequences.** Keycloak keeps no data in the stack, so the next start imports `atlas` and no `demo` realm
remains. Browsers signed in to `demo` sign in again. Tokens are issued by
`https://localhost:9000/auth/realms/atlas`.
