# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-875. The editor's field controls are one presentational component; the form state stays in the drawer

- **Status:** Proposed
- **Increment:** 7.49
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The loop that built a control for every resolved field (EDT-03) —
the text, number, boolean, enum, multi and markdown kinds with their label seat
(EDT-11), required star (FORM-REQ-001) and error line (FORM-ERR-002) — moves into
one component, `EntityFields`, in the editor feature. It takes five signal inputs
(the resolved `fields`, the drawer's `form` tree, the `values` model, and the two
functions that say whether a control shows an error and which verdicts name it)
and emits two outputs (the enum row picked, the multi row deleted). The markdown
field's three labels move with it. It injects nothing. The drawer keeps the whole
form: `form` and its `required`/`disabled` rules (DD-354), the seed effect that
writes `values`, the validation round (EDT-23), the save and its door body
(EDT-06), the version race (VDE-07) and the name-taken line (VDE-08). Because
`showError` and `validationItems` now cross a template boundary as inputs, they
become arrow properties so they keep their `this`; the typed per-kind slot
readers the loop needed and the two shared types (`EditorValue`, `EnumRow`) move
with the loop, the types to their owner `form-fields.ts`. The component's
stylesheet carries the two rules the loop owned (the gap between stacked fields
and the multi row's flex line) because an emulated-encapsulation parent cannot
style a child's inner markup.

**Why.** After 7.46's `HistoryTab`, 7.47's `TypeField` and 7.48's
`GovernanceLines`, this loop was the drawer's last piece of own repeated markup:
one hundred and sixty HTML lines, six per-kind branches, and the slot readers
that only that template called. Extracting it is the same shape the earlier
increments set — a presentational child, signal inputs, no injection, markup
moved verbatim so every pinned class, id and `data-` attribute stays
byte-identical (the e2e suite and the specs walk `#editor-*` and
`[data-field]`). The hard line is where the reactive state sits. A loop that
reads `this.form()[name]()` cannot leave the tree that owns `form` without the
tree itself crossing as an input — so the form tree and the model cross as
objects, and everything that _writes_ them (seed, conflict, save, validation,
multi add) stays in the drawer. Moving the state too would mean moving
`EditorState` ownership, which is Phase 5c-part2, not a paint-only move. Keeping
`errorFor`/`verdictsFor` as functions rather than recomputing them in the child
is deliberate: both read drawer state (touch flags plus `saveAttempted`, and the
verdict routing `validationItems` already owns), and the child has no business
re-deriving either. The tests move verbatim and still drive the whole drawer —
driving the child alone would fake the field builder, the seed, and the save,
changing what is under test without covering new code.

**Considered and rejected.** _Move the whole form out_ — the plan's literal
"entity-form component". Infeasible here: the seed effect, the validation round,
the save, and the conflict path all write the store and the router, so pulling
them out moves `EditorState` ownership and the drawer's whole reactive core in a
single PR that would dwarf the 1,500-line budget and mix a behaviour-identical
split with a state relocation. _Rebuild a fresh signal form inside the child_ —
two forms over one model would fight; the drawer's rules (required-without-
boolean, the unique lock) would have to be duplicated, and a validation touched
one and saved the other. _Pass the slot readers as inputs_ — six function inputs
that are one line each (`this.form()[name] as ...`) is more ceremony than the
child typing them itself. _A directive on the loop_ — a structural directive
cannot own the per-kind SCSS or host the markdown labels; a component is the
smaller concept. _Leave the SCSS in the drawer_ — emulated encapsulation stops a
parent rule reaching a child's inner nodes, so the stacked-field gap and the
multi row line would silently stop applying; they ride the child, which is the
same fix 7.46 and the ui-lib fields made.

**Consequences.** `entity-editor.component.ts` drops from 1,054 to 1,002 lines
and its template from 442 to 308; `entity-fields.component.ts` (261 lines with
its doc and inline template) and its small stylesheet hold the moved markup.
`form-fields.ts` gains the two type aliases their doc already described. The
spec split goes from 84 to 85 files and from 1,047 to 1,051 tests. The six
render tests move verbatim, and the drawer spec keeps the save, conflict,
notification and validation tests. Four tests join them, because SonarCloud
reads the moved markup as new code and its new-code gate wants it covered: the
shared fixtures carry only the text and markdown kinds, so the enum, boolean,
number, date and multi branches sat uncovered until a DataSet chain
(`ALL_KINDS_*` in `editor-testing.ts`) rendered them. No string id changes (the
markdown labels carry their `components.markdownEditor.*` ids unchanged), so the
catalogue and both locale fixtures stay byte-equal (SHL-08's gate untouched). The drawer loses
`MarkdownEditor`, `Select`, `FormField` and `FontAwesomeModule` from its imports
— `FontAwesomeModule` and `faXmark` now belong to the child, which needs them for
the multi delete. No `AGENTS.md` change: the editor feature documents its own
components in their file headers.
