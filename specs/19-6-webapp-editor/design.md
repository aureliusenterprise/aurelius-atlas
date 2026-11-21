# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-802. The editor states its own delete outcome

- **Status:** Proposed
- **Increment:** 19.6
- **Date:** 2026-11-21
- **Relates to:** WFE-01, WFE-02.

**Decision.** The code that performs a delete sets the outcome on a signal the editor reads. The effect that
today
scans `this.alerts.alerts()` for `this.deletingLine` with a `lastSeen >= started` clock test goes away.

**Reason.** The current test (`entity-editor.component.ts:621-638`) asks "is there an alert whose text equals
my
own deleting line and was last seen after I started?" A reworded or localized delete line makes that
comparison
false, so a successful delete reads as a refusal. The unit tests keep passing because they assert the current
text, so the bug only shows for a real reader in another language. A code path that performed the action knows
the
outcome, so it should say it.

**Alternatives.**

- **Match the alert by an id instead of its text.** Better than text, and still an inference: the editor
  watches a log for evidence of its own action instead of being told. The alerts store groups by text, so even
  an id leaks alert formatting into the editor's logic.

### DD-803. The delete signal follows the save signal

- **Status:** Proposed
- **Increment:** 19.6
- **Date:** 2026-11-21
- **Relates to:** WFE-02.

**Decision.** The delete outcome reuses the shape of the `EntitySaved` tick, a signal that fires an outcome
for one
guid. The delete path fires the same kind of signal.

**Reason.** The save path already solved the same problem (the drawer leaves before the answer renders) with
the
`EntitySaved` tick, and that tick is the named exception to the no-shared-store rule DD-322 set, because it
shares
an event and not entity data. Reusing that shape means one pattern for "my write finished", not two.

**Alternatives.**

- **A second signal type for deletes.** Two near-identical signals invite them to drift, when one event type
  with an outcome field covers both.

### DD-804. The classification combobox becomes its own component

- **Status:** Proposed
- **Increment:** 19.6
- **Date:** 2026-11-21
- **Relates to:** WFE-03.

**Decision.** The classification combobox leaves `entity-editor.component.ts` as its own component, with its
members, its five handlers, and its own spec file.

**Reason.** The combobox is about twenty members and five handlers with no coupling to the rest of the editor
class, so it makes the component large while sharing nothing with it. As its own component it has a focused
spec
and the editor's spec stops carrying combobox cases.

**Alternatives.**

- **Keep it in the component.** The editor component keeps growing, and the combobox cannot be tested without
  the whole editor fixture.

### DD-805. One guard keeps client form rules against their Python originals

- **Status:** Proposed
- **Increment:** 19.6
- **Date:** 2026-11-21
- **Relates to:** WFE-05.

**Decision.** A guard test reads a fixture that lists the form-rule vocabulary the server enforces, and fails
when
a client rule in `form-fields.ts` no longer matches it. The fixture is produced by the server's own tests, not
hand-written on the client.

**Reason.** `form-fields.ts` re-implements rules the server owns: the required and disabled form of a field,
the
cardinality of a picker, and the parent-child shape. When 18.3 changed a server rule, the client copy lagged.
The
repository already has this pattern for labels (`attribute-labels.spec.ts` fails when a label drifts from the
catalogue), so a fixture-backed guard is house style, not a new kind of test.

**Alternatives.**

- **Derive every client rule from the server response and copy none.** Some rules need a value the form has
  and the field definition does not, so a copy stays, and a guard is the cheaper honest fix than a server
  round-trip per keystroke.
- **Trust the e2e to catch drift.** An e2e catches a rule that is visibly wrong, not one that is silently
  different from the server on an edge case.

### DD-806. PME-10 moves to form-fields with a direct test

- **Status:** Proposed
- **Increment:** 19.6
- **Date:** 2026-11-21
- **Relates to:** WFE-04.

**Decision.** The PME-10 parent-choice blocking logic moves from the component to `form-fields.ts`, beside
PME-01
and PME-03, and gains a unit test that calls it directly instead of driving the DOM.

**Reason.** The rule decides which picker is disabled, which is a pure rule over the field definitions, and
PME-01
and PME-03 already live in `form-fields.ts`. Deciding it in the component forces its test to build a DOM, so
the
rule's edge cases are under-tested.

**Alternatives.**

- **Leave it and add more DOM cases.** More DOM cases are slower and still cannot reach the rule's edges
  without a large fixture.

### DD-807. The editor stops reaching into the details feature

- **Status:** Proposed
- **Increment:** 19.6
- **Date:** 2026-11-21
- **Relates to:** WFE-06.

**Decision.** The `cardTypeAlias` helper the editor imports from `details/shared/card` moves to a place both
the
editor and the details feature import from.

**Reason.** The editor imports a helper owned by the details feature, so a details refactor breaks the editor
for a
type alias both could share. The webapp's own purity guard (the signals-only rule `check-webapp-purity.sh`
enforces)
already says feature code should not reach across features for plumbing, and a shared alias is the same kind
of
reach.

**Alternatives.**

- **Duplicate the alias in the editor.** Cheaper and the reason the cross-import happened. It lets the two
  copies disagree on how a type displays, which is the drift the move removes.

### DD-808. No change to a server answer

- **Status:** Proposed
- **Increment:** 19.6
- **Date:** 2026-11-21
- **Relates to:** WFE-01, WFE-04, WFE-05.

**Decision.** This increment ships no change to what the editor sends to the server or what the server
answers.
The e2e for the editor delete and save flow is the proof, run at level 2.

**Reason.** Every rule here changes how the editor knows an outcome or where a rule lives, not the request it
makes. Holding the request fixed keeps the increment out of the parity surface, so it can move at front-end
capacity without waiting on the Python increments.

**Alternatives.**

- **Fix a server rule at the same time.** A front-end refactor that also changes a server answer needs the
  parity gate, which couples this increment to the Python queue for no benefit.
