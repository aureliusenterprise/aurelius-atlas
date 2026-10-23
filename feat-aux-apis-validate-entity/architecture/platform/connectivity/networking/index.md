# Networking

How the parts reach each other. The page states what the system **requires of a network**; the development topology that satisfies them, slice by slice, is the contributor guide's [Dev Topology](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/contributor-guide/development-environment/#dev-topology>).

## Production

The production topology is the deployment arrangement's subject — [deployment](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/platform/delivery/deployment/index.md>) (6.4). What the system requires of it:

- **Every path TLS with certificate verification** against the deployment's own CA ([data encryption](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/architecture/platform/security/data-encryption/index.md>)). The plaintext listeners developers see exist only in the development arrangement, as named relaxations.
- **Discovery by DNS name, with the service names present in the certificates.** Services reach each other by name, not IP — verification is of the name in the certificate, so an address that connects can still be rejected.
- **The catalogue service reaches the store and the signal collector; browsers reach the catalogue service** for the API and the UI, **and the identity provider** for sign-in. Nothing else needs a path: the store serves only the catalogue service, and the collector receives signals without the system calling back through it. Reaching the collector's ingest ports is not enough to write to them — the browser leg accepts only Keycloak user tokens, the service leg only the shared ingest token (DD-103).

## Development and CI

The development arrangement is one compose project per infrastructure slice, each on its own network, with the app's containers joining the networks of the slices they use — so the service-name rule above is exercised locally, exactly as a deployment must satisfy it. The published host ports, network names, and per-slice commands are in [Dev Topology](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/contributor-guide/development-environment/#dev-topology>) and each slice's README; certificates are development material issued per project ([TLS Certificates](<https://aureliusenterprise.github.io/feat-aux-apis-validate-entity/contributor-guide/tls-certificates/index.md>)).

> [!WARNING]
>
> **The store is reachable only by service name**
>
> Pointing a client at `localhost` or an IP address — the reflex from a laptop install — fails certificate verification, not connectivity: the store's certificate is issued for its service name. Join the slice's compose network and use the name, as the server's e2e container does.
