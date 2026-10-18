# 6.1 Authentication

- **Status:** in progress
- **Pull request:** [\#91](<https://github.com/aureliusenterprise/aurelius-atlas/pull/91>), extended onto 0.6
- **Records:** DD-036 to DD-041; DV-10, DV-11, DV-12 (DV-04 and DV-06 are retired when this lands); relies on ADR 007, ADR 039, ADR 046, ADR 052, DD-034

## Scope

The server becomes an OpenID Connect relying party in front of the shared identity provider (`dev/keycloak`, ADR 007), the dashboards learn who the user is, and every endpoint except the few Java Atlas keeps public starts demanding a principal. This ports the Keycloak mode of Atlas 2.4.0 (`atlas.authentication.method.keycloak` on): the adapter's browser flow, its session, its bearer acceptance, its CSRF filter, and the session endpoint's user and groups.

- **`apps/aurelius-atlas-server`**: a new `auth` module — OIDC discovery and JWKS verification, the authorization-code flow, server-side sessions with the `ATLASSESSIONID` cookie, bearer access-token verification, the `AtlasCSRFPreventionFilter` port, and the guard that admits or rejects every request; `admin/session` reports the real user and groups.
- **`dev/keycloak`**: a confidential client for the Atlas relying party, realm roles for the dev users, in `import/master.json`.
- **`apps/aurelius-atlas-dashboard`**: nginx gates page loads with `auth_request` and hands unauthenticated browsers to the server's login start (DD-036); the resolved config and its shipped template change together. No vendored dashboard source changes (ADR 046).

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Per-endpoint authorization policies (who may read/write what) | 6.2 (simple authorizer only, DV-02) |
| File/LDAP/PAM/Knox login | not planned (ADR 050) |
| `createdBy`/`updatedBy` on type definitions and audit | 1.4–1.5 retro-fit; DV-06 retired here |
| Saved searches per user | 4.5 (`UserProfileService`) |
| Shared session state across server replicas | not planned (HA not planned) |
| TLS and issuer changes | none; issuer is `keycloak.localhost` |

## Semantics

Configuration names follow the FastAPI example's pattern; all are `AURELIUS_ATLAS_SERVER_`-prefixed (SRV-01). The relying-party registration mirrors the adapter config of `AtlasSecurityConfig#adapterDeploymentContext` (`atlas.authentication.method.keycloak.{realm,auth-server-url,resource,credentials-secret}`).

### The guard

| Id | Rule |
| --- | --- |
| AUTH-01 | Authentication is on when an issuer is configured; with no issuer configured the server answers as before and the session reports no user (DV-04, scoped to unconfigured installations) |
| AUTH-02 | Every Atlas API request needs a valid principal, except `admin/status`, `admin/liveness` and `admin/readiness` (DV-12) and the auth endpoints themselves (`/api/atlas/auth/*`, `/logout.html`); static files are served by the dashboard origin and are never guarded (DSH-08) |
| AUTH-03 | A request carrying `Authorization: Bearer <token>` is authenticated by verifying the token against the issuer's JWKS (signature, `iss`, `aud`, `exp`) and requiring the access-token type (`typ: Bearer` — an ID token proves a login, not API access); it never creates or touches a session; an invalid bearer is answered 401 |
| AUTH-04 | An unauthenticated API request is answered 401 with the Atlas error body (SRV-04), never with a redirect — an expired session mid-use looks like an error to the dashboard, which has a 401 handler (DV-11) |
| AUTH-05 | A CSRF-protected browser request (CRS-01) without a valid session fails the CSRF check — there is no token to match — and is answered as CRS-01 dictates, before the endpoint or any redirect logic is reached |

### The browser flow and the session

| Id | Rule |
| --- | --- |
| AUTH-06 | `GET /api/atlas/auth/login`, reached for a guarded page load without a valid session (DSH-07), 302s to the issuer's authorization endpoint (authorization-code flow with PKCE, `state` and `nonce` kept server-side) with the registered redirect URI; the intended URL is kept and returned to after login (only paths of this origin — leading-`//`, backslash and control-character forms are dropped); the flow is bound to the browser by a short-lived `HttpOnly` `Secure` `SameSite=Lax` flow cookie (DD-041) |
| AUTH-07 | `GET /api/atlas/auth/callback` exchanges the code, validates the `id_token` (JWKS signature, `iss`, `nonce`, expiry — the login belongs to this flow) and the `access_token` (signature, `iss`, `aud`, expiry), creates the session from the **access token's** claims (DD-038 — Keycloak keeps roles out of the `id_token`, as `AtlasKeycloakAuthenticationProvider` reads the access token), and 302s to the kept URL; a `state` mismatch, a missing or foreign flow cookie, or a failed exchange is answered 401 and creates no session (DD-041: the callback mints a session only in the browser that started the flow) |
| AUTH-08 | The session cookie is `ATLASSESSIONID` — `HttpOnly`, `Secure`, `SameSite=Lax`; the session id is minted at login and never accepted from the query string (no URL rewriting); the server keeps sessions in memory (in-process) and sweeps every expired or over-lifetime session on store activity, so abandoned sessions are reclaimed (DD-041) |
| AUTH-09 | The server refreshes the session's access token with the stored refresh token before it expires — the window capped to half the token's issued lifetime — and updates the session's user and groups from the refreshed token, so a role change reaches the session; a session without a refresh token authenticates only until its access token expires; when the refresh fails, the session is destroyed and requests to it are answered as unauthenticated (AUTH-04 for the API, AUTH-06 for a page load) |
| AUTH-10 | `GET` or `POST` `/logout.html` at the origin destroys the session, expires the cookie, and sends the browser to the issuer's end-session endpoint, with `/login.jsp` on the deployment's own origin as the post-logout redirect — Atlas's `logoutSuccessUrl` — and landing back at it, where the login page answers and the login flow starts again; the issuer allowlists each installation's landing (DV-10, DD-040) |

### The session endpoint

| Id | Rule |
| --- | --- |
| ADM-06 | With authentication on, `GET /api/atlas/admin/session` on a valid session or bearer reports `userName` (the token's preferred username) and `groups` (the union of the user's realm roles and the relying-party client's roles, deduplicated, first-seen order); the other session values keep their server-wide defaults, and both entity permissions stay false until the authorizer arrives (6.2) |
| ADM-07 | When a session idle timeout is configured, the session response carries `atlas.session.timeout.secs` so the dashboard's idle timer matches it; an idle session is destroyed and answers as unauthenticated |

### CSRF

| Id | Rule |
| --- | --- |
| CRS-01 | A request whose `User-Agent` matches the browser regex (`^Mozilla.*,^Opera.*,^Chrome`) and whose method is not in `atlas.rest-csrf.methods-to-ignore` (default `GET,OPTIONS,HEAD,TRACE`) must carry the custom header (`X-XSRF-HEADER` by default) with the session's CSRF token; a missing or wrong header is answered 400 with the JSON body `{"msgDesc": "Missing header or invalid Header value for CSRF Vulnerability Protection"}`, as in Atlas |
| CRS-02 | The `_csrfToken` the session reports is minted at the first session call on the session (20 letters and digits, ADM-05's form) and stays the same for the session's whole life |
| CRS-03 | A request whose `User-Agent` does not match the browser regex is exempt from the CSRF check — the path service clients (and bearer calls without a browser UA) take, as in Atlas |

### The dashboard origin

| Id | Rule |
| --- | --- |
| DSH-07 | An unauthenticated browser request for a dashboard page (`/`, `/index.html`, `/n`, `/n/`) is redirected to the server's login start and, after Keycloak, back to the intended page; an authenticated page load is served unchanged |
| DSH-08 | Static assets (JS, CSS, images, favicons) are served without authentication, as in Atlas's ignore list, so the login flow's own assets load |
| DSH-09 | `/login.jsp` — Atlas's login URI (AtlasLoginServlet), its `logoutSuccessUrl`, and the vendored UI's 401 landing — is the fifth gated page: an anonymous visit takes the login start with the URI kept (as Atlas's adapter runs the dance through it), and a visit on a session is served the login page, which resolves to the dashboard the user was on: the session's `atlas.ui.default.version` picks the default, the browser's `last_ui_load` wins over it, and a URL fragment carries over — the resolver of Atlas's login form (DD-040) |

### The parity harness with authentication on

| Id | Rule |
| --- | --- |
| SCN-16 | A scenario may declare `needs_auth: true`: a harness that runs a guard-on installation passes it (`load_scenarios(..., authenticated_run=True)`), and a plain run skips it with the reason — its expectations exist only where the guard answers (AUTH-01's guard-off installation reports no user) |

DD-036 explains why page-load gating lives in nginx while the OIDC flow lives in the server; DD-037 fixes the server as the relying party and keeps the OIDC plumbing inside `aurelius_atlas_server` until the template's example retires (DD-019).

## Java origin

Apache Atlas `release-2.4.0`:

- `server-common/.../security/AtlasKeycloakAuthenticationProvider.java`: token → principal, role → authority extraction (what `groups` reports)
- `webapp/.../web/security/AtlasSecurityConfig.java`: the Keycloak filter chain, the `KeycloakAuthenticationEntryPoint` browser redirect, the public ignore list (`/login.jsp` kept guarded under Keycloak), `SessionCreationPolicy.ALWAYS`, session-fixation `newSession`, logout at `/logout.html` with `KeycloakLogoutHandler`, `logoutSuccessUrl("/login.jsp")` and `deleteCookies("ATLASSESSIONID")` (DD-040), and the adapter config keys
- `webapp/src/main/webapp/WEB-INF/web.xml`, `AtlasLoginServlet`, `login.html.template`, `dashboardv2/public/js/modules/atlasLogin.js`: `/login.jsp` as the login page and the `last_ui_load` resolver DSH-09 repeats
- `webapp/.../web/filters/AtlasCSRFPreventionFilter.java`: CRS-01 to CRS-03 and `ATLAS-401-00-040`
- `webapp/.../web/resources/AdminResource.java#getUserProfile`: user and groups in the session response
- `dashboardv2/public/js/main.js`, `utils/CommonViewFunction.js`, `views/site/Header.js`: the origin contract this must satisfy — the session fetch before start-up, the 401/403 handler, the idle timer reading `atlas.session.timeout.secs`, and the logout link to `/logout.html`

## Deviations

Added to [Deviations](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/conversion/deviations/index.md>) with this increment:

- **DV-10**: the browser dance is nginx `auth_request` plus the server's login start under `/api/` rather than the adapter's `/login.jsp` URI, because the dashboards are served by a separate process (DD-034) and the vendored UI is not touched (ADR 046).
- **DV-11**: an expired session hits by XHR is answered 401 with the Atlas error body where Atlas's entry point redirects the browser to Keycloak and the XHR receives its login page as HTML.
- **DV-12**: `admin/liveness` and `admin/readiness` stay unauthenticated; container probes and load balancers cannot hold a session. (`admin/status` is public in Atlas too.)
- **DV-13**: the session's `atlas.entity.update.allowed` and `atlas.entity.create.allowed` report false: the authorizer that answers them per user is increment 6.2, so 6.1 reports the user without yet reporting what the user may do.

Retired when this increment lands: DV-04 (authentication exists; its open behaviour survives only for unconfigured installations, AUTH-01) and DV-06 (the server knows a user).

## Acceptance

- `apps/aurelius-atlas-server/scenarios/admin/session.scenario.yaml` — gains the authenticated variant (ADM-06, the Java example `userName: admin, groups: [ADMIN]` met by a dev user holding the `ADMIN` realm role) and the DV-04 deviation rows are removed.
- `apps/aurelius-atlas-server/tests/` — the guard (AUTH-01 to AUTH-05) against a Keycloak testcontainer (the pattern of the FastAPI example's auth tests), bearer verification, session and refresh (AUTH-06 to AUTH-10), CSRF (CRS-01 to CRS-03), session user and groups (ADM-06, ADM-07); every function named by a `@pytest.mark.covers(..., rules=[...])` marker (ADR 049).
- `apps/aurelius-atlas-server/e2e/` — the stack grows `dev/keycloak`; tests log in as `aurelius-writer` (gets `ADMIN`) and `aurelius-reader` (no roles) and prove the flow over TLS.
- `apps/aurelius-atlas-dashboard/e2e/` — DSH-07 to DSH-09 with Playwright: an unauthenticated load lands on Keycloak's login and back; signing out of dashboardv3 and back in returns to it (DD-040); assets load without a session; the header shows the logged-in user (conftest starts Keycloak with the stack).
- Run: `uv run pytest apps/aurelius-atlas-server/tests`, `nx test aurelius-atlas-server -c ci`, `nx e2e aurelius-atlas-server -c ci`, `nx e2e aurelius-atlas-dashboard -c ci`, and `uv run aurelius-atlas-trace check` for the gaps.
