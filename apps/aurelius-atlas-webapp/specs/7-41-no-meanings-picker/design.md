# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-828. The editor drops the term-assignment end at field build

- **Status:** Proposed
- **Increment:** 7.41
- **Date:** 2026-11-22

**Decision.** The editor's relationship-attribute walk drops `meanings`, the
glossary model's term-assignment end, before a picker field is built. No picker
renders, the catalogue label reaches no control, and the save body carries no
`meanings` key, so the door leaves any stored term assignment untouched
(AVW-05). The drop is one named set in `form-fields.ts`, beside the set that
already drops `qualifiedName` and `guid`. The door's `meanings` key (DD-612),
the glossary endpoints (5.2c, GTA), the shipped glossary model (18.1, DV-178),
and every read path that walks the assignments stay exactly as they are. The
bridge's `meanings` branch in `bodyFromEdits` is deleted with its only caller,
and the `ViewSaveRequest.meanings` type stays in the data-access lib because
the door still answers the key.

**Reason.** The picker writes data no Aurelius screen shows. The details table
drops `meanings` under the legacy blacklist (DET-11), no card or result row
prints assigned terms, and no Aurelius page has a glossary. A control that
writes into a blind spot invites a person to spend effort on a change they can
never confirm, which is the case DV-181 settled the opposite way for labels:
the webapp followed the Aurelius catalogue because the screen showed the thing.
Here the screen shows nothing. The stock Apache Atlas pair does have a reader,
its detail page's associated-terms card, and the vendored dashboards still
serve that card unchanged. Aurelius deliberately ported the editor and not the
glossary screens (18.1 ships the model for the wire, not the UI), so the editor
inherits a form field for a screen that was never ported. Dropping it at the
field build is the smallest change that closes the gap: it is one `Set`, and it
leaves the server, the wire, and the model untouched, so no accepted record is
superseded and no parity scenario moves. It also preserves the data path for
the day a glossary screen lands: the door key, the 5.2c bookkeeping and the
read paths are all still there, and re-enabling the picker is deleting one
name from one set.

**Alternatives.**

- Filter in the template, where `renderedRelationshipFields()` is read:
  refused, the picker field still exists, so the audit change tables and the
  save body keep a `meanings` entry to explain, and a picker that is built and
  hidden is a control someone un-hides by accident.
- Delete the catalogue key and label too: refused, the audit change tables
  name a relationship through the same label map (EDT-33), the completeness
  guard is one-way (SHL-08), and the key costs nothing while it costs nothing.
  Removing it means editing two vendored dictionaries for no behaviour change.
- Send an empty `meanings` key on every save, so the editor owns the set:
  refused, that deletes every term assignment of every entity anyone saves for
  any other reason. The door's rule is right (AVW-05): a set no picker owns is
  left alone.
- Retire the glossary model from the shipped metamodel: refused, it is a
  series-sized increment. The glossary REST endpoints and their GTA rules, the
  19.x parity scenarios, the export term list and the audit scrub all read it,
  and 18.1 shipped it on purpose (DV-178). It also supersedes accepted records,
  which needs a human decision rather than a UI tidy-up.
- Port the stock detail page's associated-terms card so the picker has a
  reader: refused for this increment. It is a details feature with its own
  parity work, and the user-visible ask was the picker, not a glossary UI.

**Consequences.** `bodyFromEdits` loses its only asymmetric key and becomes the
plain `sections` builder the spec table of 16.5c now says it is. The three
editor specs keep a guard each: the field builder answers no `meanings` field,
the body builder answers no `meanings` key even when handed a picker named
`meanings`, and the component renders no picker block and posts no key for a
type that carries the end. A type the person installs with their own
`meanings` attribute is dropped by the same name, which is the rule the details
blacklist already applies (DET-11), so the two screens agree on the name and not
on the glossary model.
