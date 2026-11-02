# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-141. Auth is guarded at the app root; the bearer token is stated inert until 6.1

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The webapp wires the example app's Keycloak set — `provideKeycloak`
(check-sso, silent-SSO, DD-004's in-memory token store), `createAuthGuard` on the app
root route, `includeBearerTokenInterceptor` on `/api` — and guards every route. The
Aurelius `libs/authentication` (raw `keycloak-js`, `ReplaySubject` auth state, manual
`updateToken(5)` loop, guard applied by `Shell.childRoutes`) is not ported (WBP-02). The
Atlas server does not verify tokens until 6.1; the webapp sends the bearer token anyway.

**Reason.** The legacy shell guards every search route (`Shell.childRoutes` with
`requiresAuth: true`), so parity of behaviour means guarding. keycloak-angular's
`createAuthGuard` declares the guard where routing is declared — the app root — instead
of a library wrapping routes from the outside; the Aurelius `AuthTokenProvider`
constructor-injection (each API client wiring its own auth interceptor) disappears with
the interceptor's URL-pattern config. The token is sent from day one so 6.1 activates
authentication with no webapp change, and ADR 038's precedent covers the state it
describes: "every authenticated person can do everything" is a stated condition of the
pre-6.2 system, not a security property — the same is said here of the pre-6.1 server.

**Alternatives.** Ship providers without guards until 6.1: leaves the app public in
production while the product's own UI never was; the e2e suite would also keep testing an
unauthenticated flow nobody uses. Enforce per-screen guards as each screen arrives: the
root guard is one line and no screen can forget it.

**Consequences.** Dev and e2e now need Keycloak up (serve `dependsOn` gains it; the e2e
suite gains the example's authenticated-login fixture as `aurelius-writer`). The
unauthenticated redirect-to-sign-in is itself tested (APC-05) — the sign-in page is the
app's first collaborator, and the flow is proven in CI, not assumed.

### DD-142. The webapp e2e stack runs the real Atlas server behind the proxy

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The webapp's e2e compose grows an `atlas-server` service (the image its own
`docker-build` produces, TLS, joined to the dev Elasticsearch network), and the e2e nginx
`/api/` location proxies it with CA verification. The placeholder assertion (`/api/` →
Keycloak, `{"realm": "master"}`) is replaced by `GET /api/atlas/admin/version` answered
by the real server.

**Reason.** The placeholder nginx comment records the intent: "the Atlas API server joins
this proxy when 7.3 wires real data". A proxy test that passes against a stand-in backend
proves only nginx config; with the server in the stack, one e2e request proves the whole
chain this slice builds — nginx location, TLS verify, prefix forwarding (APC-08), server
routing, ES store — against the parity-tested surface. The image and its env already
exist for the server's own e2e; reusing them is copying, not building.

**Alternatives.** Keep Keycloak as the `/api/` backend: cheapest, and the chain stays
untested until 7.4 — the same gap 7.1 accepted with a comment; 7.3 is where the comment
matures. Mock the server in nginx config: a mock that answers like the server is a second
server to maintain.

**Consequences.** Webapp e2e `dependsOn` gains `aurelius-atlas-server:docker-build` and
the dev Elasticsearch `up`; the suite's boot chain lengthens by one container (ES is
already up for the server's own e2e, so cache-hit order matters little). The dev-pair
`nx serve aurelius-atlas-server` + `nx serve aurelius-atlas-webapp` becomes the documented
development loop.
