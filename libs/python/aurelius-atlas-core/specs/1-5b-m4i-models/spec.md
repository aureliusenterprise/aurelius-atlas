# 1.5b The m4i data dictionary types

- **Status:** in review
- **Pull request:** [#274](https://github.com/aureliusenterprise/aurelius-atlas/pull/274)
- **Records:** ADR 058, DD-362, DV-139; relies on DD-032 (the built-in models vendored unchanged), DD-033 (one
  change per model file) and DD-316 (the start's typedef audits held to one write)

A new catalogue holds the m4i data dictionary types from its first start (ADR 058). The server loads them as
it loads Apache Atlas's built-in models (1.5): one more models directory, read after Atlas's, under the same
rules.

## Scope

In `aurelius-atlas-core`, the models directory `aurelius_atlas_core/m4i_models/` and `M4I_MODELS_DIR`. In
`aurelius-atlas-server`, the setting `m4i_models_enabled` (`AURELIUS_ATLAS_SERVER_M4I_MODELS_ENABLED`, on by
default), `ServerSettings.model_dirs`, the start-up loading each directory in turn, and the chart's value.

The types are the data dictionary group of `m4i_atlas_core` at `54d9e04`: 14 entity types, 20 relationship
types and the classifications `PII`, `key_data`, `low_risk`, `medium_risk` and `high_risk`. Its `process`
group is contained in it. Not in scope: its kubernetes and connector groups, and `m4i_connector_process`,
which none of its groups holds.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MDD-01 | With `m4i_models_enabled`, the server loads the m4i models directory at every start, after `models_dir`, by the rules of 1.5 (MDL-01 to MDL-04, MDL-15): its definitions not registered are created, those of a greater `typeVersion` update the registered ones, and its changes are audited with the start's (DD-316)                                                                                                                  |
| MDD-02 | The directory holds one model file of the 39 definitions of the sample exports in `data/atlas-sample/`, as `small.zip` and `sample_data.zip` define them, without what a stored definition adds (`guid`, `createdBy`, `updatedBy`, `createTime`, `updateTime`, `version`, `category`, `subTypes`, `relationshipAttributeDefs`, `businessAttributeDefs`). They are `m4i_atlas_core`'s data dictionary group; each is at `typeVersion` 1.0 |
| MDD-03 | With `m4i_models_enabled` off, the directory is not loaded: a new store holds no m4i type, and one that holds them keeps them                                                                                                                                                                                                                                                                                                            |
| MDD-04 | The definitions resolve against Atlas's base model alone. A store that holds them at the same version is not changed by a load. An import of a sample export into a store holding Atlas's models and these creates no type (IMS-03)                                                                                                                                                                                                      |

## Java origin

None in Apache Atlas: a new Atlas holds only `addons/models`. The loading is that of
`AtlasTypeDefStoreInitializer`, as increment 1.5 ports it, applied to one more directory; Atlas reads only
`$ATLAS_HOME/models`.

The definitions come from `aureliusenterprise/m4i_atlas_core` at `54d9e04`
(`m4i_atlas_core/entities/atlas/data_dictionary`, `m4i`, `processes/GenericProcess.py`), whose
`scripts/load_type_defs.py` created them against a running Atlas.

## Deviations

- **DV-139:** a new catalogue holds the m4i data dictionary types besides Atlas's own (ADR 058).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__m4i_models.py`: MDD-01, MDD-02 and MDD-04. The model file
  against the three sample exports; a load after Atlas's base model and a second load that changes nothing;
  `small.zip` and `sample_data.zip` imported into a store with Atlas's models and these, no type created.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_m4i_models.py`: MDD-01 and MDD-03. The setting
  and its directories; a started server reading `m4i_dataset` and `PII`, keeping them after a restart with the
  setting off; a new store without them when it is off.
- The e2e stacks start with the setting on, as a deployment does. No e2e test or scenario creates a type of
  these names, and the metrics scenario treats `typeCount` as volatile.
