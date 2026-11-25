# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-872. The History pane owns a store of its own, provided by the drawer

- **Status:** Proposed
- **Increment:** 7.46
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The History pane becomes two files in the editor feature:
`history/audit-state.ts` (the `AuditTrail` store: the listed events, the loading
and end-of-trail flags, the open change list, the cursor read, the change
computation) and `history-tab.component.ts` (the render). `AuditTrail` is an
`@Injectable` listed in `EntityEditor`'s `providers` and nowhere else, so one
instance lives exactly as long as one drawer. `HistoryTab` receives it as a
required signal input, plus `activeGuid` and `restoreShown` inputs, and emits a
restore line or a pressed crumb. It injects `EditorState` for the restore
button's two states and nothing else — no HTTP service, no router, no
`AlertsService`. The drawer keeps the tab pair, the pane wrapper with its region
ids, the trail loading line, the restore write and its outcome line, and the
crumb's navigation. The audit read's failure rides the DD-871 seam: the store
pushes `{ severity: "error", message: AUDIT_RETRIEVE_LINE }` onto `failures()`
and the drawer's existing `alertOnFailure(this.trail)` relays it.

**Why.** The drawer held 1,403 lines because the pane's whole read sat inside it.
A store separates the read from the render, which is the pattern the search
screens already use (DD-871 built the failure seam for exactly this split), and
it lets the pane's spec assert the trail through the store instead of through
private members of the drawer. Providing it on the drawer rather than at the app
root is what makes the trail entity-correct for free: the drawer is routed by
guid, so a new drawer gets a new store and an old trail can never show under a
different entity, which is what HST-03's re-read guarded against in the merged
component. The store is a component-scope provider, so `guid` is passed to
`open()` per call rather than injected from the route — the store stays unaware
of routing and can be specced with a plain guid. `HistoryTab` stays presentational so the
template text stays reviewable in one file, and its strings stay byte-identical
because `AlertsService` groups on the exact message (ALR-03) and the e2e specs
pin the ids and roles the pane wrapper keeps in the drawer.

**Considered and rejected.** _Keep the state in the drawer and pass ~12 signals
into a dumb child_ — the pane would still need `toggleChanges`, `changeOf`, and
`loadMore`, which are behaviour, so the child ends up owning the state anyway
with a wider prop surface to prove it. _Put the audit state on `EditorState`_ —
that store models the entity being written (WFE-01/WFE-02), and the audit trail
is read-only history of a different read (AUD-06); merging them would give every
editor spec an audit payload and let an audit failure look like a write failure.
_Provide `AuditTrail` at the app root_ — then two drawers, or a drawer reopened
on another guid, would share one trail and re-introduce the cross-entity leak the
re-read exists to prevent. _Emit the restore all the way out and let the pane
call `EditorState`_ — the write belongs to the screen that shows its outcome line
(WFE-02), so the drawer must own it.

**Consequences.** `entity-editor.component.ts` drops from 1,403 to 1,084 lines and
its template from 742 to 493 lines, the moved History block being about 250 of
them; the pane's SCSS moves with it, so the drawer's stylesheet loses 91 audit rules. The `search/editor/`
folder gains a `history/` level, which the DD-870 purity gate allows (a feature
reaching into its own subfolder stays inside the feature) and needs no new rule.
`editor-testing.ts` is a new test-only module, so the spec split holds the total
at 1,046 tests while adding one file. The pane carries no `$localize` text of its
own making — every string moved verbatim, so `extract` output is unchanged.
`AGENTS.md` needs no change: the drawer's own doc header now names the pane's
owner, and the webapp's removal map already covers the editor feature as one
unit. Accepted edge: `AuditTrail` is not reusable outside this drawer as it
stands, because `restoreShown` and the restore emit are wired to the editor's
write gate — a second consumer would need those two inputs generalised.
