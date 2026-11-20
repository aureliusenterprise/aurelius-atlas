# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-744. The parent choice is a constraint on the relationship end definition

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** DD-740 (the `SINGLE` child end builds the attribute), HCA-02, PME-01.

**Decision.** `AtlasRelationshipEndDef` gains an optional `constraints` list in the same shape an attribute
definition already uses (PME-01). The m4i model states the parent choice as one constraint on each child
end: `{"type": "mutuallyExclusive", "params": {"group": "m4i_data_entity_parent"}}` on
`m4i_data_entity_assignment.endDef2` (`dataDomain`) and `m4i_parent_entity_assignment.endDef1`
(`parentEntity`), and the same shape with the group `m4i_field_parent` on `m4i_field_assignment.endDef2`
(`datasets`) and `m4i_field_parent_assignment.endDef1` (`parentField`). The type system rejects the
constraint on a container end.

**Reason.** The rule belongs to the child end, because that is the end that names the parent, and the
constraint type already exists on the other typedef element. `AtlasConstraintDef` is the ported shape Atlas
uses for `ownedRef` and `inverseRef` on an attribute (`typedef.py`, `CONSTRAINT_TYPE_OWNED_REF`), so the
model, the JSON wire format, and the read path all carry it without a new container. The child attribute
cannot hold the rule directly in the source model: the m4i child types declare no attribute for their parent
at all (HCA-02), so the registry builds it. `relationshipAttributeDefs` is output-only, because the typedef
store nulls it on write and the type rebuilds it on read, so a declaration there does not survive a save.
The end def is the one place that both survives the store and reaches the built attribute.

**Alternatives.**

- **A plain list of sibling attribute names on each child attribute definition.** The m4i model has no child
  attribute definitions to put it on, so this needs a new field on the entity definition and a second copy
  of the rule per type.
- **A field on the entity definition naming the mutually exclusive relationship names.** It sits away from
  the ends it constrains, so an end that moves to another relationship leaves a stale entry behind. Nothing
  checks the pair.
- **Enforce the rule in the webapp only.** The server accepts both parents, so any API client or import
  creates a two-parent entity. Increment 12.7's governance banner then reports a shape the model does not
  allow.

### DD-745. The registry copies the end's constraints onto the attribute it builds

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** DD-744, HCA-03, PME-02, PME-05.

**Decision.** `RelationshipType._add_to_end` passes `end.constraints` to the `AtlasAttributeDef` it builds
for a child end that has no entity-declared attribute (PME-02). An entity-declared attribute keeps its own
constraints, and the copy does not merge the two lists. The built attribute reaches
`relationshipAttributeDefs` through the existing write-back, so a client reads the rule from the end def or
from the attribute (PME-05).

**Reason.** `_add_to_end` already builds the child attribute and already decides `is_optional` and
`cardinality` from the end def, so the end's constraints are one more end fact to carry. Today only a
composition container end gets a constraint (the built-in `ownedRef`). Copying the end list makes the
generic case follow the same path rather than adding a parallel one. The write-back in
`EntityType._write_back` dumps each built attribute as it stands, so the constraint reaches the API with no
change to the read path.

**Alternatives.**

- **Merge the end constraints with an entity-declared attribute's list.** A merged list cannot say which
  constraint wins, and the case does not arise in the shipped model, where no child declares a parent
  attribute. It is more machinery than the increment needs.
- **Read the end def at validation time instead of copying.** The write path works on attributes, and a
  check there needs the registry's relationship index for every save. The copy keeps one source of truth in
  the built attribute.

### DD-746. One constraint names a group, and both ends of the group carry the same name

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** DD-744, PME-03, PME-04.

**Decision.** The constraint's single parameter is `group`, and the group holds the attributes that exclude
each other. Both ends of one parent choice name the same group id, so
`m4i_data_entity.dataDomain` and `m4i_data_entity.parentEntity` both carry
`"group": "m4i_data_entity_parent"`. The write check collects the filled attributes of the saved entity's
type per group and reports one error per group with more than one filled member. A group that names only one
attribute of a type enforces nothing (PME-03).

**Reason.** A shared group id states the rule once per pair, so adding a third parent to a type means one
new end def with the existing group name rather than edits to two sibling lists. It also matches how the
ported code reads the shipped `ownedRef` constraint: a constraint names itself, and the parameter holds the
target. Per-attribute sibling lists need every member to list the others, and a list that misses one member
silently stops enforcing that pair.

**Alternatives.**

- **An `exclusiveWith` parameter naming the sibling attribute on each end.** It needs a symmetric-pair check
  at registration, since a one-sided entry is a silent hole. The pair check is code that the group id does
  not need.
- **A named top-level section of the model, like an Atlas `businessMetadataDefs` block.** The rule then
  lives outside the types that use it, and the type read path needs a join to serve PME-05.

### DD-747. The write check reads the request values and the stored active edges

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** PME-07, PME-08, PME-09, HCA-04, EWR-07 (the check and normalise step a save runs through).

**Decision.** `EntityDiscovery.validate_and_normalize` gains the group check. For each group of the saved
entity's type it treats an attribute as filled when the request body names it with a value or the stored
entity holds an active edge on it, and it raises `AtlasError(INSTANCE_CRUD_INVALID_PARAMS)` when two are
filled. The check runs on the create path and on the full and partial update paths with the same rule
(PME-07, PME-08). A save with at most one filled member passes unchanged (PME-09).

**Reason.** A partial update names one parent and omits the other, so a request-only check lets an entity
that already holds a data domain gain a parent entity. `_prepare` already loads the stored entity before
validation, so the stored side costs no extra read. An edge read over the stored entity, not the stored
attribute value, is what HCA-04 makes authoritative: the single-end write path replaces the edge, so the
edge is the parent. The active-state filter matters because a cleared parent leaves its last edge in the
graph as `DELETED` for the timeline, and that edge must not count as a filled parent. One error code covers
it because both parent attributes are ordinary optional relationship attributes, and
`INSTANCE_CRUD_INVALID_PARAMS` is the code the attribute checks already raise for a bad value.

**Alternatives.**

- **Reject the second parent in the relationship create endpoint instead.** The editor and the import path
  set the parent through the entity body, not the relationship endpoint, so this misses the common case. It
  also needs the same stored-edge lookup in a second place.
- **Auto-clear the other parent on a save.** A silent write deletes a parent the author did not name. Atlas
  returns an error for a conflicting attribute value, and a rejected save is easier to reason about than a
  side-effect write.
- **Reject at the graph layer when a second ACTIVE edge appears.** The graph has no type knowledge, and the
  entity write path already orders validation before any graph write, so a graph check runs later and
  cannot return the attribute names the author must fix.

### DD-748. The constraint goes in at type version 1.2 and needs no migration

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** DD-744, DD-742 (18.2 went to `1.1` with a bump and no migration), ADR 058, MDL-02, PME-04,
  PME-06.

**Decision.** The four m4i relationship definitions that carry the new end constraints go to type version
`1.2` (PME-04). The other twelve m4i types keep `1.1`. The bundle loader applies `1.2` over a store at `1.1`
through the ordinary typedef update check, and the shipped sample bundles are regenerated with the
constraints in their `atlas-typesdef.json`. No migration runs, and no stored entity changes (PME-06).

**Reason.** The update check passes the change. `_check_relationship_update` compares the ends on type,
name, container flag and cardinality only, so a new constraint on an end is not a change to an end, and the
attribute check blocks only a retype or a new mandatory attribute. Adding constraints therefore reaches an
existing store as a plain metadata update. ADR 058 versions the m4i dictionary with the server, so a
content change bumps the version, and only the four definitions whose content changes get `1.2`. Regenerating
the bundles keeps `test__m4i_models.py`'s equality check between the model file and each bundle's typedef
file green.

**Alternatives.**

- **Bump every m4i type to `1.2`.** It marks twelve types with a version change they do not carry, which
  makes the version useless as a signal of what changed.
- **Keep `1.1`.** ADR 058 ties the version to the content, and a store that already holds the unconstrained
  `1.1` definitions then holds a definition the server no longer ships.
- **Declare the change breaking, as 18.2 did for `SINGLE` (HCA-10, DD-742).** It is not breaking in the
  sense 18.2 meant. 18.2 changes the wire shape of an attribute from a list to an object, which a stored
  entity can contradict. This increment adds a validation no stored sample violates. A probe over
  `data/atlas-sample/` found no entity that fills both parents of its type: of 16 data entities, 13 hold a
  data domain, 2 hold a parent entity, and 1 holds neither. Of 264 fields, 248 hold a dataset and 16 hold a
  parent field. A store that did hold such an entity keeps it readable, and only a later save to that pair
  fails.

### DD-749. The editor disables the sibling picker of a parent group

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** DD-745 (the registry copies the group onto the child attribute), DD-713 (`TokenPicker`,
  UIC-44), PME-05, PME-10, EDT-17.

**Decision.** The editor reads each parent group off the entity's relationship attribute definitions
(PME-05), and disables every picker in a group that holds no pick while a sibling holds one (PME-10). A
disabled picker keeps its chip deletable, starts no search, drops its placeholder, and never blocks the
save, so a mandatory sibling cannot hold the author. The webapp ships no new sentence for the rule, so the
disabled box and the delete affordance on the chip carry it. `TokenPicker` gains a `disabled` input for
the look and the closed panel (UIC-44 amended).

**Reason.** PME-07 refuses the pair at the server, but the author learns that only after a save. Disabling
the sibling states the rule at the control, which is what the user asked for: "it should be impossible to
select both a parent entity and a parent domain". The alternative affordance was a hint sentence under the
pickers. The webapp's i18n completeness gate (SHL-08) allows no string outside the vendored legacy
catalogue, and inventing one is against the porting rule, so the hint is out of scope. Reversal stays one
click: delete the chip, and both pickers answer again. The picker cannot be cleared from the keyboard
while the sibling is disabled, so the chip's delete button is the escape and stays live on purpose.

**Alternatives.**

- **Show a hint sentence under both pickers.** It needs a new UI string, which the completeness spec
  rejects, and it leaves the author able to make the mistake.
- **Hide the sibling picker.** The author then cannot see the other choice, and cannot tell whether the
  field is missing from the type or already answered.
- **Validate on save and point at both fields.** This keeps the mistake possible, and PME-07 already does
  it as the last line of defence for every client.
- **Enable the sibling and clear the first pick on select.** A silent write deletes a parent the author did
  not name, which DD-747 already rejects for the server.

### DD-750. The corpus words its parent rules for one parent of each kind

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** DD-637 (12.7c made this rule a pair), DD-635, PME-11, HCA-02, DV-184.

**Decision.** The sample corpus states the data-entity parent rule as one data domain or parent entity, in
its name, its description and both messages (PME-11). The rule's qualified name, its expression, its
dimension and its verdicts do not change. The `--source` companion record of `sample_data.zip` carries the
same three sentences, so a rule page names one thing. A rule over a SET attribute keeps the "at least one"
wording, because there the count still means something.

**Reason.** 18.2 made `dataDomain` and `parentEntity` both `SINGLE`, so "at least one data domain or data
entity" describes a set the type no longer holds, and the details page banner prints that sentence today.
A user read it and asked for the plain form. The messages are corpus data, not code: no production string
changes, and `aurelius_atlas_quality.governance` keeps printing whatever the rule stores (GQ-06). Only
the two rule records of `sample_data.zip` and one of `only_gov_quality.zip` change. The `--source` record
of `only_gov_quality.zip` is a different rule that reuses the GUID, so it keeps its own sentence. An audit
of all 95 governance rules of the corpus found no other rule whose wording contradicts a cardinality: the
other hierarchy rules measure SET attributes, and the rest already read singular.

**Alternatives.**

- **Leave the corpus alone and rewrite the banner text in the webapp.** The banner prints what the rule
  stores, and rewriting it in code would split the rule's own sentence from the rule page that shows the
  stored text (EDT-24).
- **Edit the frozen oracle fixtures too.** They are recordings of the legacy product (ADR 060). Editing a
  recording destroys the evidence, so the gates count the difference instead, as DV-171, DV-172 and DV-174
  do for the five earlier rule edits.
- **Retire the rule and ship a new one.** A new GUID strands every stored verdict and every saved report
  that names the old rule, for no gain over an edit to the sentences.

### DD-751. The corpus words every governance rule sentence in plain English

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** DD-750, PME-11, PME-12, GQ-06.

**Decision.** The sample corpus words each governance rule sentence in plain English (PME-12). A bare
camel-case field name in a description or a message becomes its words, with the article and the number to
match the reading, so `parentDataset` reads "parent dataset" and `kafkaClusters` reads "Kafka clusters".
A quoted Atlas type name keeps its spelling, because it names a type and not a field, so
`m4i_indexPattern` stays. The qualified name, the expression, the dimension and the verdicts do not change.

**Reason.** The banner and the rule page print what the rule stores, and `aurelius_atlas_quality.governance`
passes it through untouched (GQ-06), so a reader sees `This entity is missing a parentDataset` on a details
page today. The field name is developer-speak, and the reader asked for the plain form. The change is data
in the two rule bundles of `data/atlas-sample/`, with no code and no wire change. The frozen `atlas-dev`
oracle is untouched, because none of its 27 governance rules carries a camel-case sentence, so its four
text counters hold and no deviation record joins this increment.

**Alternatives.**

- **Rewrite the banner text in the webapp.** The banner prints what the rule stores, and rewriting it in
  code splits the shown sentence from the rule page that shows the stored text (EDT-24). It also needs a
  name-to-phrase table to maintain in a second place.
- **Split the camel case mechanically, grammar unchanged.** A bare split is not enough. It leaves a broken
  article on `Elasticsearch cluster` and turns the predicate `hasContent` into the words "has content"
  inside a sentence that already has a verb. The reader asked for plain English, so those sentences get
  fixed where a split falls short.
- **Change the rule's qualified name or attribute too.** The qualified name drives the rule-to-type join
  (VEV-07) and `atlas-export-order.json` names the GUIDs, so a rename breaks the walk and the import. Only
  the three printed fields change.

### DD-752. The corpus ships only governance rules the m4i model can answer

- **Status:** Proposed
- **Increment:** 18.3
- **Date:** 2026-11-20
- **Relates to:** DD-750, DD-751, ADR 058 (the m4i types ship with the server), ADR 060 (a frozen oracle is
  never edited), PME-13, DV-185, DV-173.

**Decision.** The sample corpus deletes the 29 governance rules whose expression names a type, attribute or
relationship the m4i model does not define (PME-13). The rule records go, from `sample_data.zip` and from
`only_gov_quality.zip`, and their GUIDs leave each bundle's `atlas-export-order.json`. The corpus ships 66
rules after the pass, down from 95. A rule that names a missing type, a missing attribute, or a missing
relationship definition is dead, so `test__m4i_models.py` rejects any bundle that carries one.

**Reason.** The corpus carried these rules in from the legacy product, whose metamodel had types the m4i data
dictionary does not define, such as `m4i_elastic_field`, a `kibanaSpace` attribute, or a
`m4i_system_assignment` relationship. Each dead rule stamps a noncompliant verdict on every entity of its
type forever, so the quality banner reports a permanent failure for a property no entity can hold. 15 of
the 29 read today and hold 245 of those always-false verdicts. The frozen `atlas-dev` oracle records a
document for every one of the 95 rules, so five gates of series 14.6 now drop the 29 GUIDs from the oracle
side. One shared list in `test__app_search_engine.py` names them, because all five gates read the same
recording. The oracle's governance verdict fixture covers 27 rules, none of them in the 29, so the verdict
comparison keeps its kept, moved and lost counts untouched.

**Alternatives.**

- **Retire the rules with `active` false.** 12.7b and 12.7d retired two rules that way, and DV-173 counts
  that damage. Rejected here because the name the rule points at no longer exists, so no data change revives
  the rule. A retired record still ships in every bundle, still loads into every tenant catalogue, and still
  prints a dead row on the rules page.
- **Add the 13 missing types and attributes to the model.** They left the m4i data dictionary on purpose, and
  the model scope recorded that (increment 18.1). Restoring them to rescue 29 always-false rules lets the
  rules drive the model.
- **Keep the rules and accept the failures.** Every entity of the type keeps a noncompliant verdict for as
  long as the corpus ships. A score that can never reach its target tells the reader nothing.
- **Edit the frozen oracle fixtures too.** They record the legacy product (ADR 060), so the gates subtract
  the 29 GUIDs instead, as DV-173 does for its two inactive rules.
