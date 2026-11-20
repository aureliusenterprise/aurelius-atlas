# 18.5 A dataset picks a collection or a parent dataset

- **Status:** in review
- **Pull request:** #422
- **Records:** DD-760 to DD-766 (here), DV-188. Relies on
  [ADR 058](../../docs/architecture/adr/058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types.md),
  increment 1.5 (MDL, the loader), [18.2](../18-2-hierarchy-cardinality/spec.md) (HCA, one parent),
  [18.3](../18-3-parent-mutual-exclusion/spec.md) (PME, the parent group), and
  [18.4](../18-4-parent-safe-children/spec.md) (RPS, the parent-safe save).

## Scope

A dataset hangs under a collection, or under another dataset. Today the type lets it hold both at once, and
it lets it hold many collections. The sample corpus already states the intended rule in plain words: the
governance rule "Dataset belongs to a collection or has a parent" reads one collection or one parent
dataset. The m4i type never enforced it.

This increment makes the dataset hang the way a field hangs. A field belongs to one dataset or under one
parent field (PME-04). A dataset belongs to one collection or under one parent dataset. A collection still
holds many datasets, and a parent dataset still holds many child datasets, so each side is one-to-many on
the parent and exactly-one on the child.

In scope:

1. The `m4i_dataset_assignment` relationship puts its dataset end at `SINGLE` with the `mutuallyExclusive`
   constraint, and the `m4i_dataset` entity drops its mirrored `collections` array attribute (HCA-02's
   shape). The two relationship definitions and the dataset type go to version `1.2`.
2. The group `m4i_dataset_parent` joins `collections` and `parentDataset`. The write check, the editor's
   disabled sibling, the parent-safe refusal and the picker filter all read it with no new code path
   (DD-761).
3. The editors' pickers follow. The dataset's `collections` picker becomes a single pick (HCA-06). The
   collection's `datasets` picker becomes a parent-side picker, so it filters on `hasParent` false (RPS-07).
4. The scanners write the single shape: one collection per dataset, as one object, not a one-item list
   (DD-762).
5. The card field `hasParent` becomes consistent with the write check for datasets. The stored mark already
   reads a collection as a parent (RPS-06), and now the server refuses a second parent the same way
   (DD-764).

Out of scope:

- Changing `m4i_system.parentSystem`. A system has one parent kind only, so it needs no group. The
  governance rule "System has a collection or a subsystem" reads a system's children, not its parent, and
  does not change.
- Changing `m4i_data_attribute.dataEntity` or `m4i_generic_process.system`. Each has one parent kind.
- Migration. A catalogue that holds `collections` at `SET` is rebuilt, not migrated (HCA-10's precedent).

## Amendments in place

| Rule   | Amendment                                                                                                                                                                                                                           |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HCA-01 | The child-side end of nine m4i relationships is `SINGLE`. `m4i_dataset_assignment` (`collections`) joins the list of eight.                                                                                                         |
| PME-04 | The model puts `collections` and `parentDataset` into the group `m4i_dataset_parent`, beside the two groups of 18.3.                                                                                                                |
| PME-06 | PME-06 covers the `parentDataset` end, which keeps `SINGLE` and only gains its constraint, so `1.2` loads over a store at `1.1` as PME-06 says. It does not cover `m4i_dataset_assignment`, whose end changes cardinality (DCP-09). |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DCP-01 | The dataset end of `m4i_dataset_assignment` is `SINGLE` and carries the `mutuallyExclusive` constraint for the group `m4i_dataset_parent`. The collection end stays `SET`.                                                                                                                                                                                                                                                                                                |
| DCP-02 | The `m4i_dataset` entity definition declares no `collections` attribute. The registry builds the attribute from the relationship end definition, as one object reference (HCA-02, HCA-03).                                                                                                                                                                                                                                                                                |
| DCP-03 | `collections` and `parentDataset` share the group `m4i_dataset_parent`, so the write check of PME-07 refuses an entity that fills both, on create and on update.                                                                                                                                                                                                                                                                                                          |
| DCP-04 | A save that names `collections` replaces the edge the dataset holds, exactly as `datasets` does on a field (HCA-04). A read answers one collection, not a list (HCA-05).                                                                                                                                                                                                                                                                                                  |
| DCP-05 | The editor disables the `parentDataset` picker while `collections` holds a pick, and the `collections` picker while `parentDataset` holds a pick (PME-10). Clearing the pick frees the sibling.                                                                                                                                                                                                                                                                           |
| DCP-06 | A collection's `datasets` picker is a parent-side picker (RPS-07). It filters its search to candidates with `hasParent` false, and a save that adds a held dataset follows RPS-01: refuse without `unsafeReparent`, clear the old parent with it.                                                                                                                                                                                                                         |
| DCP-07 | Every dataset of every bundle under `data/atlas-sample/` holds at most one `collections` value and never both parents, in the single shape: no mirrored attribute, one object in `relationshipAttributes` (HCA-08). Each bundle also has to agree on both sides of a parent edge, because a child's own value and its parent's listing name the same edge. The scan found two datasets that a second parent listed, and the corpus no longer lists them (DV-188, DD-766). |
| DCP-08 | The App Search document keeps one `hasparent` boolean per dataset. A dataset in a collection is held, which is now also what the write check refuses, so the picker filter and the refusal agree (DD-764). The derivation version does not move.                                                                                                                                                                                                                          |
| DCP-09 | The bootstrap does not change a catalogue that holds the dataset types at the old shape. A new catalogue holds the `SINGLE` shape at type version `1.2` (HCA-10).                                                                                                                                                                                                                                                                                                         |

## Java origin

Nothing in Apache Atlas 2.4.0. The m4i data dictionary is Aurelius's own model, versioned with the server
(ADR 058). 18.2 already set the precedent: a cardinality edit and a type version bump are the sanctioned
path, and no Java behaviour ports here.

## Deviations

None from Apache Atlas. The end-definition constraint itself is DV-183 (18.3), and this increment only puts
one more end into one more group. The data conformance of DCP-07 needs its own entry, because the scan found
two datasets that two parents each claimed: the dataset named one parent in `parentDataset`, and a sibling
listed the same dataset in its `childDataset`. An import writes both sides of an edge (RPS-08), so the store
held the child under both. The deviation is DV-188, and the data decision is DD-766.

## Acceptance

- Unit: `libs/python/aurelius-atlas-typesystem/tests/test__hierarchies.py` (DCP-01: the end def is `SINGLE`
  with the group, the opposite end stays `SET`),
  `libs/python/aurelius-atlas-core/tests/test__m4i_models.py` (DCP-01, DCP-02, DCP-07: the dictionary names
  the end at `SINGLE` with the group at version `1.2`, the dataset entity declares no mirrored attribute,
  the model equals the typedef file of every bundle, no bundle dataset breaks the rule, and every bundle
  child answers one parent across both sides of the edge),
  `libs/python/aurelius-atlas-core/tests/test__model_loader.py` (DCP-09: a model file that changes a stored
  end's cardinality is refused whole and changes nothing; PME-06 as written still covers the `parentDataset`
  end, which keeps `SINGLE` and only gains its constraint),
  `libs/python/aurelius-atlas-core/tests/test__relationship_attributes.py` (DCP-03, DCP-04: the create and
  update checks over the dataset group, and the replace-one-parent save),
  `libs/python/aurelius-atlas-core/tests/test__entity_retriever.py` (DCP-04: the read answers one
  collection),
  `libs/python/aurelius-atlas-core/tests/test__view_search.py` (DCP-06: the `hasParent` filter over a
  dataset held by a collection),
  `libs/python/aurelius-atlas-core/tests/test__relationship_attributes.py` (DCP-06: the collection save that
  reaches a held dataset, refused and moved by the opt-in),
  `libs/python/aurelius-atlas-core/tests/test__app_search_indexer.py` (DCP-08: a dataset a collection holds is
  held, at the derivation version that does not move),
  `apps/aurelius-atlas-db-scanner/tests/test__graph.py` and
  `apps/aurelius-atlas-kafka-scanner/tests/test__graph.py` (DCP-04: the scanners write `collections` as one
  object).
- Webapp: `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts` (DCP-05: a
  filled collection disables the parent picker and the reverse),
  `form-fields.spec.ts` (the group reads off the definitions; `parentSide` lands on the collection's
  `datasets` picker and not on the dataset's `collections` picker).
- E2E: `nx e2e aurelius-atlas-server` (the registry bootstraps the group on a real store), the scanner e2e
  suites (one bulk request writes the tree with the single shape).
- Data: each bundle's `atlas-typesdef.json` changes with the model, which `test__m4i_models.py` compares
  (DCP-01). `sample_data.zip` loses the two phantom `childDataset` listings (DD-766), and the three 14.6
  gates of `libs/python/aurelius-atlas-core/tests/` re-baseline with it (DV-188).
