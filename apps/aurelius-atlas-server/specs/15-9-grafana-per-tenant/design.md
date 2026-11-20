# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the Design Log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-735. The stack's Grafana sits behind the proxy and signs in through Keycloak alone

- **Status:** Proposed
- **Increment:** 15.9
- **Date:** 2026-11-20

**Decision.** The stack's Grafana is served at `https://localhost:9000/grafana/` by the stack's proxy, from a
sub-path, and publishes no port. It signs a browser in through Keycloak's client `grafana` with Grafana's generic
OAuth, the only way in: anonymous access and the login form are off. Grafana runs in the proxy's network, so its
server-side calls to Keycloak use the address the browser uses, as the server's do.

**Reason.** A tenant's dashboards show the tenant's catalogue, so Grafana must know who is looking, and the
realm is where every person of the stack already is. Behind the proxy, Grafana's address is the stack's, the
issuer of its tokens is the one the browser sees, and the certificate is the stack's. Generic OAuth is in
Grafana's free edition, which the chart's Grafana already signs in with (DD-661).

**Alternatives.**

- Grafana's own users: a second password per person, and no tenant.
- Grafana on its own port with Keycloak: the issuer and the redirect name two addresses, and a second
  certificate.

**Consequences.** `http://localhost:3000` no longer answers. The local administrator is reached by the command
on the stack's network alone (TGF-12). The dev observability slice's Grafana is unchanged.

### DD-736. The command keeps a person's Grafana organizations, not the token

- **Status:** Proposed
- **Increment:** 15.9
- **Date:** 2026-11-20

**Decision.** Grafana takes no organization and no role from a person's token. The command makes each tenant
member a Viewer of the tenant's Grafana organization when it adds them to the tenant, makes them in Grafana when
they have never signed in, and takes them out when it removes them. `grafana sync` brings everyone in step with
the realm, and deletes the Grafana users the realm no longer gives a tenant (TGF-14). A person Grafana meets
first at their sign-in joins only the main organization, with no role, and sees nothing until the command adds
them.

**Reason.** Grafana can map a token's organizations to its own (`org_mapping`), but the mapping is Grafana's
configuration, read at its start: every new tenant would edit the stack's files and restart Grafana, which 15.7
removed from adding a tenant. The command already adds and removes a tenant's people in the realm; doing the
same in Grafana keeps one place that does both.

**Alternatives.**

- `org_mapping` from the token's `organization` claim: a configuration change and a restart per tenant.
- Every person in one organization, the tenant chosen by a dashboard variable: a person could read another
  tenant's data by changing the variable.
- One Grafana instance per tenant: a Grafana, a volume and an address per tenant.

**Consequences.** A person added to a tenant in Keycloak's console, not by the command, sees the tenant in
Grafana only after `grafana sync`. Grafana's own organization switcher is how an operator moves between
tenants, as the webapp's tenant switch is for the catalogue.

### DD-737. Each tenant's data sources read as a store user of that tenant alone

- **Status:** Proposed
- **Increment:** 15.9
- **Date:** 2026-11-20
- **Supersedes:** the store user `grafana_demo_reader` and `GRAFANA_ES_READER_PASSWORD` of 303fcf80d

**Decision.** Each tenant has a store user `grafana_<tenant>_reader` with a role that reads the tenant's indices
and the cluster's status, nothing else. The command generates its password and gives it to the tenant's Grafana
data sources alone; no file or variable holds it. A re-run that finds the data sources keeps the password; one
that finds the user without them sets a new one in both.

**Reason.** Grafana's Elasticsearch data source reads as one fixed store user, and the store's per-user token
realm needs a paid licence. So the isolation is the store user: a tenant member who edits a query in their
organization still reads only their tenant's indices.

**Alternatives.**

- One reader of every tenant, data sources filtered by index: an edited query reads another tenant.
- The person's own token forwarded to the store: the store's JWT realm is not in its basic licence.

**Consequences.** The store holds one more user per tenant, removed with the tenant (TGF-08).

### DD-738. The tenant dashboards ship in the server's package and are made through Grafana's API

- **Status:** Proposed
- **Increment:** 15.9
- **Date:** 2026-11-20
- **Supersedes:** the file-provisioned demo tenant data sources and dashboards of 303fcf80d

**Decision.** The dashboards _catalogue_ and _activity_ are JSON files in the server's package, with the data
sources named by fixed uids. The command creates them, and the data sources, in each tenant's Grafana
organization through Grafana's API, read-only. The platform's organization keeps the infra slice's provisioned
dashboards.

**Reason.** Grafana provisions files into an organization that exists when it starts. A tenant added later needs
its organization, data sources and dashboards made then, which only the API does. In the server's package, the
dashboards travel with the command that makes them, on any deployment.

**Alternatives.**

- Provisioning files per tenant: a file and a restart per tenant.
- The dashboards in the stack's folder, mounted into the one shot: a Kubernetes deployment would need them too.

**Consequences.** A dashboard change reaches a tenant at the next `grafana sync`, which replaces the tenant's
copy with the package's.

### DD-739. A person's first sign-in finds the Grafana user the command made, by email

- **Status:** Proposed
- **Increment:** 15.9
- **Date:** 2026-11-20

**Decision.** Grafana's generic OAuth looks a person up by email as well as by the realm's subject
(`oauth_allow_insecure_email_lookup`). The first sign-in then finds the user the command made (TGF-07) and
links it, with its organizations and roles; later sign-ins find it by the subject.

**Reason.** Without the lookup, Grafana finds no user by the subject on a first sign-in, tries to make one, and
refuses the sign-in because the login exists. Grafana has no API that links a user to a subject in advance.

**Alternatives.**

- Let the first sign-in make the user, and make the memberships at the next `grafana sync`: until then the
  person sees only the main organization, where they have no role.
- Let the first sign-in make the user and put it in its organizations with Grafana's `org_mapping`: a restart
  of Grafana for each tenant (DD-736).

**Consequences.** Grafana trusts the realm's email. The realm refuses duplicate emails and changes of username,
both by default, so an email reaches only the person who holds it in the realm. A realm that allowed duplicate
emails would need this decision revisited.
