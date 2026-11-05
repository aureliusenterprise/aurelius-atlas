# 8.6 Aux API failure hardening

- **Status:** done
- **Pull request:** — (follows the review of 2026-10-24, DD-214)
- **Records:** DD-214 (the review that scoped this); cites 8.1, 8.2, 8.3, 8.5, ADR 052

This page is the `aurelius-atlas-data2model` part of increment 8.6; its rule table is the increment's shared
set. The other parts are with [`aurelius-atlas-lineage-model`][part-0] and
[`aurelius-atlas-validate-entity`][part-1] .

## Scope

Test-completeness, not new semantics: the review found the aux APIs' failure
behaviours **already specified** (DTM-04/06/07, LM-07/11/12/13, VE-01) with
unproven paths. This increment closes the proof gaps in the three auxiliary
apps:

- `data2model` — the extraction engine's view-edge selection, dynamic views,
  dynamic view names, the `archimate_hierarchical` layout, and relation-level
  id dedupe (all at 0% line coverage).
- All three — **negative parity scenarios**: 400/401 stages in YAML, which the
  per-app scenario files (all happy-path today) run against both the in-process
  app and the container, per ADR 052.

It does **not** deliver: the server's mid-request store failure (deferred
backlog #1, DD-214 — the 2.x track's), new client-library behaviour (8.7),
frontend UX (7.19), container-stopping e2e (9.1).

## Semantics

No new rule ids (DD-214): every behaviour below is already specified by the
cited rule, in the cited increment's spec. This table restates the exact
path each test pins, so the test names are auditable against the originals.

- **DTM-04** (8-1): a relation rule's duplicate `id_key` yields one
  edge/metadata entry — keep-first at the relation level.
- **DTM-06** (8-1): a dynamic view groups rows by `id_key` (null keys skipped);
  a dynamic view name reads `view_name_key`, `view_name_prefix`, and the legacy
  `'nan'` when the group's key column is absent (DV-70);
  `archimate_hierarchical` lays out bottom-to-top.
- **DTM-07** (8-1): a view's `view_edges` rules select edge ids from the
  relation's `id_key` column: model-edge intersection, dedupe in first-seen
  order, absent-column skip, null-value skip; the selection then filters the
  between-nodes edges.
- **LM-07** (8-2): a transport failure from an upstream
  (`httpx.RequestError` — connect refused, DNS) is answered `502` with the
  Atlas body, DV-80. An upstream **timeout** is such a transport failure: a
  hanging upstream past `UPSTREAM_TIMEOUT_SECONDS` answers `502`, not a hang
  (LM-10).
- **LM-12** (8-5): the **data2model** circuit, once open, answers `502` with
  `FAST_FAIL_D2M` **without calling the extract upstream** — the mirror of the
  proven Atlas-side fast-fail.
- **LM-13** (8-5): a transport failure **counts as an outage** for its breaker:
  repeated connect failures open the circuit.
- **VE-01** (8-3): the mock accepts an oversized body and a body with no
  `content-type` verbatim — the body is never read (DV-67).
- (framework default, no rule id): `GET /` on validate-entity's mock route
  answers `405` — the legacy is POST-only (DV-67) and there is no GET parity;
  the test names the route function for ADR 049.

## Java origin

None new: this increment proves rules whose Java origin 8.1/8.2/8.3/8.5
already cite (`data2model`'s `extract.py`/`to_JSON.py`, `lineage_model`'s
`lineage_model.py`, the legacy validation mock). The negative parity
stages cite the same legacy sources as their positive counterparts, with
the deviation refs the rules carry (DV-70, DV-79, DV-73, DV-75).

## Deviations

None new. The negative scenarios state existing deviations, each with its
`deviations:` ref in the YAML (the 8.0 harness's feature, DV-06): DV-79
(malformed body → 400, not the legacy Flask 500), DV-73 (a malformed/missing
query → 400, not the legacy's `int()`/`Enum()` crash 500), DV-67 (any body
accepted), DV-70 (null view name renders `'nan'` as the legacy does).

## Acceptance

Unit (naming rules per ADR 049; run `uv run pytest apps/<app>/tests`):

- `apps/aurelius-atlas-data2model/tests/test__extract.py` — appended tests:
  `test__a_relation_id_seen_twice_yields_one_edge` (DTM-04),
  `test__view_edges_select_their_rule_column_of_the_model_edges` (DTM-07),
  `test__a_view_without_edge_rules_holds_every_edge_between_its_nodes` (DTM-07),
  `test__view_edge_selection_skips_a_null_value` (DTM-07),
  `test__a_view_edge_rule_for_an_absent_column_is_skipped` (DTM-07),
  `test__a_dynamic_view_groups_rows_by_its_key_column` (DTM-06),
  `test__a_dynamic_view_name_comes_from_its_key_column` (DTM-06),
  `test__a_dynamic_view_name_without_its_key_column_is_the_legacy_nan` (DTM-06, DV-70),
  `test__the_hierarchical_layout_ranks_bottom_to_top` (DTM-06, DTM-08).
  Parity scenarios (ADR 052; run in-process by `tests/test__*_scenarios.py` and
  against the container by `e2e/*_scenarios_e2e.py`):

- `apps/aurelius-atlas-data2model/scenarios/lineage/extract-rejections.scenario.yaml`
  — a malformed body (`{"data": "not rows"}`) → 400 Atlas body
  (`deviations: [DV-79]`, cites the legacy `extract` view's `ValueError`),
  and an unknown `concept_type` rule → 400 (DTM-11).
  Gates: `uv run aurelius-atlas-trace check` green (the appended tests name the
  functions they already name — no new public functions land; check the gap
  count does not grow), `nx test <app> -c ci` green for the three apps, the two
  new scenario sets pass in-process and in e2e, Sonar's coverage of
  `extract.py` / `app.py` rises (no new-code dip).

[part-0]: ../../../aurelius-atlas-lineage-model/specs/8-6-aux-failure-hardening/spec.md
[part-1]: ../../../aurelius-atlas-validate-entity/specs/8-6-aux-failure-hardening/spec.md
