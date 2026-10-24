# aurelius-atlas-server

The Aurelius Atlas server: the Apache Atlas 2.4.0 REST API, implemented in Python on Elasticsearch
([ADR 046](../../docs/architecture/adr/046-the-catalogue-keeps-its-public-contract.md),
[ADR 047](../../docs/architecture/adr/047-one-search-store-is-the-system-of-record.md)).

Introduced by increment 0.5 with the admin endpoints; every later increment adds the endpoints of its
Atlas resource. What is ported, and how, is tracked in the
[conversion ledger](../../docs/architecture/conversion/index.md).

## Endpoints

| Endpoint                          | Answers                                                               |
| --------------------------------- | --------------------------------------------------------------------- |
| `GET /api/atlas/admin/version`    | Name, release and revision of the server                              |
| `GET /api/atlas/admin/status`     | `{"Status": "ACTIVE"}` while the server runs                          |
| `GET /api/atlas/admin/session`    | The dashboard's settings and the user (no login until 6.1)            |
| `GET /api/atlas/admin/liveness`   | `Service is live` while the server runs                               |
| `GET /api/atlas/admin/readiness`  | `Service is ready to accept requests` while Elasticsearch is healthy  |
| `/api/atlas/v2/types/...`         | The type definitions: read, search, create, update and delete         |
| `GET /api/atlas/v2/entity/...`    | Entities and their headers by GUID or unique attributes, one or many  |
| `POST`/`PUT /api/atlas/v2/entity` | Entities created or updated, in bulk, by unique attributes or by GUID |
| `DELETE /api/atlas/v2/entity/...` | Entities deleted by GUID, in bulk or by unique attributes             |
| `PUT /api/atlas/admin/purge`      | Deleted entities removed for good                                     |
| `/api/atlas/v2/search/basic`      | Entities by type, attribute filters, sort and paging                  |

## Dashboards

The server also serves the Apache Atlas 2.4.0 dashboards from
[`aurelius-atlas-dashboard`](../aurelius-atlas-dashboard/README.md): `dashboardv2` at `/` and
`dashboardv3` at `/n/`. The API is matched first. The image contains them; outside the image,
`AURELIUS_ATLAS_SERVER_DASHBOARD_DIR` names the built directory, and without it only the API is served.

## Type definitions

At start-up the server loads the type definitions stored in Elasticsearch (the `aurelius-atlas-typedefs`
index) into its type registry, through [`aurelius-atlas-core`](../../libs/python/aurelius-atlas-core/README.md).
It checks for another process's type change at most every `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS`
(default 5). Then it loads Apache Atlas's built-in models and applies their patches, as Atlas does from
`$ATLAS_HOME/models`: by default the 2.4.0 models shipped with the server, or the directory
`AURELIUS_ATLAS_SERVER_MODELS_DIR` names, laid out as Atlas's. Only new types, newer `typeVersion`s and patches
not applied before change anything, so a restart writes nothing.

The 26 endpoints of Atlas's `TypesREST` (`aurelius_atlas_server/routes/types.py`) read and change the
definitions through that store. `GET typedefs` and `typedefs/headers` take Atlas's filter parameters (`type`,
`name`, `servicetype`, `supertype`, their `not` forms and `excludeInternalTypesAndReferences`) and list each kind
sorted by name (DD-034).

## Entities

The reads of Atlas's `EntityREST` (`aurelius_atlas_server/routes/entity.py`) answer entities from the entity
store as Atlas does: `guid/{guid}`, `uniqueAttribute/type/{typeName}` with `attr:<name>=<value>`, their
`header` forms, and `bulk` by `guid` or by `attr_<n>:<name>=<value>` sets, with `minExtInfo` and
`ignoreRelationships`. Its writes create and update entities through the entity writer: `POST` with one entity
and those it names, `POST bulk`, `PUT uniqueAttribute/type/{typeName}` and `PUT guid/{guid}?name=<attribute>`,
each answering Atlas's `EntityMutationResponse`. Classifications and business attributes given with an entity
are ignored until their increments. Relationship attribute values, legacy ends among the attributes included,
become relationships, and reads answer them in `relationshipAttributes` (DD-064). An update that drops an owned
entity deletes it, listed under `DELETE` in the response (DD-068).

Classifications are attached, read, changed and removed by `guid/{guid}/classifications`,
`guid/{guid}/classification/{name}`, their `uniqueAttribute` forms and `bulk/classification`; entities read
with them, and an entity create attaches those it gives (DD-070). `bulk/setClassifications` sets entities'
classifications to those of their headers. Classifications propagate over relationships through tasks that a
worker in every server process runs after the request (DD-079, DD-080); entities list theirs in
`pendingTasks`, and `GET`/`DELETE /api/atlas/admin/tasks` read and remove them. With
`AURELIUS_ATLAS_SERVER_TASKS_ENABLED=false` propagation happens within the request instead (DD-077, DD-081).
`bulk/headers` lists the entities whose classifications changed since a time, from their audit events.

Each entity a write, delete or purge changes, and each classification attached, changed, removed or
propagated, gets an audit event in the index behind
`aurelius-atlas-entity-audits`, written once the change has committed (DD-082); `GET {guid}/audit` lists them
newest first from a `startKey`, by `auditAction`, or sorted by `sortBy` and paged by `offset` and `count`, as
the dashboards' audit tab asks.

Its deletes (`DELETE guid/{guid}`, `DELETE bulk`, `DELETE uniqueAttribute/type/{typeName}`) delete an entity
with the entities it owns and change those referring to it; `PUT /api/atlas/admin/purge` removes deleted
entities for good. Deletes are soft unless `AURELIUS_ATLAS_SERVER_DELETE_TYPE` is `hard`; with
`AURELIUS_ATLAS_SERVER_DELETE_TYPE_OVERRIDE=true` a request's `deleteType` chooses (DD-059).

## Relationships

The endpoints of Atlas's `RelationshipREST` (`aurelius_atlas_server/routes/relationship.py`) create, read,
update and delete relationship instances; deleting an entity deletes its relationships with it. An entity
write creates, reuses and deletes the relationships its relationship attributes name, in the same write
(DD-066).

## Search

The basic search endpoints of Atlas's `DiscoveryREST` (`aurelius_atlas_server/routes/discovery.py`) find
entities by type, with sub types or of every type (`_ALL_ENTITY_TYPES`), by attribute filters with Atlas's
operators, by state, sorted and paged by offset or marker: `POST` and `GET search/basic` and `GET
search/attribute`. Entity attributes are searched in typed fields named after the type that defines them
(DD-088); classification search follows in 4.1b, free text in 4.2.

## Running it

```bash
npx nx serve aurelius-atlas-server   # builds the dashboards, starts the dev store and observability; https://localhost:21000
```

The server does not start without its store. Settings are environment variables prefixed
`AURELIUS_ATLAS_SERVER_`; see `aurelius_atlas_server/settings.py` for the full list.
