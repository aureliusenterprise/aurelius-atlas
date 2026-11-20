# 18.3 A child that can sit under two parents picks one

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-744 to DD-748 (here), DV-183 (deviations). Relies on
  [ADR 058](../../docs/architecture/adr/058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types.md)
  (the m4i types ship and version with the server), increment 1.5 (MDL, the loader), and
  [increment 18.2](../18-2-hierarchy-cardinality/spec.md) (HCA-01 to HCA-10, the single parent).

## Scope

Some types can sit under two different parents. A data entity hangs either under a data domain or under
another data entity. A field hangs either under a dataset or under another field. Today an entity can fill
both places at once, and the lineage page draws two parents for one object.

This increment puts the choice in the type definition. The end of a hierarchical relationship carries a
constraint naming a mutual-exclusion group, and every child end in that group shares the group name. The
typesystem copies the constraint onto the attribute it builds for the child end, so the rule reaches the
server and the metamodel API through the same attribute definitions the API already returns. Saving an
entity that fills two attributes of one group is an error. Apache Atlas has no such constraint (ADR 051),
so this is a deliberate deviation (DV-183).

In scope:

1. A new constraint type on a relationship end definition, plus the Python model field.
2. The typesystem copies the end constraint onto the attribute it builds for the child end.
3. The bundled m4i model puts the two ends of each choice into one group, and the four relationship
   definitions that carry them go to type version `1.2`.
4. Server-side validation rejects an entity that fills two members of one group, on create and on update.

Out of scope:

- A grouped parent picker in the webapp editor. The server rejects the pair and the editor shows the
  error text it already shows for a rejected save.
- A "must choose one" variant. Filling neither member stays legal, the same as an empty optional attribute.
- Mutual exclusion between anything other than hierarchical children. The constraint type is generic, but
  only 18.2's child ends use it.

## Semantics

A **parent group** is a named set of hierarchy child attributes of one type, named by a
`mutuallyExclusive` constraint. An attribute is **filled** when a create or update body names it with a
value, or when the stored entity holds an active edge on it. A partial update that names neither member of
a group changes nothing, so it stays valid. Each rule is enforced by a test that names its id
(`@pytest.mark.covers(..., rules=[...])`, ADR 056).

| Id     | Rule                                                                                                                                                                                                                                                                                            |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PME-01 | A relationship end definition carries an optional list of constraints, in the same shape as an attribute definition. The type system rejects a constraint on a container end.                                                                                                                   |
| PME-02 | When the registry builds the attribute for a child end, it copies the end's constraints onto that attribute. An attribute the type declares itself keeps its own constraints, unchanged.                                                                                                        |
| PME-03 | A `mutuallyExclusive` constraint carries a non-empty `group` parameter. The write check compares the filled attributes of one type per group, and ignores a constraint whose group names no other attribute of that type.                                                                       |
| PME-04 | The m4i model puts `dataDomain` and `parentEntity` into the group `m4i_data_entity_parent`, and `datasets` and `parentField` into `m4i_field_parent`. The model declares this on the four child relationship end definitions, and those four relationship definitions go to type version `1.2`. |
| PME-05 | The metamodel API returns the constraint on the end definition and on the entity's relationship attribute definitions, so a client reads the rule from either place.                                                                                                                            |
| PME-06 | The bundle loader applies the m4i model at `1.2` over a store that holds it at `1.1` through the normal typedef update check, with no migration and no error.                                                                                                                                   |
| PME-07 | A create that fills both members of a group fails with `INSTANCE_CRUD_INVALID_PARAMS`.                                                                                                                                                                                                          |
| PME-08 | An update fails when it adds a second parent while the entity already holds the other one. An update that moves the entity from one parent to the other succeeds.                                                                                                                               |
| PME-09 | Filling neither member, or exactly one, succeeds. An entity saved with one parent reads back with exactly one parent of that type.                                                                                                                                                              |

## Java origin

Nothing in Apache Atlas 2.4.0. `AtlasRelationshipEndDef` has no constraints field, and no validation
compares two relationships of one instance (ADR 051). The constraint type, the copy step, and the
validation all come from this increment. See [DV-183](../../docs/architecture/conversion/deviations.md).

## Deviations

- **DV-183 (Interface):** The type system and the metamodel API accept a constraint on a relationship end
  definition, and the instance API enforces the group. Atlas has no equivalent, so any client that sends
  one to Atlas gets an unknown field, and Atlas stores both parents.

## Acceptance

- Unit: `libs/python/aurelius-atlas-typesystem/tests/test__hierarchies.py` (PME-01, PME-02, PME-03: the end
  def carries constraints and rejects a container end, the built attribute carries the end's constraints
  while a declared attribute keeps its own, and a lone group enforces nothing),
  `libs/python/aurelius-atlas-core/tests/test__m4i_models.py` (PME-04: the dictionary names the groups on
  the four child ends at type version `1.2`, and the model equals the typedef file of every bundle in
  `data/atlas-sample/`), `libs/python/aurelius-atlas-core/tests/test__model_loader.py` (PME-06: the loader
  applies `1.2` over a store at `1.1`),
  `libs/python/aurelius-atlas-core/tests/test__relationship_attributes.py` (PME-03, PME-07, PME-08, PME-09:
  the create and update checks, beside the HCA-04 and HCA-07 tests),
  `libs/python/aurelius-atlas-core/tests/test__type_reads.py` (PME-05: the type read answers the constraint
  on the end def and on the entity's relationship attribute definitions).
- Data: the `atlas-typesdef.json` of each bundle in `data/atlas-sample/` changes with the model, which
  `test__m4i_models.py` compares (PME-04).
- E2E: `nx e2e aurelius-atlas-server` (the registry bootstraps the constraints on a real store, PME-05).
- Parity: unchanged. The scenario fixtures under `apps/*/scenarios` name no m4i parent attribute and no
  end-def constraint (checked at spec time), so no scenario re-baseline.
