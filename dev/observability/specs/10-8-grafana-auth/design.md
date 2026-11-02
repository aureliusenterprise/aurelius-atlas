# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-276. Grafana logs in through the realm, with a request-derived root URL

- **Status:** Accepted (supersedes DD-267's login-form-stays-disabled clause)
- **Increment:** 10.8
- **Date:** 2026-10-31

**Context.** Enabling the login (H4) has an operator cost DD-267 named
obliquely: its reason paragraph said enabling the form would put a
password surface behind a route with no Keycloak front — 10.8 removes that
objection by putting Keycloak in front. The other half of DD-267 (the
generated `-grafana-admin` Secret, never ship-defaulted) stands untouched
and keeps its env joins; it becomes account recovery rather than a dormant
credential.

**Decision.** `GF_AUTH_*` swaps anonymous-off/login-form-on/OAuth-on
(CHT-84); `GF_SERVER_ROOT_URL` **stays unset** and the client's
`redirectUris` carry both `https://__GRAFANA_HOST__/login/generic_oauth` and
`http://localhost:3000/login/generic_oauth` (CHT-82). Grafana derives the
redirect from the request Host header when root_url is unset, so
`kubectl port-forward` to the pod — the documented default access path —
completes the full OIDC round-trip through Keycloak at the public issuer
URL, while a browser reaching `grafana.<domain>` (if exposed) round-trips
through the same client. The localhost entry is a fixed dev/operator URI,
not a wildcard: an attacker who cannot land a browser on `localhost:3000` of
the operator's machine cannot use it.

**Alternatives.** (a) Pin `GF_SERVER_ROOT_URL` to `https://grafana.<domain>`
— rejected: it breaks the port-forward path (Grafana would redirect the
browser to a host that isn't listening) and pins the pod to one hostname;
the umbrella's `hosts.grafana.enabled=false` default makes the request-
derived form the correct general shape. (b) The `+` wildcard redirect —
rejected: CHT-77 forbids `+` in a cluster asset, and a wildcard on a
confidential client is the open-redirect shape the realm was hardened
against. (c) A second `grafana-dev` client for the localhost path —
rejected: one client, two exact URIs is less surface and one row of drift.

**Consequences.** DD-267's table row and body carry the partial-supersession
annotation; its generated-Secret half is unchanged. Keycloak's 8443 dialer
set gains the Grafana pod (CHT-86) — the token exchange and JWKS fetches are
new real traffic and the full-dialer-set philosophy (CHT-62) admits them
without a flag. A render with `global.hosts.grafana.host` set to something
unreachable still logs in fine over port-forward; the host entry is inert
allow-list filler (CHT-82), not a dependency.
Next free DD: 277.
