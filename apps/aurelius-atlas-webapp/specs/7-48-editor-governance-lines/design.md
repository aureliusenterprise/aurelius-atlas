# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-874. The governance banner is one presentational component; the routing stays in the drawer

- **Status:** Proposed
- **Increment:** 7.48
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The banner lines that sat under every control and every
relationship picker (EDT-24 as amended by 12.7, DD-446/DD-498) move into one
component, `GovernanceLines`, in the editor feature. It takes one signal input,
`verdicts` — the `GovernanceVerdict[]` that measure the control the lines sit
under — and paints one `is-size-7` line each: the warning triangle or the
success circle by the boolean `compliant`, then the verdict's message. It
injects nothing. The drawer keeps `validationItems(name)`, because deciding
which verdicts belong to a control — a verdict rides its `attribute` and every
`anyOf` alternative (VEV-09, DD-636), so one rule can name several controls —
is routing over the whole form, not a fact the lines can see on their own. The
drawer's two `NgTemplateOutlet` mounts become two component mounts fed by that
same method, and the shared `ng-template`, the `NgTemplateOutlet` import, and
the two banner icons leave the drawer. The validate round (EDT-23: the debounced
`validateDraft`, the generation guard, the quiet swallow) is untouched: it
drives the store the form reads, so it is drawer behaviour, not paint.

**Why.** The banner was the last repeated fragment of markup in the drawer
(7.47's `TypeField` and 7.46's `HistoryTab` took the other two), and it was the
only place the drawer still needed `NgTemplateOutlet`. Two identical mounts of
one template, forty-four lines in the drawer's four-hundred-line HTML, for a
rule that never changes: the extraction is the same shape 7.46 and 7.47 set —
a presentational child, signal inputs, no injection, markup moved verbatim so
every pinned class, id, and `data-` attribute stays byte-identical (the e2e
suite pins `[data-gov-line]`). Leaving the routing in the drawer rather than
pushing the whole verdict list into the child is the deliberate line: a child
that filtered verdicts itself would need the form's attribute set to know
whether a name has a control, and it would have to repeat the anyOf fan-out
twice (once per mount site); feeding it the already-routed list keeps it a pure
painter and leaves VEV-09's "one rule, every named control" in one place. The
tests move verbatim and still drive the whole drawer — the routing is what they
pin, and testing the child in isolation would either fake the routing or move
`validationItems`, both of which change what is under test without changing the
code it covers.

**Considered and rejected.** _Move `validationItems` into the component and
hand it all verdicts_ — the child would then re-implement the form-wide routing
at two mount sites and still need the field list; it turns a painter into a
second copy of the drawer's verdict logic, which is the kind of duplication the
conversion ledger warns about. _Keep the `ng-template` and pass verdicts into
its context_ — that keeps `NgTemplateOutlet`, the two icon members, and the
drawer-wide markup, and gains nothing over a named component that the AOT
compiler can check; the outlet existed only because the template needed the
field name, and the component receives the verdicts directly instead. _Extract
the validate round too (EDT-23)_ — its effects write the store the whole form
reads, and splitting it from the drawer means splitting `EditorState` ownership;
that belongs to the entity-form move of Phase 5c-part2, not to a paint-only
PR. _A `data-gov-line` host binding on the component selector_ — the line
element carries the attribute and the legacy's classes; putting it on the host
would change the DOM shape the specs walk upward through (`line.closest(
".aurelius-editor-field")`) for no benefit.

**Consequences.** `entity-editor.component.ts` drops from 1,060 to 1,054 lines
and its template from 467 to 442; `governance-lines.component.ts` (56 lines
with its doc, inline template) holds the moved markup. The drawer's stylesheet
loses nothing (the banner had never had a rule of its own — `is-size-7` and
Bulma's `icon-text` do all the styling). The spec split holds the total at
1,047 tests while going from 83 to 84 files: the four EDT-24 render tests move
verbatim, and the drawer spec keeps the EDT-23 round, which is about the request
and its swallow, not the lines. No string moves (the banner prints verdict
messages from the server and no `$localize` text of its own), so the catalogue
and both locale fixtures stay byte-equal (SHL-08's gate untouched). The drawer
loses its `NgTemplateOutlet` dependency and two icon members; `faXmark` and
`FontAwesomeModule` stay for the multi row's delete icon. No `AGENTS.md`
change: the editor feature documents its own components in their file headers.
