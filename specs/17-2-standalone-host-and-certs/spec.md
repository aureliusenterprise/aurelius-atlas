# 17.2 Standalone host and certificates

- **Status:** in progress
- **Pull request:** [#393](https://github.com/aureliusenterprise/aurelius-atlas/pull/393)
- **Records:** DD-678 to DD-681 (here); relies on
  [ADR 065](../../docs/architecture/adr/065-compose-stacks-that-deploy-the-whole-system-live-at-the-root.md)
  (the compose fragments and the root `docker/`),
  [ADR 066](../../docs/architecture/adr/066-infrastructure-components-live-at-the-repository-root.md)
  (the infra slices the stack extends), and increment 17.1 (IRT, DD-667..677).

## Scope

The standalone stack serves `https://localhost:9000` and nothing else. A customer who wants to open it on a
host name, or to bring their own certificates, must edit files in seven places and run a developer tool they
do not have (`nx certgen`). This increment makes the browser host one value and the certificates the
customer's own, without changing what the applications do.

It delivers:

- One host value for the stack. The Keycloak hostname and issuer, the apps' issuer URLs, the realm's redirect
  URIs, and the collector's validated issuer all derive from it. The default is `localhost`, so `nx serve`,
  the e2e stacks, and the current README commands are unchanged (SPS-01, SPS-05, SPS-06, SPS-08).
- The trust model written down: only the proxy's edge leaf names the browser host. Every internal leaf keeps
  its service name. The browser host changes no internal certificate (SPS-02, SPS-03, SPS-10).
- The mechanism that lets the in-network applications reach a non-localhost host: the proxy maps the host to
  `127.0.0.1` and the applications share the proxy's network, so they dial the browser URL and land on the
  proxy (SPS-04).
- A certificate script the stack ships. It makes a CA and the leaves for the host with `openssl` alone. A
  customer may supply their own CA and leaves instead. The script never installs into a system trust store
  (SPS-09).
- Two documented ways to change the host on a stack that already holds data (SPS-07).

It does not deliver, with the increment that will:

| Not delivered                                                                                                                                         | Lands with              |
| ----------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| A shipped delivery bundle (the flattened compose tree, published as an OCI artifact and a tarball)                                                    | the bundle increment    |
| Production hardening of the stack's settings (restart policy, resource caps, image digest pinning, container hardening, observability port overrides) | the hardening increment |
| Making the host reachable on the local network by default (the stack stays loopback-only)                                                             | not planned             |

## Semantics

"The host" is the one value a customer sets for the browser address of the stack, `STANDALONE_HOST`. The
"edge leaf" is the certificate the proxy serves. An "internal leaf" is a certificate one service serves to
another service inside the stack's networks. "The stack's issuer" is `https://<host>:9000/auth/realms/aurelius-atlas`.
The "browser host" is the host the person's browser types, which is the host.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| SPS-01 | The stack reads one host value, `STANDALONE_HOST`, default `localhost`. The Keycloak `KC_HOSTNAME`, each application's issuer URL and token URL, the sample import's and tenants' URLs, and the collector's validated issuer all carry it. No application reads the host any other way, and no application code changes (DD-678). The stack's published port and the proxy's single server block do not change.                      |
| SPS-02 | The proxy publishes `9000` on loopback only, as it does now. Only the edge leaf names the browser host in its Subject Alternative Name (SAN). The proxy's `server_name` names the host, and it remains the catch-all default server (DD-679).                                                                                                                                                                                        |
| SPS-03 | An internal service-to-service connection keeps the service name as its SNI and its peer name. The proxy still reaches the server, the webapp, the collector, and Keycloak by their service or loopback names, and those names stay in the internal leaves. Changing `STANDALONE_HOST` changes no internal leaf (DD-679).                                                                                                            |
| SPS-04 | Each application that shares the proxy's network reaches the browser URL through it. The proxy carries the host in its `extra_hosts` mapped to `127.0.0.1`, so every container in that network resolves the host to the proxy and dials the browser port there (DD-678).                                                                                                                                                             |
| SPS-05 | Keycloak answers at `https://<host>:9000/auth` behind the proxy, and its issuer is that address. The server, the three aux apps, and the webapp verify tokens issued by that issuer. The host change does not move Keycloak off the plaintext in-network listener the proxy terminates.                                                                                                                                              |
| SPS-06 | On a fresh store, the realm's redirect URIs, web origins, and post-logout URIs for the clients `aurelius` and `aurelius-atlas-server` carry the host. The host reaches them through the realm's existing `replace-placeholders` import mechanism, so the realm asset names no literal host (DD-680).                                                                                                                                 |
| SPS-07 | After the store holds the realm, a restart with a new host does not change the stored realm. Keycloak skips the import of a realm that already exists. The stack's `README.md` gives two paths: empty the store (`down -v`), which re-imports for the new host, and keep the data, which re-points the two clients through the Keycloak admin API (DD-680).                                                                          |
| SPS-08 | The collector's OIDC validator keeps one issuer, the stack's issuer named by the host, read from the JWKS file the `jwks-fetch` one shot writes. Only its `issuer_url` derives from the host (DD-675 carried the mechanism).                                                                                                                                                                                                         |
| SPS-09 | The stack ships one certificate script. Given a host, it creates a CA and issues the edge leaf for that host plus `localhost` and `127.0.0.1`, and issues the internal leaves for their service names, using `openssl` and a config file alone. It installs nothing into a system trust store and needs no developer tool (DD-681). A customer may provide their own CA and leaves at the same paths, and the script is then unused. |
| SPS-10 | The stack trusts the CA by mount, not by the browser or system trust store. The edge leaf, its key, each internal leaf, each internal key, and the CA are bind-mounted into the services that use them. A private CA makes the browser warn once for the host; that is expected and not a broken setup.                                                                                                                              |

## Java origin

None. This increment ports no Apache Atlas behaviour. It changes how one Aurelius deployment is addressed
and secured (ADR 065, ADR 066).

## Deviations

None new. The stack's single host, single entry topology stays Apache Atlas's simplicity, recorded under
ADR 053 and ADR 054. The one deliberate move away from a stock try-me is SPS-04 and SPS-09: the stack serves
a chosen host and trusts a mounted CA, because a customer evaluation does not run on `localhost` and cannot
run a developer certificate tool.

## Acceptance

The root standalone suite parses the compose files with no Docker daemon (`uv run pytest tests`), and the new
`tests/test__standalone_host.py` pins:

- every issuer URL, token URL, `KC_HOSTNAME`, and the collector's `issuer_url` carry `${STANDALONE_HOST}` and
  default to `localhost`, read through `standalone_compose()` (SPS-01, SPS-05, SPS-08).
- the realm asset holds no literal `localhost` host for the two clients; each carries the host placeholder,
  and the merged config resolves it (SPS-06, SPS-07).
- the proxy carries `extra_hosts` for the host, and only the edge leaf's SAN set (from its issued cert) names
  the host; the internal leaves keep their service names (SPS-02, SPS-03, SPS-04).
- the certificate script is present, executable, names only `openssl`, and issues the leaves SPS-09 lists
  (a unit test reads the script and its leaf manifest; a live run is not in this suite).

Live (level 2, a human run, recorded in the PR):

- `STANDALONE_HOST=atlas.test` with a `/etc/hosts` entry for `atlas.test`, the script run, the stack `up`, and
  a sign-in through the webapp and the dashboards (SPS-04, SPS-05, SPS-10).
- the two SPS-07 paths: one `down -v` start on a new host, and one keep-data admin-API re-point on a running
  stack, each proven by a sign-in afterward.
- the default path unchanged: the current README command with no `STANDALONE_HOST` still serves
  `https://localhost:9000` and signs in (SPS-01).
- `docker compose -f docker/docker-compose.yaml ... config --quiet` passes both with and without the host set.
- the three docs gates pass, and `nx affected -t test e2e -c ci` is green as for any change.
