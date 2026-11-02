# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-145. The Shell chrome is ported search-free; the root composes header and footer

- **Status:** Proposed (the "navbar search bar" wording superseded by
  [DD-218](../7-4a-search-results/design.md#dd-218-74-splits-in-two-and-the-search-bar-lands-in-the-hero-the-list-is-infinite-scroll)
  )
- **Increment:** 7.11
- **Date:** 2026-10-20

**Decision.** The Aurelius chrome (header, footer) is ported now, on the user's request,
as its own slice (7.11), composed directly by the root component — `Header` (the 7.2
ui-lib component) over the router outlet, footer below. What is ported: the brand (app
name from `/config.json`, linking to the default route), the Documentation link, the
language dropdown, the account dropdown (identity, Keycloak account console, logout),
and the copyright footer. What is not: the global search bar and nav buttons (they join
7.4, unchanged from DD-143's reasoning), the PWA install/update buttons (no service
worker is ported), the Models4Insight services dropdown (not part of this product), the
sticky loading/pipeline block (nothing to track yet), and the login button (every route
is guarded, APC-05 — the logged-out navbar is unreachable). The navbar is not
`is-fixed-top`. Switching language is a full-page navigation into the locale tree, not
ngx-translate's runtime swap.

**Reason.** DD-143 deferred the chrome _with the search bar_ because wiring them was one
decision; the user has since asked for the shell as its own deliverable, so the seam
moves: the frame is orthogonal to search, and a screen wearing its header/footer is
strictly closer to the product than a bare outlet. DD-143's search half stands
unchanged — this entry supersedes only its Shell-chrome sentence. The deferred controls
each fail a test this workspace already enforces: an install button with no service
worker is a promise the build does not keep; a services dropdown points at products
outside this repo; a login button behind a guard is dead markup; a loading bar has no
long navigation to track while the only screen is static. Aurelius's `Shell` module,
its service (token refresh on window focus — keycloak-angular owns refresh, DD-141) and
its reusable-route strategy are Redux-era plumbing the port's idioms replace (DD-135).

**Alternatives.** Port the shell wholesale with the deferred controls hidden behind
config flags (Aurelius's own `standalone`/`hideDocumentation` knobs): config that only
one deployment ever flips is dead code (the atlas environments never set them); the
user asked for the shell, not for a feature-flag audit. Wait for 7.4: the chrome is
search-independent and the user wants it now.

**Consequences.** The 7.11 navbar is static; 7.4 adds the search bar and nav buttons to
it, at which point `is-fixed-top` and the content offset return together with the sticky
loading bar (a pinned header is a layout contract, not a class). The root's "bare
outlet" spec (SHL-03, 7.1) is superseded by SHC-01 — the Aurelius root _is_ the shell,
and the reading that motivated 7.1's placeholder retires. The shell's chrome strings are
new vendored fixtures (`shell.header.*`, `shell.footer.*`), bridged like the components
dictionary (DD-136), so UIC-04's invented-string gate extends to them.

### DD-146. Session chrome injects the keycloak-js `Keycloak` instance, not keycloak-angular's

`KeycloakService`

- **Status:** Accepted
- **Increment:** 7.11
- **Date:** 2026-10-20

**Decision.** `Session` and `ShellHeader` inject the `Keycloak` client
instance (keycloak-js) — the token `provideKeycloak` registers — for the
identity read (`tokenParsed`) and for `logout()`. keycloak-angular's
`KeycloakService` is not injected anywhere.

**Reason.** `KeycloakService` is the deprecated pre-v19 class: v21's
`provideKeycloak` provides the `Keycloak` instance and the event signal
and does **not** register `KeycloakService` (the library's own services
and guards inject `Keycloak`, e.g. `includeBearerTokenInterceptor`,
`createAuthGuard`'s `AuthGuardData.keycloak`). Injecting the
not-provided class crashes the production image at boot (NG0201
NullInjectorError, found by the 7.11 e2e run: every authenticated
scenario errored in the guard, where the chrome renders). Unit specs
missed it — they mock the token; the dev server never renders the chrome
before the guard redirects, so only the built image exercised it.

**Alternatives.** Provide `KeycloakService` manually (`useExisting: Keycloak`
-style): re-provides a deprecated facade for a class slated for removal.
`inject(KEYCLOAK_EVENT_SIGNAL)`: a signal wrapper, not the client — no
`logout()` on it.

**Consequences.** SHC-05/SHC-08's "Keycloak client" is now precise: the
keycloak-js instance. Spec test providers use `{ provide: Keycloak, … }`.
7.4's session-touching code follows the same token.

### DD-147. Dev Keycloak users carry `default-roles-master` explicitly

- **Status:** Accepted
- **Increment:** 7.11 (dev infrastructure)
- **Date:** 2026-10-21

**Decision.** The dev users in `dev/keycloak/import/master.json`
(`aurelius-writer`, `aurelius-reader`) declare `"realmRoles":
["default-roles-master"]`.

**Reason.** The SHC-05 Account-security link opens the Keycloak Account
Console, whose REST calls (`/realms/master/account/*`) require the
`account` client's `manage-account`/`view-profile`; those roles reach a
user only through `default-roles-master`'s composites. Keycloak's realm
import does **not** auto-grant the realm default role to imported users,
so the dev users reached the console with no roles and every REST call
401s — the console renders "Something went wrong". Verified live: with
the role granted, the console's profile page renders; without it, the
same session 401s on `supportedLocales` and the account root. The Admin
REST cannot repair a running realm here (every `role-mappings/realm`
POST answers 404 "Role not found" for these users), which makes the
import file the single declarative place the grant can live.

**Alternatives.** Grant the roles per user through the admin console by
hand: invisible to new clones, lost on stack recreate. Add the account
client roles directly to the users: duplicates what
`default-roles-master` already composites and drifts when Keycloak
version changes reshape that role. A `defaultRoles` realm attribute
(makes the role default for users created after import): does not reach
the users the import itself creates.

**Consequences.** The Account Console works for both dev users, dev and
e2e. Applying the change to a running stack requires recreating the
users — a boot re-import skips an existing realm wholesale — the recipe
is in `dev/keycloak/AGENTS.md`. New realm-default-role needs (e.g.
`offline_access` for refresh tokens) arrive here, not per client.
