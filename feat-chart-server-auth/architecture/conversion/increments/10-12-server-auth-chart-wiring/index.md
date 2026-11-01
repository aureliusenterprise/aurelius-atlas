# 10.12 Server authentication, chart wiring

- **Status:** in review
- **Pull request:** TBD
- **Records:** DD-296, DD-297 (relies on: DD-250/251 on main — 6.1a's auth settings and session; DD-256's placeholder resolver; CHT-74's realm contract, CHT-87's per-client placeholder rule, CHT-88's realm-shaped secrets)

## Scope

6.1a (\#188, on main) made the server's identity settings **required**: `auth_server_url` and `auth_client_secret` have no defaults, so a server pod whose environment lacks them fails at settings load — an umbrella install of a post-6.1a image crash-loops. The charts were authored before that merge and render no `AUTH_*` env for the server. This increment closes that gap and completes the Helm story for authentication:

- the prod realm asset gains the `aurelius-atlas-server` confidential client (the dashboards' sign-in client, 6.1a/DD-250), hardened and host-tokenised like its `aurelius` peer;
- the umbrella mints its secret (`<release>-server-client`), the Keycloak chart resolves the import placeholder from it (both realm assets carry the same `${ATLAS_SERVER_CLIENT_SECRET}`), and the server chart joins the same Secret into `AUTH_CLIENT_SECRET`;
- the server chart renders the whole auth env block (`AUTH_SERVER_URL`, `_AUTH_REALM`, `_AUTH_CLIENT_ID`, `_AUTH_AUDIENCES`, `_AUTH_CA_FILE`) from the existing issuer/realm/trust joins;
- the three aux charts fix a latent CHT-74 drift: their `AUTH_REALM` was a static `master`, while the cluster's imported realm is `global.realm` — on a prod-realm install they would verify tokens against `/realms/master`. It becomes a realm join like every other realm-bearing env.

This increment does **not** deliver: browser-exposing the dashboards by default (the dashboard host stays `enabled: false` — ADR 054; the login leg only becomes reachable when an operator turns it on, DD-296), the webapp's own token handling (7.3/6.1a, unchanged — the webapp's nginx `/api/` proxy already forwards the browser's bearer token and the webapp chart's realm wiring predates this), or 6.1b's acting-user settings (no chart surface).

## Semantics

| Id | Rule |
| --- | --- |
| CHT-108 | The server chart's auth env is joins, never literals: `AURELIUS_ATLAS_SERVER_AUTH_SERVER_URL` is the issuer URL (the chart's `issuerUrl` helper — CHT-03's `global.issuer.url`/`global.domain` derivation, whose required-guard now always fires), `_AUTH_REALM` is `global.realm` (CHT-74's one realm fact), `_AUTH_CLIENT_ID` and `_AUTH_AUDIENCES` come from the chart's `auth` values block (defaults `aurelius-atlas-server` and `["aurelius"]` — the server's own confidential client plus the webapp's client whose forwarded tokens it accepts, AUT-02/AUT-10), `_AUTH_CA_FILE` is the mounted Certificate's `ca.crt` beside the TLS pair it already pins, and `_AUTH_CLIENT_SECRET` arrives by secretKeyRef from `<release>-server-client` key `client-secret`, with `credentialSecrets.serverClient` naming a brought Secret (the DD-287 pattern). A render without `global.issuer.url`/`global.domain` fails — an authless server cannot boot. |
| CHT-109 | The umbrella's `<release>-server-client` Secret (key `client-secret`) generates once and survives upgrades by the lookup/preserve/override rule documented in `secret-elasticsearch.yaml` (values at `secrets.serverClient.clientSecret`). It renders when either consumer is installed: the Keycloak chart (its imported realm's asset carries the placeholder — for **both** shipped assets, unlike CHT-80's master-only users or CHT-83's prod-only grafana credential) or the server chart (the join's other end). Neither installed ⇒ nothing generates. |
| CHT-110 | The prod asset `files/aurelius-atlas.json` gains the `aurelius-atlas-server` client: confidential (`publicClient: false`, `serviceAccountsEnabled: false`, `standardFlowEnabled: true`, `directAccessGrantsEnabled: false`), `clientAuthenticatorType: "client-secret"`, secret `${ATLAS_SERVER_CLIENT_SECRET}` (CHT-87's placeholder mechanism, never a rendered secret), `pkce.code.challenge.method: "S256"`, and redirects/webOrigins/post-logout URIs built from the `__ATLAS_HOST__`/`__DASHBOARD_HOST__` tokens at `…/login.jsp` (AUT-05's return leg lands on the server's own login page, so the dashboard host is a first-class browser host and `atlas.<domain>` works for a reverse-proxied server too). Its dev peer (master's client, DD-250) differs only in the hardening fields, per the CHT-79 drift guard. |
| CHT-111 | Every realm-bearing env in every chart names `global.realm` — including the aux APIs' `AUTH_REALM`, which joins the chart's realm helper (the CHT-74 enumeration extended: the umbrella render pins the server's and the three aux pods' `AUTH_REALM` against the realm the Keycloak chart imports). `master` (the escape hatch) restores `master` everywhere from the same one fact. |

## Java origin

No new Java behaviour ports: this wires 6.1a's already-ported authentication (`AtlasKeycloakAuthenticationProvider`, the `atlasRealmProperties` in `atlas-application.properties`) into the deployment shape — the equivalent of Atlas's `WEB-INF/classes/atlas-application.properties` realm/client block, expressed as chart joins (DD-296).

## Deviations

None new. (Apache Atlas ships a static properties file per deployment; Aurelius composes the same facts from the umbrella's issuer/realm/secret contract — established in 10.1–10.3, extended here.)

## Acceptance

Chart-contract suites (run: `uv run pytest tests/test__charts_server.py tests/test__charts_keycloak.py tests/test__charts_umbrella.py tests/test__charts_data2model.py tests/test__charts_lineage_model.py tests/test__charts_validate_entity.py`):

- `test__charts_server.py` — CHT-108: the auth env block on the stock render (issuer URL, realm, client id, audiences, CA path, secret join); the issuer guard fails a render with no domain/issuer; `credentialSecrets.serverClient` renames the Secret.
- `test__charts_keycloak.py` — CHT-110: the prod asset's client roster gains `aurelius-atlas-server`; its hardened fields; host substitution and the placeholder's verbatim survival; the CHT-79 peer delta stays inside the hardened set; CHT-109/110: the StatefulSet carries `ATLAS_SERVER_CLIENT_SECRET` on **both** the prod and master renders.
- `test__charts_umbrella.py` — CHT-109: `<release>-server-client` in the generated roster with its one key; it renders for the keycloak-only and server-only installs and not for neither; CHT-111: server + aux `AUTH_REALM` equal the imported realm.
- `test__charts_data2model.py` (+ lineage/validate twins) — CHT-111: `AUTH_REALM` follows `global.realm` (prod default and the master hatch).
