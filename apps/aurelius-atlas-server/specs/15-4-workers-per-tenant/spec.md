# 15.4 Workers per tenant

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-576 to DD-579 (here); relies on 15.2 (TSS-07, TSS-08, DD-571) and 15.3
  (TPR-05, TPR-07, TPR-08, DD-574, DD-575)

15.2 gave each tenant its own store set but left the background work on the default one (DD-571). 15.3 recorded
the tenants in an index and opened a tenant's store set as it appeared. This increment gives every store set its
own workers, started and stopped with it, keeps the store sets in step with the tenants index in the
background, gives each tenant its own import and export lock, and offers tenancy in the chart and the standalone
stack.

## Scope

- `aurelius-atlas-server`:
    - the workers of a store set, started and stopped with it (`tenant_workers.py`, `tenant_stores.py`,
      `app.py`);
    - the store sets kept in step with the tenants index in the background (`tenant_workers.py`);
    - the import and export lock per store set (`tenant_stores.py`, `routes/admin.py`);
    - `provision --existing-ok`, and removal's wait (`provisioning.py`);
    - the chart's tenancy values and its provisioning Job (`helm/`);
    - the standalone stack's tenancy setting and the user guide's tenants section (`standalone/`).

Not delivered, with the increment that will:

| Not delivered                                                                                                       | Lands with  |
| ------------------------------------------------------------------------------------------------------------------- | ----------- |
| The tenants' organizations, their role groups and the operators' membership in the dev, standalone and chart realms | 15.5        |
| A sample imported by the chart's provisioning Job                                                                   | not planned |
| The webapp's tenant shown, and switching tenant                                                                     | 15.6        |

Until 15.5, a deployment that turns tenancy on sets up the realm's organizations by hand.

## Semantics

"The tenancy setting", "a store set", "a tenant's aliases" and "the command" are as in 15.1 to 15.3. "A store
set's workers" are those the settings turn on: the task worker (TSK-04), the App Search worker (ASU-06), the
embedding worker (VEC-07), the audit aging (AGE-05) and the metrics history (MHS-05).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| WPT-01 | Every open store set runs its own workers, on its own indices and type registry alone; this replaces TSS-07 for the workers. The server's start audit and its snapshot watcher stay the deployment's, on the default store set (DD-576)                                                                                                                                                                                    |
| WPT-02 | A store set's workers start when it opens, at start or later (TPR-08), and stop before it closes to requests. The server's stop stops every store set's workers                                                                                                                                                                                                                                                            |
| WPT-03 | The embedding service's client is one per server, shared by every store set's embedding worker, and closed when the server stops (DD-576)                                                                                                                                                                                                                                                                                  |
| WPT-04 | With the tenancy setting on, the server also reads the tenants index in the background every `tenancy_refresh_seconds` (one second at least), opens the store set of each tenant newly `active` and closes those of tenants no longer `active`, without a request (DD-577)                                                                                                                                                 |
| WPT-05 | `remove` waits twice `tenancy_refresh_seconds` before it deletes the tenant's indices, so every server has read the record and stopped the tenant's workers; this replaces the wait of TPR-05 (DD-577)                                                                                                                                                                                                                     |
| WPT-06 | One export or import at a time runs per store set: one in a tenant doesn't refuse one in another, and within a store set EXP-01 holds as before; this replaces TSS-08 for the lock (DD-578)                                                                                                                                                                                                                                |
| WPT-07 | `provision --existing-ok` leaves a tenant already `active` as it is and exits 0, so that it can run on every deployment; a tenant `removing` is still refused                                                                                                                                                                                                                                                              |
| WPT-08 | The chart's `tenancy.enabled` sets the tenancy setting, `tenancy.operatorOrganization` and `tenancy.refreshSeconds` theirs. With tenancy on, each tenant of `tenancy.tenants` (an alias, and `trustsOperators`, true by default) is provisioned by a Job the chart runs after each install and upgrade, with `--existing-ok`. A render fails for an alias that isn't index-safe or is the operator organization's (DD-579) |
| WPT-09 | The provisioning Job's pod reaches the store as the server does, and never receives the server's traffic: the Service selects the server's component (DD-579)                                                                                                                                                                                                                                                              |
| WPT-10 | The standalone stack's `ATLAS_TENANCY_ENABLED` sets the tenancy setting, off by default; its README shows how a tenant is provisioned                                                                                                                                                                                                                                                                                      |
| WPT-11 | With the tenancy setting off, the server runs one set of workers and one import and export lock, as before, reads no tenants index, and no answer of Apache Atlas's API changes; the chart renders no Job and no tenancy setting                                                                                                                                                                                           |

## Java origin

None: Apache Atlas has no tenants (ADR 063). Its workers and its import and export lock are one per server
(`TaskManagement`, `ImportService`), which the server keeps with tenancy off.

## Deviations

None beyond DV-163 and DV-164: no Atlas endpoint changes.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_tenant_workers.py`:
    - WPT-01 to WPT-03: a tenant's tasks run, its App Search documents and embeddings are made, in its own
      indices; its workers start with its store set and stop when it closes; the embedding client is shared;
    - WPT-04: a tenant recorded `active` is opened and its workers started without a request, one recorded
      `removing` closed;
    - WPT-06: an export in one tenant while one runs in another;
    - WPT-11: tenancy off runs one set of workers.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_provisioning.py`: WPT-05's wait and WPT-07.
- `tests/test__tenancy_chart.py`: WPT-08 and WPT-09 by `helm template`; WPT-11's render without tenancy;
  WPT-10's setting in the standalone compose file.
- `uv run pytest apps/aurelius-atlas-server/tests tests` (level 0, `helm` on the path).
