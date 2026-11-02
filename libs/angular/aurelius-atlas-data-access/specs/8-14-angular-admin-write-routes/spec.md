# 8.14 Angular admin twin — the admin write routes

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-315; cites DD-217 (the admin client lands on both sides of
  the wire), 7.3 (APC-01..APC-04, ADM-01/02/05), 8.11 (CLW-01..CLW-06, the
  Python twin), and the server's rules ENS-10, EDL-01..03, EXP-01..06,
  IMS-01..06, TSK-06, DV-10.

`AdminService` answers three of the twelve routes of `routes/admin.py`
(APC-02, ADM-01/02/05). The lib's own rule is one typed method per endpoint
the server implements, and its AGENTS.md keeps the admin wire contract in step
with its Python twin (`AtlasClient.admin`, CL-11). 8.11 completed that twin
with the nine write and health routes; this increment lands the same nine
routes on the Angular side and closes the pair.

## Scope

In scope: `GET /liveness`, `GET /readiness`, `GET /patches`, `PUT /purge`,
`POST /export`, `POST /import`, `POST /importfile`, `GET /tasks`, and
`DELETE /tasks` of `routes/admin.py` in `AdminService`, the patch, task,
mutation, and export/import DTO files, and their Vitest specs.

Out of scope: the three routes of APC-02 (unchanged); the entity,
relationship, glossary, and lineage Angular clients (increments 8.15 and
after — this increment is the admin pair only); any screen that calls the new
methods.

## Semantics

Each rule's id is named in its Vitest `it()` title, the APC family's
convention (the trace check reads pytest files only; the APC rules are already
in its gap list). The method names are the Python twin's snake_case names in
camelCase (`import_data` → `importData`), per 8.13's convention.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AAC-01 | `liveness()` and `readiness()` answer `GET /liveness` and `GET /readiness` as plain text — `Observable<string>`, requested with `responseType: "text"` (ADM-03, ADM-04). A server that is not ready answers through the error channel with its status and body (APC-04); because the call asked for text, the body arrives as text, and the Atlas JSON is what the caller parses.                                                                        |
| AAC-02 | `patches()` answers `GET /patches` and maps the server's `{"patches": [...]}` envelope to `Observable<AtlasPatch[]>` — the unwrapped list, the Python twin's shape (ENS-10, CLW-01).                                                                                                                                                                                                                                                                     |
| AAC-03 | `purge(guids)` answers `PUT /purge` with the guid array as the bare JSON body and answers an `EntityMutationResponse` (EDL-01..EDL-03, CLW-02). An empty list still sends `[]`: the server reads a missing or non-array body as `BAD_REQUEST` (DV-10), never as "purge nothing" — the method sends what it is given.                                                                                                                                     |
| AAC-04 | `export(request?)` answers `POST /export` and answers `Observable<AtlasExportAnswer>` — `{ body, contentType }`, the ZIP bytes and the `Content-Type` header, the twin of the Python tuple (EXP-01..EXP-06, CLW-03, DD-315). No request sends no body (DV-120). The server's 204 for an empty export asked to omit its ZIP (EXP-05) answers `{ body: null, contentType: "" }`. `body` is an `ArrayBuffer`, requested with `responseType: "arraybuffer"`. |
| AAC-05 | `importData(content, request?)` answers `POST /import` as `multipart/form-data`: the `data` part is the Blob as the file `export.zip`; the `request` part, when given, is a plain text field holding the request as JSON — never a file part (IMS-01..IMS-05, CLW-04, the DD-313 pair). `importFile(request)` answers `POST /importfile` with the request as the bare JSON body (IMS-06, DV-125, CLW-05). Both answer an `AtlasImportResult`.            |
| AAC-06 | `tasks(guids?)` answers `GET /tasks` and answers `Observable<AtlasTask[]>`; each guid travels as a repeated `guids` parameter and none given sends no parameter, which the server reads as "every task" (TSK-06, CLW-06). `deleteTasks(guids)` answers `DELETE /tasks` with the same repeated parameter and answers `void` (the 204).                                                                                                                    |
| AAC-07 | The three methods of APC-02 keep their names, paths, and behaviour. The nine new methods join the same class; APC-02 is extended, not edited (the relation 8.11's CLW-07 set for CL-11).                                                                                                                                                                                                                                                                 |

### The coverage matrix (`routes/admin.py`, 12 routes)

Open means no client method yet. All 12 are covered as of this increment.

| Method and path    | Server function   | Client method           | Rule        |
| ------------------ | ----------------- | ----------------------- | ----------- |
| `GET /version`     | `get_version`     | `getVersion`            | APC-02 done |
| `GET /status`      | `get_status`      | `getStatus`             | APC-02 done |
| `GET /session`     | `get_session`     | `getSession`            | APC-02 done |
| `GET /patches`     | `get_patches`     | `patches` (covered)     | AAC-02      |
| `GET /liveness`    | `get_liveness`    | `liveness` (covered)    | AAC-01      |
| `GET /readiness`   | `get_readiness`   | `readiness` (covered)   | AAC-01      |
| `PUT /purge`       | `purge_by_ids`    | `purge` (covered)       | AAC-03      |
| `POST /export`     | `export`          | `export` (covered)      | AAC-04      |
| `POST /import`     | `import_data`     | `importData` (covered)  | AAC-05      |
| `POST /importfile` | `import_file`     | `importFile` (covered)  | AAC-05      |
| `GET /tasks`       | `get_task_status` | `tasks` (covered)       | AAC-06      |
| `DELETE /tasks`    | `delete_task`     | `deleteTasks` (covered) | AAC-06      |

After this increment, `routes/admin.py` is fully covered on both sides of the
wire.

Bodies, hand-mirrored (APC-03): `AtlasPatch` and `PatchStatus` in
`atlas-patches.ts`, from `aurelius_atlas_model/patches.py`; `AtlasTask` and
`TaskStatus` in `atlas-tasks.ts`, from `aurelius_atlas_model/tasks.py`;
`EntityMutationResponse` and `EntityOperation` in `atlas-mutation.ts`, from
`aurelius_atlas_model/instance/entity_mutation_response.py` and
`entity_operation.py` (the response reuses the `AtlasEntityHeader` DTO of
`atlas-search.ts` unchanged); `AtlasExportRequest`, `AtlasImportRequest`,
`AtlasImportResult`, `AtlasExportData`, and `OperationStatus` in
`atlas-impexp.ts`, from `aurelius_atlas_model/impexp.py`; and `AtlasObjectId`
in `atlas-entity.ts`, from `aurelius_atlas_model/instance/object_id.py` (the
export request's `itemsToExport` needs it, and the entity increment after this
one will too).

## Aurelius origin

- Apache Atlas 2.4.0 `AdminREST` (the health, purge, export/import, patch, and
  task routes).
- This workspace: `routes/admin.py` (paths, the plain-text health answers, the
  `{"patches": [...]}` envelope, the repeated `guids` parameter) and the
  server's specs — `libs/python/aurelius-atlas-core/specs/` (ENS, EDL, EXP,
  IMS, TSK) — cited, not restated. `AtlasClient.admin` (CL-11, CLW-01..CLW-06
  in `libs/python/aurelius-atlas-server-client/specs/8-11-client-relationship-admin-routes/`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-217 (both-sides landing) and
DD-315 (the export answer) in [`design.md`](./design.md). Against the Python
twin, three shapes differ on purpose: the Python `export` returns a
`(bytes, content-type)` tuple while AAC-04 answers the typed
`AtlasExportAnswer` pair, because an `Observable` carries no second return
value (DD-315, the DD-314 pattern); the Python `import_data` takes `bytes`
while AAC-05 takes a `Blob`, the browser-native byte container `FormData`
accepts; and on the two plain-text health routes the twin parses the Atlas
error body from the raw bytes whatever it asked for (`_error_info`, CL-04),
while AAC-01 leaves the failed text body as text — `atlasErrorFrom` does not
fire on a text request, and the caller parses the one JSON body readiness can
send. The status code, which is what readiness is asked for, is identical on
both sides.

## Acceptance

- Unit: `src/lib/atlas/admin.service.spec.ts` grows one `it()` per row naming
  its method, its URL, its body or parameters, and the rule ids (APC-10's
  pattern, extended; Vitest `HttpTestingController`).
- Unit: AAC-04's 204 answer (`body: null`, `contentType: ""`) gets its own
  `it()`, and AAC-05's plain-text `request` part (not a file part) gets its
  own `it()` — the two facts a caller can get wrong silently.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
