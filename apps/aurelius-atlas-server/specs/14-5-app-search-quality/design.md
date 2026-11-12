# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-528. A quality result is kept on its score entity, one per rule and dataset

- **Status:** Proposed
- **Increment:** 14.5
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** Each score entity holds its quality result, under `qualityResult` on its entity document: the
fields of `atlas-dev-quality`, read from the score, its rule, the rule's fields in the scored dataset and their
documents. The result's `id` is the score entity's GUID, and `fieldguid` and `fieldqualifiedname` list every
field of the rule in that dataset. `name` is the rule's name, `businessruleid` its `id` attribute, and
`datadomainname` the data domain above the fields' data attributes.

**Reason.** The scanner scores a rule over a dataset and keeps the newest score per pair (DD-456). The webapp
asks the engine for a field's results by `fieldguid`, and a list matches a field as one value does. A rule over
two datasets has two scores, so the rule's qualified name, the legacy `id`, no longer names one result. The
legacy `name`, `businessruleid` and `datadomainname` came from a source the catalogue does not hold (DD-485):
of 42 legacy results, 41 are named `Rule <businessruleid>`, and the identifier matches the rule's `id` in 24.

**Alternatives.**

- A result per rule and field: a score entity would hold several documents, and the index has one per entity.
- A document of its own per result, in another index: a second index to keep in step with the entities.

**Consequences.** A webapp that reads a result's `id` as a rule's qualified name reads a GUID (DV-159). The
webapp's field page reads `guid`, never `id`.

### DD-529. The results and totals are derived again in full each round

- **Status:** Proposed
- **Increment:** 14.5
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** After the documents, each round of the App Search worker lists every score and every entity
holding a result or totals, reads the rules, their fields and the documents the roll-up passes through, and
derives every result and every total from them. An entity whose result or totals differ from what it holds is
read again and written with them on the version read; one that holds them and no longer has any is written
without. The totals are kept under `qualityTotals` on the entity document, beside `appSearch` and outside its
source hash.

**Reason.** A score reaches its field, the field's data attributes and every entity of both breadcrumbs, and a
moved field, a renamed rule or a deleted score changes them all. Following each change as 14.3 does would need
a cascade of its own for every input. The scores are one per rule and dataset, far fewer than the entities, and
the documents they pass through are read by GUID. A round derived from what is stored corrects whatever an
earlier round missed. Kept out of `appSearch`, the totals do not make the document stale, and the indexer's
writes keep them.

**Alternatives.**

- Updating the totals by the difference a score makes: a lost write would leave them wrong for good.
- The roll-up at search time: a sort or filter on a score field needs it stored.

**Consequences.** A round reads every score, so its cost grows with the scores. A change shows in the totals one
round after the documents it passes through are current.

### DD-530. A document without totals answers zero

- **Status:** Proposed
- **Increment:** 14.5
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** Only an entity that a result reaches holds totals. The engine's number fields read from the index
carry a value for when the index holds none: `0` for the score fields. A filter or range that holds 0 also
matches the documents without the field, a sort puts them where 0 sorts, and a facet counts them as 0.

**Reason.** Most entities have no score, and `atlas-dev` held 23 zeros and five empty lists for each of them.
Storing them would add 28 fields to every entity document, which DD-498 kept to what the catalogue derives.
Elasticsearch's `missing` in sorts and `terms` aggregations answers them as 0 without storing them.

**Alternatives.**

- Zero totals on every document: a write of every entity when the roll-up starts, and on every new entity.

**Consequences.** The score fields answer as `atlas-dev` did for every document, with or without a score.

### DD-531. An engine is its documents and its fields

- **Status:** Proposed
- **Increment:** 14.5
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** `atlas-dev` and `atlas-dev-quality` are each a name, the filter of the entity documents it holds,
and the table of its fields (DD-523). The request's checks, its translation into one search, and the answer are
shared, and read the engine's table.

**Reason.** The two engines answer the same Search API, and differ only in what they hold. 14.6 adds the third
the same way.

**Alternatives.**

- A module per engine: the checks and translation of ASE-04 to ASE-11 written twice.

**Consequences.** A fix to the Search API's handling reaches every engine at once.

### DD-532. Only a scored rule's result counts

- **Status:** Proposed
- **Increment:** 14.5
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A score with the ERROR verdict, a dataset's `overall` summary, and a score whose rule is deleted
or has `active` set to `false` have no result. A result whose dimension is not one of the five is answered by
`atlas-dev-quality` and adds to no total.

**Reason.** An ERROR has no score (DQS-08). The summary scores a dataset, not a rule, and `atlas-dev` sums the
rules' results itself. The scanner scores only active rules (DQS-02), so a deactivated rule's last score would
otherwise stay in the totals for good. `atlas-dev` has score fields for the five dimensions only.

**Alternatives.**

- Keeping a deactivated rule's last score: totals that no scan can change.

**Consequences.** Deactivating a rule takes its result and its share of the totals away in the next round. In
the legacy results, one rule that is not active had a result.
