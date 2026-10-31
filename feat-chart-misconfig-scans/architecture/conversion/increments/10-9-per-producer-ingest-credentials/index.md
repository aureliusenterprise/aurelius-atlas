# 10.9 Per-producer ingest credentials

- **Status:** in review
- **Pull request:** [\#183](<https://github.com/aureliusenterprise/aurelius-atlas/pull/183>) (stacked on \#182)
- **Records:** DD-196 (completes its deferral), DD-273/DD-274/DD-275 (relies on), DD-277 (adds)

## Scope

The pre-pentest triage's **M5** (per-producer telemetry credentials, as scoped in 10.7's exclusion list): the seven `otel-*` realm clients share one secret. Both realm assets spell `"secret": "${OTEL_INGEST_CLIENT_SECRET}"` in all seven client blocks, the umbrella generates one `<release>-otel-clients` Secret with one key, and every producer — the server, the three aux APIs, and both metrics pullers — joins that one key into its env. A leaked secret from any one producer's container (the aux API with the smallest surface wins the race) forges telemetry for **all seven**: the collector's OIDC leg verifies the audience and signature, not which client the bearer was minted for, and `azp` attribution (CIA-09) is only as honest as the credential that minted the token. DD-196 deferred the fix deliberately for dev ("one shared dev client secret, the clients differ by id"); the same deferral should never have applied to the cluster shape, and 7.18's "production manifests" gap is what this increment closes.

This increment gives each `otel-*` client **its own secret**:

- The prod asset's seven clients carry seven distinct placeholders (`${OTEL_ATLAS_SERVER_CLIENT_SECRET}`, … — client id uppercased, `_`-joined, suffixed `_CLIENT_SECRET`); the one deterministic mapping is spelled in the asset, and the charts derive it mechanically.
- `<release>-otel-clients` becomes realm-shaped: a non-master realm gets one key per client id (each generated/preserved independently — rotating one never regenerates the others), `master` keeps today's single `OTEL_INGEST_CLIENT_SECRET` key verbatim (the hatch's overrides keep working).
- The Keycloak StatefulSet's placeholder env follows the same shape: seven envs feeding the prod import, the single shared env for master.
- Every producer's `OTEL_CLIENT_SECRET` join reads the key its realm shape uses — its client id on the prod realm, the shared key on master. The env names inside the containers (the apps' settings, the pullers' `oauth2client` configs) do not change: only the join key does.

This increment does **not** deliver: a rotation mechanism (the realm import applies at first boot; rotating a live client's secret stays admin-console work, now scoped to one producer — runbook), per-client secrets in the **dev compose** (`import/master.json` keeps the shared placeholder — DD-256's byte-copy and the e2e suites stay untouched; CHT-79 gains its second named exception), any change to which producer rides which leg (Keycloak-native and the FastAPI example stay legacy-leg, DD-196), or M9 (digest pinning).

## Semantics

The roster — `otel-atlas-server`, `otel-data2model`, `otel-elasticsearch`, `otel-keycloak`, `otel-lineage-model`, `otel-postgres`, `otel-validate-entity` — is the asset's; the umbrella Secret's keys, the Keycloak StatefulSet's placeholder envs, and the six producer joins all derive from it, and a test pins the three cluster-side spellings against the asset itself.

| Id | Rule |
| --- | --- |
| CHT-87 | In `files/aurelius-atlas.json` each `otel-*` client's `secret` is its own placeholder: the client id uppercased with `-` → `_`, suffixed `_CLIENT_SECRET`, wrapped in `${…}` (so `otel-atlas-server` → `${OTEL_ATLAS_SERVER_CLIENT_SECRET}`). No two otel clients share a placeholder and none shares the master asset's `${OTEL_INGEST_CLIENT_SECRET}`. `files/master.json` is unchanged — its seven clients keep the single shared placeholder (DD-256's byte copy). CHT-79's structural parity is amended a second time: each prod `otel-*` client equals its dev peer **minus `id` and `secret`**, and the `secret` difference is exactly this rule's placeholder. |
| CHT-88 | The umbrella's `<release>-otel-clients` Secret carries exactly the keys the imported realm consumes. Non-master realm: one key per client id (`otel-postgres`, …), each value independently lookup-preserved, `secrets.otelClients.clients.<client-id>`-overridden, or `randAlphaNum 32`-fresh (CHT-19 pattern, seven times over — one rotated or supplied value never disturbs the others). Master realm: the single `OTEL_INGEST_CLIENT_SECRET` key with `secrets.otelClients.secret` as its override — byte-for-byte today's behavior. The realm decision reads the same `$kcRealm` chain as CHT-80's users gate. A render never carries a credential no consumer joins and no placeholder resolves. |
| CHT-89 | The Keycloak StatefulSet's import-placeholder env follows the realm shape (CHT-83's pattern, generalized): non-master → one env per client id, named by CHT-87's mapping, each from the Secret key of the same client id; master → the single `OTEL_INGEST_CLIENT_SECRET` env, unchanged. The `DEV_USER_*` and `GRAFANA_CLIENT_SECRET` gates are unchanged; the import's placeholder set and the pod's env set stay equal for both shapes. |
| CHT-90 | Every producer's ingest client-secret join (server, data2model, lineage-model, validate-entity, the Elasticsearch puller, the Keycloak puller) reads `<release>-otel-clients` under key = its own client id on a non-master realm, and `OTEL_INGEST_CLIENT_SECRET` on `master` — resolved from the chart's own realm helper over `global.realm` (CHT-74's fact). The container-facing names never change: `AURELIUS_ATLAS_*_OTEL_CLIENT_SECRET` and the pullers' `${env:OTEL_INGEST_CLIENT_SECRET}` config refs keep spelling what the apps' settings and the `oauth2client` extension read. Each producer keeps naming its client id once per chart (values `config` entry or puller ConfigMap literal); that literal is the join key's twin, and the roster-drift test catches a rename in the asset. |
| CHT-91 | The dev shape is unchanged: `dev/keycloak/import/master.json` and its chart copy keep the shared placeholder, the four `e2e/` suites and the dev `.env` values keep one `OTEL_INGEST_CLIENT_SECRET` everywhere, and the collector's receivers are untouched (they verify signatures and audience, unchanged since 7.18). A per-client dev posture was rejected (DD-277): seven secrets multiply the `.env.enc` surface and the placeholder machinery for a loopback-only dev stack, and DD-196's dev deferral stands. |

## Java origin

None — this increment ports no Apache Atlas behaviour. The reference is the pre-pentest triage's M5 item and DD-196's recorded deferral ("prod deployments inject per-client secrets, the realm import supports it as-is" — which the shared placeholder made impossible until now).

## Deviations

None against Atlas. The dev↔prod divergence deepens along the line DV-88 drew: the realm assets now differ in credential shape as well as hardening — the prod asset's seven per-client placeholders against master's shared one — and CHT-79's drift guard carries the second named exception for exactly this field (the first was 10.8's `grafana` client). DD-277 records the design: one Secret with per-client keys over seven Secrets, realm-conditional keys keeping the `master` hatch fully functional over prod-only keys, and dev staying shared.

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green (the chart owners).
- `tests/test__charts_keycloak.py` names CHT-87 (the rendered prod asset's seven distinct placeholders; master's shared one; CHT-79's amended parity — otel peers equal dev minus `id` and `secret`, with the secret delta exactly the rule), CHT-89 (StatefulSet envs: seven named envs on the stock render with their key joins, the shared env on master).
- `tests/test__charts_umbrella.py` names CHT-88 (stock Secret keys = the seven client ids, each independently generated and length-checked; per-client values override leaves the others generated; master render = the single shared key; the roster-drift guard: Secret keys == the asset's otel client ids == the StatefulSet's env joins) and CHT-91's negative (master gains no per-client keys).
- `tests/test__charts_{server,aux,elasticsearch}.py` name CHT-90 on their stock renders (key = client id) and on a `global.realm=master` render (key = shared name) — six producers, both shapes.
- Runbook: the credentials section names the per-client keys; the rotation note says one leaked producer rotates one key (realm re-import or admin console — the mechanism is unchanged, the blast radius is not). `dev/keycloak/AGENTS.md` and `helm/AGENTS.md` record the realm-shaped Secret; `dev/elasticsearch/AGENTS.md` and the aux `AGENTS.md` notes if their join lines are documented there.
- Hand check: not run in CI here (no live Keycloak); proven by render — a stock umbrella's seven producers join seven distinct keys and the realm import resolves seven distinct placeholders from seven distinct envs.
