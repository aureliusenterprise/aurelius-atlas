# 7.39 History change tables

- **Status:** in review
- **Pull request:** #444
- **Records:** DD-823 (the change list is a table, and a relationship end is a
  crumb to its own details screen) and DD-824 (an attribute that holds nothing
  claims no line). Adds HST-12, HST-13 and HST-14, amends how HST-10 shows its
  lines. Relies on HST-01..HST-11 (7.35..7.38), AUD-03/AUD-04 (the stored
  bodies), AUD-06 (the audit wire is read-only), VDR-06 and DET-26 (the crumb
  anatomy and its type icon), UIC-11 (a crumb is a link, never a dead one),
  EDT-03/EDT-33 (a field's label), EDT-09 (write gating), EWR-15 (the
  single-attribute write) and SHL-08 (every string is catalogued).

## Scope

A change list answers what an audit row changed (7.37), but it prints each
answer as one flexed line, so a name, its value, and a long list value run
together and a wide value pushes the drawer wider than it is. This increment
presents the same answers as tables: one table per section, with the action,
the thing it happened to, and the value each in its own column. A relationship
end also gains the crumb the rest of the product uses for an entity — its type
icon and its name — and pressing it opens that entity's details screen.

Nothing about the answer changes. The diff, the sections, the two "not loaded"
and "not recorded" answers, and the restore button (7.38) all keep the rules
they have. This increment only moves those answers into cells and gives a
relationship end a link.

Not delivered here:

| Deferred                                                | Lands with | Why                                                                                                                                                                                                  |
| ------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A full parent trail per relationship end                | –          | The audit body stores only the end's guid, type and display text, so a parent trail needs one read per end (DD-823)                                                                                  |
| Naming the entities inside a plain list or struct value | –          | The stored attribute value is raw JSON: reading a reference out of a value that holds none is a rule of its own, not of layout. A reference the body does hold is read as an end and named (HST-12). |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
in the Vitest title.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HST-12 | An open change list shows its attributes and its relationships as two separate tables, each under the section caption of 7.37, and a section with no changes shows no table and no caption (HST-10). Each table is the app's sortable table component (UIC-05), paged wide enough that one audit row's changes always fit on one page. The attributes table carries a header row of `Action`, `Name` and `Value` and one body row per attribute change (HST-10): the `Action` cell says `Added`, `Changed` or `Removed`; the `Name` cell names the attribute as HST-14 words it; the `Value` cell holds the added value for an added attribute, the old value for a removed one, and the old value, an arrow, and the new value in the `del` and `ins` marks of 7.37 for a changed one, with the restore button of HST-11 kept in that cell. The relationships table carries a header row of `Action`, `Relationship` and `Entity` and one body row per end (HST-10): the `Action` cell says `Added` or `Removed`; the `Relationship` cell names the relationship attribute the end belongs to; the `Entity` cell shows the end as one breadcrumb crumb (VDR-06's anatomy, DET-26's icon) of its type icon and its display text, or its guid when it carries none. An end the body stores among the attributes — the shape Atlas keeps a reference in (AUD-03) — is read as an end and appears only in the relationships table, never as JSON in the attributes table. That crumb is a link that closes the editor drawer and opens the details screen of the end entity (the save path's own navigation), except when the end is the entity being edited, which shows as plain text (UIC-11). Pressing a crumb writes nothing and asks for nothing: the audit wire stays read-only (AUD-06). A long value wraps inside its own cell and never widens the drawer. Any other attribute whose value is a list or an object prints as text; its parts are not named. Every header word and every action word is catalogued in both locales (SHL-08). |
| HST-13 | An attribute that holds nothing claims no line. An attribute the store keeps blank — no value at all, empty text, an empty list or an empty struct — is not a change, so a row neither adds it nor removes it (DD-824). This is what keeps a create short: the store writes every attribute its type defines, so an entity that sets six of its forty fields answers six added lines and not forty. Clearing a field the entity did hold stays a change and reads as one, down to the blank value it now holds.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| HST-14 | Both change tables speak the person's language. Every header word, action word and section caption of a change list is a catalogued string, so a person reading the drawer in Dutch reads Dutch headers (SHL-08). A `Name` or `Relationship` cell names its field with the same label the editor paints above that field (EDT-33) — its catalogued label, with a required star left off, since the drawer paints no field here. A field the catalogue does not name keeps its stored name, as the same form field would (EDT-03). The restore button's accessible name (HST-11) carries that same word, so what a screen reader speaks matches the row it sits on. Sorting a header announces the sort in the header's own word, because the table reads back the header it rendered (UIC-03).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

## Aurelius origin

Neither reference screen has a change list, so this slice has no parity
reference for the tables (ADR 046):

- Apache Atlas 2.4.0 `audit-table.component.js` — the stock dashboard's audit
  table lists the action, the time and the user only, and never opens a change
  list. It has no write control and no per-field detail.
- The Aurelius 17 app (`apps/atlas/src/app/search/components/editor/`), the
  history template — the drawer's history tab shows the translated action, the
  user and the time, and nothing else.

Two shipped shapes carry over instead:

- `libs/angular/aurelius-atlas-ui/src/lib/sortable-table/` (UIC-05) — the
  sortable table the browse lists and the info dialogs already use: a header
  row, one body row per item, and columns declared as templates. It is the
  app's answer to "show a list of rows with named columns" (DD-823).
- `libs/angular/aurelius-atlas-ui/src/lib/breadcrumbs/` (UIC-11, DD-624,
  DD-714) — the crumb component the details header, the shared card, and the
  relationship picker's rows already use for an entity, including a trail
  printed inside a row that owns its activation.

## Deviations

Against Apache Atlas: none. The stock dashboard shows no change list at all, so
there is nothing to diverge from.
