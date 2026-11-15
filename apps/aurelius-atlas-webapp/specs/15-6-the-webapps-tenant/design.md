# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-634. The webapp remembers its tenant and asks the silent check for it

- **Status:** Proposed
- **Increment:** 15.6
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** With tenancy on, the webapp keeps the alias of the tenant its token names in the browser's local
storage. At start, its silent check asks Keycloak for `openid organization:<alias>` of that tenant, or for
`openid organization` when it remembers none. A sign-in the webapp starts always asks for `openid organization`.

**Reason.** A check on Keycloak 26.7.4 found the following:

- A silent check (`prompt=none`) for `organization` answers `login_required` to a person in two organizations,
  because they must choose. Every page load and every new tab would send them to the choice.
- For `organization:acme`, the same check answers a token that names acme with its groups, for either of the
  person's organizations.
- For an organization the person isn't a member of, it answers `invalid_scope`, with no token.
- A person in one organization gets their token from the silent check for `organization`.

So the remembered alias restores the person's last choice without asking, and Keycloak still decides
membership. A remembered alias that no longer holds is refused, and the sign-in offers the choice.

**Alternatives.**

- No memory: a person in several organizations chooses on every page load.
- The tenant in the URL: a link would carry it to someone else, and the server would have to check it (ADR 063,
  R3).

**Consequences.** The memory is the browser's: another browser or a cleared storage asks for the choice once more.

### DD-635. Switching tenant is signing in again, without signing out

- **Status:** Proposed
- **Increment:** 15.6
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** "Switch tenant" calls Keycloak's sign-in for `openid organization`, with no `prompt`, back to the
page shown. The token that comes back names the tenant chosen, which the webapp remembers.

**Reason.** On Keycloak 26.7.4, with a session open, a sign-in for `organization` asked the person only to choose
an organization, with no password, and the token named the one chosen. `prompt=login` asked for the password and
kept the organization chosen before, so it can't switch. Signing out first asked for the name, the organization
and the password again.

**Alternatives.**

- Sign out and in: the person types their password to change tenant.
- `prompt=select_account`: Keycloak 26.7.4 answered as without a prompt, so it adds nothing.

**Consequences.** A person in one organization who switches comes straight back to it.

### DD-636. The webapp learns tenancy from the server, and gates its controls as the server does

- **Status:** Proposed
- **Increment:** 15.6
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** The server answers `GET /api/aurelius/v1/tenancy` without a user: whether tenancy is on, and the
operator organization and role. The webapp reads it at start. With tenancy on, its write controls follow the
tenant's `/atlas-write` group and the operator cap, as TEN-05 and TEN-06 read them.

**Reason.** Whether tenancy is on is the server's setting. Read from the server, the webapp can't disagree with
it, and no deployment keeps a second switch for the webapp: the chart, the standalone stack and dev all follow.
The answer tells nothing a token doesn't carry, so it needs no user, and the webapp needs it before it signs in.
The write controls follow the roles the server enforces, or a tenant's reader would see controls the server
refuses.

**Alternatives.**

- A key in `/config.json`: each deployment keeps it in step with the server's setting; the standalone stack's
  file is static and would need a second variable.
- Always asking for the organization scope: with tenancy off, a person in two organizations would be asked to
  choose for nothing.

**Consequences.** The webapp starts only when the server answers; until 15.6 it started without the server.
