# 15.2 Tenant-scoped stores

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-568 to DD-571 (here); relies on 15.1 (TEN-03, TEN-04, TEN-08, DD-565,
  DD-567)

15.1 taught the server which tenant a request acts in. This increment gives each tenant its own indices and its
own type registry, and makes every route read and write the request's tenant's stores. The operator
organization keeps the indices a single-tenant deployment has, so turning tenancy on doesn't move a catalogue.

## Scope

- `aurelius-atlas-server`:
    - a tenant's index prefix (`tenant_stores.py`);
    - the store set of the default tenant and of each provisioned tenant, opened at start (`app.py`,
      `tenant_stores.py`);
    - the request's store set, for every route that reads a store (`routes/`).

Not delivered, with the increment that will:

| Not delivered                                                                                                   | Lands with |
| --------------------------------------------------------------------------------------------------------------- | ---------- |
| The `aurelius-atlas-tenants` index; creating a tenant's indices and loading its models by the CLI, not at start | 15.3       |
| The task, App Search, embedding, audit-aging and metrics-history workers per tenant; the per-tenant import lock | 15.4       |
| Offering tenancy in the chart and the standalone stack                                                          | 15.4       |

Until 15.4, a tenant's deferred tasks, App Search documents, embeddings and metrics history are not made, so
tenancy must still not be turned on in a deployment (DD-566).

## Semantics

"The tenancy setting", "a token" and "the operator organization" are as in 15.1. "The default store set" is the
indices of a single-tenant deployment, `aurelius-atlas-*`. "A store set" is the indices of one tenant's
catalogue and the type registry loaded from them.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TSS-01 | With the tenancy setting off, the server has one store set, the default, and every request reads and writes it                                                                                                                                                                                                                             |
| TSS-02 | With it on, a request acting in the operator organization reads and writes the default store set (DD-567)                                                                                                                                                                                                                                  |
| TSS-03 | With it on, a tenant other than the operator organization has its own indices: each default index name with `aurelius-atlas` replaced by `aurelius-atlas-tenant-<alias>`. That covers the entities, unique values, entity journal, relationships, classifications, tasks, governance verdicts, entity audits and type definitions (DD-568) |
| TSS-04 | With it on, the server opens the store set of each tenant in `tenancy_tenants` when it starts, as it opens the default: it creates the indices that are missing, loads the type registry from the tenant's type definitions, loads the models, and recovers interrupted writes (DD-569)                                                    |
| TSS-05 | Each store set has its own type registry. A type created in one tenant is unknown in every other, and each registry is refreshed from its own tenant's type definitions                                                                                                                                                                    |
| TSS-06 | Every route that reads or writes a store uses the request's tenant's store set: types, entities, relationships, glossary, lineage, discovery, saved searches, search by meaning, the admin audits, export, import, purge, metrics, patches and tasks, and the App Search engines (DD-570)                                                  |
| TSS-07 | The task worker, the App Search, embedding, audit-aging and metrics-history workers, and the server's start audit run on the default store set alone (DD-571)                                                                                                                                                                              |
| TSS-08 | The store's health (readiness), the import and export lock and the server's own statistics are the deployment's, shared by every tenant (DD-571)                                                                                                                                                                                           |
| TSS-09 | No answer of Apache Atlas's API changes while the tenancy setting is off                                                                                                                                                                                                                                                                   |

## Java origin

None: Apache Atlas has no tenants (ADR 063).

## Deviations

[DV-164](../../../../docs/architecture/conversion/deviations.md): with tenancy on, each tenant has a catalogue
of its own, types included, which no request of another tenant reads. While the setting is off, nothing
deviates.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_tenant_stores.py`:
    - TSS-01 to TSS-03: the index prefix of no tenant, the operator organization and a tenant, and the index
      names a tenant's store set creates;
    - TSS-04 and TSS-05: a tenant's store set opened at start with its own registry; a type and an entity
      created in one tenant, unknown and not found in another and in the operator organization;
    - TSS-06: an entity's audits and the metrics read in the request's tenant; the request's store set, which
      every route dependency and the App Search engines read, for no tenant, the operator organization and a
      tenant;
    - TSS-07 and TSS-08: the workers on the default store set; readiness the same for every tenant.
- TSS-09: the existing server suite, with tenancy off, unchanged.
- `uv run pytest apps/aurelius-atlas-server/tests` (level 0).
