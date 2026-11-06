# Plan: 1.5b The m4i data dictionary types

The decision is ADR 058. The rules are MDD-01 to MDD-04 of [the spec](./spec.md), the design DD-362.

## Analysis

- **Where the types are defined:** `aureliusenterprise/m4i_atlas_core` (`54d9e04`, version 0.1.0). Its
  `scripts/load_type_defs.py` creates four groups against a running Atlas: `data_dictionary`, `process`,
  `connectors` and `kubernetes`. `m4i_data_management` and `m4i_backend_core` define no types.
- **The groups:** `data_dictionary` holds 14 entity types, 20 relationship types and 5 classifications.
  `process` is the generic process and its two relationships, all also in `data_dictionary`. `kubernetes` (11
  entity and 14 relationship types) and `connectors` (13 and 9) describe those systems.
  `m4i_connector_process` is defined but in no group.
- **The samples:** all three exports in `data/atlas-sample/` use only the `data_dictionary` types, besides
  Atlas's own. `small.zip` and `sample_data.zip` define them exactly as the library does.
  `only_gov_quality.zip` comes from an older install whose `businessOwner` descriptions differ.
- **Clashes:** none of the names is one of Atlas's types. No test or scenario on a shared store creates a type
  of these names.

## Chosen scope

The `data_dictionary` group, `process` with it: 39 definitions. Kubernetes and connectors stay out (ADR 058).

## Steps

1. The model file `m4i_models/0010-m4i_data_dictionary_model.json`, from `sample_data.zip`'s
   `atlas-typesdef.json`: the 39 definitions sorted by name, without the fields a stored definition adds.
2. `M4I_MODELS_DIR` beside `BUILTIN_MODELS_DIR`; the setting `m4i_models_enabled`, on, and
   `ServerSettings.model_dirs`; the start-up loading each directory in turn under one audit buffer.
3. The chart's `AURELIUS_ATLAS_SERVER_M4I_MODELS_ENABLED: "true"`; the server unit tests' settings turn it
   off, as they load no models.
4. Tests: the file against the samples, the load and reload, the imports creating no type, the setting and a
   started server.
5. Records: ADR 058 (Proposed), DD-362, DV-139, the roadmap row 1.5b, the java-map row, the module docs.
6. Verify on Elasticsearch: the standalone stack starts with the types and imports `small.zip` creating none.
