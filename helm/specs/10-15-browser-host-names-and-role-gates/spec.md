# 10.15 Role-named browser hosts and role-gated sign-ins

- **Status:** in review
- **Pull request:** (this PR)
- **Records:** DD-658 (adds; supersedes the `<entry>.<domain>` label defaults of
  CHT-03 and the host-named redirect/issuer derivations of CHT-16/CHT-77/CHT-82),
  DD-659 (adds; supersedes the Viewer fallback in CHT-84's role mapping),
  DD-660 (adds; relies on: CHT-80's userless asset, DD-275's grafana client),
  DD-661 (adds; extends CHT-133's defined-scopes rule to the roles scope)

## Scope

The deployment review asked for three things. None of them change what the
platform does; all three change who can see it and under which name.

1. **The browser hosts read by product role, not by pod name.** The edge
   hosts were named after the component behind them (`atlas`, `keycloak`,
   `grafana`). The values keys now read `app` (the catalogue webapp), `auth`
   (the identity provider) and `o11y` (Grafana), and the derived hosts follow
   ADR 069: the product answers at the apex (`<domain>`) and observability at
   `observability.<domain>`, while `auth` and `dashboard` keep their labels.
   The rename carries no compatibility alias:
   the chart set is young and atlas-dev is its only live deployment, so
   the entry keys, the derived defaults, and every consumer move in one
   step (DD-658).
2. **A Grafana sign-in requires a realm role.** The role mapping mapped
   `grafana:admin` to Admin, `grafana:editor` to Editor, and every other
   authenticated realm user to Viewer — read access was the default. The
   mapping now returns nothing for a user without one of the two roles and
   `role_attribute_strict` denies the sign-in (DD-659).
3. **Named platform admins exist.** Two people get realm accounts with
   `grafana:admin` (the observability surface) and `realm-management:admin`
   (the Keycloak console), each with a generated password and a
   must-change-it-on-first-login flag, plus membership of the staged
   `aurelius` tenant organization. The realm asset stays userless
   (CHT-80): the accounts are deployment state, and the runbook carries
   the commands (DD-660).

Not in scope: renaming the internal Service names (the CHT-13 name rule is
machine-facing and unchanged), tenancy enablement (the 15.x series; the
`aurelius` organization is staged in the realm only), and the `dashboard`
host's name.

## Semantics

| Rule    | Statement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHT-135 | The umbrella's `global.hosts` entries are `app`, `auth`, `dashboard` and `o11y`. The `app` entry's default host is `global.domain` itself (the zone apex, ADR 069); every other entry's default host is a role label joined to `global.domain` (`auth.<domain>`, `dashboard.<domain>`, `observability.<domain>`). The `app` and `o11y` entry keys stay — listener names, route names, and the realm asset's host placeholders ride the keys, not the labels; an explicit `hosts.<key>.host` wins, as before. One derivation serves every consumer: the gateway listeners and their names, the edge Certificate SANs, the health-check policy names and paths (`global.gateway.healthCheck.paths.<key>`), the realm asset's `__APP_HOST__`/`__DASHBOARD_HOST__`/`__O11Y_HOST__` placeholders, Grafana's root URL, and every component chart's issuer fallback (`auth.<domain>`). |
| CHT-136 | Grafana's OAuth role mapping maps `grafana` client role `admin` to Admin and `editor` to Editor, and returns no role for anyone else; with `GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_STRICT=true` Grafana denies the sign-in of an authenticated user who holds neither. The mapping is a parseable JMESPath expression. The password admin (`GF_SECURITY_ADMIN_*`) and its recovery Secret are unchanged, so a locked-out operator keeps a way in.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| CHT-137 | The prod realm asset defines a `roles` client scope whose single mapper mints the `resource_access.<client>.roles` claim (multivalued, on the ID and access tokens), so the clients that name the scope in their default scopes resolve it and their tokens carry the claim the Grafana gate and the server authorization read. An asset may only name scopes it defines (CHT-133's rule).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Ported from

Not a Java port. The role-gate mechanism is Grafana's own strict role
mapping (`role_attribute_strict`, Grafana 13 docs); the rename is this
chart set's naming.

## Deviations

- **No old-name alias.** A values file that sets `global.hosts.grafana.*`
  or `global.hosts.atlas.*` after this increment silently changes nothing
  (the key is unknown, the entry defaults still render under the new keys).
  Accepted: one deployment, documented in the runbook's rename step.
- **`o11y` key, `observability` host.** The entry key stays `o11y` (it names
  the listener, route, and realm token), while the derived hostname spells
  `observability` so it explains itself to whoever lands on it (ADR 069).
- **The issuer moves with the rename.** Keycloak's issuer is
  `https://auth.<domain>` once the host does; every client derives it from
  the same rule, and atlas-dev re-imports the realm on the upgrade's pod
  restart. An existing deployment treats the old issuer as dead after the
  rename (sessions and issued tokens from before it stop validating).

## Acceptance

- `tests/test__charts_edge.py`: the listener set names `app`, `auth`,
  `o11y` (`test__gateway_listeners_per_enabled_host`); the edge
  Certificate SANs and the HTTPRoute hostnames carry the derived hosts;
  `test__health_check_policies_cover_every_backend` names the policies
  `<release>-app`, `<release>-auth`, `<release>-o11y`.
- `tests/test__charts_keycloak.py`: the placeholder test substitutes
  `__APP_HOST__`/`__O11Y_HOST__` like the browser hosts (CHT-77/CHT-82);
  the issuer chain derives `auth.<domain>`; the asset defines the `roles`
  scope with the resource-access mapper (CHT-137).
- `tests/test__charts_observability.py`:
  `test__grafana_root_url_follows_the_host` rides `global.hosts.o11y`;
  `test__grafana_rbac_maps_grafana_client_roles` pins the strict mapping
  (CHT-85/CHT-136): `GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_STRICT=true`
  and a `ROLE_ATTRIBUTE_PATH` with no Viewer fallback, written in the
  JMESPath the parser accepts (DD-661).
- Live on atlas-dev: `https://<domain>` (the apex) serves the webapp,
  `https://auth.<domain>/realms/master` answers,
  `https://observability.<domain>/api/health` answers, a realm user without a
  grafana role is denied at the callback, and an account holding
  `grafana:admin` lands as Admin.
