# 10.7 Production identity realm

- **Status:** in review
- **Pull request:** [#178](https://github.com/aureliusenterprise/aurelius-atlas/pull/178) (stacked on #176)
- **Records:** DD-256 (relies on, unchanged), DD-273 (adds), DD-274 (adds)

## Scope

The pre-pentest review's **H3**: the cluster shape today authenticates the whole
system against Keycloak's own **`master`** admin realm. `dev/keycloak` ships one
identity asset (`files/master.json`, a byte-copy of the dev import under DD-256),
imported with `realm.name: master`, and `realm: master` is a default in all seven
consuming charts. Importing the application _as_ `master` drags in Keycloak's
admin clients (`admin-cli`, `security-admin-console` with `webOrigins: ["+"]`,
`account`), the master admin roles, localhost-only redirect URIs and origins,
`sslRequired: external`, brute-force detection off, no password policy, PKCE
unset, and ROPC (`directAccessGrants`) on the public browser client.

This increment gives the cluster a **separate, hardened application realm**
named **`aurelius-atlas`**:

- `global.realm` joins the CHT-03 values contract (default `aurelius-atlas`) and
  is the one fact every realm-bearing env derives from; the Keycloak chart
  imports `files/<realm>.json` selected by it.
- A new chart asset `files/aurelius-atlas.json` carries the prod identity config:
  the same client/role/scope surface the system authenticates against, with the
  H3 hardening applied and no seeded end-users.
- Every consuming chart's realm-bearing join (the OTLP mint URLs, the collector's
  OIDC issuer, the webapp's `/config.json`, the pullers' issuer-wait probes)
  renders from `global.realm`, and a test pins that all of them name the realm
  the Keycloak chart imports.

This increment does **not** deliver: SSO/Keycloak-gating of Grafana (H4, its own
increment), per-producer ingest-token rotation (M5), image/chart signing (M9), or
any change to the **dev compose stack** — `dev/keycloak/import/master.json` and
the four `e2e/` conftests keep importing `master` exactly as today (the localhost
origins, ROPC password-grant, and demo users are the Playwright conveniences the
dev login needs; the cluster and the dev stack are intentionally different
shapes). The `master` realm asset and DD-256's byte-copy guard stay in place as a
documented dev escape hatch (`realm.name: master` loads `files/master.json`).

## Semantics

The realm is a **deployment identity fact** like `global.domain`: one value,
every consumer. Renaming it is a first-boot decision (Keycloak pins the realm
issuer then, as it pins the realm-issuer URL — runbook).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CHT-74 | `global.realm` (default `aurelius-atlas`) is the realm the whole system authenticates against. The Keycloak chart imports `files/<global.realm>.json` and stamps `realm`/`id` = that name; every realm-bearing env of every chart — the server's `OTEL_TOKEN_URL`, the three aux APIs' and both store pullers' token/well-known URLs, the collector's `oidc.issuer_url`, the webapp's `/config.json` `keycloak.realm` — renders `/realms/<global.realm>/…` (or the bare name for the SPA). A render whose Keycloak-imported realm differs from any consumer's is a contract violation (pinned by test).                                                                                                                                                                                                                                                                                                                                                                                                                  |
| CHT-75 | The prod asset `files/aurelius-atlas.json` is **minimally authored**: it carries exactly the application-facing surface — the `aurelius` public browser client (with its `aurelius-write` client role), the seven `otel-*` service accounts (client credentials, audience `otel-collector` via the `otel-ingest` default scope), and the custom `otel-ingest` client scope — and nothing else. Keycloak's built-in per-realm defaults (`account`, `account-console`, `admin-cli`, `broker`, `security-admin-console`, `realm-management`, the browser flows, the key providers, the builtin client scopes) are **not** in the file: Keycloak creates them when the realm is created, which is why the file never references master's admin composites and imports cleanly into a fresh realm. No `users` are seeded.                                                                                                                                                                                                     |
| CHT-76 | The prod realm is hardened: `sslRequired: "all"`, `bruteForceProtected: true` (with the login-failure thresholds set), `registrationAllowed: false`, `resetPasswordAllowed: false`, `rememberMe: false`, `passwordPolicy` naming a minimum length + complexity, and realm + admin events enabled (`eventsEnabled`, `adminEventsEnabled`). The `aurelius` browser client keeps `publicClient: true`, `standardFlowEnabled: true`, `directAccessGrantsEnabled: false`, and the `pkce.code.challenge.method: "S256"` client attribute (keycloak-js 26 sends PKCE by default), with `post.logout.redirect.uris` pinned to the browser hosts; `bearerOnly`/`serviceAccountsEnabled` stay false. Each `otel-*` client is byte-equal to its dev peer except `id`: a confidential service account (`publicClient: false`, `serviceAccountsEnabled: true`, `standardFlowEnabled: false`, `directAccessGrantsEnabled: false`) whose `secret` is the `${OTEL_INGEST_CLIENT_SECRET}` placeholder (DD-256's resolver, shared secret). |
| CHT-77 | The `aurelius` client's `redirectUris`, `webOrigins`, and post-logout URIs carry the tokens `__ATLAS_HOST__` / `__DASHBOARD_HOST__`; `configmap-realm.yaml` substitutes them with the browser hosts resolved by the umbrella's host rule (values override, else `atlas.<domain>` / `dashboard.<domain>`) — so no `localhost`, `127.0.0.1`, or `+` reaches a cluster render. Hosts not exposed yield inert allow-list entries (a redirect that no route answers); the chart does not read host `enabled` flags. Credential placeholders stay verbatim for Keycloak's own resolver (DD-256's rule preserved), and the token substitution is a literal `replace` over the asset text — no templating inside the JSON.                                                                                                                                                                                                                                                                                                       |
| CHT-78 | `realm.name: master` (the dev escape hatch) still loads `files/master.json` **byte-for-byte** as today — DD-256's byte-copy drift guard against `dev/keycloak/import/master.json` is unchanged and still runs. Selecting a realm with no shipped asset fails the render (`required`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| CHT-79 | The two assets stay application-peer-faithful: a test asserts the prod asset's client-id set equals `aurelius` + the seven `otel-*` names, each `otel-*` client dict equals its dev peer minus `id`, the `otel-ingest` scope's audience mapper config is unchanged, and the `aurelius` client differs from its dev peer **only** in the hardened fields (ROPC off, the PKCE attribute, the tokenised origins, post-logout pin) — so an identity change landing in the dev realm must be mirrored in the prod asset or named in the same commit (the drift guard DD-256 gives the byte-copy, given here structurally).                                                                                                                                                                                                                                                                                                                                                                                                    |
| CHT-80 | The demo-user plumbing is dev-only: the `${DEV_USER_WRITER_PASSWORD}` / `${DEV_USER_READER_PASSWORD}` / `${OTEL_INGEST_CLIENT_SECRET}` placeholders appear in `master.json`; the prod asset carries only the otel one (no seeded users). The Keycloak StatefulSet's `DEV_USER_*` env and the umbrella's `<release>-keycloak-users` Secret therefore render only when the imported realm is `master` — a stock `aurelius-atlas` install generates no demo-user Secret and no `DEV_USER_*` env. The `*-otel-clients` and `*-keycloak-admin` Secrets stay (the otel clients and the bootstrap admin are not demo conveniences).                                                                                                                                                                                                                                                                                                                                                                                             |

## Java origin

None — this increment ports no Apache Atlas behaviour. The reference is the
pre-pentest review's finding H3 and the Keycloak 26.7 realm-import format the dev
stack already uses (DD-196/DD-256).

## Deviations

None against Atlas. Deliberate dev↔prod divergence (recorded as DD-273): the dev
compose and the four `e2e/` suites stay on the `master` realm with localhost
origins, ROPC, and demo users — the browser-login test rig — while the cluster
installs the separate `aurelius-atlas` realm. This is the two-shape posture 10.6
already established for network policy (compose runs policy-free, cluster
segments), extended to identity. DD-274 records the realm-name plumbing
(`global.realm` as a contract value) and the two-asset model.

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green (the chart owners).
- `tests/test__charts_keycloak.py` names CHT-74 (imported realm == `global.realm`,
  asset selection, `master` escape hatch + DD-256 byte-copy retained, CHT-78
  `required` on a missing asset), CHT-75/76/77 (the prod asset's clients/roles/
  absent-internal-clients, hardening flags, real-host origins — read off the
  rendered ConfigMap), CHT-79 (structural parity vs the dev asset), CHT-80 (the
  `master`-gated users). `tests/test__charts_{server,aux,elasticsearch,
observability}.py` and `tests/test__charts_edge.py`/`test__charts_umbrella.py`
  re-assert their realm-bearing URLs at the new default (`realms/aurelius-atlas`)
  and pin CHT-74 (every consumer names the imported realm).
- Runbook (`docs/architecture/deployment/runbook.md`): the cluster issuer/realm
  examples move to `realms/aurelius-atlas`; the issuer-pin warning notes the realm
  name is likewise first-boot-immutable. `dev/keycloak/AGENTS.md` and
  `helm/AGENTS.md` record the two-asset split. `deviations.md` gains the
  dev-`master`/prod-`aurelius-atlas` divergence.
- Hand check (10.5, scripted there): a stock umbrella on minikube boots Keycloak
  with the `aurelius-atlas` realm imported, the `iss` of a minted ingest token is
  `…/realms/aurelius-atlas`, and the browser leg's `/config.json` points the SPA
  at `aurelius-atlas`. Not run in CI here (no live Keycloak); proven by render.
