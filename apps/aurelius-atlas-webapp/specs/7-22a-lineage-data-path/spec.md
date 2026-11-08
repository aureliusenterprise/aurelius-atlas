# 7.22a Lineage diagram: the data path

- **Status:** proposed
- **Pull request:** —
- **Records:** LDG-01..08 (the band this slice opens), DD-384..387; adds DV-142
  to [deviations](../../../../docs/architecture/conversion/deviations.md) in the
  implementation PR; corrects 7-3's origin row for
  `libs/atlas/api/src/lib/get-lineage-model/**` (its "not ported — backends
  Aurelius Atlas does not have" is void: increment 8.2 shipped the backend);
  relies on LM-01..LM-08/LM-10 (8.2, the API contract), DV-68/DV-69/DV-74 (the
  forwarding chain and its audience), DD-139 (the client composes the prefix),
  DD-142 (the e2e nginx data path), DD-203 (the Python client's models),
  DD-223 (no shared-service restarts in e2e), ADR 055 (the auxiliary APIs)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The legacy details page draws its lineage diagram from one call: the browser
asks the lineage-model API for the opened entity, and the API answers with an
archimate3 model document (a JSON string) plus one metadata row per concept, or
with `204` when the entity has no lineage. Aurelius Atlas shipped that API in
increment 8.2 (`apps/aurelius-atlas-lineage-model`, the LM rules, port and
contract unchanged). What never shipped is the browser's way to reach it: the
webapp's nginx proxies only `/api/` and `/otel/`, its runtime config names no
third base URL, and no Angular client exists for the aux API.

This increment is the data path only. Delivered here:

- the nginx proxy: a third same-origin location, `/lineage-model/`, to the aux
  API (LDG-06) — the legacy's `lineage_model` deployment-proxy path, renamed to
  the kebab style the webapp's own locations use (DV-142, DD-384)
- the runtime configuration: an optional `lineageModelBaseUrl` key in
  `/config.json` (default `/lineage-model`), the settings channel pattern
  APC-01/DD-139 already sets (LDG-07)
- the bearer token on every call to the new prefix (LDG-05, the APC-06
  interceptor pattern)
- the acceptance for the new audience: the aux API verifies tokens (LM-08), and
  the webapp sends the browser's own token (azp `aurelius`, what LM-04 forwards
  upstream); the app gains an `auth_extra_audiences` setting and the charts join
  the browser client, so the shared verifier accepts it without loosening the
  app's own client (DD-385)
- the Angular client: `LineageModelService` in `aurelius-atlas-data-access`
  (`src/lib/aux/`, the lib's one-subfolder-per-contract layout; the aux APIs are
  not the Atlas surface): `getLineageModel(guid, depth = 3, direction = 'BOTH')`
  with the query always sent (the ALN-01 convention), the typed answer
  `{ model, metadata }`, and `null` for the `204` (LDG-01..04)
- the dev chain: `nx serve aurelius-atlas-webapp` starts the lineage-model and
  data2model apps beside it, and the webapp's e2e compose gains the two aux
  containers pointed at the stack's real Atlas server (LDG-08)

Explicitly not delivered here, with the increment that will:

| Not delivered                                                    | Lands with | Why                                                              |
| ---------------------------------------------------------------- | ---------- | ---------------------------------------------------------------- |
| The lineage box on the details page, its states, and its diagram | 7.22b      | The box is the renderer; this slice only proves the data arrives |
| The selection panel and the quickview                            | 7.22c      | Unchanged                                                        |
| The toolbar and PNG export                                       | 7.22d      | Unchanged                                                        |

## Semantics

Rules LDG-01..08, the band the lineage-diagram slice opens; TS tests name the
ids (the 7.21a convention). The server contract is cited, not restated: LM-01
owns the query, LM-04 the answer body, LM-05/LM-06 the `204`, LM-08 the token.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LDG-01 | `LineageModelService.getLineageModel(guid, depth = 3, direction = 'BOTH')` issues `GET {baseUrl}/?guid=&depth=&direction=` — the aux API's route is its root (`apps/aurelius-atlas-lineage-model/.../routes/lineage.py`). Every parameter travels on every call (the ALN-01 convention), composed from the injected base URL (LDG-07).                          |
| LDG-02 | A `200` answer is read as `{ model: string, metadata: { id, data }[] }` (the `LineageModelResponse` twin, DV-68's passthrough: `model` stays a JSON string, not a parsed object).                                                                                                                                                                               |
| LDG-03 | A `204` answer is the empty lineage (LM-05, LM-06): the method answers `null`, not an error. The caller decides what absence looks like.                                                                                                                                                                                                                        |
| LDG-04 | A `400`, `401`, or `502` answer stays on the error channel with the parsed Atlas-shaped body (`{ errorCode, errorMessage }`, LM-07): the client adds no interpretation.                                                                                                                                                                                         |
| LDG-05 | Every request under the lineage-model prefix carries the bearer token: the webapp's `bearerTokenConfig` gains the prefix (the APC-06 pattern). The chain forwards that token upstream unchanged (LM-04).                                                                                                                                                        |
| LDG-06 | The webapp's nginx serves the aux API same-origin at `/lineage-model/`: a third location beside `/api/` and `/otel/`, proxied over TLS with the stack's CA verified and the upstream's name pinned (the DD-142 posture — the calls carry user tokens). Anonymous requests reach the aux API's own `401` (LM-08); nginx adds no auth of its own.                 |
| LDG-07 | The runtime configuration gains the optional `lineageModelBaseUrl` key (`AppConfig`, `parseAppConfig`): when set, the app provides it to the client; when absent, the client's default is `/lineage-model` (SHL-10 — the config file is the settings channel; the legacy's per-environment deployment proxy is not ported, DD-139).                             |
| LDG-08 | The development serve target starts `aurelius-atlas-lineage-model:serve` and `aurelius-atlas-data2model:serve` beside the webapp (`dependsOn`, the dev-infra pattern), and the webapp's e2e compose carries both containers, the aux app pointed at the stack's real Atlas server (DD-223: the suite starts its own named services and restarts no shared one). |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
cited by path so a reviewer can compare:

- `libs/atlas/api/src/lib/get-lineage-model/get-lineage-model.ts` — the client
  being twinned: `GET lineage_model?guid={guid}&depth=3&direction=BOTH`
  (defaults depth 3, direction `BOTH`). 7-3's origin table marked it "not
  ported"; that row is corrected here, because increment 8.2 shipped the backend.
- `apps/atlas/proxy.conf.json` (`/lineage_model` → the legacy Flask app on
  `:7100`) and `k8s/charts/reverse-proxy/conf.d/atlas.yaml` (the same path to
  the legacy backend) — what LDG-06 replaces.
- `libs/authentication` — the token the legacy chain forwards; here the
  keycloak-angular session and the APC-06 interceptor (LDG-05, DD-141).
- `libs/repository/src/lib/modelview-convert/**` (`POST modelview/api/convert`)
  — not ported: the legacy snapshot calls it nowhere (dead surface; recorded
  with 7-3's other unported rows, and cited again in 7.22d).

## Deviations

None against Apache Atlas: no server surface is added or changed. Against the
Aurelius product (DV-142 joins `deviations.md` in the implementation PR):

- **DV-142**: the legacy serves the API at `lineage_model` (an underscore path
  chosen by its deployment proxy); Aurelius Atlas serves it at `/lineage-model/`
  behind the webapp's own nginx, beside `/api/` and `/otel/` (DD-384). The
  legacy's standalone `:7100` origin disappears.
- the `204` becomes a typed `null` answer instead of an HTTP error the caller
  must catch (LDG-03, DD-386); the legacy service swallowed every failure
  silently, and this client swallows nothing (LDG-04 keeps the errors visible).
- the aux API accepts the browser client as an extra audience instead of
  trusting the token blindly (DV-74's posture, kept): the verifier's rule stays
  LM-08 (DD-385).

## Acceptance

- Vitest (unit, the data-access lib): `lineage-model.service.spec.ts` —
  the composed URL and the always-sent query (LDG-01), the typed `{ model,
metadata }` read (LDG-02), `204` → `null` (LDG-03), `400`/`401`/`502` pass the
  Atlas-shaped body through (LDG-04); the webapp's config spec covers
  `lineageModelBaseUrl` parse and default (LDG-07); the interceptor spec covers
  the new prefix (LDG-05).
- Python (unit): the aux app's settings gain `auth_extra_audiences`, passed to
  the shared verifier (its spec grows one test: a token minted for the browser
  client passes, a third client's is still rejected — LM-08's shape).
- Playwright (e2e, pytest — `apps/aurelius-atlas-webapp/e2e/`, authenticated
  fixture APC-10): through the served webapp's origin —
  `GET /lineage-model/?guid=<unknown>` answers `204`, and an anonymous request
  answers `401` (LDG-06, LM-08); with the seeded m4i mini-graph (DET-34's), a
  request for the seeded dataset answers `200` and the body carries a `model`
  string that parses to an `ar3_model` document plus its metadata rows (the
  LM-04 chain over the real server, the real data2model, and the browser token).
- Dev: `nx serve aurelius-atlas-webapp` answers `/lineage-model/?...` with the
  chain up (LDG-08).
- Gates: `nx lint aurelius-atlas-webapp`, `nx test aurelius-atlas-webapp -c ci`,
  the purity script (WBP-02, unchanged), `nx e2e aurelius-atlas-webapp`,
  `nx test aurelius-atlas-lineage-model -c ci`.
