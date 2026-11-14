# 15.3 Tenant provisioning

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-572 to DD-575 (here); relies on 15.1 (TEN-04, DD-565, DD-567) and 15.2
  (TSS-03, TSS-04, DD-568, DD-569)

15.1 and 15.2 took the provisioned tenants from the setting `tenancy_tenants`, a stand-in. This increment
records the tenants in an index of their own, and adds the command that provisions a tenant, changes its trust
of the operators, lists the tenants and removes one. The server reads which tenants are provisioned from that
index, so a tenant provisioned while the server runs is served without a restart.

## Scope

- `aurelius-atlas-server`:
    - the tenants index and its records (`tenants.py`);
    - the command `python -m aurelius_atlas_server.provisioning` (`provisioning.py`);
    - the provisioned tenants read from the index, kept current, and their store sets opened as they appear
      (`tenants.py`, `tenant_stores.py`, `authentication.py`, `oidc_client.py`, `app.py`);
    - the setting `tenancy_tenants` removed, `tenancy_refresh_seconds` added (`settings.py`).

Not delivered, with the increment that will:

| Not delivered                                                                                                 | Lands with |
| ------------------------------------------------------------------------------------------------------------- | ---------- |
| The workers per tenant; the per-tenant import lock; the provisioning Job in the chart; tenancy offered        | 15.4       |
| The tenant's organization, its role groups and the operators' membership kept in step with the recorded trust | 15.5       |

Tenancy must still not be turned on in a deployment before 15.4 (DD-566).

## Semantics

"The tenancy setting", "a token", "the operator organization" and "a store set" are as in 15.1 and 15.2. "The
command" is `python -m aurelius_atlas_server.provisioning`, run with the server's settings in its environment.
"A tenant's aliases" are the default store set's aliases with the tenant's prefix (TSS-03).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TPR-01 | The index `aurelius-atlas-tenants` holds one record per tenant, under its alias: its state (`provisioning`, `active` or `removing`), whether it trusts the operators, the sample it was provisioned with if any, when it was created and last changed, and by whom (DD-572)                                                                                                                                            |
| TPR-02 | `provision <alias>` refuses an alias that is not index-safe (DD-565), the operator organization's, or one already `active` or `removing`. Otherwise it records the tenant `provisioning`, opens its store set as the server opens the default (TSS-04), imports the export ZIP `--sample` names if given, and records the tenant `active` (DD-573)                                                                     |
| TPR-03 | A tenant is recorded as trusting the operators unless `provision` is given `--no-operator-trust`. `trust <alias> on` and `trust <alias> off` change that on a recorded tenant. The server does not read it (DD-567)                                                                                                                                                                                                    |
| TPR-04 | `provision` of a tenant left `provisioning` by an interrupted run carries on from the start: opening a store set and importing a sample are idempotent                                                                                                                                                                                                                                                                 |
| TPR-05 | `remove <alias>` refuses the operator organization and an alias with no record. Otherwise it records the tenant `removing`, waits `tenancy_refresh_seconds` so that no server still serves it (TPR-07), deletes every index behind each of the tenant's aliases, and deletes its record. It never deletes by a pattern, so no index of another tenant is touched (DD-574)                                              |
| TPR-06 | `list` prints each recorded tenant: its alias, state, trust and sample. Every command exits 0 when it did what was asked, 1 with the reason on standard error when it refused                                                                                                                                                                                                                                          |
| TPR-07 | With the tenancy setting on, the provisioned tenants are the operator organization and the tenants recorded `active`; this replaces `tenancy_tenants` in TEN-04 and TSS-04, and the setting is removed. The server reads the index when it starts and again at most every `tenancy_refresh_seconds` (30 by default) as requests arrive. A browser session whose tenant is no longer provisioned is signed out (DD-575) |
| TPR-08 | The server opens each `active` tenant's store set when it starts, loading the models (TSS-04). A tenant that becomes `active` later is opened on its first request, without loading the models, which its provisioning loaded. A store set whose tenant is no longer `active` is closed to requests                                                                                                                    |
| TPR-09 | With the tenancy setting off, the server neither creates nor reads the tenants index, and no answer of Apache Atlas's API changes                                                                                                                                                                                                                                                                                      |

## Java origin

None: Apache Atlas has no tenants (ADR 063).

## Deviations

None beyond DV-163 and DV-164: the command is Aurelius's own, and no Atlas endpoint changes.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_tenants.py`:
    - TPR-01: a record written, read and listed, as the index holds it;
    - TPR-07 and TPR-08: a tenant provisioned while the server runs is refused until the next read, then served
      from its own store set; a removed tenant refused after the next read, its store set closed and its
      browser session signed out; the operator organization always served; only the tenants opened at start
      load the models; the setting off reads no index.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_provisioning.py`:
    - TPR-02 and TPR-03: a tenant provisioned with and without trust and a sample, its indices and models in place,
      its record `active`; the refused aliases;
    - TPR-04: a `provisioning` record carried on;
    - TPR-05: a tenant removed, every index of its aliases gone, the indices of a tenant whose alias it prefixes
      kept;
    - TPR-06: `list`, `trust`, and the exit codes.
- `uv run pytest apps/aurelius-atlas-server/tests` (level 0).
