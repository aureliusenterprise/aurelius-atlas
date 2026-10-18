# Identity Management

This page answers how a person is admitted to Aurelius Atlas and where that lives, from the identity record ([ADR 007](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/007-one-shared-identity-provider/index.md>)). The authoritative rule set is the increment spec [6.1 Authentication](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/conversion/increments/6-1-authentication/index.md>); this page is the narrative and the diagrams, and cites rule ids (`AUTH-*`, `CRS-*`, `DSH-*`) rather than restating them.

## One provider, one relying party

Aurelius Atlas holds no user accounts and implements no sign-in page of its own. Keycloak is the only place people exist ([ADR 007](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/007-one-shared-identity-provider/index.md>)), and `aurelius-atlas-server` is its **OpenID Connect relying party**: it starts the browser flow, exchanges the code, verifies the tokens the provider issued, and keeps a session for the person the provider admitted. The server decides *who* a request is from; what that person may *do* is the authorizer's question (increment 6.2, DV-13).

The whole flow runs on the **dashboard origin** (`https://localhost:8444` in dev). The session cookie and the dashboards' relative URLs need one origin, so the dashboard image serves the pages, gates them, and proxies `/api/` to the server on the same origin (DD-034 in the [design log](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/conversion/design-log/index.md>), [DV-09](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/conversion/deviations/index.md>)); the OIDC flow itself lives in the server (DD-036). nginx only asks the server whether a request has a session and redirects — it holds no token or session logic.

## The guard

Every request reaches one middleware in a fixed order (`aurelius_atlas_server.auth.guard`). Authentication is on when an issuer is configured (`AURELIUS_ATLAS_SERVER_AUTH_ISSUER`); with no issuer the server answers as an open installation (AUTH-01, the retired DV-04's surviving case).

| Step | Decision | Rule |
| --- | --- | --- |
| 1 | Authentication off, or a public path (`admin/status`, `admin/version`, the liveness/readiness probes, `/api/atlas/auth/*`, `/logout.html`) — pass | AUTH-01, AUTH-02, DV-12 |
| 2 | The CSRF check for a browser `User-Agent`, before any authorisation | CRS-01 |
| 3 | A bearer token verifies against the issuer's JWKS and authenticates on its own, never touching a session | AUTH-03 |
| 4 | Otherwise the `ATLASSESSIONID` session, refreshed before its access token expires | AUTH-08, AUTH-09 |
| 5 | No principal: a navigation (Accept: text/html, not `/api/`) starts the login flow; an API call is answered 401 with the Atlas error body | AUTH-04, AUTH-06, DV-11 |

```
flowchart TD
    R[request] --> A{auth on?}
    A -- no --> P[pass through]
    A -- yes --> PUB{public path?}
    PUB -- yes --> P
    PUB -- no --> CSRF{CSRF ok?}
    CSRF -- no --> D4[400 CSRF body]
    CSRF -- yes --> B{bearer token?}
    B -- yes --> BV{verifies?}
    BV -- yes --> OK[Principal from token]
    BV -- no --> D5[401]
    B -- no --> S{session valid?}
    S -- yes --> OK2[Principal from session]
    S -- no --> W{navigation?}
    W -- yes --> L[302 login start, URL kept]
    W -- no --> D6[401 Atlas error body]
```

## Signing in

The dashboard's page load is the entry point. nginx asks the server `/api/atlas/auth/check` as an `auth_request` subrequest (the session cookie rides it) and, on a 401, redirects to the server's login start (`error_page 401 = @login`) with the intended page kept — never through an `/api/…` `error_page` path, which would re-enter the `/api/` proxy (DD-036). The server runs the authorization-code flow with PKCE and returns to the kept URL.

```
sequenceDiagram
    autonumber
    participant B as Browser
    participant N as nginx (dashboard origin)
    participant S as aurelius-atlas-server
    participant K as Keycloak (issuer)
    B->>N: GET /n/ (page load)
    N->>S: auth_request /api/atlas/auth/check (cookie rides)
    S-->>N: 401 (no session)
    N-->>B: 302 /api/atlas/auth/login?next=/n/ (error_page lands in @login)
    B->>S: GET /api/atlas/auth/login?next=/n/ (proxied /api/)
    Note over S: keeps next=/n/ and mints state + nonce (AUTH-06)
    S-->>B: 302 authorize URL (PKCE, registered redirect_uri)
    B->>K: GET /protocol/openid-connect/auth?...
    K-->>B: login form (#kc-form-login)
    B->>K: username + password
    Note over K: signs an access token (realm roles) and an id_token (nonce)
    K-->>B: 302 callback?code=...&state=...
    B->>S: GET /api/atlas/auth/callback (AUTH-07)
    S->>K: POST token (code + PKCE verifier)
    K-->>S: access_token, id_token, refresh_token
    Note over S: verifies both, session minted from the ACCESS token claims (DD-038)
    S-->>B: 302 /n/ with Set-Cookie ATLASSESSIONID
    B->>N: GET /n/ again
    N->>S: auth_request /api/atlas/auth/check
    S-->>N: 200 (session)
    N-->>B: dashboardv3
```

The session's principal comes from the **access token**, not the `id_token` (DD-038): Keycloak keeps realm and client roles out of the `id_token`, and Atlas's own `AtlasKeycloakAuthenticationProvider` reads the access token too — which the token-exchange test asserts with a roleless `id_token` and a roled access token. `GET /api/atlas/admin/session` then reports `userName` and `groups` (the union of realm and client roles) to the dashboard (ADM-06).

## Signing out, and back to the dashboard you left

The two vendored dashboards record the UI a person is on in the browser's `localStorage.last_ui_load` (v3's header and 401 handler write `"v2"`, v2's write `"v1"`) and both navigate to the same `/logout.html`, so the server cannot tell the source UI from a request. Atlas 2.4.0 keeps that decision in the **login page**: logout's `logoutSuccessUrl` is `/login.jsp`, and under Keycloak the URI stays off the ignore list so the adapter runs the dance through it, where the page's script (`atlasLogin.js`) reads `last_ui_load` and lands you back where you were.

Aurelius Atlas answers the same URI (DD-040, DSH-09): logout sends the browser to the issuer's end-session endpoint with `/login.jsp` as the post-logout redirect, `/login.jsp` is the fifth gated page, and on a session it serves the dashboard project's own login page (`apps/aurelius-atlas-dashboard/webapp/login.html`) — its inline script repeats the vendored resolver, so the vendored JavaScript is never edited (ADR 046).

```
sequenceDiagram
    autonumber
    participant B as Browser
    participant N as nginx (dashboard origin)
    participant S as aurelius-atlas-server
    participant K as Keycloak (issuer)
    Note over B: on dashboardv3, the header writes localStorage last_ui_load = v2
    B->>N: GET /logout.html (ungated, proxied)
    N->>S: ... (AUTH-10)
    S-->>B: destroys session, deletes cookie, 302 to end-session with post_logout_redirect_uri=origin/login.jsp
    B->>K: end-session (Atlas logoutSuccessUrl, DD-040)
    K-->>B: logout confirm (#kc-logout), then 302 origin/login.jsp
    B->>N: GET /login.jsp without a session
    N-->>B: 302 /api/atlas/auth/login?next=/login.jsp (fifth gated page, DSH-09)
    Note over B,K: the sign-in dance runs again, keeping next=/login.jsp
    S-->>B: 302 /login.jsp with a fresh cookie
    B->>N: GET /login.jsp on a session
    N-->>B: webapp/login.html (the login page)
    B->>S: XHR /api/atlas/admin/session (the page script)
    S-->>B: atlas.ui.default.version = v2
    Note over B: resolver of atlasLogin.js: last_ui_load = v2 wins, so /n/index.html
    B->>N: location.replace /n/index.html
    N-->>B: dashboardv3 - back where they left
```

## CSRF, and the API from scripts

A browser `User-Agent` on a state-changing method must carry the session's CSRF token in `X-XSRF-HEADER`; a missing or wrong header is answered 400 with Atlas's body (CRS-01). A non-browser `User-Agent` — every service client and every bearer call — is exempt, as in Atlas (CRS-03). A programmatic caller that holds no session uses a bearer token instead (AUTH-03), which the guard verifies against the JWKS and never turns into a session.

## The development arrangement

| Piece | Where |
| --- | --- |
| The realm, clients, and dev users | `dev/keycloak/import/master.json`, imported on start (`dev/keycloak/README.md`) |
| The relying-party client | the `aurelius-atlas` confidential client (PKCE `S256`, front-channel logout) |
| Dev users | `aurelius-writer` (realm `ADMIN`, client `aurelius-write`), `aurelius-reader` (no roles) |
| The server's settings | `AURELIUS_ATLAS_SERVER_AUTH_*` (`aurelius_atlas_server/settings.py`) |
| The page gate and login page | `apps/aurelius-atlas-dashboard/nginx.conf` and `webapp/login.html` |

The issuer is `https://keycloak.localhost:8443/realms/master`; its TLS listener carries every E2E/CI path, and the plaintext listener (8080) is the developer-browser convenience that [Data Encryption](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/platform/security/data-encryption/index.md>) records as the named relaxation of ADR 039. `nx up aurelius-atlas-dashboard` starts Keycloak with the product, so the authenticated path is exercised end to end wherever the system runs (ADR 007); the Playwright suite walks the whole sign-in and the sign-out-and-back dance.
