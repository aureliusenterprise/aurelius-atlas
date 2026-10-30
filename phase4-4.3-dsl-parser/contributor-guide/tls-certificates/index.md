# TLS Certificates

How local TLS material is declared, issued, and cleaned up in this repository. The architecture rule it serves — every path TLS with verification, plaintext exceptions named — is [Data Encryption](<https://aureliusenterprise.github.io/phase4-4.3-dsl-parser/architecture/platform/security/data-encryption/index.md>); the security record is [ADR 039](<https://aureliusenterprise.github.io/phase4-4.3-dsl-parser/architecture/adr/039-data-is-protected-where-it-travels-and-where-it-rests/index.md>). This page is the practitioner's walkthrough.

## Declare: `tls.json`

Each project that serves or consumes TLS owns a `tls.json` listing the certificates it needs: the service names, keystore formats, and truststores that project's `serve` and `e2e` targets consume. The server, the identity provider slice, and the observability slice each declare their own; there is no central certificate manifest.

## Issue: `nx certgen`

```
npx nx certgen <project>    # issue this project's material into its certs/ directory
```

- Material lands in the project's own gitignored `certs/`: PEM keypairs, PKCS12 keystores, a JVM `truststore.p12` where needed, and a `ca.pem` copy for pure clients.
- The certificate authority itself has no workspace home: `certgen` installs mkcert's own root CA into the system trust stores (it lives in mkcert's per-machine store, outside the repository) and copies it into each project's `certs/`.

> [!NOTE]
>
> **Why the CA lives outside the repository**
>
> Trust is installed, not cloned: the root CA sits in mkcert's per-machine store, where the operating system's trust machinery finds it. Committing a CA would ship a trust decision; `certgen` reissues material per machine instead, so a fresh clone becomes trusted by running `nx certgen`, not by receiving a key.

- Generation is on demand: `serve` and `e2e` targets declare a `certgen` dependency, which itself depends on `decrypt`, because truststore passwords live encrypted in each project's `.env.enc` (see [Secrets Management](<https://aureliusenterprise.github.io/phase4-4.3-dsl-parser/contributor-guide/secrets-management/index.md>)).
- Service names appear in the certificates, so clients must reach services by the name in the certificate — the compose service name, not `localhost` (see [Development Environment](<https://aureliusenterprise.github.io/phase4-4.3-dsl-parser/contributor-guide/development-environment/#dev-topology>)).

> [!WARNING]
>
> **Service-name verification fails on localhost**
>
> Pointing a client at `localhost` or an IP address — the reflex from a laptop install — fails certificate verification, not connectivity: the store's certificate is issued for `elasticsearch`. Join the slice's compose network and use the service name, as the server's e2e container does.

## Clean up

```
npx nx certclean <project>    # remove this project's material, keep the CA
mkcert -uninstall             # drop the CA and its system trust entries entirely
```

`certclean` removes a project's material but never the CA, which other projects share.

> [!IMPORTANT]
>
> **Nothing in `certs/` is production material**
>
> Copying a `certs/` file into a deployment ships a development key whose CA is every developer's laptop: the deployment serves a certificate no client trusts, and worse, one whose CA is public. A deployment generates its own CA and key material; the repository's exists to make TLS the default locally, not to travel.

## Named development relaxations

The architecture page names the rule; these are the specific plaintext exceptions a developer sees, each accepted deliberately ([ADR 039](<https://aureliusenterprise.github.io/phase4-4.3-dsl-parser/architecture/adr/039-data-is-protected-where-it-travels-and-where-it-rests/index.md>)):

- The identity provider slice serves a plaintext HTTP listener (port 8080) so the developer browser opens a familiar URL; its TLS listener (8443) serves every CI/E2E path.
- Browser-facing developer surfaces (SPA dev-server, Grafana, Storybook) stay plaintext on a developer machine.
- Playwright's bundled browsers carry their own trust stores and cannot enroll the mkcert root, so frontend E2E page navigation skips browser certificate verification (`ignore_https_errors`). The E2E suite verifies the same browser-facing endpoint against the CA out-of-band (hostname + chain), and nginx still verifies the backend with `proxy_ssl_verify`.

> [!NOTE]
>
> **Why does frontend E2E skip browser certificate verification?**
>
> The relaxation is the browser's trust store, not the TLS: Playwright's bundled browsers cannot enroll the mkcert root, so page loads set `ignore_https_errors` while the suite verifies the endpoint's hostname and chain against the CA out-of-band. The encryption and the certificate are both proven — just not by the browser's padlock.

Every plaintext occurrence in this repository carries a comment naming ADR 039.
