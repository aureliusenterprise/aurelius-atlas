# 7.46 The History tab leaves the editor drawer

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-872 (here). No new rule ids. Cites HST-01..HST-16 (7.35..7.40:
  the tab pair, the trail read and its pages, the change lists, the description
  diff, the restore), AUD-04/AUD-06/AUD-07/AUD-08 (7.35: what the audit read
  returns and what it never writes), LR-002/LR-005 (7.1: the named region and the
  outcome line), WFE-01/WFE-02 (7.7a: the write and its outcome line), UIC-11/
  UIC-21/UIC-26 (7.39: the crumb that never links back, the change table, the
  relationship line), DD-816/DD-817/DD-820..DD-825 (the History decisions this
  keeps), and DD-871 (7.45: the failure seam the moved read now rides).

## Scope

The entity editor drawer owns two panes (HST-01): the entity form and the audit
trail. Both live in `entity-editor.component.ts`, which had grown to 1,403 lines
of code and a 742-line template, 250 lines of it the History pane. This increment
moves the History pane into its own feature folder, with no change to what a user
sees, clicks, or reads.

The change (no behaviour, template text, or string change):

- A new `search/editor/history/` folder holds the pane. `history-tab.component.ts`
  with its `.html` and `.scss` render the trail, and the audit helpers
  `audit-details.ts`, `audit-display.ts`, and `description-diff.ts` moved in with
  their specs by `git mv`.
- A new `history/audit-state.ts` holds `AuditTrail`, an `@Injectable` store with
  the audit state the drawer used to hold: the listed events, the loading and
  end-of-trail flags, the open change list, the cursor read (HST-08), and the
  change computation (HST-10). It is provided on `EntityEditor` only, so its life
  is the drawer's life.
- `EntityEditor` keeps what belongs to the drawer, not to the pane: the tab pair
  and its keyboard switch (HST-02), the pane wrapper and its region ids, the trail
  loading line (LR-002), the restore write and its outcome line (WFE-02, HST-11),
  and the relationship crumb's navigation (HST-12, UIC-11).
- The audit read's failure now rides the DD-871 seam instead of calling
  `AlertsService` inline. The store pushes onto `failures()`, and the drawer's
  existing `alertOnFailure(this.trail)` relays it. The message string and severity
  are byte-identical, so `AlertsService` groups them exactly as before (ALR-03).
- The spec splits the same way. `history/history-tab.component.spec.ts` holds the
  52 History tests with their names unchanged, and a new `editor-testing.ts` holds
  the fixtures and settle helpers both specs share.

It does **not** deliver: any change to a string, a css class, an id, or a role (the
e2e specs pin the ids and the parity tests pin the strings); the type picker or the
entity form moving out (Phases 5b and 5c of the webapp refactor plan); a `Storybook`
story (the webapp has none, by the ui-lib-only convention); or a change to
`java-map.md` and `deviations.md` (nothing here touches Atlas behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The pane renders from the store alone.** `HistoryTab` takes `AuditTrail` as a
  required input and touches no HTTP service and no router. Every string it prints
  sits in the same `$localize` block it sat in before.
- **The trail re-reads on every switch to History** (HST-03 as amended by 7.36).
  `showTab("history")` calls `trail.open(guid)` each time, which is what the
  drawer did before the move.
- **A page shorter than `AUDIT_PAGE` ends the trail** (HST-08, AUD-08). The store
  reads `count=100` explicitly and stops the sentinel when a page comes back short.
- **The restore still writes one attribute** (HST-11, EWR-15). The pane emits the
  chosen line, and the drawer's `restoreAttribute` calls `state.restore`, so the
  write and its outcome line stay owned by the screen.
- **The crumb of the edited entity stays plain text** (HST-12, UIC-11). The drawer
  passes `auditEndActiveGuid()` into the pane, which prints that one crumb without a
  link.
- **1,046 tests stay green** across 82 files: the same 118 editor tests, now 66 in
  the drawer spec and 52 in the pane spec, plus every other suite untouched.
- **The trace tool sees no change.** The test names that carry HST ids are moved
  verbatim, so `uv run aurelius-atlas-trace check` reports the same single
  pre-existing finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `HistoryTab` or `AuditTrail`. The audit read it
maps to (`EntityAuditManagerV2` behind `GET /api/atlas/v2/entity/guid/audit`) is
already ported and specced at the data-access layer (AUD-04, AUD-08). Moving
Aurelius code between Aurelius files adds nothing a parity test can see, so this
increment adds no row to `java-map.md`.
