# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-740. The hierarchy child end is SINGLE and the child entity declares no mirrored attribute

- **Status:** Proposed
- **Increment:** 18.2
- **Date:** 2026-11-20
- **Relates to:** ADR 058 (the m4i types version with the server), DD-032 and DD-362 (the m4i dictionary
  layout), THY-10 (the relationship end builds the entity's attribute).

**Decision.** The child-side end of the eight m4i hierarchy relationships becomes `SINGLE` (HCA-01):
`m4i_data_entity_assignment.dataDomain` on `m4i_data_entity`, `m4i_parent_entity_assignment.parentEntity` on
`m4i_data_entity`, `m4i_data_entity_attribute_assignment.dataEntity` on `m4i_data_attribute`,
`m4i_field_assignment.datasets` on `m4i_field`, `m4i_field_parent_assignment.parentField` on `m4i_field`,
`m4i_system_parent_assignment.parentSystem` on `m4i_system`, `m4i_system_process_assignment.system` on
`m4i_generic_process`, and `m4i_dataset_parent_assignment.parentDataset` on `m4i_dataset`. Each child's entity
definition loses the mirrored `array<...>` attribute of that name (HCA-02), so the registry builds the
attribute from the `SINGLE` end def as a single object reference (HCA-03). The parent-side end of each stays
`SET`. The eight many-to-many m4i relationships keep both ends `SET`.

**Reason.** A hierarchy child has one parent, and the metamodel says `SET` on both ends, so the type lets a
data entity sit in many data domains and the editor offers a multi-pick. The end def already carries
`SINGLE`, `LIST`, or `SET` and the ported type system, write path, read path and editor all honour it: the
vendored base and glossary models use `SINGLE` on four of their seventy ends, and
`RelationshipType._add_to_end` builds a single object reference when the entity declares no attribute of the
end's name. The reason the m4i types do not get this today is a mirrored attribute: `m4i_data_entity` declares
its own `array<m4i_data_domain>` attribute named `dataDomain`, and an entity-declared attribute overrides the
end def (it becomes a legacy attribute). Setting the end to `SINGLE` alone does nothing while the array
attribute stays. Removing the mirrored attribute and keeping the `SINGLE` end def is the smallest change that
makes the child attribute single, and it reuses behaviour Atlas and the port already have rather than adding a
new validation. No store runs this version, so the breaking shape change costs nothing now (DD-742).

**Alternatives.**

- **Keep the array attribute and enforce one value with `valuesMaxCount: 1`.** The attribute stays a list type,
  so the wire keeps a list shape for a value the model calls single, and the read and editor keep a list
  path. It is more state than a `SINGLE` end needs.
- **Add a runtime "at most one parent" check to the relationship create path.** It duplicates the guard the
  `SINGLE` write path already gives, and Apache Atlas has no such check, so it diverges for no model gain.
- **Make each hierarchy a COMPOSITION with a mandatory parent.** This also forbids a second parent and is
  stronger than HCA-04. It forces a decision this increment does not make (DD-741) and changes delete and
  tag-propagation behaviour across every hierarchy. It is a later increment if a parent must be mandatory.

### DD-741. A hierarchy parent stays optional, not a mandatory composition

- **Status:** Proposed
- **Increment:** 18.2
- **Date:** 2026-11-20
- **Relates to:** DD-740, HCA-07.

**Decision.** Every m4i hierarchy stays an `ASSOCIATION` with a non-container parent end. A child's parent
attribute stays optional. A child holds zero or one parent. The increment does not change
`relationshipCategory` and does not set `isContainer`.

**Reason.** `SINGLE` answers the question the user asked (a child has at most one parent, not many). A
mandatory parent is a different question, and the sample corpus and scanners create children before their
parent exists, so a composition that validates a mandatory parent on create (EVL-08) refuses those writes.
`ASSOCIATION` keeps the zero-or-one cardinality that matches the data.

**Alternatives.**

- **`COMPOSITION` with the parent end as container.** It forbids a second parent by `validateAtlasRelationshipDef`
  and makes the parent mandatory, which is stronger than asked. The existing data and the import order make a
  mandatory parent wrong today, and it changes delete cascades for types that are not yet ready for it. A later
  increment chooses this per relationship if the rule "every child must have a parent" becomes real.

### DD-742. The change is breaking, with a type version bump and no migration

- **Status:** Proposed
- **Increment:** 18.2
- **Date:** 2026-11-20
- **Relates to:** ADR 058, MDL-02 (a model file updates a stored type only when its `typeVersion` is greater),
  TDS-08 (a stored attribute cannot be retyped or removed).

**Decision.** The m4i data dictionary model file becomes type version `1.1` with the `SINGLE` child ends and
the mirrored attributes removed. The bootstrap creates the new shape in a fresh catalogue (HCA-10). No patch,
migration, or store rewrite ships. A catalogue that already holds the m4i hierarchy types at the `SET` shape is
not corrected by the bootstrap.

**Reason.** Atlas refuses to retype or remove a stored attribute (TDS-08). The only in-place door is a
`REMOVE_LEGACY_REF_ATTRIBUTES` patch that bumps `1.0` to `1.1` and rebuilds the child attribute. No catalogue
runs this version of Aurelius Atlas yet: it is pre-release, ADR 058 bootstraps the types, and no deployment
holds them. So the patch carries code and a test for a store that does not exist. The user chose the breaking
path. `MDL-02` makes a `1.1` file replace a stored `1.0` only on the version comparison, so an old catalogue
keeps its `SET` shape instead of half-upgrading into a shape its stored attributes cannot hold.

**Alternatives.**

- **Ship a `REMOVE_LEGACY_REF_ATTRIBUTES` patch from `1.0` to `1.1`.** It upgrades an existing store in place,
  which is what a released model needs. It costs a patch file, a loader test, and a parity check for stores
  that do not exist yet. Add it when a released catalogue needs it.
- **Leave `typeVersion` at `1.0`.** Then `MDL-02` skips the file every start and no fresh catalogue gets the
  `SINGLE` shape, which defeats the increment.

### DD-743. The sample bundles and the governance corpus re-baseline to the single value

- **Status:** Proposed
- **Increment:** 18.2
- **Date:** 2026-11-20
- **Relates to:** HCA-08, HCA-09, the 14.6 frozen verdict corpus (DV-160, DV-171), the 12.7 hierarchy pair rules.

**Decision.** Every bundle under `data/atlas-sample/` holds at most one active value on each hierarchy child
attribute (HCA-08). A `test__sample_bundles.py` check reads each bundle and asserts it. The governance verdict
corpus in `test__app_search_governance.py` is re-baselined so a hierarchy attribute reads present when it holds
a parent and absent when it holds none (HCA-09).

**Reason.** The single scan of `sample_data.zip` (687 entities) found all hierarchy child attributes single
except `m4i_dataset.parentDataset`, where two datasets name two parent datasets. The `SINGLE` end makes a two
value write replace the edge, so the seed data and the type must agree. A `SINGLE` attribute changes what the
governance engine reads for a hierarchy rule (the relationship value becomes one object, not a list), so the
14.6 corpus that freezes those verdicts moves and is re-baselined rather than left stale.

**Alternatives.**

- **Keep `m4i_dataset.parentDataset` at `SET`.** A dataset that rolls up from two parents is a real warehouse
  pattern, and the two corpus datasets lean on it. But "a child has one parent" is the rule the increment
  sets, and a self-nesting dataset rollup is the same hierarchy. Flipping it keeps the model honest; the two
  datasets drop to their first parent. If the rollup proves to need two parents, that relationship returns to
  `SET` as its own decision, and HCA-01 loses that one line.
- **Leave the sample data and corpus as is.** Then the demo import creates a child with two parents against a
  `SINGLE` type, and the read answers the first edge while the next save deletes the other: a data split the
  type now forbids.
