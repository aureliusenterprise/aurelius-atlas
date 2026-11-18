# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-678. One host value, reached through the proxy's network and its extra_hosts

- **Status:** Proposed
- **Increment:** 17.2
- **Date:** 2026-11-18
- **Supersedes:** nothing. It generalises the literal `localhost:9000` the series 9.5 and 17.1 stack carried,
  and the `https://localhost:9000/auth` issuer DD-669 and DD-673 fixed.

**Decision.** The stack reads one value, `STANDALONE_HOST`, default `localhost`. It interpolates into the
Keycloak `KC_HOSTNAME` and issuer, into each application's issuer and token URLs, into the sample import's
and tenants' URLs, and into the collector's validated `issuer_url`. No application code changes: each already
takes its issuer as a setting. The proxy, whose network the server and the three aux apps already share
(`network_mode: service:proxy`), carries `extra_hosts: ["<host>:127.0.0.1"]`. Because an `extra_hosts` entry
lands in `/etc/hosts` of that shared network namespace, every container in it resolves the host to the proxy
and dials the browser port on the proxy. The browser resolves the host by the operator's own DNS or
`/etc/hosts`.

Two files the browser reads are composed by hand rather than interpolated, because their images have no
templating at rest: `docker/gateway/nginx.conf` (its `server_name` is the host) and the webapp's
`config.json` (its `keycloak.url` is the browser's issuer, which keycloak-js resolves with `new URL(...)` and
so cannot be a relative path). The `gateway-config` one shot, beside them, replaces the `@STANDALONE_HOST@`
placeholder in both with the container's environment value before the proxy starts, into volumes the proxy
mounts; the proxy answers `/config.json` itself from the rendered copy, so the browser always receives the
file that names its own host. The webapp's bind-mounted copy keeps its literal `localhost` and serves no
browser. The collector's `issuer_url` uses its own templating (`${env:STANDALONE_HOST}`, confmap's env
provider), with the compose piece giving the container the variable and its default.

**Reason.** `libs/python/aurelius-atlas-auth` uses one string for two jobs: the issuer root is both the URL it
dials for discovery and JWKS and the value it asserts as the token's `iss` claim (`KeycloakAuth.base_url`
feeds `jwt.decode(..., issuer=...)`). A split "dial this, expect that" was measured to be absent, and adding
it would be a library change with parity consequences. The cleaner move keeps the one string honest: an
application dials exactly the issuer it expects, because the host maps to the proxy in its own network
namespace. That is how the stack already works for `localhost` — the apps share the proxy's namespace, so
`localhost:9000` is the proxy. `extra_hosts` generalises that same fact to any host with one line, and keeps
the proxy as the single entry the browser and the apps agree on (SPS-01, SPS-04).

**Alternatives.**

- Add a dial-versus-expect split to the auth library. Rejected: it touches the token verifier every service
  and the chart share, needs new rules and parity review, and buys nothing the namespace mapping does not.
- Run each app on the stack network and give it a `host:` alias there. Rejected: the apps already share the
  proxy namespace so their issuer host is the proxy's; moving them off it re-opens the e2e network shape and
  splits the server from its proxy sidecars (sample-import, tenants).
- Tell the operator to add the host to each container with `docker exec`. Rejected: not declarative and not
  reproducible across a recreate.

**Consequences.** The host is a value the bundle's `.env.example` names and the README sets. The proxy's
`extra_hosts` is the only new mechanism, and it is one line. A host that is not `localhost` needs an
`/etc/hosts` or DNS entry on the browser machine — documented, not automated. The `nx serve` and e2e stacks
keep the `localhost` default and see no change.

### DD-679. Only the edge leaf names the browser host

- **Status:** Proposed
- **Increment:** 17.2
- **Date:** 2026-11-18
- **Supersedes:** nothing. It makes explicit the trust split the stack's `proxy_ssl_name` lines and each
  service's `tls.json` already implied.

**Decision.** The browser host appears in exactly one certificate: the proxy's edge leaf, presented as
`aurelius-atlas-server` today. It keeps `localhost` and `127.0.0.1` too, so the browser path and any
loopback dial both verify. Every internal leaf — the webapp's, the embedder's, the three aux apps', the
collector's, Elasticsearch's — keeps its service name as its only meaningful SAN, and the proxy reaches each
with `proxy_ssl_name <service-name>`. Changing the host never re-issues an internal leaf.

**Reason.** The internal hops are in-network and resolve by Docker service name, so their TLS verification
names the service, not the browser host. Putting the browser host in an internal leaf would be wrong
(nothing dials that name internally) and would force a re-issue of eight certificates on every host change.
The stack already verifies this way (`proxy_ssl_name aurelius-atlas-webapp`, `... otel-collector`), so the
rule writes down an existing shape and turns it into a contract a test can pin (SPS-02, SPS-03).

**Alternatives.**

- Put the host in every leaf. Rejected: over-trusts and re-issues eight certificates to name something no
  caller uses.
- Use one wildcard leaf for everything. Rejected: a wildcard cannot name distinct service names and a host
  at once, and it hides which hop trusts what.

**Consequences.** A host change touches one leaf. The script (DD-681) issues the edge leaf with the host plus
`localhost` and `127.0.0.1`, and the internal leaves unchanged. The internal leaves and the CA are still
mounted, never installed into a trust store, so a private CA needs no OS step on the host (SPS-10).

### DD-680. The realm host comes from the import, and a host change on a full store has two documented paths

- **Status:** Proposed
- **Increment:** 17.2
- **Date:** 2026-11-18
- **Supersedes:** the implicit assumption in 17.1 (DD-673) that the realm asset's literal `localhost` redirect
  URIs are fixed for the stack's life.

**Decision.** The two clients that carry browser URIs in `docker/keycloak/aurelius-atlas.json` (`aurelius`,
`aurelius-atlas-server`) replace their literal `https://localhost:9000` with a placeholder resolved by the
realm import's existing `replace-placeholders` mechanism, the same JVM flag that already resolves the client
secrets. The stack's `KC_HOSTNAME` is set to `https://<host>:9000/auth`. On a fresh store the import lands the
host with no further step. The suite and docs state the limit, measured on Keycloak 26.7: a start with
`--import-realm` on a realm that already exists logs `Import skipped` (strategy `IGNORE_EXISTING`), so the
stored redirect URIs do not move. Two paths are documented (SPS-07):

- Empty the store: `down -v`, then start with the new host. The realm re-imports for the new host, and the
  store is empty. This matches the README's existing "`down -v` empties the demo".
- Keep the data: re-point the two clients through the Keycloak admin API (a one-shot or a documented command
  that PUTs the clients' `redirectUris`, `webOrigins`, and post-logout URIs for the new host). The catalogue
  and Keycloak's own realm data survive.

**Reason.** Keycloak's import is create-if-absent by design, so no restart can refresh an existing realm; an
attempt to make the stack do it silently would be a surprise. A try-me's honest answer for "change the host"
is the wipe path, and a customer who imported data needs the admin-API path. Documenting both, with the
measured behaviour and the Keycloak version named, lets the operator choose instead of guessing (DD-673's
production-posture realm is otherwise unchanged).

**Alternatives.**

- Always admin-API re-point on every start. Rejected: a create-time import already does the work on a fresh
  store, and an unconditional API write would fight the operator who edited a client by hand.
- Delete and re-import the realm on a host change. Rejected: it drops any user the operator added through the
  admin console, which is exactly the data the keep-data path exists to save.
- A Helm-style render that bakes the host into the asset. Rejected for compose: there is no templating step
  between the committed asset and Keycloak, and `replace-placeholders` already bridges that gap (the chart
  uses a literal `__APP_HOST__` replace for the same reason — hosts are deployment topology, not credentials).

**Consequences.** The realm asset names no literal host, so a test can require the placeholder. The
`--hostname` option is a Keycloak runtime option (feature `hostname:v2`, already on through the stack's
`preview` feature), so the hostname change is a restart, not a re-augment (DD-676's prod-mode build is
unaffected). The two paths are README text and one tested admin-API command, not new stack services.

### DD-681. One shipped certificate script built on openssl, with bring-your-own as the default posture

- **Status:** Proposed
- **Increment:** 17.2
- **Date:** 2026-11-18
- **Supersedes:** the requirement that a stack operator run `nx certgen` per project (seven projects) to
  obtain the stack's certificates. The `nx certgen` path stays for the e2e and `nx serve` dev stacks.

**Decision.** The stack ships one script that creates a CA and issues the leaves the stack mounts: the edge
leaf for the host plus `localhost` and `127.0.0.1`, and the internal leaves for their service names. It uses
`openssl` with a config file only — the leaf-issuing core of `tools/tls/certgen.sh`, which issues serverAuth
and clientAuth leaves with `openssl` against a CA. It does NOT install the CA into any system or browser
trust store (the `mkcert -install` step of `certgen.sh` is deliberately left out). The customer may instead
place their own CA and leaves at the same paths, and then the script is unused. The stack trusts the CA only
by bind mount, so the browser warns once for the host — stated as expected in the README.

**Reason.** A customer cannot run `nx certgen`: it needs the repo's tools and an age key. Bring-your-own
certificates is the production posture and what an enterprise evaluation expects, so it is the default. The
script exists so that a try-me is still possible without a PKI on hand. Building on `openssl` means it runs
anywhere Docker runs, with no mkcert and no system mutation. Reusing `certgen.sh`'s leaf logic keeps the two
paths issuing the same shape of certificate (serverAuth and clientAuth), so a customer leaf behaves like a
dev leaf (SPS-09).

**Alternatives.**

- Require bring-your-own with no script. Rejected: it makes the try-me need a PKI, which defeats a try-me.
- Ship pre-made certificates. Rejected: they cannot name the customer's host, and a committed private key is a
  security problem.
- Keep mkcert. Rejected: `mkcert -install` mutates the host's trust stores, which a production posture must not
  do, and mkcert is not everywhere Docker is.

**Consequences.** The stack stops depending on `apps/*/certs` existing on the host. That opens the single-`certs/`
mount consolidation for the bundle increment, but this increment does not do it — it keeps the current per-
project mount targets so the dev path is untouched. The script's leaf list is one manifest, shared in intent
with the `tls.json` SANs, and a test reads the script and its manifest (SPS-09). The browser once-warn is a
documented expectation, not a bug.
