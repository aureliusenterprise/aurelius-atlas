# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the Design Log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-767. A tenant's dashboards are for its stewards, administrators and trusted operators

- **Status:** Proposed
- **Increment:** 15.10
- **Date:** 2026-11-21
- **Supersedes:** the half of TGF-07 that makes every member of a tenant a Viewer of its Grafana organization,
  and TGF-14's "a member of an active tenant"

**Decision.** The Viewers of a tenant's Grafana organization are its members in the group `atlas-write`, which
the roles `atlas` and `steward` grant, and the operators its trust made members. The server answers the webapp's
menu item by the same rule: `atlas-write` in the token's tenant groups, or the token's subject among the record's
`operatorMembers`. The webapp's tokens carry no realm roles, so the operator role can't be read from them.

**Reason.** The dashboards summarise the whole catalogue and its changes by user, which the tenant's owners chose
to show to the people who curate it. A menu that hid the link while Grafana still let a scientist in would hide
nothing; the rule holds in both places.

**Alternatives.**

- Every member, as in 15.9: the owners asked for fewer.
- A dashboards group of its own per tenant: one more group to grant by hand, for a rule the roles already draw.

**Consequences.** A data scientist's Grafana user is deleted at the next `grafana sync` (TDL-03). A role changed
in Keycloak's console shows in the webapp at the next sign-in and in Grafana at the next `grafana sync`.

### DD-768. The tenant record holds its Grafana organization id; the server never calls Grafana

- **Status:** Proposed
- **Increment:** 15.10
- **Date:** 2026-11-21

**Decision.** The command, which already keeps each tenant's Grafana organization, writes its id into the tenant
record. The server answers the dashboards link from the record, the token and its Grafana address for the
browser; it calls no Grafana API.

**Reason.** The link needs the organization id: a person in two tenants would otherwise land in whichever
organization Grafana last opened, where the dashboard's uid names that tenant's dashboard, not this one's.
Asking Grafana per request would give the long-running server Grafana's admin password and make the menu depend
on Grafana answering.

**Alternatives.**

- The server asks Grafana's admin API for each person: exact to the second, at the cost above.
- Grafana organizations found by name in the browser: Grafana has no link by organization name.

**Consequences.** A tenant whose Grafana organization was made before 15.10 gets its id at the next `grafana
sync`, which the standalone stack's seeding runs.

### DD-769. One menu item, the catalogue, in a new tab

- **Status:** Proposed
- **Increment:** 15.10
- **Date:** 2026-11-21

**Decision.** The account menu shows one item, "Dashboards", under "Switch tenant". It opens the tenant's
catalogue dashboard in a new browser tab.

**Reason.** Grafana lists the tenant's other dashboard, activity, one click away, and the menu stays one line.
A new tab keeps the webapp open where the person was.

**Alternatives.**

- One item per dashboard: the menu grows with every dashboard the package ships.
