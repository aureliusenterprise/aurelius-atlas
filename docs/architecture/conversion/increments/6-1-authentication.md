# 6.1a Authentication

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-250, DD-251, DV-105 to DV-109; removes DV-04; relies on ADR 007, DD-141

The server requires an authenticated user on every request, as Atlas with its Keycloak provider does. A
request authenticates with a bearer token the provider issued, or with the session a browser signs in to
through the provider. The webapp and other clients send bearer tokens (DD-141); the vendored dashboards sign in
with the server's own login, an OpenID Connect authorization code flow, and keep a session cookie. The session
endpoint reports the user and their groups.

Recording the acting user on writes (`createdBy`, `updatedBy`, audits; DV-06, DV-15) is 6.1b; what a user may
do is 6.2.

## Scope

| Path                           | Answers                                                                      |
| ------------------------------ | ---------------------------------------------------------------------------- |
| every path but the open ones   | 401 or a redirect to sign in without an authenticated user                   |
| `GET /login.jsp`               | a redirect to the provider's sign-in; on its return, to the page first asked |
| `GET /logout.html`             | a redirect to the provider's sign-out, the session ended                     |
| `GET /api/atlas/admin/session` | the user's name and groups, and the session's CSRF token                     |

In `aurelius-atlas-auth`, the verifier's further audiences, `verify` and `discovery` (AUT-10). In
`aurelius-atlas-server`: `authentication` (the token verifier, the provider's metadata and keys, the
session store, the middleware) and `routes/login` (the login and logout pages); settings for the provider, the
confidential client and the session. In `dev/keycloak`, the confidential client `aurelius-atlas-server`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AUT-01 | Every request needs an authenticated user but `admin/status`, `admin/liveness`, `admin/readiness`, the dashboards' `css`, `img`, `libs` and `js` (also below `/n/`), `ieerror.html`, `migration-status.html`, `login.jsp` and `logout.html`                                                                                                                                                                                                                                                                           |
| AUT-02 | A request with an `Authorization: Bearer` header is authenticated by that token alone: an RS256 JWT signed by a key of the provider's key set, of the configured issuer, unexpired, whose `azp` or `aud` names a configured audience. Any other token is refused, whatever session the request carries                                                                                                                                                                                                                |
| AUT-03 | A user's name is the token's configured principal claim (`preferred_username` by default); their groups the configured groups claim, else the token's realm roles (DD-250)                                                                                                                                                                                                                                                                                                                                            |
| AUT-04 | A request without an authenticated user is answered 401 with `WWW-Authenticate: Bearer realm="atlas.com"` when it is below `/api/`, asks with `X-Requested-With: XMLHttpRequest` or carries an `Authorization` header (DV-106); any other is redirected to `login.jsp`, the URL it asked for remembered                                                                                                                                                                                                               |
| AUT-05 | `login.jsp` signs a browser in: it sends the browser to the provider's authorization endpoint with the confidential client, `openid` scope, a state, a nonce and a PKCE challenge; on the browser's return it exchanges the code, verifies the ID token (issuer, audience, nonce), starts a new session in the `ATLASSESSIONID` cookie (`HttpOnly`, `Secure`, `SameSite=Lax`) and sends the browser to the remembered URL, else `/`. A return with another state, an error or a code the provider refuses answers 401 |
| AUT-06 | A session authenticates as its user while its access token is valid; an expired one is refreshed with the refresh token. A session idle for the session timeout (60 minutes, as Atlas's `web.xml`), or whose refresh fails, ends (DD-251)                                                                                                                                                                                                                                                                             |
| AUT-07 | `logout.html` ends the session, expires its cookie and sends the browser to the provider's end-session endpoint with the ID token as hint, to return to `/`                                                                                                                                                                                                                                                                                                                                                           |
| AUT-08 | A request authenticated by its session, from a browser (`User-Agent` matching `^Mozilla.*`, `^Opera.*` or `^Chrome`), with a method other than `GET`, `OPTIONS`, `HEAD` or `TRACE`, must carry `X-XSRF-HEADER` equal to the session's `_csrfToken`, else it is answered 400 `Missing header or invalid Header value for CSRF Vulnerability Protection` (DV-107)                                                                                                                                                       |
| AUT-09 | `admin/session` answers the user's `userName` and `groups`; its `_csrfToken` is the session's, made on first ask and kept, or a new one for a request without a session. The entity permissions stay false until 6.2 (DV-105)                                                                                                                                                                                                                                                                                         |
| AUT-10 | The shared verifier (`aurelius-atlas-auth`) accepts tokens of several audiences, verifies a token outside a route dependency, and gives the issuer's discovery document, which the login uses                                                                                                                                                                                                                                                                                                                         |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/security/AtlasKeycloakAuthenticationProvider.java`: the user's groups from a claim
- `webapp/.../web/security/AtlasSecurityConfig.java`: the open paths, the Keycloak filters, the logout and
  session settings
- Keycloak's Spring Security adapter, which Atlas configures: `KeycloakAuthenticationEntryPoint` (401 or the
  login redirect), `KeycloakAuthenticationProcessingFilter` (bearer and login), `KeycloakLogoutHandler`
- `webapp/.../web/filters/AtlasCSRFPreventionFilter.java`
- `webapp/.../web/resources/AdminResource.java`: `getUserProfile`
- `webapp/src/main/webapp/WEB-INF/web.xml`: the session cookie and its timeout

## Deviations

- **DV-04** is removed: every endpoint but the open ones needs a login, and the session reports the user.
- **DV-109:** until 6.1b, audit events name no user, as DV-04 said of them before.
- **DV-105:** until 6.2, the session's `atlas.entity.create.allowed` and `atlas.entity.update.allowed` are false.
- **DV-106:** an API request without credentials is answered 401, where Atlas redirects any request but an
  `XMLHttpRequest` to its login page; the 401 has no body, where Jetty writes its HTML error page.
- **DV-107:** the CSRF header is required of session-authenticated requests only. Atlas requires it of every
  browser request, bearer-authenticated ones too, which a browser does not send unasked.
- **DV-108:** no basic authentication. Atlas's Keycloak adapter can exchange `Basic` credentials for a token;
  here clients obtain tokens from the provider themselves, and the server never sees a password (ADR 007).

## Acceptance

- `apps/aurelius-atlas-server/tests/` — AUT-01 to AUT-09 with tokens signed by a test key and a fake provider.
- `apps/aurelius-atlas-server/e2e/` — the parity scenarios and the e2e tests with tokens from the dev Keycloak,
  and the browser sign-in against it.
- `uv run aurelius-atlas-trace check`.
