# 7.3 API client and auth wiring

- **Status:** in progress
- **Pull request:** \#100
- **Records:** ADR 053; DD-050, DD-051, DD-052, DD-053; relies on ADR 007, ADR 018, ADR 038, DD-004, DD-041, DD-044

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

Give the webapp a real backend: the Atlas REST client in `aurelius-atlas-data-access`, and the Keycloak wiring the shell deferred (DD-044). This is the slice that closes the 7.0 audit question — *how does the Aurelius interface reach the server?* — and retargets the webapp's proxies at the server that answers.

The audit's answer shapes the whole slice (DD-050): the Aurelius app has **no base URL at all**. Every legacy URL is a relative path resolved against `<base href>`, and the `/api/atlas` prefix is injected entirely by the deployment proxy (the dev `proxy.conf.json`, the k8s Apache `ProxyPass`). Aurelius Atlas is built the other way round: the client owns the base URL (`API_BASE_URL`, fed from runtime `/config.json`, DD-041) and the proxy forwards a same-origin prefix untouched.

The client ports **the surface the server implements today** (DD-051): the type definitions of increment 1.6 (`/api/atlas/v2/types/**`) and the admin endpoints of 0.5 (`/api/atlas/admin/**`). It does not port calls to endpoints 2.x–4.x have not built — notably the search client, which the audit found is not an Atlas call at all (the Aurelius search posts to DuckDuckGo App Search engines that Aurelius Atlas does not have), and which arrives in 7.4 redesigned against `/v2/search/basic` when browse consumes it.

- **`aurelius-atlas-data-access`**: `TypeDefsService` and `AdminService` over the implemented endpoints, the typedef cluster of `libs/atlas/api/src/lib/types.ts` as typed DTOs with the server's camelCase wire names, and the Atlas error shape.
- **`apps/aurelius-atlas-webapp`**: `provideApiBaseUrl`, `provideKeycloak` (check-sso + silent-SSO), the bearer-token interceptor, a guard on the app root, and `silent-check-sso.html` — the provider set proven at the example app, minus what 7.1 already ships.
- **Proxies and dev infrastructure**: the dev proxy and the e2e nginx `/api/` location retargeted at the Atlas server; the Keycloak client gains the webapp's origins; the e2e stack runs the real Atlas server behind the proxy (DD-053).

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Any search call, and the App Search → Atlas search redesign | 7.4 (search), against `/v2/search/basic` (4.1) |
| Entity, relationship, glossary and lineage clients | 7.5–7.9, each behind its server increment (2.3+) |
| A server that verifies the bearer token | 6.1 (Authentication); 6.2 the authorizer |
| Sign-in enforced per-screen, session user in the UI | 7.4/7.5 (the `Shell` chrome reads `/admin/session`) |
| Type-definition UI | none — the client exists for 7.4's browse first |

## Semantics

| Id | Rule |
| --- | --- |
| APC-01 | The client composes every URL from the injected `API_BASE_URL` token; no endpoint host, port, or `/api/atlas` prefix is hard-coded in the client (WBP, DD-050) |
| APC-02 | Every endpoint the server implements today has exactly one typed client method: the typedefs of `/api/atlas/v2/types` and `version`/`status`/`session` of `/api/atlas/admin` (DD-051) |
| APC-03 | Client DTOs use the wire names the server writes (camelCase Java getter names), and the typedef cluster carries the fields of `AtlasTypesDef` (TDM-01, TDM-13) |
| APC-04 | A failed call surfaces the Atlas error shape (`errorCode`, `errorMessage`, optional `errorCause`) as a typed error, not a bare HTTP status |
| APC-05 | Bootstrap initialises Keycloak with `onLoad: "check-sso"` and a silent-SSO redirect; an unauthenticated visit to a guarded route redirects to the sign-in page |
| APC-06 | Every `/api` request carries `Authorization: Bearer <token>`; tokens live in Keycloak's in-memory store, never `localStorage` (DD-004, ADR 007) |
| APC-07 | Token refresh is keycloak-angular's, not a ported loop: no hand-written `updateToken` scheduler exists in the webapp (WBP-02) |
| APC-08 | Both webapp proxies forward `/api` to the Atlas server with the prefix intact — the dev proxy and the e2e nginx both (DD-050) |
| APC-09 | The Keycloak `aurelius` client's redirect URIs and web origins cover the webapp's dev ports (4300, 4301) and its e2e origin (18444) |
| APC-10 | Every client method has a Vitest spec naming it, the guard has one, and the e2e suite proves the guarded flow and a real server response through the proxy |

APC-01 is the rule the audit exists to write. A client that hard-codes `/api/atlas` reproduces the Aurelius coupling to its deployment: it cannot be tested against a stub, and it breaks the moment the API moves. The token already exists in `aurelius-atlas-data-access`; 7.3 is the slice that plugs it in.

APC-02 and APC-05..07 deliberately stop at the live surface. The legacy client is 65 files of endpoints the Aurelius server answers with a 404 today; porting them would ship a client that lies about the system, and its specs would assert calls nobody serves. The client grows one increment at a time, each method landing with the server increment that answers it.

APC-06 states what the token does today: the server ignores it until 6.1, and the interceptor is proven at the example app, which does verify. Sending a credential the server does not check is a stated condition of the pre-6.1 system (ADR 038 says the same of authorization), not a hidden gap.

## Aurelius origin

Cited by path in `aureliusenterprise/aurelius` at the cloned commit, so a reviewer can compare:

| Aurelius | Becomes |
| --- | --- |
| relative URLs + `<base href>` + deployment proxy (no base URL anywhere) | `API_BASE_URL` token from `/config.json`, prefix forwarded untouched (DD-050) |
| `libs/atlas/api/src/lib/type-def-api.service.ts` (`atlas/v2/types`) | `TypeDefsService.getTypedefs`, `getTypeDefByName`, per-kind lookups |
| `libs/atlas/api/src/lib/get-type-defs/`, `get-type-by-name/`, `get-classification-def-by-name/` | the same `TypeDefsService` methods (legacy duplicated service + free function) |
| `libs/atlas/api/src/lib/types.ts` (typedef cluster: `AtlasTypesDef`, `AtlasEntityDef`, `AtlasStructDef`, `AtlasClassificationDef`, `AtlasEnumDef`, `AtlasRelationshipDef`, `AtlasAttributeDef`, `AtlasConstraintDef`, `RelationshipEndDef`, `TypeCategory`, `Cardinality`, `IndexType`) | `atlas-typedef.ts` DTOs, same wire names (APC-03) |
| `libs/atlas/api/src/lib/utils.ts` (`createHttpParams`, nil-filtering) | `filterParams` in the client (the idiom the lib already uses) |
| `libs/atlas/api/src/lib/elastic/**`, `engines/atlas-entity-search.service.ts`, the `AppSearchService`→`AtlasEntitySearchService` DI alias | not ported — 7.4 redesigns it against `/v2/search/basic` (DD-051) |
| `libs/atlas/api/src/lib/{get-lineage-model,get-dashboard,gov-quality}/**` | not ported — backends Aurelius Atlas does not have |
| `libs/authentication` (`keycloak-js` + `ReplaySubject` auth state + manual `updateToken(5)` loop + `AuthenticationGuard`) | `keycloak-angular`: `provideKeycloak` + `createAuthGuard`, keycloak-angular's refresh (DD-052) |
| `libs/http/authorization-header.interceptor.ts` (`AuthTokenProvider` ctor injection per client) | `includeBearerTokenInterceptor` + `INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG` on `/api` |
| `libs/shell/shell.ts` `childRoutes(..., requiresAuth)` applying the guard | the guard declared once on the webapp root route (DD-052) |
| `apps/atlas/proxy.conf.json` (`/atlas` → `:21000/api/atlas`, prefix rewritten) | webapp `proxy.conf.json` `/api` → the Atlas server, no rewrite (APC-08) |
| `backend/m4i-reverse-proxy` (Apache `ProxyPass` per prefix) | the webapp nginx `/api/` location, TLS-verified (APC-08, DD-053) |

The legacy `libs/http` is not ported at all: `HttpService` (an `HttpClient` subclass), its cache interceptor, and its IE-header interceptor solve problems this workspace's `HttpClient` + interceptors do not have (WBP-02).

## Deviations

None against Apache Atlas: this slice adds a client for the Atlas REST API the server already implements, and the shapes come from the server's parity-tested models.

Against the Aurelius product, three intended differences are recorded in [design-log](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/conversion/design-log/index.md>): the client owns the base URL where Aurelius delegated it to the proxy (DD-050); the search client is not ported in this slice and will not be ported as written (DD-051); and the auth wiring is keycloak-angular's, not the Aurelius `libs/authentication` (DD-052, on the pattern 7.1 set for the rest of `Core.imports`).

## Acceptance

- `libs/angular/aurelius-atlas-data-access/src/lib/*.spec.ts` (Vitest, `HttpTestingController`) — every `TypeDefsService` and `AdminService` method names its URL and its response type (APC-02, APC-03); the error spec proves the typed Atlas error (APC-04). SHL-13's rule applies here too: coverage gate holds.
- `apps/aurelius-atlas-webapp/src/app/*.spec.ts` — the guard redirects an unauthenticated visit and lets an authenticated one through (APC-05); the config spec proves the providers are assembled (APC-06).
- `apps/aurelius-atlas-webapp/e2e/` — an unauthenticated load lands on the Keycloak sign-in page (APC-05); an authenticated session reaches the browse placeholder (APC-05, APC-09); `GET /api/atlas/admin/version` **through the nginx proxy** returns the server's version document (APC-08, DD-053), replacing the placeholder assertion that proxied Keycloak.
- Umbrella checks: `nx build`, `nx test -c ci`, `nx lint`, `nx e2e` for the app, plus `nx test aurelius-atlas-data-access -c ci` and `nx build aurelius-atlas-data-access`.
- Consumer regression: the example app is the data-access lib's current consumer, so `nx test aurelius-atlas-frontend-example -c ci` and its build must stay green (UIC-09's rule, applied to the lib).
- Purity: `check-purity` covers `libs/angular` since DD-048, so the ported client is gated — no `@models4insight/` import, no state-owning `BehaviorSubject`.

### Definition of done, in order

1. `nx serve aurelius-atlas-server` + `nx serve aurelius-atlas-webapp`: signing in through Keycloak lands on `/search/browse`, and a `/api/atlas/v2/types/typedefs` call from the browser answers through the proxy.
2. The client specs and guard specs pass, each naming its APC rule id.
3. `nx e2e aurelius-atlas-webapp` passes in all three browsers against the image, with the real Atlas server behind the proxy (DD-053).
4. The example app's tests and build are untouched-green.
5. `aurelius-atlas-data-access` and the webapp's `AGENTS.md`/`README.md` describe the new wiring and its removal, per [ADR 003](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/adr/003-every-project-documents-itself/index.md>).
