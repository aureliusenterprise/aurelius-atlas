# 7.41 Entity editor: no term-assignment picker

- **Status:** in review
- **Pull request:** #452
- **Records:** DD-828 (here). Adds EDT-36; amends EDT-13 (7.7c) and VDE-04
  (16.5c) in place, and enters DV-193. Relies on EDT-13..EDT-17 (7.7c, the
  pickers this narrows), AVW-05 (16.3, a set the body leaves out is left
  unchanged), VDR-02 (16.5b, the ends a view answers), DET-11 (7.20, the
  details blacklist that already drops `meanings`), DV-178 (18.1, the glossary
  model ships on purpose), and DD-612 (16.5c, the door's own `meanings` key).

## Scope

The editor builds one relationship picker for every relationship attribute of
the edited type and its supertypes (EDT-13). One of those attributes is
`meanings`. The glossary model of Apache Atlas declares it on `Referenceable`,
so the type system builds it onto every shipped entity type, and it holds the
glossary terms assigned to that entity.

That picker is the only term-assignment control in the Aurelius webapp, and no
Aurelius screen shows the terms it assigns. The details table drops `meanings`
under the legacy blacklist (DET-11), and no card, result row, or section prints
it. A person can write term assignments through a control that never answers
what was written, and no other Aurelius screen reads them back.

This increment hides the picker. The editor stops building a field for
`meanings`, so no picker renders, and a save body carries no `meanings` key.
The door then leaves the stored term assignments exactly as they are (AVW-05).
Everything else about the glossary model stays as shipped: the model itself
(18.1, DV-178), the glossary REST endpoints and their rules, the door's
`meanings` key for the glossary callers, and the read paths that walk the
assignments (the export term list, the audit scrub, and the stock dashboards'
term cards).

Explicitly not delivered here:

| Deferred                                               | Lands with                                       | Why                                                                                                                                                                                                             |
| ------------------------------------------------------ | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A term-assignment control anywhere in the webapp       | only with a screen that shows the assigned terms | A write control needs a read path. The picker's result is invisible from every Aurelius screen today, so it stays out until a screen prints the terms it writes.                                                |
| Retiring the glossary model from the shipped metamodel | not planned                                      | 18.1 ships it on purpose (DV-178). The glossary endpoints, their term-assignment rules, the parity scenarios and the export path all read it. Retiring it is its own increment and supersedes accepted records. |
| Hiding `meanings` on the details screen                | already shipped (DET-11, 7.20)                   | The details properties table drops it under the legacy blacklist today.                                                                                                                                         |
| Hiding it in the stock dashboards                      | never                                            | `apps/aurelius-atlas-dashboard` is vendored unchanged (DD-017).                                                                                                                                                 |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDT-36 | The editor builds no field for the glossary model's term-assignment attribute, `meanings`. The relationship-attribute walk of EDT-13 drops the name, so no picker renders for it, its catalogue label reaches no control, and a save body carries no `meanings` key. The drop holds for a definition that names the attribute itself and for one that inherits it, which is every shipped entity type. An entity that already holds term assignments keeps them: the save leaves the set out, and the door leaves a set it does not name unchanged (AVW-05). No other relationship attribute is dropped, and no other rule of EDT-13..EDT-17 changes. The read side is untouched: the view door still answers the stored ends, and the details screen and the stock dashboards show the terms as DET-11 and the vendored dashboards leave them. |

## Aurelius origin

Neither reference screen pairs a term write with an Aurelius term read:

- The two vendored dashboards (`apps/aurelius-atlas-dashboard`) build an editor
  field for every `relationshipAttributeDef` of the type
  (`dashboardv2/public/js/views/entity/CreateEntityLayoutView.js`, and the same
  file under `dashboardv3`), so the stock create and edit forms list a
  `meanings` control. The stock detail page prints the assigned terms from
  `relationshipAttributes.meanings`
  (`dashboardv2/public/js/views/detail_page/DetailPageLayoutView.js`), and the
  stock glossary page writes them through its own assign-term view
  (`AssignTermLayoutView.js`). The stock pair has a writer and a reader.
- The Aurelius webapp has the writer and no reader. The details screen drops
  `meanings` under DET-11, and no Aurelius screen prints assigned terms. The
  editor's picker was the only place the data was touched at all.

Two shipped shapes carry over instead:

- `apps/aurelius-atlas-webapp/src/app/search/details/property-filter.ts`
  (DET-11): the details blacklist already names `meanings`. This increment
  brings the editor's drop in line with the drop the details screen already
  makes, so both Aurelius screens treat the attribute the same way.
- `apps/aurelius-atlas-webapp/src/app/search/editor/attribute-labels.ts`
  (EDT-33, DV-181): the catalogue key
  `search.components.editor.attribute.meanings` stays. The audit change tables
  name a relationship through the same map, and the completeness guard (SHL-08)
  holds the catalogue and the vendored dictionaries set-equal, so the unused
  key costs nothing.

## Deviations

Against Apache Atlas: DV-193. The stock editor forms list a `meanings` control.
The Aurelius editor lists no picker for it and sends no `meanings` key, so a
save leaves the entity's term assignments untouched.

Against the stock read path: none new. The Aurelius details screen already
dropped the attribute before this increment (DET-11), and the stock dashboards
the server serves still print the assigned terms as vendored (DD-017).

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/search/editor/form-fields.spec.ts` —
  `buildRelationshipFields` answers no field for a `meanings` definition,
  whether the definition names it itself or inherits it, and still answers
  every other relationship attribute in the same walk (EDT-36, EDT-13).
- `apps/aurelius-atlas-webapp/src/app/search/editor/view-as-entity.spec.ts` —
  `bodyFromEdits` answers no `meanings` key even when a picker named `meanings`
  is handed to it (EDT-36). The body's key set stays the door's shape, and a set
  no picker owns is still left out (AVW-05).
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts`
  — an entity whose type carries the glossary end renders no picker block for
  it, and its save posts a body with no `meanings` key and no `sections` entry
  that claims the set (EDT-36, AVW-05). Every other picker still renders and
  still posts as EDT-16 left it.
- Run from the repo root: `nx test aurelius-atlas-webapp -c ci`. No new string
  is added, so the catalogues and the vendored dictionaries stay as SHL-08 left
  them.
