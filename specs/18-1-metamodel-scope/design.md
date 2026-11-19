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
`4000-MachineLearning/`, and `5000-Couchbase/` (196 files: 19 model files, 31 patches, and their folders) are
deleted from the repository (MMS-01). The `diff -r` check in the core README narrows to `0000-Area0/`. The
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
  390 KB of vendored definitions in the repository with no consumer and no test, which is the drift ADR 009
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
