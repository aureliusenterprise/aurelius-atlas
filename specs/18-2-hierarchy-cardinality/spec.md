# 18.2 The metamodel gives every hierarchy child one parent

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-740 to DD-743 (here). Relies on [ADR 058](../../docs/architecture/adr/058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types.md)
  (the m4i types ship and version with the server), increment 1.5 (MDL, the loader), and increment 18.1 (MMS,
  the metamodel bootstrap).

## Scope

Every m4i hierarchy relationship declares both ends as `SET`. A data entity gets its data domain as an
`array<m4i_data_domain>` attribute, so it can hold many. The same holds for the entity, attribute, field,
system and process parent links. A child in a hierarchy has one parent. A data entity sits in one data domain.
A data attribute belongs to one entity. A field sits in one dataset and under one parent field.

Apache Atlas already carries a cardinality on a relationship end: `SINGLE`, `LIST`, or `SET`. The ported type
system honours `SINGLE` end to end (the base and glossary models use it on four of their seventy ends). The
m4i data dictionary never sets it, because each hierarchy child also declares a mirrored `array<...>`
attribute on its own entity definition, and that attribute overrides the end def.

This increment flips the hierarchy child ends to `SINGLE` and removes the mirrored array attribute, so the end
def governs. It is a breaking change to the shipped m4i types. No catalogue runs this version yet, so nothing
migrates. A fresh catalogue gets the new shape and an old catalogue is rebuilt.

It delivers:

- One parent per hierarchy child. The child-side end of each of the eight m4i hierarchy relationships is
  `SINGLE`. The parent-side end stays `SET` (HCA-01).
- A hierarchy child attribute is a relationship attribute only. The child's entity definition no longer
  declares the mirrored `array<...>` attribute, so the registry resolves it from the end def as a single
  object reference (HCA-02, HCA-03).
- The store keeps one edge. A save that sets a hierarchy child attribute replaces the edge it holds, so an
  entity holds at most one parent (HCA-04). The read answers one related object, not a list (HCA-05).
- The editor shows one picker. A hierarchy child field renders as a single pick whose input hides at one chip
  (HCA-06).
- The sample bundles follow. Every shipped bundle holds at most one value on every hierarchy child attribute,
  and the two datasets under two parents become one parent each (HCA-08).
- The governance corpus follows. The frozen 14.6 verdict corpus reads the single-valued hierarchy attributes
  and is re-baselined where it moves (HCA-09).

It does not deliver, with the increment that will:

| Not delivered                                                | Lands with                     |
| ------------------------------------------------------------ | ------------------------------ |
| A mandatory parent (composition, zero-or-one to one-and-one) | a later increment, if needed   |
| Migration of a store that already holds the `SET` shape      | not planned (breaking, HCA-10) |
| Cardinality change on the base or glossary models            | not planned                    |

## Semantics

A "hierarchy child attribute" is the single-valued end of one of the eight relationships in HCA-01. The
"parent" is the entity on the other end. The many-to-many m4i relationships (the owner, steward, domain lead,
process owner, collection, dataset, data quality, and source assignments, and the field-attribute link) keep
`SET` and are out of scope.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| HCA-01 | The child-side end of each of these eight m4i relationships is `SINGLE`, and its parent-side end stays `SET`: `m4i_data_entity_assignment` (`dataDomain`), `m4i_parent_entity_assignment` (`parentEntity`), `m4i_data_entity_attribute_assignment` (`dataEntity`), `m4i_field_assignment` (`datasets`), `m4i_field_parent_assignment` (`parentField`), `m4i_system_parent_assignment` (`parentSystem`), `m4i_system_process_assignment` (`system`), `m4i_dataset_parent_assignment` (`parentDataset`). |
| HCA-02 | The entity definition at a hierarchy child end declares no attribute of that name. The registry builds the child's attribute from the relationship end def, not from an entity attribute.                                                                                                                                                                                                                                                                                                              |
| HCA-03 | The registry answers a hierarchy child attribute as a single object reference with cardinality `SINGLE`, never as `array<...>`.                                                                                                                                                                                                                                                                                                                                                                        |
| HCA-04 | A save that names a hierarchy child attribute replaces the relationship edge the entity holds. The entity holds at most one parent on that attribute.                                                                                                                                                                                                                                                                                                                                                  |
| HCA-05 | A read answers a hierarchy child attribute as one related object, not a list. An entity with no parent answers none.                                                                                                                                                                                                                                                                                                                                                                                   |
| HCA-06 | The editor renders a hierarchy child field as a single pick: one chip, and the input hides once it holds one.                                                                                                                                                                                                                                                                                                                                                                                          |
| HCA-07 | A save with a value on a hierarchy child attribute stays valid when that attribute is optional, and a save with no value leaves the entity parentless.                                                                                                                                                                                                                                                                                                                                                 |
| HCA-08 | Every bundle under `data/atlas-sample/` holds at most one active value on every hierarchy child attribute. The two datasets that held two parent datasets hold one each.                                                                                                                                                                                                                                                                                                                               |
| HCA-09 | The governance verdicts over the frozen 14.6 corpus read a single-valued hierarchy attribute as present when it holds a parent and absent when it holds none.                                                                                                                                                                                                                                                                                                                                          |
| HCA-10 | The bootstrap does not change a catalogue that already holds the m4i hierarchy types at `SET`. A new catalogue holds the `SINGLE` shape at type version `1.1`.                                                                                                                                                                                                                                                                                                                                         |

## Java origin

This increment changes Aurelius's own m4i data dictionary (ADR 058), not Apache Atlas code. The Atlas
behaviour it depends on is already ported:

- `AtlasRelationshipEndDef.cardinality` and `AtlasRelationshipType.addRelationshipAttribute` (the end def
  builds the child's attribute when the entity declares none), ported in increment 3.1,
  `aurelius_atlas_typesystem.relationship_type`.
- `AtlasArrayType` count and cardinality checks, and the single-reference read and write paths, ported in
  increments 2.x and 3.1, `aurelius_atlas_typesystem.array_type` and `aurelius_atlas_core.relationship_mapper`.
- The base model and glossary model already carry `SINGLE` ends (`AtlasGlossaryTermAnchor`,
  `AtlasGlossaryCategoryHierarchyLink`), as the vendored 2.4.0 `0000-Area0` shows.

## Deviations

None from Apache Atlas. The Atlas relationship behaviour is unchanged. The m4i data dictionary is Aurelius's
own model, which ADR 058 versions with the server, so the cardinality edit and the type version bump are the
sanctioned path.

## Acceptance

- Unit: `libs/python/aurelius-atlas-typesystem/tests/test__hierarchies.py` (HCA-02, HCA-03: a `SINGLE` end with
  no entity attribute resolves to a single object reference),
  `libs/python/aurelius-atlas-core/tests/test__m4i_models.py` (HCA-01, HCA-02, HCA-08: the dictionary names
  `SINGLE` on the eight child ends and no mirrored attribute on the child entity defs, and the model still
  equals the typedef file of every bundle in `data/atlas-sample/`),
  `libs/python/aurelius-atlas-core/tests/test__relationship_attributes.py` (HCA-04: a save replaces the parent
  edge, beside the single-end replacement test already there),
  `libs/python/aurelius-atlas-core/tests/test__entity_retriever.py` (HCA-05: the read answers one object),
  `libs/python/aurelius-atlas-core/tests/test__app_search_governance.py` (HCA-09, re-baselined),
  `apps/aurelius-atlas-webapp/src/app/search/editor/form-fields.spec.ts` (HCA-06, Vitest).
- Data: the `atlas-typesdef.json` and the entity entries of each bundle in `data/atlas-sample/` change with the
  model, which `test__m4i_models.py` compares (HCA-08).
- E2E: `nx e2e aurelius-atlas-server` (the registry bootstraps the `SINGLE` shape on a real store, HCA-10).
- Parity: unchanged. The scenario fixtures under `apps/*/scenarios` name no m4i hierarchy attribute (checked
  at spec time), so no scenario re-baseline.
