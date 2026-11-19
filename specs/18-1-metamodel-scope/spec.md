# 18.1 Bootstrap only the metamodel the system serves

- **Status:** in progress
- **Pull request:** –
- **Records:** ADR 068, DD-715 to DD-719 (here), DV-178, DV-179; relies on
  [ADR 058](../../docs/architecture/adr/058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types.md)
  (the m4i types ship), increment 1.5 (MDL, the loader), increment 6.3c2 (REP, the audits writer), and
  increment 8.2 (LM-03, the lineage process family).

## Scope

The server loads its types at start-up from two shipped directories: the vendored `addons/models` of Apache
Atlas 2.4.0 (207 definitions, [DD-032](../../libs/python/aurelius-atlas-core/specs/1-5-builtin-models/design.md#dd-032-the-built-in-models-are-vendored-unchanged-and-read-from-a-directory))
and the Aurelius m4i data dictionary (ADR 058). 170 of the 207 describe systems no Aurelius product reads or
writes: Hive, HBase, Kafka, Sqoop, Falcon, Avro, Storm, Impala, Spark, FS paths, RDBMS, S3, ADLS, Ozone, GCP,
machine learning, and Couchbase. The sample corpus, the three scanners, and every Aurelius screen use only
the base model, the glossary model, and the m4i types. The connector and kubernetes types went further: the
legacy deprecated them, and ADR 058 left them with the legacy products, but two ports still name them verbatim
(the webapp's icon map, the lineage model's process family).

This increment shrinks the shipped bootstrap to what the system serves, and removes the two leftover name
lists.

It delivers:

- A bootstrap of the metamodel only. The shipped models directory holds `0000-Area0` (base model, glossary
  model, and their patches) and nothing else, and the m4i directory stays as it is (MMS-01, MMS-02).
- The domain models out of the image. The five directories `1000-Hadoop`, `2000-RDBMS`, `3000-Cloud`,
  `4000-MachineLearning`, and `5000-Couchbase` and their 31 patch files are deleted (MMS-01).
- The override door kept. `AURELIUS_ATLAS_SERVER_MODELS_DIR` still points the loader at any directory, so an
  operator who restores a copy of `addons/models` gets the old behaviour unchanged (MMS-03, MDL rules).
- A replication audit keyed by GUID. The Hive database lookup in the audits writer is deleted; every type
  keys on its own GUID (MMS-04, DV-179).
- The connector names gone from the screens. The webapp's icon map keeps only the types of the metamodel, and
  the lineage model's process family keeps the one process type of the metamodel (MMS-05).

It does not deliver, with the increment that will:

| Not delivered                                         | Lands with           |
| ----------------------------------------------------- | -------------------- |
| Deleting domain types an existing store already holds | not planned (MMS-02) |
| A connector shipping its own models directory         | its own increment    |
| Re-baselining parity fixtures over a domain model     | not planned          |

## Semantics

The "metamodel" is the set of types in `models/0000-Area0` (the Atlas base model and glossary model, with
their patches) plus everything in `m4i_models` (ADR 058). The "domain models" are the type and patch files of
the five deleted directories. The "icon map" is `apps/aurelius-atlas-webapp/src/app/search/meta/type-icons.ts`
(DD-378). The "process family" is `PROCESS_TYPES` in the lineage model (LM-03).

| Id     | Rule                                                                                                                                                                                                                                          |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MMS-01 | The shipped bootstrap contains only the files of `models/0000-Area0` and `m4i_models`. No file under the core package defines a domain type.                                                                                                  |
| MMS-02 | A new catalogue loads the metamodel and no domain type: its registry holds `hive_table` under no name, and holds `Referenceable`, `AtlasGlossary`, and `m4i_dataset`. Types an existing store already holds are not removed by the bootstrap. |
| MMS-03 | Pointing `AURELIUS_ATLAS_SERVER_MODELS_DIR` at a directory with copies of the deleted files loads them exactly as increment 1.5 does (MDL-01 to MDL-15 unchanged).                                                                            |
| MMS-04 | A replication audit keys its server details on the entity's own GUID for every type (DV-179). The Hive database grouping is gone.                                                                                                             |
| MMS-05 | The icon map and the process family name no connector or kubernetes type: an icon entry or a process name is one of the metamodel's. An unknown type name still renders the default icon (DD-378) and, in lineage, an entity row.             |

## Java origin

- `AtlasTypeDefStoreInitializer` (which files it loads) — increment 1.5, `aurelius_atlas_core.model_loader`.
  The loader itself is unchanged; only the shipped directory's contents differ.
- `AuditsWriter.ReplKeyGuidFinder` (the Hive database grouping) — increment 6.3c2,
  `aurelius_atlas_core.audits_writer`.
- The legacy Aurelius dashboard's `iconsByType` map and `lineage_model.py`'s `process_types` — the verbatim
  ports of increments 7.x and 8.2, now narrowed to the metamodel.

## Deviations

- DV-178: A new catalogue bootstraps the base model, the glossary model, and the m4i types, and none of the
  other Apache Atlas domain models (ADR 068). Apache Atlas bootstraps all of `addons/models`.
- DV-179: A replication audit keys its details on the entity GUID for every type. Apache Atlas groups a Hive
  table or column under the GUID of its `hive_db`.

## Acceptance

- Unit: `libs/python/aurelius-atlas-core/tests/test__model_loader.py` (MMS-01, MMS-02, MMS-03 with a restored
  directory fixture), `tests/test__replication_audits.py` (MMS-04),
  `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_typedefs.py` (MMS-02),
  `apps/aurelius-atlas-lineage-model/tests/test__lineage.py` and `test__aurelius_atlas_lineage_model_app.py`
  (MMS-05), `apps/aurelius-atlas-webapp/src/app/search/meta/type-icons.spec.ts` (MMS-05, Vitest).
- E2E: `nx e2e aurelius-atlas-core` (the typedef store bootstraps the metamodel on a real store) and
  `nx e2e aurelius-atlas-server`.
- Parity: unchanged. No scenario fixture under `apps/*/scenarios` names a domain type (checked 2026-11-19);
  the legacy `atlas-dev` app-search fixtures name connector types and stay as read-only evidence (14.1).
