# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-363. The prefix is uvicorn's root path, and the standalone proxy shares its network with the server

- **Status:** Proposed
- **Increment:** 9.5
- **Date:** 2026-11-06

**Decision.** The server takes its prefix as `root_path`, which uvicorn puts on every request. The few checks
that judge a path read it without the prefix, and the redirects the server makes add it. In the standalone
stack, nginx strips `/atlas2` before the server and passes `/auth` to a Keycloak that serves under `/auth`
itself, with `https://localhost:9000/auth` as its public address. The server and the sample import run in
nginx's network, so their `localhost:9000` is the proxy too.

**Reason.** Uvicorn's root path is the ASGI way to say where an application is mounted: the base URL, and with
it the sign-in's return and the sign-out's address, follow from it with no change. The proxy could rewrite the
server's redirects instead, but the return address the provider checks is built from the base URL, which only
the server can get right. Keycloak checks a token's issuer against the address it was asked at. The browser
asks at `https://localhost:9000/auth`; when the server asks there too, the issuer it verifies is the one the
browser's tokens carry. Sharing the proxy's network is the simplest way to give the server that address,
without a second name for the same Keycloak.

**Alternatives.**

- An `X-Forwarded-Prefix` from the proxy: uvicorn ignores it, so the server would read and trust another
  header.
- nginx `proxy_redirect` and `sub_filter` rewriting the server's answers: brittle, and it cannot fix the
  return address the provider receives.
- The dev Keycloak behind `/auth`: its address `keycloak.localhost:8443` is the issuer every other dev service
  and e2e suite trusts, so the stack runs its own.

**Consequences.** The stack's Keycloak imports the dev realm at every start, so its sessions and changes don't
last. The realm's `aurelius-atlas-server` client also accepts `https://localhost:9000/atlas2/` as a sign-in return
and sign-out address.
