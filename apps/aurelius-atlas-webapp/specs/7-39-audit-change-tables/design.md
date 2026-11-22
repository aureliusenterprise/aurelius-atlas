# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-823. The change list is a table, and a relationship end is a crumb to its own details screen

- **Status:** Proposed
- **Increment:** 7.39
- **Date:** 2026-11-22

**Decision.** The change list of an audit row keeps the answers of 7.37 and
puts them in two tables instead of two lists. The attributes table has a
header row of `Action`, `Name`, `Value` and one body row per attribute change;
the `Value` cell keeps the `del` and `ins` marks of 7.37 for a changed
attribute and holds the restore button of 7.38 in the same cell. The
relationships table has a header row of `Action`, `Relationship`, `Entity` and
one body row per end. Both are the app's sortable table component (UIC-05),
the one the browse lists and the info dialogs already use: it brings its own
header row, striping, column sort buttons and screen-reader live region, so
the drawer styles nothing but its size. Its page size is set past any change
list's length, because one audit row's changes must all be on screen — a fold
inside an opened accordion is not a page. A relationship end shows through the
ui library's `Breadcrumbs` component as one crumb — the type icon and the
display text — with `activeGuid` set to the entity being edited, so the end
that is that entity prints as plain text and every other end is a link. The
click carries the editor's own navigation: the primary outlet goes to
`search/details/<guid>` and the drawer outlet closes, the way a save leaves the
screen. The audit body carries each end's `typeName`, and `audit-details.ts`
passes it through to the change line so the crumb can take its icon from the
app's type map (DET-26). An attribute whose value on either side is an
`AtlasObjectId` — one, or a non-empty list of them — is treated as a
relationship rather than a value, and its lines go to the relationships table:
Atlas keeps a reference that way in `attributes` (AUD-03), and the audit
listener builds its body from an entity read without relationships, so
`systems`, `datasets` and `db` arrive there in practice. A long value wraps
inside its cell with `overflow-wrap` and never widens the drawer. The one
header word a table borrows is `Value`, the existing dictionary key of the
Properties table; `Name` is a history word of its own, because the editor's
label for the `name` attribute bakes a required star into it (`Name*`) and a
table header has no field to mark (DD-356). Five words (`Action`, `Changed`,
`Entity`, `Name`, `Relationship`) join the history section of the dictionary.
A `Name` or `Relationship` cell does not print the stored name: it sends it
through `fieldLabel`, the lookup the form fields already use for their own
labels (EDT-33), so the row for `qualifiedName` reads _Qualified Name_ in
English and _Gekwalificeerde Naam_ in Dutch, and three attributes the history
needed (`qualifiedName`, `replicatedFrom`, `replicatedTo`) gain catalogue
entries. A name the catalogue does not hold stays raw, which is what the form
field for it shows (EDT-03).

**Reason.** A list of flexed lines cannot hold a diff, because the reader has
to find each part of a change again on every line. A table puts the action in
one column and the value in its own cell, so the eye scans the actions down a
straight edge and a wide value costs its own cell instead of the drawer's
width. The app ships both pieces already — the sortable table for row lists,
and the crumb for an entity mention — so the increment adds no new vocabulary
and reads like the rest of the product. Linking an end is what
every other mention of an entity does (the details header, a shared card, a
picker row), and the audit body already names the end's guid, so the link
costs no request. Showing the edited entity itself as text rather than a link
is the crumb component's own rule for the entity being viewed (UIC-11): a
link that reloads the screen behind the drawer is a dead link. Wrapping beats
clamping because the reader came to the change list to read values, and the
drawer's pane can spare the height that a truncated value would steal back
through a tooltip.

**Alternatives.** Reusing the Properties table's `Key` word for the name
column: refused on review, because the column lists attributes and _Key_ is a
database word — the drawer's own field labels call the same thing a name.
The editor's `name` attribute label for the header: refused, it reads
`Name*`/`Naam*` and the star belongs to a required field, not a column.
A hand-rolled Bulma `table is-fullwidth`, as the Properties table renders it
(DET-11): refused on review, because the app already ships
the sortable table and every other row list in the product uses it — a second
table style in the same drawer would own borders, striping, a sort affordance
and a live region that the component gets right already. A full parent trail
per end (Dataset → Collection → Process), like the details header shows:
refused, the audit body stores only the end's guid, type and display text, so
each listed end would need one entity read. A change list must ask for nothing (HST-10, AUD-06), and an open
row with six ends would spend six round trips on a read-only screen. A value
clamped to one line with an ellipsis and a tooltip: refused, a diff reader
needs the value, and a tooltip is the worst place to read a long description.
A plain-text end with no link: refused, the change list would be the only
place in the product where naming an entity gives no way to reach it. A
change-list component in the ui library: refused, two tables of three columns
need no new component, and the library would have to own the diff's action
words, which are the editor's business. Better CSS on the existing lists:
refused, no amount of flexbox gives columns, and the wide-value overflow
returns with the next long value.

### DD-824. An attribute that holds nothing claims no change line

- **Status:** Proposed
- **Increment:** 7.39
- **Date:** 2026-11-22

**Decision.** When an attribute appears on one state and not the other, the
change list asks what the side that gained it actually holds: no value, empty
text, an empty list or an empty struct is nothing, and nothing earns no line.
A blank attribute that both states hold stays a change, because the write did
take a value away.

**Reason.** The store writes every attribute the type defines onto every entity,
so a create arrives with forty keys of which the person filled six (AUD-03,
DD-302 keeps the business attributes in the same map). Listing the blanks made
the change list report an entity's own type definition as its creation, and the
table grew past the drawer's height with `Added Collections []` rows the reader
has to scroll past to find what was set (HST-13). A field the entity never held
and still does not hold is not something the write did.

**Alternatives.** Dropping only empty lists: refused, because `Definition`
arrives as `""` just as often and shows the same nothing in an empty cell.
Reading the type definition and listing only its required attributes: refused,
it would ask for the typedef the audit body does not carry (AUD-06 forbids the
read) and would hide a genuinely set optional attribute. Showing blanks as a
greyed row instead of a line: refused, the reader's question is "what changed",
and a row that answers "nothing" spends a line to say so. Collapsing the blanks
behind an "unchanged fields" toggle: refused, that is a second disclosure
inside an already-open accordion, for content no one reads.
