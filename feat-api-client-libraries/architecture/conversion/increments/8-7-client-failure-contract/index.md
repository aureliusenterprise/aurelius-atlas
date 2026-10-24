# 8.7 Client failure contract

- **Status:** in progress
- **Pull request:** — (follows the review of 2026-10-24, DD-125)
- **Records:** DD-125 (the review that scoped this; reserves CL-08); cites 8.4, ADR 055

## Scope

Test-completeness plus one minted rule: the review found the four client libraries test their happy path, their 4xx/5xx errors, and the connect-refused propagation — and test nothing about the responses in between. The systematic holes (DD-125): a **200 whose body fails the response model** (no test proves what happens), a **timeout** (only connect-refused is proven), a **token source that raises**, and **`with_token` under concurrency**. This increment closes them across all four libraries:

- `aurelius-atlas-server-client` — `AdminApi`, `TypesApi`, and `get_lineage` against garbage 200s; transport timeout; raising token source; concurrent wrappers on the shared pool.
- `aurelius-atlas-data2model-client` — `extract` against garbage 200s; a 5xx carrying the Atlas body; timeout; raising token source.
- `aurelius-atlas-lineage-model-client` — `get` against garbage 200s; timeout; raising token source; the 5xx/unreachable pair split into one test per behaviour, like the other three libraries.
- `aurelius-atlas-validate-entity-client` — `validate` against garbage 200s; a 5xx carrying the Atlas body; timeout; raising token source.

It does **not** deliver: aux API tests (8.6), frontend error UX (7.19), container-stopping e2e (9.1), any production-code change — every test below pins behaviour the 8.4 clients already have (the review's core finding: the code is right, the proofs are missing).

## Semantics

CL-08 is minted here (DD-125's reservation): the behaviour exists in the 8.4 code (the `model_validate_json` calls) and was never stated. Everything else is already specified by the cited rule in 8.4; the bullets state the exact path each test pins.

| Id | Rule |
| --- | --- |
| CL-08 | A 2xx answer whose body the client's response model rejects — the wrong shape, a JSON type that is not the contract's, or bytes that are not JSON at all — raises the validation failure at the boundary: pydantic's `ValidationError` where the client parses bytes as its model, the JSON decoder's own error where it decodes first (the server client). Never the library's `*ClientError` (that is the non-2xx of CL-04) and never a success: a malformed success is the contract failing, and the caller's own recovery (LM-07's 502, the webapp's alert) is the app's job, exactly as with CL-05's transport failure. |

Proven paths (stated in 8.4):

- **CL-04** (8.4): a non-2xx with a parseable Atlas body carries status, `errorCode`, and `errorMessage` in the library's `*ClientError` — proven today on 400/401/404; this increment adds the **5xx carrying the Atlas body** (d2m, VE), the outage shape the 8.2 chain's breakers ride.
- **CL-05** (8.4): `httpx.RequestError` propagates as httpx's own error — proven today for `ConnectError` only; this increment adds the **timeout** (`httpx.TimeoutException`, the pool's own bound), the infrastructure failure category's client-lib half.
- **CL-03** (8.4): the token source is read per call — this increment adds the **raising source**: its error travels out unchanged and **no request leaves** (a caller whose credential fetch fails never speaks to the wire).
- **CL-03 / CL-02** (8.4): `with_token` shares the pool — this increment adds **concurrency**: two wrappers answering two callers at once, each bearer on its own request, one pool underneath.

## Aurelius origin

None new: CL-08 states the 8.4 clients' own behaviour (the DD-114 contract: the library's model parses the library's response), and the proven paths cite 8.4's own origin list (the Angular `libs/atlas/api` DTOs, the aux-API contracts of 8.1–8.3). No wire behaviour changes, so no Java/legacy citation is added.

## Deviations

None. No wire behaviour changes; 8.4's DD-114/DD-115/DD-116 stand.

## Acceptance

Unit (naming rules per ADR 049; run `uv run pytest libs/python/<lib>/tests`):

- `libs/python/aurelius-atlas-server-client/tests/test__aurelius_atlas_server_client_client.py` — appended: `test__a_200_with_a_body_of_the_wrong_shape_is_the_contract_failing` (CL-08, `AdminApi.version`), `test__a_200_of_plain_text_is_the_contract_failing` (CL-08, `get_lineage`), `test__a_typedefs_answer_of_the_wrong_shape_is_the_contract_failing` (CL-08, `TypesApi.typedefs`), `test__a_timeout_propagates_as_httpxs_own_error` (CL-05, `AdminApi.status`), `test__a_token_source_that_raises_travels_out_unsent` (CL-03, `get_lineage`), `test__with_token_wrappers_serve_concurrent_callers` (CL-03, CL-02, `with_token`).
- `libs/python/aurelius-atlas-data2model-client/tests/test__aurelius_atlas_data2model_client_client.py` — appended: `test__a_200_with_a_body_of_the_wrong_shape_is_the_contract_failing` (CL-08), `test__a_200_of_plain_text_is_the_contract_failing` (CL-08), `test__a_server_outage_answer_carries_the_status_and_the_fields` (CL-04), `test__a_timeout_propagates_as_httpxs_own_error` (CL-05), `test__a_token_source_that_raises_travels_out_unsent` (CL-03).
- `libs/python/aurelius-atlas-lineage-model-client/tests/test__aurelius_atlas_lineage_model_client_client.py` — appended: the two CL-08 tests, the CL-05 timeout test, the CL-03 raising source test (same names); the 8.4 test that packed the 5xx raise and the unreachable propagation in one body is split into `test__a_server_outage_answer_carries_the_status_and_the_fields` (CL-04) and `test__an_unreachable_service_propagates_httpxs_own_error` (CL-05), matching the other libraries' one-behaviour-per-test shape.
- `libs/python/aurelius-atlas-validate-entity-client/tests/test__aurelius_atlas_validate_entity_client_client.py` — appended: the two CL-08 tests, `test__a_server_outage_answer_carries_the_status_and_the_fields` (CL-04), the CL-05 timeout test, the CL-03 raising source test (same names).

Gates: `uv run aurelius-atlas-trace check` — CL-08 shows as named (no gap), the gap count does not grow; `nx test <lib> -c ci` green for the four libs (Sonar reads the coverage — no new production code, so no new-code dip); `ruff check` clean.
