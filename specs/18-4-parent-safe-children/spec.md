# 18.4 Adding a child never reparents silently

- **Status:** in review
- **Pull request:** #419
- **Records:** DD-755 to DD-759 (here), DV-186 to DV-187 (deviations). Relies on
  [ADR 058](../../docs/architecture/adr/058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types.md)
  (the m4i types ship and version with the server), increment 18.2 (HCA-01 to HCA-10, the single parent),
  and increment 18.3 (PME-01 to PME-13, the parent choice). AVS-01 amended in place (DD-758): the card
  gained `hasParent`.

## Scope

A type can sit under one parent through a hierarchy child attribute (18.2). A child that is already under a
parent can be reached again from the other side: the editor adds a field to a dataset, and that field
already hangs under another dataset or under a parent field. Today the two write doors handle this
differently, and both are wrong.

Neither door moves the child today, and both leave it under two parents. The Atlas wire door's relationship
mapper replaces the child's edge only of the attribute being written, so adding a note to a choice that is
already boxed keeps the box and adds the note. The view door's `sections` step creates the new edge through
the relationship store and clears nothing at all (DV-186). Either way the `SINGLE` cardinality of increment
18.2 is broken and the child reads back with two parents.

This increment makes the move explicit and stops the corruption. A save that adds a child on the parent
side, when that child already holds a parent of the same group, is refused unless the request opts in with
`unsafeReparent`. On both doors the opt-in means "move it": the old parent edge of the group is cleared and
the child ends with exactly one parent. In the editor, the relationship picker for a parent-side attribute
only offers candidates that hold no parent of the relevant group, so the ordinary path never asks for the
opt-in.

In scope:

1. A shared server check: a parent-side save that reaches an already-parented child is refused without the
   opt-in, on both the wire and the view door (RPS-01, RPS-02, RPS-03).
2. The opt-in `unsafeReparent`, a query parameter on the wire create/update endpoints and on the view door
   mutation (RPS-04).
3. With the opt-in, the view door clears the child's old parent edge of the group, so the child moves to
   exactly one parent (RPS-05). The door no longer leaves a child under two parents.
4. The view door's search answers a stored boolean of whether an entity holds any parent (RPS-06), which
   forces the document derivation version to `3`.
5. The editor's parent-side picker searches only candidates that hold no parent (RPS-07).
6. The wire guard exempts an import, so an export replays without the flag (RPS-08).

Out of scope:

- A "move" action that names the old parent. The opt-in moves whatever parent the child holds. There is no
  targeted transfer.
- Hiding candidates in the single-parent (child-side) pickers. Those already offer any entity, because
  choosing one there is the legitimate move of the edited entity itself. PME-10 disables the sibling picker
  instead.
- The wire door's single-parent relationship endpoints. The check is on entity saves only.

## Semantics

A **parent-side save** names a relationship attribute of cardinality `SET` whose opposite end is a hierarchy
child end of cardinality `SINGLE` (the eight ends of HCA-01). It adds an edge from the edited entity to a
candidate. The candidate's **parent family** is that single child attribute of its type, together with the
members of the `mutuallyExclusive` group that single attribute names (PME-03), when there is one. A
candidate is **held** on the save when it already holds an active edge on any member of its parent family to
a parent other than the one the save names, and that parent is not itself dropped from the candidate in the same
request. Each rule is enforced by a test that names its id
(`@pytest.mark.covers(..., rules=[...])`, ADR 056).

| Id     | Rule                                                                                                                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| RPS-01 | A create or update that adds a parent-side edge to a held candidate is refused with `INSTANCE_CRUD_INVALID_PARAMS`, on the wire door and the view door, unless the request carries `unsafeReparent` (DV-187).                                                |
| RPS-02 | Adding a parent-side edge to a candidate that holds no parent of the family, to the parent it already sits under, or whose other parent the same request updates to drop it (a deliberate move) is never refused by this rule.                               |
| RPS-03 | A refusal lists each candidate that is held, naming the child attribute and the parent it already holds. It applies the rewind, so nothing is written (DD-590).                                                                                              |
| RPS-04 | `unsafeReparent` is a query parameter read as `Boolean.valueOf` (true only for `true` in any case, absent means false) on the wire create/update and the view door mutation.                                                                                 |
| RPS-05 | With `unsafeReparent`, a save that would move a child clears the child's other active parent edge of the family on both doors first, so the child reads back with exactly one parent.                                                                        |
| RPS-06 | The view door's search answers a card's `hasParent`: true when the entity holds any parent, false when it holds none. It comes from a stored boolean on the entity document, derived next to the breadcrumb (LAS-04), so the derivation version goes to `3`. |
| RPS-07 | The editor's picker for a parent-side attribute filters its search to candidates with `hasParent` false, so a held candidate never appears. The child-side single pickers do not filter this way.                                                            |
| RPS-08 | An import is exempt from RPS-01: the writer's import mode writes the bundle's edges as the bundle states them, so replaying an export never asks for the flag.                                                                                               |

## Java origin

Apache Atlas 2.4.0 moves a child only within the attribute it writes. `EntityGraphMapper.addInverseReference`
replaces the candidate's existing edge of that one relationship when the opposite end is `SINGLE`, so writing
`parentDataset` again re-parents. It never looks at a different relationship: adding a field through
`datasets` when the field already hangs under a `parentField` keeps both edges, and nothing refuses it. The
Java engine enforces the `SINGLE` child end nowhere on a parent-side write (Aurelius enforces it on a
child-side save since HCA-04). Aurelius requires the opt-in on both doors and clears the family edge with it,
which is an improvement over Atlas and not parity (DV-187).

## Deviations

- **DV-186 (Interface):** The view door's `sections` step created a parent edge on a candidate that already
  held one and cleared nothing, not even an edge of the same relationship, so a child moved by the wire door
  on the same attribute stayed in two places through the view door. Aurelius now refuses the save without
  `unsafeReparent` and clears the family edge with it. Recorded for the behaviour change on Aurelius's own
  surface.
- **DV-187 (Interface):** Atlas accepts a parent-side write that leaves a child under two parents when the
  edge it already holds is of another relationship type, and never refuses it. Aurelius refuses that write
  unless the request carries `unsafeReparent`, and with it clears the old edge, so a child holds at most one
  parent of the group. A client that re-parents through the Atlas wire API must now send the parameter.

## Acceptance

- Unit: `libs/python/aurelius-atlas-core/tests/test__relationship_attributes.py` (RPS-01, RPS-02, RPS-03,
  RPS-05, RPS-08 on the wire writer: a held candidate is refused, a free or same-parent candidate passes, the
  opt-in moves the child, and an import is exempt),
  `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_entity_write.py` (RPS-04: the query parameter
  reads as `Boolean.valueOf`), `apps/aurelius-atlas-server/tests/test__view_mutation.py` (RPS-01, RPS-03,
  RPS-05 on the view door: a held candidate on a `sections` add is refused and rewinds, and the opt-in clears
  the old edge), `libs/python/aurelius-atlas-core/tests/test__view_search.py` (RPS-06: the card answers
  `hasParent`).
- Webapp: `apps/aurelius-atlas-webapp/src/app/search/editor/entity-relationship-input.component.spec.ts`
  (RPS-07: a parent-side picker sends `hasParent` false and drops a held candidate), `form-fields.spec.ts`
  (a parent-side attribute is recognised from its definitions).
- E2E: `apps/aurelius-atlas-server/e2e/test__view_mutation_e2e.py` (a held dataset refuses a view-door save
  naming its parent, and the opt-in moves it to exactly one parent).
- Parity: the change is on Aurelius surfaces only (the view door, the view search, the m4i dictionary). The
  frozen `atlas-dev` oracle reads none of these fields, so no scenario re-baseline.
