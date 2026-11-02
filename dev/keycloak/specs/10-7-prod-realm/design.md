# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-273. Two identity realms: hardened `aurelius-atlas` for clusters, `master` as the dev escape hatch

- **Status:** Accepted
- **Increment:** 10.7
- **Date:** 2026-10-30

**Context.** The pre-pentest review's H3: the cluster authenticated the whole
system against Keycloak's own `master` admin realm, because
`dev/keycloak/import/master.json` — built for the compose/e2e browser-login
rig (localhost origins, ROPC password grant, demo users, Keycloak's admin
clients with `webOrigins: ["+"]`) — was also the chart's only realm asset.
Splitting the shapes raises the question of what the prod asset is made of.
Stripping master's export down to the app surface looked attractive until
its composites were checked: `default-roles-master` composites the
account/realm-management client roles, so a pruned export either keeps dead
references or breaks import, and no offline check can prove which — there is
no running Java-Atlas-style reference Keycloak here, and the cluster shape
only ever boots for real in the 10.5 hand check.

**Decision.** Two assets, two shapes (CHT-75, CHT-78). The cluster's realm is
the minimally-authored `files/aurelius-atlas.json`: exactly the
application-facing surface — the `aurelius` public client (with its
`aurelius-write` client role), the seven `otel-*` service accounts, and the
`otel-ingest` scope — with the H3 hardening applied and no seeded users;
Keycloak recreates its built-in clients, scopes, flows, and roles when it
creates the realm, so the file never carries or references them.
`files/master.json` stays exactly as DD-256 made it (byte-copy of the dev
import, drift guard running): the dev compose and the four `e2e/` suites keep
importing `master` with its localhost origins, ROPC, and demo users — the
browser-login conveniences the Playwright suites need — and `realm.name:
master` remains the documented cluster escape hatch that loads it byte-for-
byte. The demo-user plumbing (the umbrella's `<release>-keycloak-users`
Secret, the StatefulSet's `DEV_USER_*` env) is gated on the master realm
(CHT-80): a stock install provisions no people.

**Alternatives.** (a) One realm for everything, hardened — rejected: it
breaks the dev login rig (Playwright's ROPC grants and localhost origins are
the suite's contract, DD-206's shape) and drags dev into the first-boot
hostname pin. (b) A pruned export of master as the prod asset — rejected as
unverifiable offline (composite transplant, above). (c) Seed prod users from
values — rejected: a cluster realm with no users is the pentest-clean shape;
operator provisioning through the admin console is the normal path, and
placeholder-fed demo identities in a prod chart re-create the finding.

**Consequences.** The CHT-79 structural-parity test is the two-asset drift
guard: the otel-* clients and the otel-ingest scope must equal their dev
peers and the aurelius client may differ only in the hardened fields, so an
identity change in dev must be mirrored in the prod asset or named in its
commit. The two shapes are deliberate (DV-112): a reviewer comparing the dev
stack's login behaviour to the cluster's should expect them to differ.
