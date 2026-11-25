# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-871. A search store holds its failure; the owning screen relays it to the alerts drawer

- **Status:** Proposed
- **Increment:** 7.45
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** A search store never injects `AlertsService`. Instead each store
implements a two-member seam — a `failures` signal of `{ severity, message }`
(oldest first) and a `handled()` that drains it — and pushes its error-path
notices onto that queue. A single shared helper, `search/shared/alert-on-failure.ts`,
exposes `alertOnFailure(store, source = "search")`: it injects `AlertsService`,
watches `store.failures()` in an `effect`, adds each notice as an alert, then
calls `store.handled()`. It is called once from the component that lists the
store in its `providers` — `SearchLayout` relays `SearchState`; `Details` relays
`DetailsState` and `RelatedSectionsState`; `EntityEditor` relays `EditorState`.
The message and severity strings stay byte-identical to the calls they replace;
`source` becomes the relay's default. `EntityEditor` keeps its own
`AlertsService.add` for the audit read, which is a component side effect, not a
store failure.

**Why.** The stores describe state — what a screen would show — but four of them
wrote to the alerts chrome inline, so a state service carried a UI dependency and
fired alerts behind whatever screen was (or was no longer) on screen. It also
forced every store unit test to stand up `AlertsService` merely to prove a failure
surfaced. Holding the failure and relaying it at the provider scope keeps the
dependency where the alert belongs (the screen showing it) and lets a store spec
assert `store.failures()` with no chrome in sight. The queue is a list, not one
slot, because one action can fail more than once before the screen reacts: a
section's resolve fires several card chunks and each failed chunk alerts (DET-18),
and a list preserves each — a single-slot signal would coalesce same-tick
failures into one alert. Wiring at the provider scope (not the store's own
constructor, not the app root) means exactly one relay per store instance, so a
failure surfaces once; draining with `handled()` keeps it from re-firing on the
next change-detection pass. Byte-identical strings are a hard requirement because
`AlertsService` groups repeats on the exact severity+source+message triple inside
its 60 s window (ALR-03) — a reworded message would stop the collapses the
pre-refactor code relied on.

**Considered and rejected.** _Single-slot `failure` signal_ — coalesces two
failures recorded in the same tick, which would drop a DET-18 chunk alert; _the
store keeps a thin `addAlert` behind an injected seam_ — still leaves the store
aware of the alerts store and firing behind the screen, the coupling this removes;
_one relay at the app root_ — the stores are route/component-scoped sole providers,
so there is no single place holding all four, and a root relay would fire for
screens that never showed the failure; _move the editor's audit-read alert into
the store too_ — that alert was never a store failure (the component reads the
audit feed itself), so moving it would invent a store state it has no reason to
own.

**Consequences.** The four stores depend on `alerts/` no longer — `grep` over
`src/app/search` finds `inject(AlertsService)` only in `entity-editor.component.ts`
(the kept audit alert) and in the shared helper itself. Store specs assert
`failures()` instead of the drawer; component specs keep asserting the drawer, so
what a user sees stays tested at the screen. Accepted edge: a failure recorded
after its owning component is destroyed (an in-flight error landing after
navigation) no longer alerts, because the relay's effect dies with its injector
scope — it replaces an alert the user had already navigated away from. The relay
is pure `search/` plumbing (feature → `shared/`), so the DD-870 purity gate stays
green and needs no new rule id. `AGENTS.md` needs no change — the alerts seam is
an internal pattern, and the store-is-state rule it enacts was already the intent
the stores' own doc headers state.
