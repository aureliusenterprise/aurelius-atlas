# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-171. The alerts store groups by a quiet window

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** `AlertsService` is the app's one alert door (ALR-03): an
in-memory signal list of groups, newest first, capped at 30 (oldest
evicted). Grouping is a quiet window — an alert whose key (severity +
source + message) matches the **newest** group's merges into it while
the window is open (60 s from that group's last alert: `count` +1,
`lastSeen` moves); after the gap, a new group starts. A `newGroups`
counter counts arrivals, not alerts (merges do not move it — ALR-02a's
ring signal). The clock is an injectable token (`ALERT_CLOCK`), not
fake timers.

**Reason.** The user's review of the plan: "Sometimes the same error
occurs multiple times in quick succession. I'd like to be able to group
notifications so the user doesn't get overloaded." A flapping endpoint
fails per retry — ungrouped, one drawer row per failure. Merging by key
shows a burst as one row with a count (×7, 14:20–14:22). The window
bound keeps history honest: merging session-wide would weld an hour-old
error to a new burst of the same message; after the gap the old burst
is context, and the new one needs its own row. The newest-only merge
keeps the store append-only (a burst ends when anything else arrives —
the row's count is the burst's, not the message's total).

**Alternatives.** Merge into any group with the same key, session-wide
(one row per message forever — the user's phrasing "in quick
succession" named a window, and history loses its timestamps).
Timestamp-bucketed grouping (fixed 60 s bins split a burst at a bin
edge). A capped ring of raw alerts, grouped at render (the store then
knows nothing, and every consumer re-derives the same groups; the
bell's ring needs arrival counting, which raw-alert caps lose).
`fakeAsync`/`tick` for the window (the token clock makes the window a
constructor argument of the test, no zone patching under zoneless).

**Consequences.** In-memory: alerts die with the tab — session events,
not preferences; the persisted lane is DD-161's and this stays out of
it. `AlertGroup` (the ui-lib model, ALR-10) is the store's public row;
the merge-key `source` is internal to the store. A 60 s constant;
raising it is a one-line change. The cap's eviction is silent (alerts
are cheap, the drawer is not an archive).

### DD-172. The app's ErrorHandler chains: alert, then trace

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The root `ErrorHandler` is `AlertsErrorHandler`,
composing the trace handler: record the uncaught error as an `error`
alert (source `app`), then delegate to `AureliusTraceErrorHandler`,
which keeps its own delegation to Angular's default (ALR-04).
Recording is wrapped in try/catch — alerting must never break the
error path. The composition is a factory in `app.config.ts`
(`useFactory: alertsErrorHandlerFactory`), not a class the app
subclasses.

**Reason.** SHL-14's telemetry (7.1) owns the root handler; the alerts
drawer (ALR-04) needs the same event. Composition keeps both promises
exactly: the trace handler sees the untouched error, the user sees the
alert. The order is record-first: a delegate that throws (the default
handler re-throws in dev mode) must not cost the user the alert.

**Alternatives.** Subclass the trace handler (`super.handleError` then
record — the user's alert would depend on the delegate surviving, and
the app inherits a library's constructor). A second `ErrorHandler`
provider (DI: one token, one value). `provideEnvironmentInitializer`
with `window.addEventListener("error")` (the listeners are the DI
handler's input, `provideBrowserGlobalErrorListeners` already wires
them; a second listener double-records).

**Consequences.** Every uncaught error is now user-visible — noisy
runtime bugs surface in the drawer (the intent, ALR-04; the store's
window, DD-171, absorbs repeat spam). The trace path is unchanged: the
`app.config.spec.ts` provider-set specs keep SHL-14's shape.

### DD-173. The HTTP reporter: 5xx and network failures on /api

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** A functional interceptor, last of the three on
`provideHttpClient`, watches the response and reports the reportable
set (ALR-05): `5xx` responses and status-0 network failures on URLs
matching `/api/` — the bearer interceptor's pattern (APC-06), not a
hardcoded prefix. The message names method, path, and status (`no
response` for status 0) and rides the server's plain `error` message
when it sends one. The interceptor reports and re-throws; the caller's
observable is untouched. 4xx is silent.

**Reason.** The user asked for "any app error messages if they occur"
— a failing catalogue call is the app's most common real error. The
`5xx`-plus-network cut is the plan's standing default, accepted: a 4xx
is a client-side correction the calling feature already handles (its
form, its not-found view), and reporting it would train users to
ignore the drawer. The report is the drawer's, not the caller's:
7.4+ features keep their own `onError` UX; DD-171's window folds the
pairs into one row.

**Alternatives.** Per-call `onError` reporting at each feature (every
slice re-wires it, and un-wired calls go missing). Reporting 4xx too
(the noise the plan asked about; Atlas proxies 404 through the 6.x
ramp). A `HttpInterceptorFn` on the data-access library (the SDK is
feature code's door; the app owns chrome-level alerting — the
interceptor sits in the webapp's provider chain, where the bearer and
OTLP interceptors sit).

**Consequences.** A failed `/api` call is visible twice when the
feature also shows its own error (accepted: the drawer is the
collected record). The status-0 case cannot tell an offline browser
from a refused connection — one message covers both.

### DD-174. The bell: severity badge and ring, one outlet

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The header bell is the gear's pattern (DD-166, DD-167):
a `navbar-item` routerLink to `(drawer:alerts)`, `is-active` while
open, and the one `drawer` outlet swaps the settings panel and the
alerts drawer (ALR-01). It carries the ui-lib `Badge`: a presence dot,
visible while the store is non-empty, coloured by the highest severity
present — presence, not a count, no read-state (ALR-02). The dot is
`aria-hidden`: inside the bell's link it would join the link's
accessible name. New groups animate the bell, a ~650 ms Web Animations
pendulum swing on the icon (the effect watches `newGroups`, so a burst
rings once, ALR-02a); `prefers-reduced-motion: reduce` skips it.

**Reason.** The user asked for a badge "to indicate notifications are
available", the "color of the highest severity notification available",
and "a little animation on the bell whenever an alert becomes
available" — the ring is the arrival, the dot is the presence, the
colour is the worst. Presence beats a count: the store caps at 30 and
merges bursts, so a count badge overflows its own model. The
single-outlet swap is DD-166's mechanism with a second segment (the
URL owns which drawer is open; the locale switch's reload keeps it,
SPL-14's mechanic reused). The ring is WAAPI, not a CSS class: the
animation restarts cleanly mid-swing (a class re-trigger needs a
reflow hack); the pivot (`transform-origin: top center`) is scss on
the icon, the keyframes are the component's.

**Alternatives.** A count badge (Bulma's `.tag`, overflow-prone,
read-state invented for it). An unread-only dot (the user's word was
"available", not "unread"). A CSS `@keyframes` class toggle (the
re-trigger hack; reduced-motion media queries alone cannot skip a
JS-driven replay). `@angular/animations` (not a dependency; the zoneless
app has no animation renderer, WAAPI is the browser's).

**Consequences.** The dot's contrast on the navbar bands is the
Badge's problem (its ring, DD-175's note); the header keeps the
DD-168 slate. The dot is a component, not Bulma's `.badge` idiom (the
lib has no Bulma DOM assumptions). A future read-model (server events,
6.x) adds a source to the store, not a new door.
