# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-128. Aurelius dictionaries become XLIFF, migrated whole, with the JSON as fixture

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius flat-JSON dictionaries (105 keys, `en-US` and `nl-NL`) are converted in
full to XLIFF catalogues for the built-in `@angular/localize` at 7.1, before any screen needs them.
The Aurelius JSON is vendored into `apps/aurelius-atlas-webapp/tests/fixtures/` and a Vitest test
asserts every key, English value, and Dutch value appears in both catalogues. `nx extract-i18n`
maintains the template catalogue from then on.

**Reason.** The Aurelius app localises through `@ngx-translate/core` and its own `I18nService`,
registered in the module constructor; this workspace localises with `@angular/localize`, whose
catalogues the build compiles and which needs no service, so no runtime translation lookup
survives. Converting all 105 keys at once keeps one slice responsible for the dictionary: a
per-screen migration scatters the work, and the missing keys surface as untranslated Dutch long
after the screen that introduced them is accepted. The vendored JSON makes completeness a checked
fact that runs offline, not a claim in a pull request.

**Alternatives.** Port `I18nService` as a shim over `$localize`: keeps a `translate` pipe and a
`@ngx-translate`-shaped API the workspace has replaced. Migrate keys per slice: no completeness
gate, and Dutch gaps found in deployment. Machine-translate the Dutch: the Aurelius `nl-NL`
dictionary is human-reviewed work, and replacing it discards that.

**Consequences.** `{{ }}` placeholders in Aurelius strings become `$localize` interpolated
expressions, and the `TranslateService.get()` call sites become static messages. Aurelius keys with
no consumer after 7.10 are dead weight until swept; the completeness test is what keeps them named
rather than silently dropped.

### DD-129. Google Analytics and clickstream are dropped, not ported

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** `@models4insight/google-analytics` and `@models4insight/services/clickstream`, both
wired by `Core.imports`, are dropped. The webapp's operational signals go to OpenTelemetry through
`aurelius-atlas-observability`, as every other app's do.

**Reason.** The workspace observes itself internally and its operational data never leaves it (
[ADR 016](../../../../docs/architecture/adr/016-the-system-observes-itself-internally.md) ). The example app's
content security policy keeps `connect-src 'self'` and names only the Keycloak origins (
[ADR 039](../../../../docs/architecture/adr/039-data-is-protected-where-it-travels-and-where-it-rests.md) ); a
browser call to a third-party analytics host would need that policy opened for a second telemetry path that
duplicates what OTel traces and metrics already carry.

**Alternatives.** Port it behind a config flag: keeps the egress and the policy exception available
in production, which is the exposure the decision avoids. Keep clickstream to OpenTelemetry:
page-view tracking is the part of it worth having, and it belongs in the observability library, not
in a port of one app's vendor integration.

**Consequences.** Product usage analytics from the browser stop when the webapp replaces the
Aurelius interface at 7.10; page views can be re-added to `aurelius-atlas-observability` as a
deliberate feature. No Aurelius code is translated, so this is the one part of `Core.imports` that
has no destination.

### DD-130. The webapp's config is a typed AppConfig, and `environment.ts` is not ported

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius `environments/environment.ts` (and its `production` flag, Keycloak
settings, `shell.appName`, i18n, telemetry, and notifications blocks, all read by `Core.imports`)
is not ported. The webapp reads a typed `AppConfig` from `/config.json` at bootstrap, following
`apps/aurelius-atlas-frontend-example`: the file is fetched and validated before
`bootstrapApplication`, and a missing, unreachable, or malformed file throws.

**Reason.** Build-time settings make one artifact behave differently per deployment, so the unit validated is
not the unit that ships (
[ADR 010](../../../../docs/architecture/adr/010-the-unit-validated-is-the-unit-that-ships.md) ), and settings
arriving through one channel that fails loudly is the workspace rule (
[ADR 018](../../../../docs/architecture/adr/018-settings-arrive-at-startup-through-one-channel.md) ). The
Aurelius app already compiles a separate bundle per environment, and its `environment.ts` carries the Keycloak
client and realm that a deployment must be free to set.

**Alternatives.** Keep `environment.ts` for dev and add `config.json` for production: two channels,
and the dev one is the one developers exercise. Read settings from `NGINX_*` variables at container
start: the hardened runtime image has no shell tooling to render them (the example app's
`AGENTS.md` records why its nginx template is resolved by the consumer, not at start).

**Consequences.** Every Aurelius call site that read `environment.x` reads `AppConfig`, so a
setting has one shape per deployment rather than one per build. The `dev/config.json` pattern means
development assets are bundled only in the development build, so a real secret never rides in a
production bundle.

### DD-132. The wildcard fallback redirects to the destination, not through the root

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius fallback `{ path: '**', redirectTo: '' }` is ported as
`{ path: '**', redirectTo: 'search/browse', pathMatch: 'full' }`. The chain
`'**' -> '' -> '/search/browse'` that the Aurelius router resolves in two hops is one hop here.

**Reason.** Angular 22.2's router no longer re-triggers the empty-path redirect after a wildcard
redirect lands on `''` (angular/angular router fix `e9bf52aa03`, "require outlets to match a route
before processing child segments"), so the literal port lands on `/` and renders a blank router
outlet — verified in a browser, not theorised. SHL-05 promises the observable Aurelius behaviour:
an unknown path ends on the default destination.

**Alternatives.** Keep `redirectTo: ''` and add a redirect-triggering route: a workaround whose
shape exists only to dodge a router fix. Land on `/` and let the root redirect handle it: changes
the observable URL (`/` vs `/search/browse`), which is the parity SHL-05 is written against.

**Consequences.** If a future Angular restores chained redirects, the one-hop form keeps working —
it encodes the destination, not the chain. The `''` route remains the single definition of the
default destination; the fallback names it, so a later slice that moves the default edits both
lines, and `routes.spec.ts` pins both.

### DD-133. Operational telemetry lands with 7.1; the auth wiring stays with 7.3

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The webapp's OpenTelemetry wiring — trace and metric exporters, the
tracing `ErrorHandler`, and the `traceparent` HTTP interceptor, all from
`aurelius-atlas-observability` — lands with 7.1, not with 7.3. The Keycloak
providers and the bearer-token interceptor stay in 7.3, which owns the auth wiring.

**Reason.** DD-129 attaches the telemetry replacement to this increment, and the
shell is where the Aurelius `Core.imports` (the single wiring point that carried
both GA/clickstream and the app's providers) dissolves — so the OTel half of that
dissolution belongs here. The exporter endpoint is already a 7.1 config field
(SHL-02), the image already proxies `/otel/` (SHL-11), and the CSP already allows
it (SHL-11); deferring the wiring to 7.3 left the plumbing with no consumer.
Telemetry is also the shell's own operational signal — the earlier it covers the
app, the more of the port it observes.

**Alternatives.** Wire everything in 7.3: keeps one bootstrap commit, but leaves
DD-129 unsatisfied for a whole increment and pairs telemetry with auth for no
dependency that exists — the OTel providers need only `AppConfig`. Wire traces
only, metrics in a later slice: the metrics provider is the same call with a
metrics exporter; splitting them adds no review value.

**Consequences.** The e2e `/otel/` proxy test (SHL-11) gains a producer: the
served app now exports through it. The interceptor covers the API calls 7.3 adds,
so trace propagation is in place before the first request exists. The bootstrap
in `app.config.ts` matches the example app's provider set minus Keycloak, which
is the visible difference between the two files.
