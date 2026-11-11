# 12.7 The governance verdicts, live

- **Status:** in progress
- **Pull request:** –
- **Records:** adds VEV-01..06 and DD-498..501 (here); adds CHT-113 (the deployed leg: the
  app chart's `SERVER_BASE_URL`/`TOKEN_URL`/`SERVER_CLIENT_SECRET` joins, the
  `<release>-validate-entity-client` Secret, and the master realm's import env — the prod
  realm's client join still lands with 12.3); amends VE-01, VE-02 and CL-40 (8.3's mock
  rules and the client twin — the card document retires); amends EDT-21, EDT-23 and EDT-24 (7.24's
  banner data path, over the new shape); adds ADR 061 (Proposed, supersedes ADR 055's mock clause)
  and DV-149 (supersedes DV-67). Relies on 12.6 (GQ-01..07, the engine half) and cites DV-146 (a
  stored expression is never executed) and DD-458 (a job's own service identity, the pattern this
  app's catalogue leg copies).

## Scope

8.3 shipped the validate-entity API as the legacy mock: `POST /` ignored the entity and answered
four canned cards (DV-67). 12.6 built the engine half — a governance rule is data, and one rule
answers one boolean verdict over one record's attributes. This increment connects them: the app
reads the ACTIVE governance rules from the catalogue, runs each over the draft the browser sent,
and answers the real verdicts. The webapp's editor banner switches to the new shape in the same PR,
so the deployed banner never shows a shape it cannot parse (the clean cut, ADR 061).

Delivered here:

| Module                                                | Holds                                                                 |
| ----------------------------------------------------- | --------------------------------------------------------------------- |
| `aurelius_atlas_validate_entity.verdicts`             | the rules door, the cache, the verdict assembly                       |
| `aurelius_atlas_validate_entity.providers`            | grows: the upstream pool, the app's own mint, the breaker             |
| `aurelius_atlas_validate_entity/routes`               | `POST /` answers verdicts over the draft's attributes                 |
| `aurelius_atlas_validate_entity_client`               | the verdict models replace the card models (CL-40 amended)            |
| `aurelius-atlas-data-access`                          | the Angular twin types and the service follow the shape               |
| `aurelius-atlas-webapp` editor                        | the banner renders verdict lines from the array, grouped by attribute |
| `dev/keycloak`, the app's `.env`/helm, the e2e stacks | the app's service identity and its upstream wiring                    |

Explicitly not delivered, with the increment that will:

| Not delivered                                        | Lands with     | Why                                                        |
| ---------------------------------------------------- | -------------- | ---------------------------------------------------------- |
| The gov rule editor form and the kinds rows for gov  | 7.28           | The editor reuses 7.27's form, which lives in PR #317      |
| Storing each entity's verdicts when the entity saves | 12.8 (planned) | The server's write path evaluates and stamps               |
| A prod-realm client join for this app                | a chart PR     | The scanner's join waits at 12.3; this app joins with it   |
| Re-validating stored entities in bulk                | a later slice  | The scanner scores dataset files; gov rules do not join it |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056). The reference is
the Aurelius source (ADR 052): the legacy `m4i-validate-entity` service and the editor's
`entity-validate` trigger — not a running system.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VEV-01 | `POST /` reads the draft entity's `attributes`. The body must be a JSON object and its `attributes` a JSON object; anything else is a `400` with the Atlas error body (the DV-79 posture — the legacy Flask 500 is not ported). The rest of the body is ignored: a verdict reads attributes, not relationships or classifications.                                                                                                                                                                                              |
| VEV-02 | One ACTIVE governance rule answers one verdict: `{ruleGuid, ruleName, attribute, dimension, compliant, message}` — `compliant` a JSON boolean, `message` the verdict line 12.6's engine carries (the rule's own message for its verdict, the kind's reason when the rule stores none). `attribute` is the rule's own attribute: the banner groups the lines by it.                                                                                                                                                              |
| VEV-03 | The rules ride the server's basic search of `m4i_gov_data_quality`, paged by marker to the end. A rule is ACTIVE unless its `active` attribute says otherwise (12.2's reading). A rule the vocabulary cannot read — a stored expression rule — answers no verdict and rides in `unreadRules` as `{ruleGuid, ruleName, error}` (DV-146): recorded, never executed.                                                                                                                                                               |
| VEV-04 | The catalogue leg signs as the app's own service identity (DD-458's pattern): a client-credentials token minted once, refreshed ahead of expiry, `atlas-read` on the server client. The caller's token verifies at the gate (VE-03 of 8.3, unchanged) and is never forwarded.                                                                                                                                                                                                                                                   |
| VEV-05 | The rule set is cached in process for `RULES_CACHE_SECONDS` (default 60; 0 off). A draft answers live on every call; the rules refresh at most once per window. A failed read caches nothing and answers as VEV-06 does: `502`, never a no-rules answer.                                                                                                                                                                                                                                                                        |
| VEV-06 | The catalogue leg travels one circuit breaker: an outage (transport failure, a `5xx`) opens it; a request fact (a `4xx`) answers and resets. An unreachable, refusing, or open-circuited upstream answers `502` with the Atlas error body (DV-80's posture, LM-07/LM-12's sibling) — never the mock document, never a silent no-rules answer. A leg with no mint configured (`SERVER_CLIENT_SECRET` unset, the join absent) answers the same `502`: a cluster without the identity shows no verdicts rather than invented ones. |

VE-04 (liveness) and the caller gate of VE-03 stand unchanged. VE-05 grows: the settings gain
`SERVER_BASE_URL`, `TOKEN_URL`, `SERVER_CLIENT_ID` (default
`aurelius-atlas-validate-entity`), `SERVER_CLIENT_SECRET`, `RULES_CACHE_SECONDS`, and the breaker
pair. The leg's two enablers — the base URL and the secret — carry dev defaults and are set in
every deployed environment; only a cluster without the realm join leaves the secret unset, which
VEV-06 answers `502` rather than a start-up failure: the app stays live without its governance
leg. CL-40 is amended: the client twin models the verdicts, not the cards. EDT-21/23/24 are
amended: the trigger and the quiet swallow stand; the banner parses the verdict array (grouping
keeps the legacy `definition` → Description alias, GOV_CARD_KEYS).

## Aurelius origin

- `backend/m4i-validate-entity/.../m4i_validate_entity.py` — the Flask mock this app replaces
  (DV-67, superseded by DV-149). Its four cards retire; the trigger contract (POST the draft,
  swallow failures quietly) survives in the webapp (EDT-23).
- `libs/m4i-governance-data-quality/.../rules/definitions/*.json` — the rule corpus the legacy
  Flink job evaluated; read by 12.6 into the two-kind vocabulary, read here through the search.
- The legacy `@cached` on the mock's answer is the precedent for VEV-05's window — narrowed to the
  rules only: a draft must never be answered from a cache.

## Deviations

DV-149 supersedes DV-67: the app answers real verdicts instead of shipping the legacy mock. ADR 061
supersedes ADR 055's validate clause: R3's "browser contract kept verbatim" retires for this
endpoint — the shape is Aurelius's own now, and the webapp twin changes in lockstep (the clean
cut). DV-146 stands extended: an expression rule reaches this endpoint as an unread rule. The
caller's `401`/`400`/`502` bodies keep the Atlas error shape (AUX-05).

## Acceptance

Unit (`uv run pytest apps/aurelius-atlas-validate-entity/tests`), on the fake issuer and a fake
upstream (8.2's harness pattern):

| Proves       | File                                                                               |
| ------------ | ---------------------------------------------------------------------------------- |
| VEV-01..06   | `tests/test__verdicts.py` (door, cache, assembly)                                  |
| VEV-01/02/06 | `tests/test__aurelius_atlas_validate_entity_app.py` (route over the fake upstream) |
| VEV-04       | `tests/test__…_providers_upstreams.py`, `tests/test__…_providers_auth.py`          |
| VE-05 grown  | `tests/test__…_settings.py`                                                        |
| CL-40        | `libs/python/aurelius-atlas-validate-entity-client/tests`                          |

Scenarios (parity, read from Aurelius source, over the fake upstream):
`scenarios/validation/verdicts.scenario.yaml` (draft + rules → verdict document) and
`verdict-rejections.scenario.yaml` (401/400/502 stages).

Webapp unit: `entity-editor.component.spec.ts` (banner over the array),
`validate-entity.service.spec.ts` (the twin). Run `nx test aurelius-atlas-webapp -c ci` and
`nx test aurelius-atlas-data-access -c ci`.

E2E: this app's own suite grows the real server and store beside the app (8.2's chain pattern: the
upstream as a container), seeds two active rules through the catalogue, and answers them live; the
`502`-with-the-server-down case stays a unit proof on a closed pool (DD-200's seam), not a stopped
container (DD-223). The webapp suite's banner test seeds the rules and pins one success and one
warning line over the deployed stack (`test__aurelius_atlas_webapp.py`).
Level 1 + 2; the realm join is exercised by the webapp suite's mint.
