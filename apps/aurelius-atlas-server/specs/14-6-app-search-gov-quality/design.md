# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-533. A governance rule's legacy expression reads in the corpus's two forms

- **Status:** Proposed
- **Increment:** 14.6
- **Date:** 2026-11-12
- **Supersedes:** none; amends GQ-07 of 12.6 (DD-487 to DD-490, Proposed)

**Decision.** `rule_from_gov_attributes` reads a rule without `dqcheckkind` from its `expression` when the
expression is one part, or several joined by `|`, each `completeness('<name>')` or each `length('<name>', 1)`:
`ATTRIBUTE_PRESENT` for the first form, `ATTRIBUTE_NOT_EMPTY` for the second, the first part's name the rule's
attribute and the others' its `anyOf`. A regular expression matches the whole text; nothing is evaluated. Any
other expression, a mix of the two forms among them, raises `QualityRuleError` as before. A rule with
`dqcheckkind` reads as before, its expression ignored.

**Reason.** Every governance rule of the sample catalogue is a stored expression: 48 of its 95 have one of the
two forms (47 read; one names no dimension), the forms the legacy definitions shipped and 12.6's vocabulary
restates (DD-488). Unread, they would leave `atlas-dev-gov-quality` empty on every catalogue imported from the
legacy product until each rule is written again. Matching a closed grammar is reading data, as DV-146's four
legacy pairs of the quality rules are: the forms map to the vocabulary's kinds, and no string reaches an
evaluator.

**Alternatives.**

- The vocabulary rules only (GQ-07 unchanged): the engine empty on the sample.
- A data patch that writes `dqcheckkind`, `dqattribute` and `dqanyOf` onto the stored rules once: it changes
  stored entities, with audit events, and a rule imported later still needs the editor.

**Consequences.** 12.7's `validate-entity` and the 7.29 governance box judge these rules too. `unreadRules`
keeps 48 of the sample: 46 `conditional_value(...)`, one `uniqueness(...)`, and `m4i_system--kafkaClusters`,
whose `qualityDimension` `clusters` is no dimension (GQ-02). `length('<name>', <n>)` with another `n` stays
unread.

### DD-534. A verdict is a document of its own, in the verdicts' index

- **Status:** Proposed
- **Increment:** 14.6
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** Each verdict is a document of `<prefix>-gov-quality` with `_id` `<entity GUID>--<rule GUID>` and
the engine's fields as its source. `Engine` (DD-531) gains the index it searches: the entity index for
`atlas-dev` and `atlas-dev-quality`, the verdicts' index for `atlas-dev-gov-quality`, whose filter holds every
document.

**Reason.** An entity has a verdict for each rule of its type, and the engine pages, filters, facets and sorts
the verdicts themselves: the webapp asks for a rule's met entities, 1,000 at a time. Elasticsearch searches
documents, not the objects nested in one, so a verdict needs a document. 14.5 rejected an index of its own
because a score holds one result (DD-528); an entity holds many verdicts.

**Alternatives.**

- The verdicts nested in the entity document: a page of verdicts across entities is not a search Elasticsearch
  answers.
- The verdicts as linked documents of the entity (DD-061): a linked kind is a catalogue instance with a type,
  which a type's use counts (DD-048).

**Consequences.** The verdicts' index is created with the entity index and mapped from the engine's fields:
keywords, with a text subfield for the query.

### DD-535. An entity is judged again when its document or its type's rules change

- **Status:** Proposed
- **Increment:** 14.6
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A round reads every governance rule and digests, per type, its readable active rules: what they
check and the fields their verdicts copy. An entity judged holds that digest under `appSearch.governedBy`, the
hash of what its verdicts read (its type, state, attributes and relationship GUIDs) under
`appSearch.governedSource`, and `governed: true` beside `appSearch` while it has verdicts. An entity write
whose hash differs drops both marks, as it marks a document stale (DD-518); a document the indexer derives
again has none, and the indexer compares documents without them. A round lists, a page at a time, the active
entities with a document of a type with rules whose document holds another digest or none, and the governed
entities no longer judged: deleted, without a document, or of a type without rules. It writes each one's
verdicts in place of those it had, then the entity with its marks, or without them, on the version read; one
changed in between waits for the next round. A purge deletes the purged entities' verdicts with them.

**Reason.** A verdict reads its entity's attributes and relationships. The document's source hash covers only
the attributes the document shows (DD-499), so the marks carry a hash of their own; a relationship deleted
leaves the entity as it was, but the indexer derives its ends' documents again (DD-520). A rule's change
changes its type's digest. So each cause leaves an entity without its type's digest, which a term query finds,
and a round reads only the entities that changed. Unlike 14.5's scores (DD-529), the verdicts are as many as
the entities of the governed types, too many to derive in full every round.

**Alternatives.**

- Every governed entity judged every round, as DD-529: work in proportion to the catalogue each round.
- The indexer judging the entity as it derives its document: a rule's change still needs a round of its own.

**Consequences.** A verdict is as current as the document it was judged with; an entity whose document is
stale waits for the indexer. A deleted entity's verdicts go once the indexer has taken its document away.

### DD-536. A rule reads a relationship attribute as the entity's read answers it

- **Status:** Proposed
- **Increment:** 14.6
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A name the entity's type has as a relationship attribute reads the other ends of the entity's
active relationships of that attribute: a list of object ids for a set or list end, one object id or none for
a single end. Any other name reads the entity's attribute. The relationship ends come from the type registry,
as the entity read's do.

**Reason.** 16 of the 47 rules of the sample that read check a relationship (`length('datasets', 1)`), and
since DD-064 a legacy end given among the attributes is stored as a relationship. The legacy job judged the
entity as Atlas's read answers it, `relationshipAttributes` included, and the same reading gives each of the
1,612 legacy verdicts of a read rule back.

**Alternatives.**

- The attributes only: every relationship rule missed by every entity.

**Consequences.** A deleted relationship no longer meets a rule; its ends' documents are derived again
(ASU-04), and with them their verdicts.

### DD-537. The core reads and judges the rules through `aurelius-atlas-quality`

- **Status:** Proposed
- **Increment:** 14.6
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** `aurelius-atlas-core` depends on `aurelius-atlas-quality`, and the governance round reads each
rule with `rule_from_gov_attributes` and judges it with `evaluate_gov_entity`.

**Reason.** One parse door for a rule (GQ-02): the editor's validation (12.5), the draft's verdicts (12.7),
the box (7.29) and the engine agree on what a rule is and what it answers. The round belongs beside 14.5's, in
the core; the server already depends on the library.

**Alternatives.**

- A copy of the two checks in the core: two readings of one rule to keep in step.
- The round in the server: the App Search rounds split across two projects.

**Consequences.** The core's environment installs polars, which the library's dataset half imports.
