# Increment 8.1 — data2model API

| Field      | Value                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Status     | accepted                                                                                                                                                     |
| Author     | Aurelius Atlas maintainers                                                                                                                                   |
| Date       | 2026-10-23                                                                                                                                                   |
| ADRs       | 055 (auxiliary APIs are a named data surface), 051 (increments), 049 (traceability), 052 (parity cites the reference; here the reference is Aurelius source) |
| Design log | DD-108 (foundation), DD-109 (no pandas: pydantic rules, plain rows), DD-043 (audience-scoped roles), DV-15 (native layout)                                   |

## Objective

Port the legacy Aurelius `m4i-data2model` service — the model-extraction API the
lineage graph draws on — to a FastAPI app: `apps/aurelius-atlas-data2model`.

`POST /extract` takes tabular data plus element/relation/view rules and returns
an archimate3 model **string** the webapp's archimate3 parser ingests, plus
per-record metadata. The legacy chain is `lineage_model → data2model /extract`
(8.2 ports the caller).

The legacy implementation is a Flask app on `m4i-analytics` (pandas, graphviz,
bokeh). Per DV-15 the analytics library is **not** ported: the ar3 JSON is
built natively, and the `archimate_process` graphviz layout is replaced by a
deterministic native left-to-right layout — coordinates only need to be
numbers to the parser (DV-15). The port adds **no pandas** (DD-109): the
request rules are pydantic models, the tabular data stays a plain list of row
maps, and the extraction is plain Python — the legacy's pandas DataFrame was
its representation, not part of the browser contract. The **browser contract**
— the JSON body of the response and the ar3 model string's shape — is the
legacy contract and is cited rule by rule.

## Scope

In scope: the app (settings, app factory, `/extract`, liveness), the ar3
builder and layout, unit tests, parity scenarios read from the Aurelius
source, container and e2e (Keycloak-protected, real tokens).

Out of scope: the caller (`lineage_model`, 8.2), the webapp lineage screen
(7.x webapp track), the legacy `/parse_dataset` endpoint (file upload to
pandas — its only caller is the legacy model-editor app, not the lineage
chain; not ported), the `m4i-analytics` library (DV-15).

## Contracts and Rules

The reference for every rule is the Aurelius source (ADR 055 R4): the legacy
service `backend/m4i-data2model/m4i_data2model/data2model.py` (`extract`),
`libs/m4i-analytics/m4i_analytics/model_extractor/ExtractorLanguagePrimitives.py`,
`.../graphs/languages/archimate/ArchimateUtils.py` (`to_JSON`, `generate_view`),
and `m4i-analytics-extensions/m4i-graphviz-layouts` (layout names).

### Extract

| ID     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Legacy source                                                                                                                                             | Enforced by                                                                                                                            | Deviation                                                                                                                    |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| DTM-01 | `POST /extract` accepts a JSON body `{data: [row…], rules: {elements: […], relations: […], views: […]}}` and answers `200` with `{metadata: […], model: "<ar3 JSON string>"}` — the `model` is a JSON **string** inside the JSON body; content type is `application/json`                                                                                                                                                                                                                                                                                                                                                                                        | `data2model.py::extract` (`dumps(result)`, `'model': ArchimateUtils.to_JSON(model)`)                                                                      | `test__extract_returns_metadata_and_an_ar3_model_string`                                                                               | The legacy Flask returned the JSON document as `text/html`; the body contract is unchanged                                   |
| DTM-02 | Each element rule reads its `id_key` column: rows with a null id are dropped, the first row per id is kept (per rule), and each yields a node `id = id_prefix + str(id)`, `type` = the rule's `concept_type` tag, `name` = `concept_name_prefix + str(name)` when `concept_name_key` is a column else `''`; a rule for a column absent from the data yields nothing. _Null_ is JSON null and the legacy's pandas NaN — the JSON request body carries both as `null`                                                                                                                                                                                              | `ExtractorLanguagePrimitives._parse_concept_definition`, `_parse_concept_node`                                                                            | `test__element_rules_read_their_id_column` `test__a_null_id_row_is_dropped` `test__a_rule_for_an_absent_column_yields_nothing`         | A null id yields nothing, not a `'nan'` node; a null name yields `''`, not the legacy's `'nan'` string (both recorded below) |
| DTM-03 | Every parsed row yields a metadata entry `{id, data}` with `data = {created_by: "Model Extractor API", m4i_id_prefix, m4i_original_id: str(id)}` plus each `mapping` entry `{key: value}` whose source column exists and is non-null (null as DTM-02), first row per id; the response's `metadata` is elements, then relations, then views, in rule order                                                                                                                                                                                                                                                                                                        | `_parse_concept_data`, `_parse_relationship_data`, `parse_view`; `data2model.py` metadata concat                                                          | `test__metadata_names_the_source_row_per_rule` `test__metadata_lists_elements_then_relations_then_views`                               | —                                                                                                                            |
| DTM-04 | Each relation rule resolves its `source`/`target` to the referenced element rule's `id_key`/`id_prefix`; rows with a null source or target are dropped, the first row per relation id is kept; an edge `id = id_prefix + str(id)` from `source_prefix + str(source_id)` to `target_prefix + str(target_id)` with `@xsi_type` = the `relationship_type` shorthand's tag (`lr` → `lineage_relation`); an edge survives only when both endpoints exist as model nodes — its metadata entry is kept either way                                                                                                                                                       | `_parse_relationship_definition`, `parse_relationship` (node-membership filter), `fmt_relation` in `data2model.py`                                        | `test__relation_rules_resolve_their_endpoint_rules` `test__every_edge_endpoint_is_a_model_node`                                        | —                                                                                                                            |
| DTM-05 | Model-wide, nodes and edges are deduplicated by `id` keeping the **last** occurrence, at the kept row's position, across all rules                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `data2model.py` `drop_duplicates(subset=['id'], keep='last')`                                                                                             | `test__duplicate_ids_keep_the_last_row`                                                                                                | —                                                                                                                            |
| DTM-06 | A view whose `view_layout` is a known layout (`archimate_process` → left-to-right, `archimate_hierarchical` → bottom-to-top) is generated; a view with an unknown layout is ignored — no view, no metadata; `id_type: "static"` produces one view ided by `id_value`, named by `view_name_value`                                                                                                                                                                                                                                                                                                                                                                 | `data2model.py` `supported_layouts` filter; `parse_view` static branch                                                                                    | `test__a_view_with_an_unknown_layout_is_ignored_entirely` `test__a_static_view_takes_its_id_and_name_from_the_rule`                    | —                                                                                                                            |
| DTM-07 | A view's nodes are the ids collected from its `view_nodes` rules (each rule scans its `id_key` column: non-null, first per id, in rule order), intersected with the model nodes in model order; empty `view_edges` means every model edge between the view's nodes, in model order                                                                                                                                                                                                                                                                                                                                                                               | `parse_view` view_nodes/view_edges scan; `generate_view` `isin` filters                                                                                   | `test__view_nodes_are_collected_by_rule_and_intersected_with_the_model`                                                                | —                                                                                                                            |
| DTM-08 | Node coordinates come from a deterministic native layout (DV-15): ranks by longest path from edge sources, left-to-right `x = rank * 320`, `y` stacked by `95` and centred per rank, rounded to integers; every view node is `w = 120`, `h = 55`                                                                                                                                                                                                                                                                                                                                                                                                                 | `ArchimateProcessLayout.get_coordinates` (graphviz `rankdir=LR`), `generate_view` `node_width/node_height`                                                | `test__the_layout_is_left_to_right_by_dependency_rank`                                                                                 | DV-15: positions are the native layering, not graphviz's; the parser contract (numeric coordinates) holds                    |
| DTM-09 | The ar3 string is `{"ar3_model": {...}}` with `@identifier` = the model name, `ar3_name`, `ar3_elements.ar3_element[]` (`@identifier`, `@xsi_type`, `ar3_name[{@xml_lang:"en",value}]`), `ar3_relationships.ar3_relationship[]` (+ `@source`/`@target`), `ar3_views.ar3_diagrams.ar3_view[]` (`@xsi_type: "ar3_Diagram"`, `ar3_node[]` with `@identifier: "<view>-<node id>--<i>"`, `@x/@y/@w/@h`, `@elementRef`, `@xsi_type: "ar3_Element"`, `ar3_connection[]` with `@source/@target` = view-node ids, `@relationshipRef`, `@xsi_type: "ar3_Relationship"`), and `ar3_organizations` folders `Other` / `Relations` / `Views` (node folder = layer capitalised) | `ArchimateUtils.to_JSON` (`format_element`, `format_relationship`, `format_view`, `format_organizations`), `generate_view` (`format_node`, `format_edge`) | `test__the_model_string_follows_the_ar3_shape` `test__organizations_group_nodes_relations_and_views`                                   | —                                                                                                                            |
| DTM-10 | Every endpoint requires a valid Keycloak bearer token (`aurelius-atlas-auth`, AUX-05); `/extract` is read-only, so no write role is required; a missing or invalid token is `401`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | legacy `@requires_auth` (decorator commented out in dev, present in the deployed service)                                                                 | `test__a_missing_token_is_rejected` `test__a_token_minted_for_another_audience_is_rejected`                                            | —                                                                                                                            |
| DTM-11 | A body that is not a JSON object, a body whose rules fail validation (unknown `concept_type` / `relationship_type`, a missing required key, a dangling rule reference), is answered `400` with an Atlas-shaped error body; an empty body behaves as `{data: [], rules: {}}` — metadata `[]` and the empty model skeleton                                                                                                                                                                                                                                                                                                                                         | legacy raises `ValueError`/`KeyError` (500)                                                                                                               | `test__a_malformed_body_is_rejected` `test__an_unknown_concept_type_is_rejected` `test__an_empty_body_yields_the_empty_model_skeleton` | The legacy answered 500 on malformed input; a 400 is the stated contract                                                     |
| DTM-12 | The request's `rules` parse as pydantic rule models (elements, relations, views); the tabular `data` stays a plain list of row maps — the port adds no pandas (DD-109)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | legacy `DataFrame(data)` and the `m4i-analytics` Definition adapters (representation only)                                                                | `test__rules_are_pydantic_models`                                                                                                      | —                                                                                                                            |

### Reference types

`concept_type` accepts the Archimate 3.0 tags the legacy `ElementType` enum
publishes; the lineage chain uses `lineage_dataset` and `lineage_process`
(both layer `Other`). `relationship_type` accepts the legacy shorthands
(`lr` → `lineage_relation`, `f` → `ar3_Flow`, …). The full tables are ported
as data, not as the enum machinery.

## Data contracts

- `POST /extract` — request/response per DTM-01..DTM-09; the lineage rules
  (4 element, 2 relation, 1 static view, DTM citations above) are the 8.2
  caller's payload and are exercised as a scenario.
- Rule models (pydantic, `aurelius_atlas_data2model.rules`):
  `ExtractionRequest{data, rules{elements, relations, views}}`, `ElementRule`,
  `RelationRule`, `ViewRule`, `ViewNodeRule`, `ViewEdgeRule`, `MappingEntry` —
  extra rule keys are ignored (the legacy adapters' `**kwargs`), null string
  fields are the legacy's empty string, and cross-rule references (relation
  source/target, view node/edge rules) are validated at parse time (DTM-11).
- `GET /liveness` — `204`, no auth (the container healthcheck).
- Settings (env prefix `AURELIUS_ATLAS_DATA2MODEL_`): `host`, `port` (21001),
  `log_level`, `tls_cert_file`/`tls_key_file`, `auth_server_url`, `auth_realm`,
  `auth_audience`, `auth_ca_file`, `otel_token_url`, `otel_client_id`
  (`otel-data2model`), `otel_client_secret`, `otel_endpoint`, `otel_ca_file`.

## Deviations (recorded in `deviations.md`)

- **DV-15** (design-level, recorded in 8.0): the ar3 model is built natively,
  not by `m4i-analytics`; coordinates are the deterministic LR layering, not
  graphviz positions. The port is pandas-free (DD-109) — the ar3 string's
  shape and the `{model, metadata}` body are unchanged.
- **DV-17**: a null element name yields `''`, not the legacy `'nan'` string
  (DTM-02).
- **DV-18**: malformed input is `400`, not the legacy `500` (DTM-11).
- **DV-19**: the answer's content type is `application/json`, not Flask's
  `text/html` (DTM-01).

## Test list

- Unit: `apps/aurelius-atlas-data2model/tests/test__extract.py` (the DTM
  rules), `test__app.py` (settings/liveness wiring).
- Scenario (parity, read from Aurelius source — ADR 052 applied to the
  Aurelius reference): `scenarios/lineage/extract.scenario.yaml` — the 8.2
  caller's fixed rules with a two-relation lineage payload, the expected
  `{model, metadata}` body read from the legacy chain's shape (coordinates
  masked volatile, the native layout carried as DV-15).
- E2E: `e2e/` — real container, Keycloak-minted token; 401 unauthenticated,
  200 with the lineage rules; collector leg exercised by the e2e stack.

## Acceptance criteria

- [x] Every rule id names a test (ADR 049 — `aurelius-atlas-trace check` green).
- [x] The ar3 string parses with the webapp's archimate3 parser expectations (DTM-09, cited).
- [x] Ruff, pyright, prettier, commit checks; `nx test`/`nx e2e` pass.

## Delivery

- Branch: `feat/aux-apis-data2model` (PR 2 of the 8.x chain, on 8.0).
- M6: the first dashboard-visible surface of ADR 055; the webapp lineage
  screen (7.x track) consumes it unchanged.

## Open questions

- Element/relationship type tables: full Archimate 3.0 ported (chosen —
  the rules are a public API, a caller may name any type) vs the lineage
  pair only.
