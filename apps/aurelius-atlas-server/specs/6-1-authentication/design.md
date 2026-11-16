# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-250. The server authenticates requests itself against the identity provider

- **Status:** Proposed
- **Increment:** 6.1a
- **Date:** 2026-10-31

**Decision.** The server verifies every request's credentials itself, in a middleware, with the shared verifier
`aurelius-atlas-auth` (DD-197): a bearer token is an RS256 JWT of the provider's key set, of its issuer,
unexpired, whose `azp` or `aud` names the server's client or a configured further client (the webapp's, which
the auxiliary APIs forward). A browser without a token signs in through the server's own confidential client,
`aurelius-atlas-server`, by the authorization code flow with PKCE, and keeps a session cookie. A user's name is
the `preferred_username` claim by default and their groups the configured groups claim, else the realm roles,
as Atlas's provider with `groups_claim` set.

**Reason.** Atlas authenticates in-process with Keycloak's Spring Security adapter: bearer tokens for clients,
a login redirect and session for its dashboards, which the server still serves. Verifying tokens in the server
keeps one path for every client, needs no proxy in front of it, and reuses the verifier the auxiliary APIs
already run. The adapter names a user by `sub` unless `principal-attribute` is set, which deployments set to
`preferred_username`, the name people know; it is a setting here too.

**Alternatives.** An authenticating proxy (oauth2-proxy) in front of the server: a second component on every
deployment, and the server would trust a header. Bearer tokens only: the vendored dashboards could not sign in.
Exchanging `Basic` credentials at the provider, as the adapter can: the server would handle passwords (DV-108).

**Consequences.** The server needs the provider's URL, realm, its client's secret and the further audiences;
every client sends a token. The dev realm gains the confidential client; the e2e suites mint tokens and sign
the browser in.

### DD-251. Browser sessions are kept in the server's memory

- **Status:** Proposed
- **Increment:** 6.1a
- **Date:** 2026-10-31

**Decision.** A browser's session — its user, its tokens, a sign-in under way and its CSRF token — is kept in
the server's memory under a random id in the `ATLASSESSIONID` cookie (`HttpOnly`, `Secure`, `SameSite=Lax`),
renewed at sign-in, ended after 60 minutes unused or when the provider refuses to refresh its token. At most
10,000 sessions are kept, the least recently used dropped first.

**Reason.** Atlas keeps its sessions in Jetty's memory, with the same cookie and a 60-minute timeout. The
session holds the tokens the server refreshes, so the browser never sees them.

**Alternatives.** A signed cookie holding the tokens: no server state, but the tokens leave the server and a
signed-out cookie stays valid until it expires. Sessions in Elasticsearch: survive restarts and serve several
instances, at a store round-trip per request.

**Consequences.** A restart signs browsers out; they sign in again at once while their provider session lasts.
Several server instances need sticky sessions.

### DD-640. A sign-out marks the browser, so the next sign-in asks for credentials

- **Status:** Proposed
- **Increment:** 6.1a (a fix, 2026-11-16)
- **Date:** 2026-11-16
- **Supersedes:** none

**Decision.** `logout.html` sets the cookie `ATLASSIGNEDOUT` for 10 minutes. A sign-in that `login.jsp`
starts while it is there asks the provider with `prompt=login`, and a completed sign-in clears it. A request
without a user for a `login.jsp` below a dashboard, such as `/n/login.jsp`, remembers that dashboard as the
page to return to, never the `login.jsp` itself.

**Reason.** dashboardv3 sends the browser to its relative `login.jsp`, `/n/login.jsp`, whenever one of its calls
answers 401. During a sign-out its calls answer 401 as soon as the server ends the session, and that navigation
can cancel the sign-out before the browser reaches the provider. The provider then still holds its session: the
next sign-in came back without a question, the browser was signed in again, and it was sent to the remembered
`/n/login.jsp`, which is no page. A person who signed out stayed signed in on a "Not Found", and the dashboards'
e2e sign-out failed now and then. With the mark, the provider asks for credentials whether its sign-out ran or
not. The dashboards stay unchanged (DD-017): the server answers what they ask.

**Alternatives.**

- Patch dashboardv3's error handler not to redirect during a sign-out: the vendored dashboards change, which
  DD-017 forbids for a fault the server can answer.
- End the session only when the browser returns from the provider's sign-out: a sign-out the browser never
  finishes would leave the server's session alive.
- `logout.html` as a page that redirects by script once the dashboard is gone: it answers 200 where Atlas
  answers a redirect (AUT-07).

**Consequences.** When the provider's sign-out was cut short, the provider's own session lasts until it expires;
only the next sign-in to Atlas asks for credentials. Other applications signed in through the same provider
session stay signed in, as they would after any sign-out the browser doesn't complete.
