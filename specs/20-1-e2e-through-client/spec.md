# 20.1 The e2e suite speaks through the client library

- **Status:** in progress
- **Pull request:** —
- **Records:** DD-812 to DD-815, plan in [plan.md](./plan.md), design in [design.md](./design.md)

## Scope

The server's e2e suite calls the container with hand-built `httpx` requests for most tests. Only the search
suite and the export scenarios go through `AtlasClient`. Each hand-built call is a wire detail the suite
maintains by hand, and a client method the suite never exercises.

This increment moves the suite onto the client library. Where the client cannot answer a route the suite
needs, the client gains the method first. The client's view family is the gap today: no client method answers
`/api/aurelius/v1/search`, the read door, or the mutation door, and the 409 of the mutation door carries a
stored view the client cannot show (DD-812). The session read also lacks the two entity permission flags the
suite checks (DD-815).

After this increment:

| Carrier                                           | Path through the client now                                                                  |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `test__view_family_e2e.py`                        | `view.search`, `view.read`                                                                   |
| `test__view_mutation_e2e.py`                      | `entity`, `view.read`, `view.save`, `ViewVersionConflictError`                               |
| `test__aurelius_atlas_server_admin_audits_e2e.py` | `types`, `entity`, `admin.purge`, `admin.audits`, `admin.audit_details`                      |
| `test__aurelius_atlas_server_export_e2e.py`       | the replication scenario too, on `admin.export`, `admin.server`, `admin.export_import_audit` |
| `test__aurelius_atlas_server_dashboards_e2e.py`   | the reader and session API tests, on `session`, `types`                                      |
| `test__aurelius_atlas_server_load_e2e.py`         | the seed and the clean-up, on `entity`, `admin.purge`, `types`                               |
| `test__aurelius_atlas_server_metamodel_e2e.py`    | `types.typedef_by_name`                                                                      |
| `test__aurelius_atlas_server_restore_e2e.py`      | `types`, `entity`, `search` over the in-process ASGI transport                               |

This increment does not deliver:

| Not delivered                                 | It lands in                                                                              |
| --------------------------------------------- | ---------------------------------------------------------------------------------------- |
| The parity runner on the client               | Not planned. It drives JSON stages of its own (ECL-01).                                  |
| The session teardown on the client            | Not planned. It is sync, the client is async-only (DD-813).                              |
| The load mix on the client                    | Not planned. Typed parsing would skew the latency budget (DD-813).                       |
| The browser probes and the raw probes on them | Not planned. Per-request headers or response headers the client does not carry (DD-813). |

## Semantics

The client rules keep the ids of the 8.4 series. The suite rule is new (ECL).

| Id     | Rule                                                                                                                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CLV-01 | `AtlasClient.view.read(guid)` answers `GET /api/aurelius/v1/entity/guid/{guid}` with the entity's `EntityView` (AVR-10). The 404 of a GUID with no entity raises `AtlasClientError` like every other non-2xx (CL-04).                                        |
| CLV-02 | `AtlasClient.view.save(view, *, unsafe_reparent=False)` answers `POST /api/aurelius/v1/entity` with the saved `EntityView` (AVW-07). `unsafeReparent=true` rides the query string only when the caller sets it (RPS-05).                                     |
| CLV-03 | A save the server refused as stale raises `ViewVersionConflictError` (AVW-04, DD-591). It is an `AtlasClientError` (CL-04), and it carries the stored view the door answered with, parsed as an `EntityView`.                                                |
| CLV-04 | `AtlasClient.view.search(request)` answers `POST /api/aurelius/v1/search` with the door's answer: `EntityCard` models as cards, the facet entries, and the total (AVR-08). The request shapes live in the client's `aurelius.py` (DD-562).                   |
| CLW-13 | `AtlasSessionInfo` carries `atlas.entity.create.allowed` and `atlas.entity.update.allowed`, as `routes/admin.py` answers them (ADM-05, AUZ-06).                                                                                                              |
| ECL-01 | Every Atlas request of the server's e2e suite goes through `AtlasClient`, except the named carriers: the parity runner, the sync session teardown, the timed load mix, the browser probes, and the two raw probes that a client call cannot answer (DD-813). |
| ECL-02 | Every migrated test names the client methods it exercises in `@pytest.mark.covers`, the way the search suite names them for CL-13.                                                                                                                           |

## Java origin

This ports nothing. The view family is Aurelius-native (16.1 to 16.3), and Apache Atlas 2.4.0 has no Python
client. The increment adds no row to [Java map](../../docs/architecture/conversion/java-map.md).

## Deviations

None from Apache Atlas: the client grows methods, and the suite changes who sends its requests. The answers
on the wire do not move. The named carriers that keep raw requests (ECL-01) are deliberate, and design.md
records why each one stays. The increment adds no row to [Deviations](../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                       | Command                                                                                     | Level |
| ------------------------------------------- | ------------------------------------------------------------------------------------------- | ----- |
| Every CLV rule has a test that names it     | `uv run aurelius-atlas-trace check` scoped to this increment                                | 0     |
| The new client methods answer the fake      | `nx test aurelius-atlas-server-client -c ci`                                                | 1     |
| The migrated suite passes the container     | `nx e2e aurelius-atlas-server`                                                              | 2     |
| No new raw Atlas call in the migrated files | a grep for `client.post`/`client.get`/`client.put`/`client.delete` in the eight files above | 0     |
| The client keeps its failure contract       | `nx test aurelius-atlas-server-client -c ci` (CL-04, CL-08 suites unchanged)                | 1     |
| Lint and types                              | `nx lint` and `nx typecheck` on both projects                                               | 0     |

## Design decisions

The reasoning lives in [design.md](./design.md) as DD-812 to DD-815. DD-812 covers the client's view family,
and DD-813 the five carriers that keep raw requests.
