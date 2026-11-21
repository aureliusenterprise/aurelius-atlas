# 12.7f The verdicts per tenant

- **Status:** in progress
- **Pull request:** to follow
- **Records:** VET-01 to VET-05 and DD-820 (here); DD-820 supersedes DD-499 for a caller acting in a tenant;
  amends VEV-04 and VEV-05 (12.7) for that caller. Relies on 15.1 (TEN-02 to TEN-04, the organization claim)
  and 15.2 (each tenant's own indices).

With tenancy on, the editor shows no governance verdict at all. The app reads the rules as its own service
account (VEV-04, DD-499), whose token names no organization, so the server refuses the search (`AURELIUS-403-00-001
… acts in no tenant`, TEN-03) and the app answers 502 on every keystroke. Each tenant's rules live in its own
indices (15.2), so the read must act in the caller's tenant. This increment reads them with the caller's token,
and caches them per tenant. Without tenancy nothing changes.

## Scope

- `aurelius-atlas-validate-entity`: the tenant read from the caller's verified token (`tenancy.py`, new), the
  rule read and cache keyed by it (`verdicts.py`), and the route passing the caller's token and tenant
  (`routes/validate.py`).

## Semantics

| Id     | Rule                                                                                                                                                                                                                                 |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| VET-01 | The caller's tenant is the one organization its verified token's `organization` claim names: a list of aliases or an object keyed by them, as the server reads it (TEN-02). A token naming none, or more than one, acts in no tenant |
| VET-02 | For a caller acting in a tenant, the rule search carries the caller's own bearer token, so the server answers that tenant's rules (TEN-03, 15.2). This replaces VEV-04's service identity for that caller (DD-820)                   |
| VET-03 | A caller acting in no tenant reads as before: the app's own service identity (VEV-04, DD-499)                                                                                                                                        |
| VET-04 | The read set is cached per tenant, and once for the callers acting in no tenant, each for `RULES_CACHE_SECONDS` (VEV-05). A tenant's cached set never answers another tenant's caller, nor a caller acting in no tenant              |
| VET-05 | A failed read of one tenant caches nothing for it and answers 502 (VEV-05, VEV-06); the other tenants' sets stay. A refusal of the caller's token by the server is that 502 too, never a no-rules answer                             |

## Java origin

None: the validate-entity service is the legacy Aurelius `m4i-validate-entity`, and Apache Atlas has no tenants.

## Deviations

None from Atlas. From the legacy, which had no tenants: none.

## Acceptance

- `apps/aurelius-atlas-validate-entity/tests/test__aurelius_atlas_validate_entity_tenancy.py`: VET-01.
- `apps/aurelius-atlas-validate-entity/tests/test__aurelius_atlas_validate_entity_app.py`: VET-02 to VET-05 against
  the fake catalogue.
- By hand on the standalone stack: editing a demo entity, the name rule's verdict shows, and turns from warning
  to check while typing a name.
