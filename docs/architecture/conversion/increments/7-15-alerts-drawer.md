# 7.15 Alerts drawer

- **Status:** in progress
- **Pull request:** [#107](https://github.com/aureliusenterprise/aurelius-atlas/pull/107)
- **Records:** DD-083 (the alerts store: windowed grouping, cap), DD-084 (the
  ErrorHandler chain: alert then trace), DD-085 (the HTTP error reporter),
  DD-086 (the bell: severity badge, ring animation), DD-087 (the ui-lib split:
  AlertList and Badge are presentational), DD-088 (the live-review fix: the
  chip's pinned pair, Clear all in the drawer head); relies on ADR 053, DD-063,
  DD-069, DD-070, DD-078, DD-079

## Scope

A drawer that collects the app's alerts for the user — the errors the app hits
while they work, and any app-level notification a future slice pushes — opened
from a bell in the header, beside the settings gear. It delivers:

- `AlertsService`: the in-memory alert store with windowed grouping (the door
  every alert walks through, ALR-03).
- `AlertsPanel`: the routed drawer (`(drawer:alerts)`) rendering the feed, with
  per-alert dismissal and clear-all (ALR-01, ALR-06, ALR-07).
- `AlertList` and `Badge` in `aurelius-atlas-ui`: the reusable feed and the
  severity dot, presentational, spec + stories (ALR-10, UIC-15's bar).
- The header bell: routerLink + `is-active` (the gear's pattern, DD-079), a
  severity badge, and a ring animation when a new alert group arrives
  (ALR-02, ALR-02a).
- Error capture: an `ErrorHandler` chain that records uncaught runtime errors
  as alerts and still delegates to the trace handler (ALR-04, SHL-14 kept),
  and an HTTP interceptor that reports failed `/api` calls (ALR-05).

It explicitly does not deliver: server-persisted alerts (the store is
in-memory; a future slice has the server's own events to deliver), notification
sources beyond runtime/HTTP errors (7.6+ feature slices push through
`AlertsService.add`), auto-dismissal (everything lives until dismissed), an
unread counter (the badge is presence, ALR-02), or served-app e2e scenarios
(the 7.10 set).

## Semantics

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ALR-01  | The bell opens the alerts drawer by navigating the `drawer` aux outlet to `(drawer:alerts)` (the DD-078 pattern), and is lit `is-active` while it is open (the gear's DD-079 pattern). The one named outlet swaps drawers: opening alerts replaces the settings panel and vice versa; dismissal navigates the outlet away. The segment rides the locale switch's full-page reload (SPL-14's mechanic, SPL-06's reload).                                                                                                                           |
| ALR-02  | The bell carries a badge — a small dot — while the store holds at least one alert, coloured by the highest severity present (`error` > `warning` > `info`, DD-063's ramp: danger, warning, info). It is presence, not a count: no read-state is tracked. The dot carries a ring in the navbar's ink so it clears 3:1 on both navbar bands (the slate, DD-080; the light band, SHM-04).                                                                                                                                                            |
| ALR-02a | When a new alert group arrives, the bell rings (a ~650 ms Web Animations swing). Merges into an existing group (ALR-03) do not ring; the badge appearing is the first arrival's ring, per group. Under `prefers-reduced-motion: reduce` the animation is skipped (the store is unchanged).                                                                                                                                                                                                                                                        |
| ALR-03  | The store is in-memory and capped (30 groups, oldest evicted). Alerts group in a quiet window: the key is severity + source + message; an alert whose key matches the newest group's and arrives within 60 s of that group's last alert merges into it (`count` +1, `lastSeen` moves); after the gap a new group starts, so the feed shows bursts as bursts. The store is a signal list, newest first.                                                                                                                                            |
| ALR-04  | An uncaught runtime error (the Angular `ErrorHandler`) becomes an `error` alert (message: the error's; source: `app`), and the trace handler still receives it — the chain records, then delegates (SHL-14 untouched, DD-084).                                                                                                                                                                                                                                                                                                                    |
| ALR-05  | A failed `/api` call becomes an `error` alert: `5xx` responses and network failures (a request that never got a response). `4xx` stays silent — client-side corrections are the calling feature's own business (DD-085). The message names the method, path, and status (or "no response"); the source is `http`.                                                                                                                                                                                                                                 |
| ALR-06  | Each row dismisses its own group (the whole burst goes); "Clear all" empties the store and rides the drawer's head, not the feed — a long feed must not bury the escape hatch, and the head does not scroll (DD-088). Shown only while the store has alerts. Dismissal is immediate; there is no undo. The badge follows the store: the last group's dismissal removes it.                                                                                                                                                                        |
| ALR-07  | Rows are Bulma notifications on the brand ramp (`is-danger`/`is-warning`/`is-info`, DD-063): severity colours the row, the message is body text, the time renders `lastSeen` through `DatePipe` under the settings' zone (SPL-07's token), and a count chip (`×N`, translated, `count > 1` only) marks a burst; the chip's pair is pinned white/dark ink — Bulma's `is-light` is a scheme trap (the brand's pinned plate under Bulma's scheme-following ink, DD-088).                                                                             |
| ALR-08  | Every chrome string is a `@@shell.alerts.*` id with entries in both fixture locales, so the completeness gate (SHL-08) and the purity gate (DD-042/DD-048) stay green. The ui-lib components take their labels as inputs with English defaults (the `Drawer.ariaLabel` pattern), so the xlf dependency stays app-side.                                                                                                                                                                                                                            |
| ALR-09  | The feed is `role="log"` with `aria-live="polite"`: alerts arriving while the drawer is open are announced. The drawer is the ui-lib `Drawer` (DD-069): backdrop, close button, Escape, focus capture and restore. Dismiss buttons are keyboard-reachable.                                                                                                                                                                                                                                                                                        |
| ALR-10  | `AlertList` and `Badge` are ui-lib components: `input()`/`output()` only, no services, no app imports, spec + stories each (UIC-15's bar). `AlertList` renders a caller-supplied `AlertGroup[]` and emits `dismiss(id)`; clearing the feed is the caller's action, projected into the `Drawer`'s `drawer-actions` head slot (DD-088) — the list is the rows, not the store's escape hatch. `Badge` wraps content and shows a severity-coloured dot on `visible`. The `AlertGroup` model is exported from the lib — it is presentation vocabulary. |

## Java origin

None. Apache Atlas 2.4.0 has no user-facing alerts surface: its notifications
are Kafka hook messages (DV-01, out of scope) and its dashboards show toasts
per feature, uncollected. The drawer is Aurelius's own interface (ADR 053).

## Deviations

| #     | Area      | Apache Atlas behaviour                                            | Aurelius Atlas behaviour                                             | Reason                                                                      | Increment |
| ----- | --------- | ----------------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------- | --------- |
| DV-13 | Interface | No alerts surface: feature toasts, Kafka hook messages to clients | An alerts drawer collects app-level alerts (runtime and HTTP errors) | The drawer is Aurelius's own interface (ADR 053), touches no Atlas endpoint | 7.15      |

## Acceptance

- Vitest (`nx test aurelius-atlas-ui -c ci`, `nx test aurelius-atlas-webapp -c ci`):
    - `badge/badge.component.spec.ts` — the dot renders on `visible`, maps the
      three severities to the ramp, hides at false; `role="status"` naming
      (ALR-02, ALR-10)
    - `alert-list/alert-list.component.spec.ts` — rows per group with severity
      classes, count chip at `count > 1` only, empty state, the `dismiss`
      output, `role="log"`/`aria-live`, no clear control in the feed (DD-088)
      (ALR-07, ALR-09, ALR-10)
    - `alerts/alerts.service.spec.ts` — add appends newest-first, the 60 s
      window merges by key (count, `lastSeen`) and a gap starts a new group,
      the 30-group cap evicts oldest, dismiss/clearAll, the badge severity is
      the highest present (ALR-02, ALR-03, ALR-06)
    - `alerts/alerts-error-handler.spec.ts` — records an error alert and
      delegates to the inner handler (ALR-04)
    - `alerts/alerts-http.interceptor.spec.ts` — 5xx and network failure report, 4xx stays
      silent, the message names method/path/status (ALR-05)
    - `alerts/alerts-panel.component.spec.ts` — renders open in the drawer
      outlet, rows from the store, dismiss removes the group, clear-all (in
      the drawer head, DD-088) empties (ALR-01, ALR-06, ALR-07)
    - `shell/header.component.spec.ts` — the bell is the `(drawer:alerts)`
      routerLink, lights `is-active` while open (ALR-01), the badge shows the
      top severity and hides on an empty store (ALR-02), the ring animation
      fires on a new group and is skipped under reduced motion (ALR-02a)
    - `routes.spec.ts` — the `alerts` route sits in the `drawer` outlet (ALR-01)
    - `i18n-completeness.spec.ts` — every new id exists in both locales (ALR-08)
- Live (dev server): force a failing `/api` call, watch the badge appear and
  the bell ring; open the drawer, see the row; repeat the call, see `×2`
  merge; clear-all, the badge goes.
- Gates: `nx lint` both projects, prod + nl-NL builds, pre-commit.
