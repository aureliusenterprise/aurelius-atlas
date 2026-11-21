# 20.1 Plan

Each step states what it changes and how it proves itself. Run level is from the root `AGENTS.md` table.

## Step 1 — Client: the view family and the session flags (CLV-01..04, CLW-13)

- `aurelius_atlas_server_client/aurelius.py`: `ViewSearchRequest` (mirrors `routes/view_search.py`'s server
  model: `query`, `mode`, `filters`, `facets`, `sort`, `limit`, `offset`), `ViewSearchAnswer` (`cards:
list[EntityCard]`, `facets: dict`, `total: int`) — the `lineage.py`/DD-562 precedent, reused models whole.
- `aurelius_atlas_server_client/client.py`: `ViewApi` (`view.search`, `view.read`, `view.save`),
  `ViewVersionConflictError(AtlasClientError)` carrying `view: EntityView`; `_Api` raises it for the door's
  409 with an embedded `view` (the 409 shape of DD-591); `AtlasClient.view` namespace.
- `aurelius_atlas_server_client/models.py`: `AtlasSessionInfo` gains `entity_create_allowed` and
  `entity_update_allowed` with their `atlas.entity.*.allowed` aliases (CLW-13).
- `__init__.py`: export `ViewApi`, `ViewVersionConflictError`, the two search shapes.
- Prove: recorder unit tests `tests/test__aurelius_atlas_server_client_view.py` — method, path, body,
  `unsafeReparent` query, the parsed conflict (CLV-01..04), the session flags (CLW-13).
- Level 0: `uv run pytest libs/python/aurelius-atlas-server-client/tests`, `nx lint`/`nx typecheck`.

## Step 2 — Client spec matrix (DD-307, DD-814)

- `libs/python/aurelius-atlas-server-client/specs/20-1-client-view-routes/spec.md`: the matrix of the two
  view route modules' endpoints, each marked covered by its method or open, the 8.9 shape.
- Level 0: docs gates (`docs/contributor-guide/writing-style.md`).

## Step 3 — Migrate the view suites (the only raw files with no client path today)

- `e2e/conftest.py`: the `api` fixture stays; `anonymous` gains nothing (the client speaks unauthenticated
  through an empty token). Tests build a reader client with `api.with_token(reader_token)` where they need it.
- `e2e/test__view_family_e2e.py`: `make()` on `api.entity.create_or_update`; search door on `api.view.search`
  (cards are `EntityCard` models); read door on `api.view.read`; anonymous 401 via `AtlasClient(http, "")`;
  covers add the CLV paths and `aurelius_atlas_server_client.client.ViewApi.*` (ECL-02).
- `e2e/test__view_mutation_e2e.py`: read/edit/save on `view.read`/`view.save`; the 409 asserts
  `ViewVersionConflictError.view`; held-parent/children reads on `entity.by_guid`; the parent-side refusal
  asserts `AtlasClientError` 404 body (CL-04).
- Prove: `npx nx e2e aurelius-atlas-server -c ci -- -k "view"` (level 2).

## Step 4 — Migrate the Atlas-route suites

- `test__aurelius_atlas_server_admin_audits_e2e.py`: types/entity/admin methods (admin_audits has no typed
  path today).
- `test__aurelius_atlas_server_export_e2e.py`: the replication scenario moves whole (typedef, entity,
  `admin.export` with the `replicatedTo` option, `admin.server`, `entity.by_guid`, `admin.export_import_audit`).
- `test__aurelius_atlas_server_dashboards_e2e.py`: the session AUZ test and the reader test move to
  `api.admin.session()` and `types` (`with_token` for the reader, empty token for anonymous); the browser and
  trace probes stay raw (DD-813).
- `test__aurelius_atlas_server_load_e2e.py`: `_seed` and `_remove` on `entity`/`admin.purge`/`types`; the mix
  and driver stay raw (DD-813).
- `test__aurelius_atlas_server_metamodel_e2e.py`: `types.typedef_by_name`, typed end-def assertions.
- `test__aurelius_atlas_server_restore_e2e.py`: `_write_catalogue`/`_read_catalogue` on `types`, `entity`,
  `search` — the in-process `_server` builds an `AtlasClient` over the same ASGI transport.
- Prove per file: `-k "<file pattern>"` (level 2).

## Step 5 — Full verification and PR

- `npx nx e2e aurelius-atlas-server -c ci` (level 2), `nx test aurelius-atlas-server-client -c ci` (level 1),
  `nx lint`/`nx typecheck` on both projects, `uv run aurelius-atlas-trace check`.
- Grep gate (ECL-01): no `client.post|get|put|delete|request` left in the eight migrated files except the
  named carriers.
- PR body: what moved, the five carriers that stayed, CLV/CLW-13/ECL rules. CI green, squash-merge.
