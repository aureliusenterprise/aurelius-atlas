# 7.45 The search stores hold their failures, the screens alert

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-871 (here). No new rule ids. Cites SDX-01 (7.4b, DD-214: the
  failed page that holds its failure), SBW-06 (11.5: the meaning-unavailable
  warning), DET-08/DET-13 (7.20: the read whose error path moved, and the failed
  read), DET-18 (7.21a: the failed chunk), ALR-05 (7.15: the 4xx stays silent),
  EDT-02/EDT-08 (7.7a: the failed editor read and the one save-failure alert),
  VDE-01/VDE-02/VDE-08/VDE-09 (16.5c: the editor read, the slices, the taken
  name, the save failure), HST-11 (7.38: the restore refusal and its re-read
  failure), and ALR-03 (7.15: the grouping the byte-identical messages feed).

## Scope

The four search stores — `SearchState`, `DetailsState`, `RelatedSectionsState`,
and `EditorState` — inject `AlertsService` and call it inline in their error
paths. That makes a state store depend on the alerts chrome, and it makes every
store unit test spin up `AlertsService` just to prove a failure surfaced. This
increment moves that one dependency out of all four stores and into a shared
relay, with no change to what a user sees.

The change (no behaviour, template, or string change):

- A new `search/shared/alert-on-failure.ts` holds `alertOnFailure(store)`. It
  injects `AlertsService`, watches the store's `failures()` signal in an effect,
  pushes each held notice into the drawer with `source: "search"`, then calls the
  store's `handled()` to drain the list. The store interface it needs is two
  members: a `failures` signal of `{ severity, message }` and a `handled()`.
- Each store gains those two members and, in every error path it used to alert
  on, pushes the notice onto the queue instead of calling `AlertsService.add`.
  The message and severity strings are byte-identical to before; only `source`
  moves (it becomes the relay's default, `"search"` — the same value every store
  passed). `DetailsState` keeps its ALR-05 rule: the error path pushes only when
  the failure is not a 404.
- Each store is wired at the one place it is a sole provider: `SearchLayout`
  relays `SearchState`; `Details` relays `DetailsState` and `RelatedSectionsState`;
  `EntityEditor` relays `EditorState`. Because the relay runs once per store
  owner, a failure alerts exactly once.
- `EntityEditor` keeps its own `this.alerts.add` for the audit read error — that
  alert never came from a store, so it stays a component side effect.

The store unit specs now assert the held failure (`store.failures()` deep-equals
the expected `{ severity, message }`) instead of the alert it becomes; the
component specs keep asserting the drawer. `details.component.spec.ts` already
pinned all three of the details screen's alert outcomes (a failed read alerts,
a 404 stays silent, a failed chunk alerts once) and passes untouched, which also
proves the effect's timing — an alert lands by the time the screen re-renders
after the HTTP flush.

It does **not** deliver: any change to a message string, severity, or grouping
(`ALR-03` collapses repeats exactly as before, because the strings are
unchanged); a move of the editor's audit-read alert (component-owned); a general
"side effects out of stores" pass beyond the alerts dependency (the stores still
own their fetch state and their HTTP services); or a change to the alerts store,
drawer, or badge (7.15 is untouched).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The alerts are byte-identical.** Every message, severity, and the `"search"`
  source match what the stores passed directly. Proven at both layers: the store
  specs assert the held notice, the component specs (unchanged) assert the drawer
  — 1,046 tests green with only the one new test added (below).
- **Each failure alerts once, per store owner.** The relay lives at the store's
  provider scope and drains with `handled()`, so a failure never doubles and
  never re-alerts on a later change-detection pass.
- **The failed chunk still alerts once per chunk.** `RelatedSectionsState` pushes
  one notice per failed section chunk (DET-18); the queue keeps them separate so
  two same-tick chunk failures each alert — a single-slot signal would have
  coalesced them. Verified by the existing DET-18 chunk test.
- **A 404 stays out of the drawer.** `DetailsState`'s 404 answers the DET-02
  empty state with no failure (ALR-05's 4xx rule), unchanged; the DET-13/ALR-05
  test at `details.component.spec.ts` still asserts "no alert".
- **One accepted edge.** A failure recorded after its owning component is
  destroyed (an in-flight error that lands after navigating away) no longer
  alerts, because the relay's effect is gone with its scope. Accepted — see
  DD-871; it replaces an alert the user could not see anyway.
- **The trace tool sees no change.** Webapp TS specs name rule ids in test names,
  not `covers()` marks, and the moved text is inside test bodies — `uv run
aurelius-atlas-trace check` reports the same single pre-existing finding
  (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `AlertsService` or signal stores — the alerts
drawer and this relay are Aurelius code ported or written in earlier increments
(7.15, 7.4a, 7.7a). Moving a dependency between Aurelius files adds nothing a
parity test can see, so this increment adds no row to
[Java map](../../../../docs/architecture/conversion/java-map.md).

## Deviations

None from Apache Atlas. Re-routing an alert through a relay changes no value a
parity test can observe, so the increment adds no row to
[Deviations](../../../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                         | Command                                                                                                       | Level |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----- |
| The suite passes with one more test than 7.44 | `nx test aurelius-atlas-webapp -c ci`                                                                         | 1     |
| No store injects `AlertsService`              | `grep -rn "inject(AlertsService)" src/app/search --include="*.ts" -l` lists only `entity-editor.component.ts` | 0     |
| Every alert source is byte-identical          | the store specs' `failures()` match + the component specs' drawer asserts                                     | 1     |
| The bundle still type-checks and builds       | `nx build aurelius-atlas-webapp`                                                                              | 1     |
| Lint clean (0 errors)                         | `nx lint aurelius-atlas-webapp`                                                                               | 0     |
| The purity gate stays green                   | `nx test aurelius-atlas-webapp -c ci` (purity `dependsOn`)                                                    | 1     |
| Every rule id still names a test              | `uv run aurelius-atlas-trace check`                                                                           | 0     |

Before 7.45: 1,045 tests in 81 files. After: **1,046 tests in 81 files** — the
one added test is `search-layout.component.spec.ts`'s "a failing search reaches
the drawer through the store's relay", the component-level proof of the
`SearchState` relay (the `Details` and `Editor` relays were already covered by
existing component tests).
