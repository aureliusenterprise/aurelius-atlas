# 069\. Each browser-facing surface answers on its own hostname

- **Status:** Proposed
- **Date:** 2026-11-22
- **Deciders:** Aurelius Enterprise

## Decision

**A person reaches each browser-facing surface of the system at a hostname of its own, under one domain that the deployment sets once.** The product surface, the sign-in surface, the observability surface, and the vendor dashboards each answer on a hostname that says what that surface is for. The hostname names the surface and the environment it runs in. The path names what lives inside one surface, such as a page of the product or a call to its API.

Nothing that describes the machinery of a deployment enters an address a person reads. The namespace of a cluster, its release name, and its node layout appear in neither the hostname nor the path.

The deployment sets one domain, and each surface sits under it. The product answers at the domain itself, and every other surface answers at its role joined to the domain. A deployment that sets the domain `atlas.example.com` answers at these addresses:

| Address | The surface a person opens |
| --- | --- |
| `atlas.example.com` | the product |
| `auth.atlas.example.com` | the sign-in door |
| `dashboard.atlas.example.com` | the Atlas dashboards |
| `observability.atlas.example.com` | the observability surface |

A deployment names any of these differently, and a surface that is turned off has no host and no address. Another environment repeats the same addresses under its own domain, so its sign-in door never shares an address with this one.

Inside the product, the path carries what lives in one surface. On `atlas.example.com`, `/` serves the catalogue pages and `/api/` serves the catalogue API they read. No path under that host reaches the sign-in door or the observability surface, and no path names the cluster that serves it.

In a deployment, the sign-in surface never shares an address with a product surface. No other surface sets cookies on the address a person signs in at ([ADR 007](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/architecture/adr/007-one-shared-identity-provider/index.md>)).

The one exception is the bundle a person runs on their own machine to try the system ([ADR 067](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/architecture/adr/067-the-standalone-stack-ships-as-one-generated-release-bundle/index.md>)). That bundle serves every surface from one host with a path in front of each one: the product at `/`, the Atlas dashboards at `/atlas2/`, and the sign-in door at `/auth/`, all of them on `localhost`. It does so because a machine that is evaluating the system has no DNS zone and no way to trust the certificates the system issues. The exception is bounded by its purpose. It is not an arrangement for a deployment, and it must not be offered as one.

Two costs are part of the decision. Every enabled hostname needs a DNS record and a certificate. The address a person signs in at cannot change after the system holds data, so it is chosen before the first install.

Turning a surface off removes its hostname and its route. Adding a surface adds both. A deployment moves a surface to another address by setting a value, never by editing a template ([ADR 018](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)).

## Context

### How an address is built today

The chart builds every address a person reads from two parts: the domain of the deployment, and the role of the surface being opened. The role names what the person opens, which is the product, the sign-in door, the observability surface, or a vendor dashboard. The domain names the deployment they open it at. One setting carries the domain and one template joins the two, so a deployment retargets every address at once.

That split raises two questions, and this record answers both.

1. Which facts about a surface earn a place in the hostname, and which belong in the path?
2. How many surfaces share one address?

### Why it needs deciding

The addresses on the development cluster show why the first question needs an answer. They read as a list of cluster parts, because the domain chosen for that cluster names the cluster and its namespace. Nothing in the chart puts a namespace in a hostname. The domain is a naming choice, and a naming choice is cheap to change while a cluster has no users.

Three forces decide the answer, and they do not all point the same way.

- An address is the only documentation most people get. It must say what the person is opening and which environment they are in.
- The address a person signs in at is permanent. Tokens carry it, and stored references point at it. A change after the system holds data invalidates every token issued before it.
- Several environments of one system must run side by side without arguing over one address. Each must keep its own sessions and must not borrow another environment's.

### What the web platform settles

Three published rules settle the first question.

- **RFC 3986 splits an address into two scopes.** Its host names an authority, which is a name space governed as one unit. A path names a resource inside that name space.
- **RFC 6454 makes the host the unit a browser separates.** Two addresses on different hosts have different origins. Two addresses on one host differ only by path.
- **RFC 6265bis removes the path as a guard.** A cookie's path gives no reliable separation, and the standard warns against serving mutually distrusting services from different paths of one host.

A hostname is therefore the smallest part of an address that carries a trust boundary. A path carries what lives inside one boundary.

### What the largest operators do

Some of the largest cloud operators apply the same rule through their own products.

Microsoft puts the storage account in the hostname (`<account>.blob.core.windows.net/<container>`). It puts the tenant in the path only at its shared sign-in service (`login.microsoftonline.com/<tenant>`), where one address serving every tenant is the point.

Google offers both shapes for its storage service and warns that the path form serves from the same origin as the endpoint. A browser that needs its own origin must use the hostname form. Google's service platform maps a custom domain to `/` and never to a path, and its recommended layout for several services on one domain is `<service>.example.com`.

## Requirements

- R1 — An address tells a person what the surface is for and which environment it belongs to. The reader needs no knowledge of the cluster to read it.
- R2 — The sign-in address stays valid for the life of the data. Nothing forces a person to change it after the system holds entities.
- R3 — Each surface can be turned on, turned off, reached, and secured on its own. A cookie one surface sets does not reach another.
- R4 — A new environment is created with settings. No code, template, or chart fork changes ([ADR 024](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>)).
- R5 — One place decides which address belongs to which surface, and a surface does not carry its own address. No component has to agree with another about a prefix by hand.
- R6 — A deployment can move any surface to an address of its own choosing without a redesign.
- R7 — Several environments of one system can run at the same time, each with its own addresses.
- R8 — A person who runs the single-machine bundle needs no DNS zone, no host file entries beyond convenience, and no certificate work.

## Alternatives

**One host per environment, with a path in front of each surface** (`<environment>.<domain>/<app>`). It gives the plainest address of the options and it solves R7. It fails R2, because the sign-in address grows a path and the identity provider bakes that path in at its first start. It fails R3, because all the surfaces share one cookie scope, so a session cookie set at the shared address reaches every surface under it. It fails R5 hardest: every surface must then know its own prefix, so the routing rule lives in the proxy and again inside each product, and the two must agree by hand. The product today assumes it owns the root of its address (its base page and its API path are written for the root), and the identity provider assumes the same. The change is a rework of the product, the proxy, the identity provider, and the tests that pin them. The single-machine bundle uses this shape and gets away with it, because it has one user, no stored data, and no tenant separation ([ADR 063](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/architecture/adr/063-each-tenant-is-an-organization-with-its-own-store/index.md>)).

**A separate host for sign-in, and one host for every other surface.** It keeps the sign-in address clean, so R2 holds, and it is the smallest change to the chart. It fails R3, because the product and the observability surface then share one cookie scope and one route table. It still fails R5, because each surface behind the shared host must know its own prefix.

**Hostnames that carry the cluster parts, as the current development domain does.** It needs no work and fails R1. It also names the environment twice once the domain already names it.

**Do nothing, and keep the current addresses.** It fails R1, and the addresses stay a list of cluster parts for anyone who did not build the cluster.

## Tradeoffs

- **Positive:** one setting retargets a whole environment. Addresses read by purpose, so a person can tell the product from the sign-in door from the observability surface without asking. Each surface keeps its own origin, so the browser separates them on its own and no code has to work around that separation. Turning observability off removes its route and its trust boundary cleanly instead of leaving a path behind ([ADR 057](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/architecture/adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs/index.md>)). The single-machine bundle keeps its simpler shape, because the rule is bounded rather than universal.
- **Negative:** every enabled hostname needs a DNS record and a certificate. The product answers at the zone apex, and an apex takes an address record rather than a CNAME, so the edge address is reserved. A wildcard certificate and a wildcard DNS record both stop at the subdomains, so the apex carries its own name in each. A public certificate issuer limits how many certificates one registered domain can issue in a period. In-cluster workloads dial the sign-in address too, so a private DNS view must name every host. The certificate's list of names must grow and shrink with the surfaces a deployment turns on, which one template derives today.
- **Neutral / follow-ups:** the development cluster's domain still names the cluster, so its addresses still read as a list of cluster parts. It needs a rename, and the runbook already documents how to rename hosts. This record decides how addresses are built, not what the domain is. The chart derives the product host at the apex and names the observability host `observability.<domain>`, and the runbook and the user guide carry those addresses. The values keys stay `app` and `o11y`, so the listener names, the route names, and the realm asset's host placeholders keep their names while the addresses they resolve to change. The single-machine bundle knowingly shares one address between the product and the sign-in surface, for that audience only.

> [!NOTE]
>
> **Does every hostname need its own firewall rule?**
>
> No. The system serves every hostname through one gateway, so a network that allows traffic to the system allows one address. A layout that puts the surfaces in paths resolves to that same address, so the count does not change. The new work is name resolution, and a private DNS view must answer for each hostname. A firewall rule adds a guard rather than granting access, because the identity provider decides admission and not the address a request arrives from ([ADR 007](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/architecture/adr/007-one-shared-identity-provider/index.md>)). A deployment that wants a stricter rule gains one, because a surface with its own hostname can move to its own load balancer and carry its own rule with it.
