# 7.1 Webapp shell and localisation

- **Status:** in progress
- **Pull request:** \#98
- **Records:** ADR 053; DD-126, DD-127, DD-128, DD-129, DD-133; relies on ADR 007, ADR 018, DD-019

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/feat-otel-edge-tracing/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

Stand up `apps/aurelius-atlas-webapp` as a real Angular 22 application in this workspace, and port the **application shell** — the part of the Aurelius interface that needs no catalogue API.

The Aurelius shell is genuinely thin, which is why it is first: `app.component.html` is a bare `<router-outlet>`, `app.component.ts` is 8 lines, and the routing module is 26. The `Shell` component of `libs/shell` is not part of the shell — it is applied by `search-routing.module.ts` and `dashboard-routing.module.ts`, so it arrives with 7.4 and 7.5.

- **`apps/aurelius-atlas-webapp`**: project, `main.ts` with `bootstrapApplication`, `app.config.ts` with zoneless change detection and runtime config, `routes.ts`, the root component, global styles, `Dockerfile`, and Playwright e2e.
- **Localisation bridge**: the Aurelius flat-JSON dictionaries (105 keys, `en-US` and `nl-NL`) become XLIFF catalogues under the built-in `@angular/localize`, and `nx extract-i18n` maintains them.
- **A placeholder route surface**, so the router, the locale switch, and the build are all real and testable before any feature exists.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| The `Shell` chrome (nav bar, breadcrumbs, app bar) | 7.4 (search), 7.5 (browse) |
| Any screen: browse, search results, entity details, editor | 7.4 – 7.9 |
| The Atlas REST client, and every call to it | 7.3 |
| Shared presentational components | 7.2 |
| Keycloak sign-in enforced on routes | 7.3, which owns the auth wiring; 6.1 the semantics |

## Semantics

| Id | Rule |
| --- | --- |
| SHL-01 | The application bootstraps with `bootstrapApplication` and `provideZonelessChangeDetection`, and declares no `NgModule` |
| SHL-02 | Bootstrap reads `/config.json` and validates it into the typed `AppConfig`; a missing, unreachable, or malformed file throws at bootstrap |
| SHL-03 | The root component renders a router outlet and nothing else, as the Aurelius root does |
| SHL-04 | `GET /search/browse` renders the browse placeholder, the Aurelius default destination |
| SHL-05 | An unknown path redirects to the default destination, matching the Aurelius `**` fallback (one hop, DD-132) |
| SHL-06 | Scroll position is restored on browser back and forward, as `scrollPositionRestoration: 'enabled'` does in Aurelius |
| SHL-07 | The app is served in `en-US` and `nl-NL`; a build localises both, and `nx extract-i18n` regenerates the template catalogue |
| SHL-08 | Every one of the 105 Aurelius dictionary keys is present in the `en-US` catalogue with its Aurelius English text, and in the `nl-NL` catalogue with its Aurelius Dutch text |
| SHL-09 | No component in the webapp imports `@ngx-translate/*`, and no template uses the `translate` pipe |
| SHL-10 | No setting is read from a build-time `environment` file: base URLs, client ids, and export endpoints come from `AppConfig` |
| SHL-11 | The built image serves the app over TLS on 8080, proxies `/api/` and `/otel/` as the example app's nginx config does, and its CSP keeps `connect-src 'self'` |
| SHL-12 | A Playwright scenario loads the app in each of chromium, firefox, and webkit, reaches the browse placeholder, and switches locale |
| SHL-13 | Every `signal`, service, and pure function the slice adds has a Vitest test naming it, and the coverage gate for the app holds |
| SHL-14 | The app exports traces and Core Web Vitals metrics to the `otelExporterUrl` through `aurelius-atlas-observability`, records uncaught errors as span events, and propagates `traceparent` on HTTP calls (DD-129) |

SHL-01 and SHL-10 are the point of the slice: they make the project real on this workspace's rules before any feature code arrives, so no later slice inherits a legacy scaffold.

SHL-08 keeps the Aurelius dictionary complete rather than migrating the keys a screen happens to use. A partial dictionary makes each later slice responsible for adding strings, and the gaps surface as missing translations in Dutch months later (DD-128).

## Aurelius origin

Cited by path in `aureliusenterprise/aurelius` at the cloned commit, so a reviewer can compare:

| Aurelius | Becomes |
| --- | --- |
| `apps/atlas/src/main.ts` (`platformBrowserDynamic().bootstrapModule`) | `src/main.ts` (`bootstrapApplication`) |
| `apps/atlas/src/app/app.module.ts` | `src/app/app.config.ts` providers; `Core.imports` is dissolved, not ported |
| `apps/atlas/src/app/app-routing.module.ts` | `src/app/routes.ts` |
| `apps/atlas/src/app/app.component.{ts,html,scss}` | `src/app/app.component.*` |
| `apps/atlas/src/environments/environment.ts` | `src/app/config.ts` + runtime `/config.json` |
| `apps/atlas/src/translations/{en-US,nl-NL}.json` | `src/locale/messages{,.nl-NL}.xlf` |
| `apps/atlas/src/styles.scss` (and the `@models4insight/styles` it uses) | `src/styles.scss` on `@aurelius/atlas-brand` tokens |
| `libs/i18n` (`I18nService`, `I18nModule.forRoot`) | `@angular/localize` + a locale service following the example app |
| `apps/atlas/proxy.conf.json`, `project.json` targets | the workspace's `proxy.conf.json` + inferred targets |

`@models4insight/google-analytics` and the `ClickstreamModule` of `libs/services/clickstream` are **dropped, not ported**: the workspace observes itself through OpenTelemetry ([ADR 016](<https://aureliusenterprise.github.io/feat-otel-edge-tracing/architecture/adr/016-the-system-observes-itself-internally/index.md>)) and `aurelius-atlas-observability`, and a second telemetry path to a third-party analytics host would add an egress the CSP is built to refuse (DD-129).

## Deviations

None against Apache Atlas: the Aurelius interface is Aurelius's own, and the Atlas dashboards are untouched (WBP-07). Against the Aurelius product, the two intended differences are recorded in [design-log](<https://aureliusenterprise.github.io/feat-otel-edge-tracing/architecture/conversion/design-log/index.md>): telemetry goes to OpenTelemetry instead of Google Analytics (DD-129), and localisation moves from a `TranslateService` abstraction to the built-in one (DD-128).

## Acceptance

- `apps/aurelius-atlas-webapp/tests` (co-located `.spec.ts`, Vitest) — config parsing and the failure modes of SHL-02, the metrics-endpoint derivation of SHL-14; the route table of SHL-04, SHL-05, SHL-06; the root component of SHL-03; the locale service of SHL-07. SHL-13.
- `apps/aurelius-atlas-webapp/e2e/` — pytest + Playwright against the built image: SHL-12, plus SHL-11's TLS and proxy paths and the CSP check. (DD-228: SHL-11's TLS half lost its e2e check — the CA-verified handshake pinned the workspace mkcert CA, i.e. dev deployment material; the shipped nginx config's TLS block is reviewed, the proxy paths and CSP stay e2e-guarded.)
- `scripts/check-webapp-purity.sh` (or an ESLint rule set) — WBP-02, SHL-01, SHL-09, SHL-10: greps the tree for `@NgModule`, `platformBrowserDynamic`, `@models4insight/`, `@ngx-translate/`, `environment`, and a state-owning `new BehaviorSubject` outside RxJS interop. Run in CI and by `nx run aurelius-atlas-webapp:check-purity`.
- Dictionary completeness for SHL-08 — a Vitest test that loads the Aurelius JSON from the cloned reference checkout path recorded in the test, and asserts each key and value appears in both catalogues. Reference JSON is vendored into `tests/fixtures/` (DD-128), so the test runs offline.
- Umbrella checks: `nx build`, `nx test -c ci`, `nx lint`, `nx e2e` for the app.

### Definition of done, in order

1. `nx serve aurelius-atlas-webapp` starts and the app loads at `/search/browse` in a browser, zoneless, with no `NgModule` in the tree.
2. The purity check passes and is wired into CI.
3. Both locales build; the 105 keys are proven present in both.
4. The e2e scenario passes in all three browsers against the built image.
5. `apps/aurelius-atlas-webapp/AGENTS.md` and `README.md` describe the app and its removal, per [ADR 003](<https://aureliusenterprise.github.io/feat-otel-edge-tracing/architecture/adr/003-every-project-documents-itself/index.md>).
