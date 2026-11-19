# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-715. The shipped models directory holds only the Area0 model files

- **Status:** Proposed
- **Increment:** 18.1
- **Date:** 2026-11-19
- **Supersedes:** DD-032's shipped set (the vendored `addons/models` in the image). The vendoring rule itself
  stays: what remains under `models/` is still Apache Atlas 2.4.0 byte for byte, and the loader of DD-031,
  DD-033 and MDL-01 to MDL-15 is untouched.

**Decision.** The package data under `aurelius_atlas_core/models/` keeps only `0000-Area0/`: the base model,
the glossary model, and the six Area0 patches. The directories `1000-Hadoop/`, `2000-RDBMS/`, `3000-Cloud/`,
`4000-MachineLearning/`, and `5000-Couchbase/` (51 files: 20 model files and 31 patches) are deleted from
the repository (MMS-01). The `diff -r` check in the core README narrows to `0000-Area0/`. The
`BUILTIN_MODELS_DIR` constant, `load_plan`, and `ModelLoader` do not change, because they read whatever
directory they are given; a catalogue started with `AURELIUS_ATLAS_SERVER_MODELS_DIR` set to a copy of Atlas's
`addons/models` bootstraps exactly the old set (MMS-03).

**Reason.** 170 of the 207 definitions are types no Aurelius product reads or writes. The sample corpus is
entirely `m4i_*`, the three scanners emit only `m4i_*` constants, and the server, the store, the dashboards
and the webapp touch only the base model, the glossary model and the m4i types. Every catalogue and every
tenant store (ADR 063 provisions one store per organization) pays the bootstrap cost of those definitions and
then shows them in `/v2/types`, the search facets, and the type metrics to a governance user who cannot create
an entity of any of them. The five directories are one removable slice (ADR 002): nothing in `libs/` or `apps/`
imports a file from them, the production code paths that name a domain type are the ones this increment also
changes, and the test files that name `hive_table` either define their own typedefs inline or are updated with
the increment.

**Alternatives.**

- **Ship the five directories and hide them with a default-off setting.** The operator gets one more flag and
  the image keeps the dead weight; the models-directory setting already gives this door.
- **Move the five directories to a data package outside the wheel.** It meets MMS-01 for the image but keeps
  a quarter-megabyte of vendored definitions in the repository with no consumer and no test, which is the drift
  ADR 009
  refuses.
- **Delete the files and the loader's directory reading together, and hard-code the Area0 files.** It fails
  MMS-03 and rewrites ported Java behaviour (MDL-01) for no gain.

### DD-716. The replication audit keys on the entity GUID for every type

- **Status:** Proposed
- **Increment:** 18.1
- **Date:** 2026-11-19

**Decision.** `repl_key_guid` in `aurelius_atlas_core.audits_writer` returns the GUID of the first exported or
imported entity, for every type. `HIVE_DB`, `HIVE_TABLE`, `HIVE_COLUMN`, `hive_db_qualified_name`, and the
`hive_db` lookup through `EntityRetriever` and `find_by_unique_attributes` are deleted (MMS-04, DV-179). The
rest of `AuditsWriter` (the entry, the server record, the `replicatedTo`/`replicatedFrom` marking) is
unchanged.

**Reason.** Atlas's `ReplKeyGuidFinder` groups a Hive table or column under the GUID of its `hive_db` so that
a replication's details line sits under the database that Hive replicated. Aurelius Atlas does not bootstrap
Hive types (DD-715) and no Aurelius product writes them, so the lookup answers "not a Hive table" for every
entity it sees and falls through to the GUID anyway, at the price of an entity read per export. DV-128 already
declared the rest of the Hive replication machinery out of scope for the same reason. Keeping the function
would keep a live dependency on type names that are no longer in the metamodel.

**Alternatives.**

- **Keep the lookup.** It costs a read per export and keeps a coupling to types this increment deletes. It
  answers identically for every entity Aurelius can hold.
- **Make the key function pluggable, so a restored Hive model gets the grouping back.** It is an
  abstraction for one caller with no second implementation (ponytail: the smallest change that works). An
  operator who restores `addons/models` accepts the GUID keying, which the ADR 068 negative states.

### DD-717. The icon map and the process family carry metamodel types only

- **Status:** Proposed
- **Increment:** 18.1
- **Date:** 2026-11-19
- **Relates to:** LM-03 (increment 8.2, the seven-name verbatim list), DD-378 (the webapp names a type icon).

**Decision.** `TYPE_ICONS` in `apps/aurelius-atlas-webapp/src/app/search/meta/type-icons.ts` keeps its twelve
metamodel entries (`m4i_data_attribute`, `m4i_data_entity`, `m4i_data_domain`, `m4i_field`, `m4i_dataset`,
`m4i_collection`, `m4i_system`, `m4i_person`, `m4i_generic_process`, `m4i_data_quality`,
`m4i_gov_data_quality`, `m4i_source`) and loses the 24 connector and kubernetes entries (`m4i_kafka_*`,
`m4i_elastic*`, `m4i_confluent_*`, `m4i_kibana_space`, `m4i_index_pattern`, `m4i_visualization`,
`m4i_dashboard`, `m4i_connector_process`, `m4i_microservice_process`, `m4i_api_operation_process`,
`m4i_ingress_*_process`, `m4i_kubenetes_serce_process`) with the comment about the legacy's own misspellings
(MMS-05). `PROCESS_TYPES` in `apps/aurelius-atlas-lineage-model/aurelius_atlas_lineage_model/lineage.py`
becomes `{"m4i_generic_process"}`. Both files' docstrings state the rule they now hold: an Aurelius catalogue
holds no other Aurelius type, and an unknown name already answers the documented default (an icon of
`undefined`, a lineage entity row).

**Reason.** Both lists were ported verbatim from the legacy Aurelius products, and both legacy products
deprecated the connector types (ADR 058 recorded leaving them behind). In an Aurelius catalogue no entity can
carry one of those 24 type names, so the entries are unreachable data that reviewers keep re-checking for a
connector product that does not exist here. The fallback behaviour is already specified and tested: DD-378's
lookup answers `undefined` for a name the catalogue never saw, and LM-02 treats every name outside the family
as an entity.

**Alternatives.**

- **Leave the two lists alone.** They are inert, but they keep the codebase claiming the deprecated types are
  first-class, which is what the user asked to stop.
- **Derive `PROCESS_TYPES` from the loaded registry (any type that extends `Process`).** It changes tested
  LM-03 behaviour (the legacy list is the rule, DV-78's posture) and adds registry coupling to a stateless
  mapper. The metamodel has one process type, so the list is one name.

### DD-718. The sample bundles ship a typedef file of the metamodel only

- **Status:** Proposed
- **Increment:** 18.1
- **Date:** 2026-11-19
- **Relates to:** MDD-02, MDD-04 (increment 1.5b, the sample exports), IMS-03 (increment 6.3, the import
  creates no type it already holds).

**Decision.** The `atlas-typesdef.json` entry of each bundle in `data/atlas-sample/` (`small.zip`,
`sample_data.zip`, `only_gov_quality.zip`) holds only the definitions whose type the shipped bootstrap
already registers (MMS-01, MMS-02). The 43 domain definitions the legacy install exported with them — the
`hive_*`, `kafka_topic`, `avro_*`, `aws_s3_*`, `spark_ml_*` types and their structs, enums, and glossary-free
relationships — are removed from each bundle, together with nothing else: every entity entry, the export order,
and the export info stay byte-identical. The definitions that stay (60 or 61 per bundle) are kept as the export
wrote them, stored fields (`guid`, `subTypes`) included, because the import of a known type is a no-op (IMS-03)
and 1.5b's MDD-02 test reads the m4i definitions straight out of these files.

**Reason.** The demo import (`SAMPLE_ZIP=sample_data.zip` on the standalone stack, 9.5c) is the one path
that could still put domain types into a new catalogue: an import creates the types its typedef file names,
which would undo MMS-02 in exactly the flow a new user tries first, and the 1.5b acceptance test
`test__a_sample_export_imports_without_creating_a_type` fails on it once the bootstrap stops registering
them. No entity in the three bundles carries a domain type — each `typeName`, relationship target, and
classification is an m4i or base type — so the domain definitions are payload the bundles never use.

**Alternatives.**

- **Delete the `atlas-typesdef.json` entry.** The importer treats a bundle without one as defining no type
  (`ZipSource.types_def` answers the empty definition), which also works. It throws away the file 1.5b's
  MDD-02 test reads the sample definitions from, and an export of this corpus from a metamodel catalogue
  looks like this file, not like nothing.
- **Keep the domain definitions and let the demo import create them.** It violates MMS-02 at the front door
  and makes the 6.3/1.5b tests model a catalogue that cannot exist.
- **Prune the stored fields and dangling relationship attributes too.** It rewrites more fixture text than
  the rule needs: an import that finds a known type ignores the definition, and a relationship attribute
  whose target type is absent is not resolved by an import of entities (the importer validates attributes
  against the entity's own type, which the metamodel holds). Smaller diff, same behaviour (ponytail).

### DD-719. The editor's create picker lists the icon map's types

- **Status:** Proposed
- **Increment:** 18.1
- **Date:** 2026-11-19
- **Relates to:** EDT-04 and VDE-02 (the picker rule, amended in place in `7-7a` and `16-5c`), MMS-05 (the
  icon map is the metamodel's name list), ADR 068, DV-180, DD-378 (the icon map as the only place that names
  a type icon).

**Decision.** `EditorState.pickerTypes` keeps an entity typedef header only when `TYPE_ICONS` names it
(MMS-07). The icon map of MMS-05 is the filter, so the picker answers the twelve metamodel types. The
glossary and `__`-prefixed exclusions of EDT-04 stay in force (the icon map holds neither), and the order and
labels do not change (DD-379, DD-497). Edit mode is untouched, so it still renders the stored type as static
text even when a legacy entity carries a type outside the metamodel.

**Reason.** The shipped registry holds 33 entity definitions, and 21 of them are scaffolding an author does
not create: the Apache Atlas base supertypes (`Asset`, `DataSet`, `Process`, `ProcessExecution`,
`Infrastructure`, `Path`, `AtlasServer`, `ddl`, `Referenceable`) that the m4i types inherit from, plus
`m4i_referenceable`, `m4i_archimate_project` and `m4i_dq_score`. The sample corpus, which is what a new user
sees, creates entities of exactly the twelve types the icon map names. Listing the rest asks a governance
user to choose between a base type and the subtype that carries the fields, and offers a score type the
quality engine writes on its own.

**Alternatives.**

- **Leave the picker as Apache Atlas has it.** It keeps full parity with the legacy type select (DV-180 goes
  away), but it keeps the choice the user reported as wrong. A picker is an authoring surface, and the
  product's own authoring list is the icon map.
- **Filter on the `m4i_` prefix.** It drops the base supertypes, but it keeps the three m4i types an author
  also cannot create (`m4i_referenceable`, `m4i_archimate_project`, `m4i_dq_score`). The icon map is already
  the narrower and tested list (MMS-05), so it answers the same question without a new name list.
- **Derive the list from the loaded registry** (every type with a registered subtype chain, or every type not
  named in `superTypes`). A connector that ships its own models directory (ADR 068's follow-up) would land in
  the picker again, and the webapp would need a registry query the picker does not make today. The icon map
  names the types the webapp can draw an icon for, which is the screen's real boundary.

### DD-720. The ArchiMate scaffold leaves the m4i data dictionary

- **Status:** Proposed
- **Increment:** 18.1
- **Date:** 2026-11-19
- **Relates to:** MMS-01, MMS-02, MMS-06, MMS-08 (here), MDD-02 (increment 1.5b, the model equals the sample
  exports), DD-718 (the sample bundles ship a metamodel-only typedef file), ADR 068 (a catalogue bootstraps
  only the metamodel it serves), ADR 058 (the m4i types ship).

**Decision.** The m4i data dictionary carries no ArchiMate type. The `m4i_archimate_project` entity
definition, its `archimateReference` attribute on `m4i_referenceable` (`array<m4i_archimate_project>`), and
the `m4i_referenceable_archimate_reference_assignment` relationship definition leave
`m4i_models/0010-m4i_data_dictionary_model.json`, and the same three definitions leave the
`atlas-typesdef.json` of each bundle in `data/atlas-sample/` (MMS-06, DD-718). The dictionary and the bundles
stay otherwise as they were: 13 entity, 19 relationship, and 5 classification definitions, byte-identical
elsewhere (MDD-02).

**Reason.** This is the same dead weight ADR 068 removes elsewhere, and the same one that made the picker
wrong (DD-719). `m4i_archimate_project` is a scaffold no Aurelius product writes — the sample corpus holds
no entity of it, and the archimate3 lineage models are built on the fly, not stored — yet because
`m4i_referenceable` is the supertype of `m4i_dataset`, `m4i_collection`, `m4i_field` and the rest, every
author-able type inherits the `archimateReference` attribute and its relationship. The webapp editor renders
a type's relationship attributes, so the create form for any m4i type offered an "ArchiMate Reference" picker
pointing at a type the catalogue cannot hold entities of. The sample bundles carry the same three definitions
in their typedef file, so the demo import (DD-718) would recreate them and undo the removal — the bundles are
cleaned for the same reason 18.1 already cleans their domain types.

**Alternatives.**

- **Hide it in the webapp.** Filter the attribute out of the editor like `property-filter.ts` hides the
  details-table key. It leaves the dead type in every catalogue and every tenant store, in the type listings
  and the search facets, which is what ADR 068 exists to stop; and the picker fix (DD-719) only hid the type,
  not the inherited attribute. The removal is at the source.
- **Keep the relationship, drop only the type.** It leaves `m4i_referenceable` with a `archimateReference`
  attribute and a relationship definition whose end names a type that no longer loads — a metamodel that does
  not resolve against itself. The whole construct leaves, or none of it.
- **Leave the stored `relationshipAttributeDefs` in the sample typedef files.** The registry derives those
  from the relationship definitions and overwrites them on load (THY-11), and MDD-02 reads the definitions
  with the stored fields stripped, so the stale copies are inert. Pruning them rewrites fixture text the rule
  does not need, the same call DD-718 makes for the same reason.
