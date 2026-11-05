# 8.11 Client route coverage — relationship and the admin writes

- **Status:** done
- **Pull request:** to follow
- **Records:** DD-307 (the per-module live-check spec), DD-309 (bodies reused from
  `aurelius-atlas-model`), DD-310 (file routes carry raw bytes), DD-313 (the
  import's `request` part is a form field, not a file); cites 8.4 (the
  five covered admin routes, CL-01..CL-08), 8.8 (CL-60..CL-65), and the server's
  rules REL, EDL, EDL-purge, EXP, IMS, TSK, ENS.

Two modules close together. The server's `routes/relationship.py` answers 4
routes and `AtlasClient` has none of them. `routes/admin.py` answers 12 and the
client covers the five reads of 8.4; the seven left are the writes and the task
list. This increment ships `AtlasClient.relationship` and completes `AtlasClient.admin`.

## Scope

In scope:

- `AtlasClient.relationship` — the 4 routes of `routes/relationship.py`.
- `AtlasClient.admin` completed — `patches`, `purge`, `export`, `import_data`,
  `import_file`, `tasks`, `delete_tasks` (7 routes).
- The export/import pair as bytes (DD-310): the ZIP out, the ZIP in.

Out of scope: the login routes (CL-65 of 8.8); server behaviour (REL, EXP, IMS,
TSK rules stay in the server's specs, cited not restated); the incremental Hive
export and the export/import audits (server 6.3c, planned).

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                         |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLR-01 | `AtlasClient.relationship` exists as a resource API (DD-203) with paths from `RELATIONSHIP_ROOT = "api/atlas/v2/relationship"` (CL-60), and every method is named in a `covers` marker.                                                                                                                                                      |
| CLR-02 | `relationship.get(guid, extended_info=False)` answers `GET /guid/{guid}`. When `extended_info` is set it sends `extendedInfo=true` and returns an `AtlasRelationshipWithExtInfo`; otherwise it sends nothing and returns the same model holding only `relationship` — the shape the server answers when the flag is absent (REL-03, REL-06). |
| CLR-03 | `relationship.create` and `update` send an `AtlasRelationship` body and return the server's `AtlasRelationship` answer. Neither verb pre-validates the ends (REL-04..REL-07): the server answers (CL-12 of 8.4).                                                                                                                             |
| CLR-04 | `relationship.delete(guid, delete_type=None)` answers `DELETE /guid/{guid}` and sends `deleteType` only when given (EDL-04, as CLE-04). It returns `None` on the 204 (REL-08).                                                                                                                                                               |
| CLW-01 | `admin.patches()` answers `GET /patches` and returns a list of `AtlasPatch`, unwrapped from the server's `{"patches": [...]}` envelope (ENS-10).                                                                                                                                                                                             |
| CLW-02 | `admin.purge(guids)` answers `PUT /purge` with a JSON array of guid strings and returns an `EntityMutationResponse` (EDL-01..EDL-03). An empty list sends `[]` — the client does not send an empty body, because the server reads a non-array as `BAD_REQUEST` (DV-10).                                                                      |
| CLW-03 | `admin.export(request=None)` answers `POST /export` with an `AtlasExportRequest` body (or none) and returns `(bytes, "application/zip")`. A 204 answer — the empty export the request asked to omit (EXP-05) — returns `(b"", "")` (DD-310). The client sends no options it was not given.                                                   |
| CLW-04 | `admin.import_data(content, request=None)` answers `POST /import` as `multipart/form-data` with the `data` part (the ZIP bytes) and an optional `request` part holding the `AtlasImportRequest` as JSON text, and returns an `AtlasImportResult` (IMS-01..IMS-05, DD-310).                                                                   |
| CLW-05 | `admin.import_file(request)` answers `POST /importfile` with an `AtlasImportRequest` body — its `fileName` names a ZIP in the server's import folder (IMS-06, DV-125) — and returns an `AtlasImportResult`. The client reads no folder of its own (DD-310); it passes the name through.                                                      |
| CLW-06 | `admin.tasks(guids=None)` answers `GET /tasks`, sending each guid as a repeated `guids` query parameter when given, and returns a list of `AtlasTask`. `admin.delete_tasks(guids)` answers `DELETE /tasks` with the same repeated parameter and returns `None` on the 204 (TSK-06).                                                          |
| CLW-07 | `AtlasClient.admin` keeps its five 8.4 methods (version, status, session, liveness, readiness) unchanged; the seven new methods join the same class (CL-11 of 8.4 stays accurate — it lists what shipped, and 8.4 is superseded here only by extension, never edited).                                                                       |

### The coverage matrix

`routes/relationship.py` (4 routes). Open means no client method yet; all 11
rows of both matrices are covered as of 8.11.

| Method and path       | Server function | Client method      | Rule   |
| --------------------- | --------------- | ------------------ | ------ |
| `POST ""`             | `create`        | `create` (covered) | CLR-03 |
| `PUT ""`              | `update`        | `update` (covered) | CLR-03 |
| `GET /guid/{guid}`    | `getById`       | `get` (covered)    | CLR-02 |
| `DELETE /guid/{guid}` | `deleteById`    | `delete` (covered) | CLR-04 |

`routes/admin.py` (12 routes; 5 covered by 8.4, 7 here):

| Method and path    | Server function   | Client method                  | Rule         |
| ------------------ | ----------------- | ------------------------------ | ------------ |
| `GET /version`     | (8.4)             | `admin.version`                | CL-11 (done) |
| `GET /status`      | (8.4)             | `admin.status`                 | CL-11 (done) |
| `GET /session`     | (8.4)             | `admin.session`                | CL-11 (done) |
| `GET /liveness`    | (8.4)             | `admin.liveness`               | CL-11 (done) |
| `GET /readiness`   | (8.4)             | `admin.readiness`              | CL-11 (done) |
| `GET /patches`     | `getAtlasPatches` | `admin.patches` (covered)      | CLW-01       |
| `PUT /purge`       | `purgeByIds`      | `admin.purge` (covered)        | CLW-02       |
| `POST /export`     | `export`          | `admin.export` (covered)       | CLW-03       |
| `POST /import`     | `importData`      | `admin.import_data` (covered)  | CLW-04       |
| `POST /importfile` | `importFile`      | `admin.import_file` (covered)  | CLW-05       |
| `GET /tasks`       | `getTaskStatus`   | `admin.tasks` (covered)        | CLW-06       |
| `DELETE /tasks`    | `deleteTask`      | `admin.delete_tasks` (covered) | CLW-06       |

After this increment, `routes/admin.py` and `routes/relationship.py` are fully
covered.

Bodies, reused whole (DD-309): `AtlasRelationship`, `AtlasRelationshipWithExtInfo`,
`AtlasPatch`, `AtlasExportRequest`, `AtlasImportRequest`, `AtlasImportResult`,
`AtlasTask`, `EntityMutationResponse`. The client imports them from
`aurelius-atlas-model` and defines none.

## Aurelius origin

- Apache Atlas 2.4.0 `RelationshipREST` and `AdminResource`, and the Angular
  `RelationshipClient` / `AdminClient` in `libs/atlas/api`.
- This workspace: `routes/relationship.py`, `routes/admin.py` (paths, the
  repeated `guids` parameter, the 204s, the ZIP content type and the empty-export
  204), and the server's specs `6-3-export`, `6-3-import` (EXP/IMS rules), and the
  tasks rules (TSK-06) — cited, not restated.
- `aurelius-atlas-model`: `relationship*`, `patches`, `impexp`, `tasks`, and
  `instance` (DD-309).

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-307, DD-309, DD-310 in [8.8's
`design.md`](../8-8-client-route-coverage/design.md), and DD-313 in [this
increment's](./design.md). CLW-07 notes the relation to
8.4: CL-11 is not edited (an accepted spec is not), and this increment extends it.

## Acceptance

- Unit: `tests/test__aurelius_atlas_server_client_relationship.py` (new) and
  `tests/test__aurelius_atlas_server_client_admin.py` (new, the seven writes —
  the five 8.4 reads stay in the client file, with their test's covers marker
  gaining CLW-07). One test per matrix row naming its method and rules; the
  `MockTransport` recorder asserts method, path, query, and body.
- Unit: CLW-03's empty-export `(b"", "")` and CLW-04's two-part form each get a
  dedicated test; CLW-06's repeated-`guids` rendering is pinned once for both verbs.
- Trace: `uv run aurelius-atlas-trace check` names CLR-01..CLR-04 and CLW-01..CLW-07.
- Gates: `nx test aurelius-atlas-server-client -c ci`, `ruff check`, `zensical
build --strict`.
