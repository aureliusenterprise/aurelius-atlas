# 10.8 Grafana login via the production realm

- **Status:** in review
- **Pull request:** \#179 (stacked on \#178)
- **Records:** DD-273/DD-274 (relies on, unchanged), DD-275 (adds; supersedes DD-267's login-form-stays-disabled clause), DD-276 (adds)

## Scope

The pre-pentest review's **H4**: Grafana ships with no authentication of its own in the cluster shape. DD-267 gave it an umbrella-generated admin Secret but kept the dev compose's posture — `GF_AUTH_ANONYMOUS_ENABLED=true` (Viewer), `GF_AUTH_DISABLE_LOGIN_FORM=true` — so the only way in is the anonymous session, and the generated admin/password pair is an account-recovery credential nobody is meant to type. If an operator flips `global.hosts.grafana.enabled` to put a dashboard behind the edge (10.3c wired that path), the dashboards — cluster topology, service maps, trace counts — go read-only-public to anyone who can resolve the host.

This increment makes Grafana a **confidential OAuth2/OIDC relying party of the `aurelius-atlas` realm** (10.7's asset):

- A new `grafana` client joins `files/aurelius-atlas.json` — the first client in the **prod asset only**: the dev compose Grafana keeps the anonymous-Viewer posture (DD-275, DV-89), so CHT-79's structural parity rule gains its first named exception (prod client set = dev set ∪ {`grafana`}).
- The observability chart's Grafana deployment swaps the anonymous env for the `GF_AUTH_GENERIC_OAUTH_*` set: issuer URLs derived from `atlas-observability.issuerUrl` + `atlas-observability.realm` (CHT-74's plumbing, reused), client id `grafana`, and a client Secret joined from the umbrella's new `<release>-grafana-oauth` Secret — the same placeholder plumbing as `${OTEL_INGEST_CLIENT_SECRET}` (DD-256's resolver, `${GRAFANA_CLIENT_SECRET}`).
- RBAC is role-mapped, not free-for-all: any authenticated realm user gets **Viewer**; the `grafana` client's `editor` / `admin` client roles escalate to **Editor** / **Admin** (`role_attribute_path`, DD-275).
- The port-forward path stays alive: the client registers `http://localhost:3000/login/generic_oauth` next to the host-based redirect, and `GF_SERVER_ROOT_URL` stays unset (request-derived), so `kubectl port-forward` to the Grafana pod completes an OAuth login (DD-276).
- Keycloak's network policy admits Grafana to the 8443 mint port (Grafana dials Keycloak for the token exchange and JWKS; CHT-62's full-dialer-set rule).

This increment does **not** deliver: per-producer telemetry credentials (M5), Grafana exposure by default (`global.hosts.grafana.enabled` stays `false` — this increment makes exposing safe, not automatic), any change to the dev compose stack (its Grafana stays anonymous-Viewer — a local dashboard over local telemetry, DV-89), or alerting/contact-points (out of scope entirely).

## Semantics

Grafana is a **browser-facing relying party** like the `aurelius` webapp client, except confidential: it has a client Secret, a fixed redirect path (`/login/generic_oauth`), and no end-users of its own — identities live in the realm.

| Id | Rule |
| --- | --- |
| CHT-81 | The prod asset carries exactly one client the dev asset does not: `grafana`, a confidential browser client (`publicClient: false`, `standardFlowEnabled: true`, `implicitFlowEnabled: false`, `directAccessGrantsEnabled: false`, `serviceAccountsEnabled: false`, `clientAuthenticatorType: "client-secret"`) whose `secret` is the `${GRAFANA_CLIENT_SECRET}` placeholder (DD-256's resolver, Keycloak-side) and whose `pkce.code.challenge.method` is `"S256"`. It defines the client roles `editor` and `admin`. CHT-79's parity rule is amended accordingly: prod client ids = dev client ids ∪ {`grafana`}, and the `grafana` name must **not** appear in `files/master.json` or `dev/keycloak/import/master.json`. |
| CHT-82 | The `grafana` client's `redirectUris` are `https://__GRAFANA_HOST__/login/generic_oauth` and `http://localhost:3000/login/generic_oauth`; `webOrigins` are `https://__GRAFANA_HOST__` (Grafana sends no origin for the flow beyond these). `configmap-realm.yaml` substitutes `__GRAFANA_HOST__` with the host the umbrella's host rule resolves for Grafana (values override, else `grafana.<domain>`, else `<release>.localhost`) — same rule as CHT-77's atlas/dashboard tokens: hosts not exposed yield inert allow-list entries. The localhost entry is deliberate (DD-276): it is the port-forward operator path, and a redirect URI that no attacker can land a browser on is not exposure. |
| CHT-83 | The Keycloak StatefulSet feeds the placeholder the same way it feeds the otel one: a `GRAFANA_CLIENT_SECRET` env from the Secret named by `atlas-keycloak.grafanaOauthSecretName` (default `<release>-grafana-oauth`, key `client-secret`). Unlike the otel env it **is** realm-gated: it renders for every realm but `master` — CHT-81 puts the client in the prod asset only, master's asset has no grafana client for the placeholder to resolve into, and CHT-80's rule says an unused credential is not generated. The umbrella generates that Secret (lookup → values override → `randAlphaNum 32`, `secrets.grafanaOauth.clientSecret`) gated on either consumer being present — a non-master keycloak install (the realm import) or the observability chart (its Grafana joins the Secret into its env); the two consumers must read the same Secret (the `secret-collector-legacy.yaml` two-consumer pattern). A master-only install generates no grafana credential. |
| CHT-84 | The observability chart's Grafana container renders `GF_AUTH_ANONYMOUS_ENABLED=false`, `GF_AUTH_DISABLE_LOGIN_FORM=false`, `GF_AUTH_GENERIC_OAUTH_ENABLED=true`, name `Keycloak`, client id `grafana`, and `GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET` from `atlas-observability.grafanaOauthSecretName` (join, `optional: false` — same join policy as the admin Secret, CHT-40). `auth_url` / `token_url` / `api_url` render from `atlas-observability.issuerUrl` + `/realms/` + `atlas-observability.realm` + `/protocol/openid-connect/{auth,token,userinfo}` — CHT-74's rule: a consumer naming another realm is a contract violation. `GF_SERVER_ROOT_URL` stays unset (request-derived, DD-276). The admin Secret env (`GF_SECURITY_ADMIN_USER`/`PASSWORD`, CHT-40/DD-267) stays: with the login form back on, the local admin is account recovery, not the daily door. |
| CHT-85 | RBAC maps from realm token roles: `GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH` = `contains(resource_access.grafana.roles[*], "admin") ? "Admin" : contains(resource_access.grafana.roles[*], "editor") ? "Editor" : "Viewer"` — every authenticated `aurelius-atlas` user gets Viewer, and escalation is an explicit client-role grant (or the local admin, CHT-40). `GF_AUTH_GENERIC_OAUTH_ROLE_LIST_PATH` and `allowed_organizations` are not used: the realm itself is the boundary and Grafana reads the flat `resource_access` shape. |
| CHT-86 | The Keycloak chart's 8443 egress allow (CHT-62's dialer set) gains the Grafana pod (`atlas-observability` / `grafana`): Grafana dials Keycloak for the authorization-code token exchange and JWKS fetches when OAuth is on. The observability chart's own egress needs no change — its collector-side rules already route the pod network where this chart permits, and Grafana's new dial is admitted from the Keycloak side (CHT-62's ownership rule: the callee admits). |

## Java origin

None — this increment ports no Apache Atlas behaviour. The reference is the pre-pentest review's finding H4 and Grafana's `generic_oauth` (OAuth2/OIDC) auth provider.

## Deviations

None against Atlas. DV-89 records the deliberate dev↔prod divergence: the dev compose Grafana stays anonymous-Viewer (a local dashboard over local telemetry, same two-shape posture as DD-273's identity split), while the cluster Grafana is Keycloak-gated — the first client that lives in one realm asset and not the other. DD-275 records the relying-party design (confidential client, prod-asset only, Viewer-default RBAC with client-role escalation); DD-276 records the request-derived `root_url` + localhost redirect that keeps the port-forward operator path working, and supersedes DD-267's "login form stays disabled" clause (its generated-admin-Secret half stands).

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green (the chart owners).
- `tests/test__charts_keycloak.py` names CHT-81/82 (the rendered prod asset's `grafana` client: confidential flags, placeholder secret, tokenised + localhost redirects, `editor`/`admin` client roles; grafana absent from the dev assets; CHT-79's amended parity set), CHT-82 substitution (stock render → `grafana.atlas.test`; host override; bare render → `<release>.localhost`), CHT-83 (the StatefulSet's `GRAFANA_CLIENT_SECRET` env, ungated).
- `tests/test__charts_observability.py` names CHT-84/85 (anonymous off, login form on, OAuth on with `/realms/aurelius-atlas/…` URLs, role-attribute-path, the oauth Secret join, `GF_SERVER_ROOT_URL` absent; admin env retained).
- `tests/test__charts_umbrella.py` names CHT-83 (stock install generates `<release>-grafana-oauth` with key set {`client-secret`}; values override; absent when both consumers are gone — observability disabled **and** the keycloak chart on `master`).
- `tests/test__charts_keycloak.py`'s 8443 dialer-set test names CHT-86 (grafana pod selectors among the mint dialers).
- Runbook: the Grafana section documents the Keycloak login, the role map, and the port-forward path. `dev/observability/AGENTS.md`, `dev/keycloak/AGENTS.md`, and `helm/AGENTS.md` record the new client/Secret/join. `deviations.md` gains DV-89. The 10.5 hand-check note extends: a stock umbrella's Grafana redirects to the realm's login at `keycloak.atlas.test` and an authenticated realm user lands as Viewer.
- Hand check: not run in CI here (no live Keycloak); proven by render.
