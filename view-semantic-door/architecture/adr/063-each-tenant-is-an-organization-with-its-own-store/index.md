# 063\. Each tenant is an organization with its own store

- **Status:** Proposed
- **Date:** 2026-11-13
- **Deciders:** Aurelius Enterprise

## Decision

**One deployment of Aurelius Atlas serves several tenants, each isolated from the others, and one operator organization runs the platform.**

- **A tenant is an organization of the identity provider.** Its members are its users.
- **A token names one tenant.** A request acts in that tenant alone.
- **Roles are held per tenant.** The same person can hold different Atlas roles in each organization they belong to.
- **Each tenant has its own administrators.** A tenant administrator manages the tenant's members and their Atlas roles, and nothing outside the tenant. This uses the identity provider's own delegated administration of an organization, not an add-on.
- **Each tenant has its own indices in the store.** That covers its entities, relationships, classifications, audits and type definitions. A request never reads or writes another tenant's indices.
- **A tenant must be provisioned before use.** Until its indices exist and its models are loaded, a token naming it is refused.
- **Every tenant starts with the base types.** Provisioning loads Apache Atlas's models and the m4i types into each tenant's indices.
- **Sample data is optional.** Whoever deploys a tenant chooses whether the sample catalogue is loaded into it.

**The operator organization.** One organization, the default, belongs to the people who run the platform.

- **Its own catalogue.** It is a tenant like any other, and it keeps the index set a single-tenant deployment has. An existing catalogue becomes the operator organization's when tenancy is turned on.
- **Direct store access.** Operators may read every tenant's indices directly in the store, for operations and support. That access is granted in the store, outside the catalogue's API.
- **Trust.** A tenant trusts the operator organization unless it is deployed without that trust, or withdraws it later. While a tenant trusts them, the operators are members of its organization with read access only, so they read it by signing in to it, as its own users do. A tenant that doesn't trust the operators is closed to them through the API.
- **Read-only, whatever is configured.** Through the API, an operator never holds more than read access in another tenant, even if the identity provider grants more.

Tenancy is off by default. While it is off, the catalogue answers exactly as Apache Atlas does ([ADR 046](<https://aureliusenterprise.github.io/view-semantic-door/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). Once it is on, the tenant and the roles come only from the token's claims, never from a header, a path or a parameter that the caller could choose.

Sharp edges:

- **Tenants share no catalogue.** No search, lineage or relationship crosses tenants. An operator reads one trusted tenant per sign-in, never several at once through the API.
- **Direct store access bypasses trust.** The operators' store access reaches every tenant's indices, trusted or not. It is for running the platform, and the deployment must grant it only to the people who do.
- **Types don't flow between tenants.** A type one tenant defines is invisible to the others, and an upgrade of the built-in models reaches each tenant through its own load.
- **Each tenant multiplies the indices and background work.** The deployment's cost rises with the number of tenants, not only with their data.

## Context

Customers of Aurelius Atlas want to run one catalogue platform for several organizations: subsidiaries that must not see each other's data, or a provider hosting several customers. Today each of them needs a deployment of its own. That means its own identity realm, its own store cluster and its own operations, and the cost of running the platform grows with every customer.

The people who run such a platform need to see what its tenants see, to answer support questions and to check that the platform works. They also need the store itself, to back it up, repair it and size it. A tenant, on the other hand, may want to keep its catalogue closed even to the platform's operators.

A new tenant either starts empty, ready for its own sources, or starts with sample data to explore and train on. Either way, it needs the base types before it can hold anything.

Apache Atlas has no notion of a tenant. Its authorization grants privileges to users and groups across the whole catalogue. Customers can't buy isolation by configuration. Isolation by convention, such as naming prefixes or classifications that mark ownership, fails open: one missed filter shows a customer's data to another.

The identity provider already manages organizations. It records who belongs to which organization, lets a person belong to several, and lets the person choose which one to act for at sign-in.

## Requirements

- **R1.** A tenant's users can't read or change another tenant's data, types included, through any endpoint.
- **R2.** A person can belong to several tenants, with different rights in each.
- **R3.** The tenant a request acts in is decided by the identity provider, not by anything the caller can choose.
- **R4.** Removing a tenant removes all its data, and nothing of the other tenants.
- **R5.** A single-tenant deployment keeps Apache Atlas's API, behaviour and parity, and its catalogue survives turning tenancy on.
- **R6.** One deployment serves many tenants, without a cluster or identity realm per tenant.
- **R7.** Operators can read every tenant that trusts them, can never change one, and can reach the whole store for operations.
- **R8.** A tenant decides whether operators may read it through the API. By default they may.
- **R9.** A new tenant starts with the base types, and with the sample data if its deployer chooses.
- **R10.** Each tenant has administrators of its own, who manage its members and their roles, and who can't manage any other tenant or the platform.
- **R11.** Every part of the identity solution can be run as a hosted service for customers without a further licence, and is maintained with the identity provider itself.

## Alternatives

- **A deployment per tenant (do nothing).** This meets R1 to R5 trivially and fails R6. The cost of running the platform grows with every customer.
- **Shared indices with a tenant field on every document.** This meets R6 with the fewest indices. It meets R1 only as long as every query in every store keeps its tenant filter, so one missed filter fails it. R4 becomes a delete-by-query across shared indices.
- **An identity realm per tenant.** This meets R1 and R3. It fails R2: a person in two realms is two people, with two passwords. It also multiplies the provider's configuration with every tenant.
- **Tenant chosen by a header or a path.** This is simple for clients and fails R3: the server would have to check the caller's right to every tenant they name, which puts the decision back into a second table of who belongs where.
- **Operators read every tenant through the API, without trust.** It is simpler, and it fails R8: a tenant could not close its catalogue to the platform's people.
- **A third-party organizations extension for the identity provider.** One mature extension offers administration roles per organization that are finer than the provider's own, such as managing members apart from the organization's settings. It meets R10, and it fails R11. Its licence forbids offering it as a hosted or managed service without a commercial licence. It is maintained by a single vendor, outside the provider's releases. And it replaces the provider's native organizations, which its vendor's own images turn off.
- **Our own tenant administration screens.** They manage members and roles through the provider's administration API under a service account. They meet R10 and R11, but they build and secure again what the provider now offers natively, and every check they make is ours to get right.
- **Operators as ordinary members, without a cap.** Trust kept only as membership in the identity provider: one wrong group assignment would let an operator change a tenant's catalogue, failing R7.

## Tradeoffs

- **Positive:**

  - Isolation holds by construction: a request reaches only its tenant's indices, so no query can forget a filter.
  - Removing a tenant drops its indices.
  - The identity provider stays the one place that says who belongs to which tenant with which rights, as [ADR 038](<https://aureliusenterprise.github.io/view-semantic-door/architecture/adr/038-what-a-person-may-do-is-decided-in-one-place-apart-from-who-they-are/index.md>) asks. Operator trust is membership like any other, so the server needs no second table of who may read what.
  - A single-tenant deployment turns tenancy on without moving its data.
- **Negative:**

  - The store's index count grows with the tenants.
  - The background work (embeddings, App Search documents, tasks) runs per tenant.
  - Each tenant loads and upgrades its own models.
  - Service identities such as the scanners must each be bound to one tenant.
  - Trust has to be kept in step with the operator organization's members: an operator who joins later must be added to every trusting tenant, and one who leaves removed.
  - Operators' direct store access sits outside the catalogue's authorization and audit.
  - A tenant administrator controls the whole organization: its settings, groups and sign-in providers. The provider can't yet grant one of these without the others.
  - The provider lets a tenant administrator assign the tenant's roles to its members, but adding, listing or removing members also needs rights over every user of the realm. Until the provider scopes those rights to an organization, members join by invitation or through a platform administrator, unless a later decision gives tenant administrators their own way to do it.
  - Delegated administration of organizations is new in the provider. Its permission checks had fixes in the release that introduced it, so it is verified before a tenant administrator is relied on, and again on each upgrade of the provider.
- **Neutral / follow-ups:**

  - The webapp has to let a person in several organizations choose one, and switch.
  - Provisioning, trust and removing a tenant become operator tasks.
  - The increments of series 15 deliver this step by step. While tenancy is off, nothing changes for existing deployments.
