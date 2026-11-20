# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-760. The dataset collection end becomes a single constrained child end

- **Status:** Proposed
- **Increment:** 18.5
- **Date:** 2026-11-20
- **Relates to:** HCA-01 (the single child ends), HCA-02 (no mirrored attribute), PME-04 (the groups),
  DCP-01, DCP-02.

**Decision.** `m4i_dataset_assignment`'s dataset end goes from `SET` to `SINGLE` and carries the
`mutuallyExclusive` constraint for the group `m4i_dataset_parent`. The `m4i_dataset` entity drops its
declared `collections` array attribute, so the registry builds the attribute from the end definition. The
relationship definition and the entity definition go to type version `1.2`, the same step 18.2 and 18.3 took.
The collection end stays `SET`.

**Reason.** This is the shape a field already has, and it is the only shape PME-02 can carry the constraint
in. 18.2 removed the mirrored array attribute from every hierarchy child for exactly this reason: a declared
attribute keeps its own constraints, so a constraint on the end definition never reaches it (HCA-02, PME-02).
A dataset that keeps its `collections` array would ignore the group and PME-07 would refuse nothing. The
corpus rule "Dataset belongs to a collection or has a parent" already reads the type this way.

**Alternatives.**

- **Keep the array attribute and put the constraint on it.** The cardinality stays `SET` and PME-07 compares
  two filled members of one group, so a dataset with two collections passes while a dataset with one
  collection and one parent dataset passes too: the cardinality check and the group check read different
  things. The 18.2 argument applies unchanged.
- **Add the constraint to the entity's declared attribute only.** The metamodel API would then answer the
  rule on the attribute definition but not on the end definition, breaking PME-05's "either place" promise
  that the editor and clients read today.
- **Group only in the webapp.** An API client or an import writes two parents freely, the same gap PME-10
  showed for the sibling picker.

### DD-761. The new group reuses every 18.3 and 18.4 mechanism unchanged

- **Status:** Proposed
- **Increment:** 18.5
- **Date:** 2026-11-20
- **Relates to:** PME-07 (the parent-group check), PME-10 (the disabled picker), RPS-01 (the parent-safe
  refusal), RPS-07 (the picker filter), DCP-03, DCP-05, DCP-06.

**Decision.** The increment adds no new rule code. `EntityType.parent_groups`, the editor's
`parentGroupOf`, and the typesystem's `parent_side_children` and `parent_family` all read whatever groups the
metamodel names. Grouping `collections` and `parentDataset` turns on the refusal (PME-07), the disabled
sibling picker (PME-10), and the parent-safe candidate check (RPS-01) for datasets in one edit of the type
definition. The collection's `datasets` picker becomes parent-side by the relationship-slice rule of DD-759,
so it sends the `hasParent` filter without a new client rule.

**Reason.** Every mechanism reads the metamodel as its single source. A dataset-specific branch would give
the dataset rules the field and the data entity do not have, and the three types would drift. The check
`parent_side_children` performs is exactly "a `SET` whose opposite end is a `SINGLE` child end", which the
new shape satisfies on the collection side.

**Alternatives.**

- **A dataset-specific validation.** Duplicated logic that 18.3's generic group already covers, and the
  webapp would need a second disabling rule.
- **Wait for a later increment to wire the editor.** The editor needs nothing: PME-10 reads the group from
  the definitions the form already fetches.

### DD-762. The scanners write the single collection end as one object

- **Status:** Proposed
- **Increment:** 18.5
- **Date:** 2026-11-20
- **Relates to:** HCA-04 (the single edge save), DD-746 (the single-end map shape), DV-183, DCP-04.

**Decision.** Both scanners write `collections` as one object reference, not a one-item list: the db-scanner
for its schema collection and the kafka-scanner for its cluster collection. Each dataset hangs under the one
collection its scan builds, so no scanner writes a second parent, and none needs `unsafeReparent`.

**Reason.** A `SINGLE` end answers a list with `ObjectId is not valid`, the same failure 18.2's list-to-scalar
fix produced for `datasets` and `dataEntity`. One collection per dataset is also the correct topology: both
scanners build one collection per scan (one schema, one cluster), so there is nothing to distribute a dataset
across.

**Alternatives.**

- **Send a one-item list and let the store collapse it.** The store never collapses a list on a `SINGLE` end
  (HCA-03), and silently accepting both shapes gives every client a second contract to guess.
- **Leave the scanners and let the write fail.** The scanner e2e suites write a whole tree in one bulk
  request; a refused write fails the suite and the scanner ships broken.

### DD-763. The collection end keeps SET and the corpus rule keeps its words

- **Status:** Proposed
- **Increment:** 18.5
- **Date:** 2026-11-20
- **Relates to:** HCA-01 (the parent side stays `SET`), PME-11 (the rule wording), DCP-07.

**Decision.** The collection side of `m4i_dataset_assignment` stays `SET`, so a collection holds many
datasets and only the child side is single. The governance rules of the sample corpus keep their sentences:
"Dataset belongs to a collection or has a parent" and "Dataset has a field or a child dataset" stay as
written, because their expressions (`length('collections', 1) | length('parentDataset', 1)`) read presence
and stay true on a single-valued end.

**Reason.** The one-to-many direction the user asked for is the parent side, and HCA-01 keeps every parent
side `SET`. The rule expressions do not count elements above one, so a `SINGLE` end answers them exactly as
a one-item `SET` did, and no re-baseline follows (unlike PME-11's "at least one" wording, which 18.3 had to
rewrite because it named a set the type no longer held).

**Alternatives.**

- **Also cap the collection's datasets.** The type would then refuse a collection's whole purpose. The user
  asked for one parent per dataset, not one dataset per collection.
- **Reword the rules.** PME-13 holds every rule to what the model defines; these already name only defined
  names. A reword changes the frozen `atlas-dev` oracle's counts for no rule change.

### DD-764. The stored parent flag stays one boolean and now agrees with the check

- **Status:** Proposed
- **Increment:** 18.5
- **Date:** 2026-11-20
- **Relates to:** RPS-06 (the `hasParent` card field), DD-758 (the stored boolean), LAS-04 (the breadcrumb
  parents), DCP-08.

**Decision.** `hasparent` keeps its derivation, `bool(breadcrumb)`, and the derivation version stays `3`.
The `PARENTS` table already reads a dataset's collection as a parent, so a dataset in a collection is marked
held. Before this increment that mark over-filtered: the picker hid candidates the server would still accept.
After this increment the server refuses a dataset that already holds a collection, so the mark and the
refusal agree, and the version bump DD-758 needed for a change of meaning no longer applies.

**Reason.** The flag is one boolean per entity, not one per group. A per-group flag would need a derivation
version bump and a field the editor does not need: only dataset, field and data entity have choices, and a
field or an entity is held on any of its parents for the same reason a dataset now is. The 18.4 filter
question was "does this candidate hold a parent the save would conflict with", and after this increment the
answer is the same one the stored boolean gives.

**Alternatives.**

- **Per-group flags (`hasparent_dataset_parent`, and so on).** Three more stored booleans, a derivation
  version bump, and a picker that selects the field by group. The over-filter it removes is the only case
  where the boolean lies, and this increment removes it.
- **Drop a collection from the breadcrumb parents.** The breadcrumb and the lineage page read a dataset's
  collection as its place in the tree; removing it would break the trail 16.x built and the rule wording.

### DD-766. The child's own parent value wins over a parent's listing

- **Status:** Proposed
- **Increment:** 18.5
- **Date:** 2026-11-20
- **Relates to:** DCP-07 (the one-parent corpus), RPS-08 (the import exemption), HCA-08 (the single shape),
  DV-188, LAS-05 (the derived relations).

**Decision.** When a bundle states both sides of a hierarchy edge and the two disagree, the child's own
single-valued end is the truth. The parent's listing is emptied to match. `sample_data.zip` held two datasets
this way, and the corpus now holds none: `kib1-hourly-table` listed `kib1-hourly-index` in `childDataset`
while the child named `kib1-hourly-bar-graph` as its `parentDataset`, and `kib1-hr-bar-graph` listed
`kib1-hr-change-index` while the child named `kib1-hr-table`. Both frames of both files (`attributes` and
`relationshipAttributes`) cleared together.

**Reason.** The child end is `SINGLE`, so the model cannot hold a second parent, and PME-07 refuses the
second parent on every write. The import is exempt from that refusal (RPS-08), which is how the store came to
hold two edges for one dataset: the import writes both sides of every edge the bundle names. A bundle that
names an edge twice in two directions is the only way that can happen, so the fix belongs in the bundle. The
child's own value is the side the API and the editor read (DCP-04), so it is the side a reader can check.
Clearing the other keeps the stored tree equal to what a client reads back.

**Alternatives.**

- **Clear the child's own value instead.** The parent-side listing is a derived view in the editor and in the
  lineage page. Choosing it would move each dataset to a parent no picker offers on the child, and it would
  change the breadcrumb the App Search document stores.
- **Leave the corpus and let the store hold two parents.** DCP-07's rule reads the corpus, the store shows a
  dataset under two parents, and DCP-06's picker filter hides a child that a governance rule counts twice.
  It is the bug this increment exists to close.
- **Repair the store on bootstrap instead of the corpus.** The corpus is the dev store, and a bootstrap patch
  would leave every future import of the same bundle broken again.

**Effect on the parity gates.** The frozen `atlas-dev` oracle walked both sides of the edge, so two of its
documents hold the phantom. `test__app_search_indexer.py` names the two pairs it no longer derives.
`test__app_search_governance.py` counts 27 moved verdicts instead of 29, because the two siblings'
field-or-child verdicts now answer the value the oracle recorded (DV-188).
