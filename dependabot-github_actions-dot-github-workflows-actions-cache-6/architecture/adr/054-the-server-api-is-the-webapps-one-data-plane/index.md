# 054\. The server API is the webapp's one data plane: the consolidated Aurelius Atlas server

- **Status:** Proposed
- **Date:** 2026-10-22
- **Deciders:** Aurelius Enterprise

## Decision

**One server, one data plane, one client.** Every data call the webapp makes — catalogue, search, and every catalogue surface that follows — goes to the Aurelius Atlas server's API, composed from the single runtime-configured base URL (`apiBaseUrl`, today `/api`). The webapp names no second data host, port, prefix, or search engine, and no second data-plane token.

**The scope is the data plane, not every socket.** The server is the successor of the legacy split — the surface that replaces App Search and the Apache Atlas APIs — and that is the whole of what this decision fixes. It is not a ban on other surfaces: the webapp already reaches Keycloak (sign-in, token refresh, the silent-SSO iframe) and the OpenTelemetry collector, and a future slice may add another. Those are not data planes; each is named at the deployment boundary (the CSP) and recorded by the increment that adds it. A new **data** surface is the event this decision governs, and needs its own record.

**The legacy split is retired, not ported.** The Aurelius application split metadata across two systems: the Apache Atlas catalogue (its REST API) and a third-party search backend carrying the search, governance-quality, and data-quality surfaces (the `/elastic`, `/gov_quality`, `/data_quality` endpoints). Aurelius Atlas consolidates both into the server: search is an endpoint family of the catalogue API (increment 4.1, built on the one store of [047](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)), and the third-party search surface has no Aurelius Atlas backend and is not ported — its client methods exist only for endpoints the server answers ([DD-140](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/conversion/design-log/index.md>)).

Today this is a stated rule over verified fact, not new work: the ported client library (7.3) injects one `API_BASE_URL` and composes every data URL from it (APC-01), the webapp contains no App Search remnants, and the served webapp's content-security policy keeps `connect-src 'self'` for the data plane, widened only for Keycloak's origins (APC-05) — the exception list is the deployment's, and the e2e CSP scenario proves the baseline.

## Context

The legacy application's split was a fact of its history: Atlas held the catalogue, the search backend held the searchable copies plus the governance features, and keeping them in step was the product's burden. Aurelius Atlas replaces the split with one store ([047](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)) and keeps Atlas's public contract ([046](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). The webapp port (7.x) inherits the legacy's two-client shape and must state, once, which API the new product speaks — before the search slice (7.4) decides by omission.

## Requirements

- **R1 — One data endpoint surface.** Every data call the webapp makes goes to the server; the runtime configuration carries one API base URL. Non-data surfaces (identity, telemetry) are the webapp's to reach, named at the deployment boundary.
- **R2 — The public contract stays Atlas's** ([046](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)): the server's endpoints are the Atlas paths, and the parity harness keeps reading the Atlas reference for them.
- **R3 — Search is the server's** ([047](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)): no second index, no third-party engine, in the webapp's view of the system.
- **R4 — The client stays honest** ([DD-140](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/conversion/design-log/index.md>)): client methods exist only for endpoints the server answers, so specs and e2e never assert a backend that will not exist.

## Alternatives

- **Keep the legacy split.** Port the search-backend client as Aurelius shipped it: a second system of record with no Aurelius Atlas backend — the wire format of a dependency this product rejects (047, 050). Fails R3, R4.
- **Proxy the split behind the server.** The server forwards search to a third-party engine: one URL, two systems of record, and a dependency the deployment must run. Fails R3; pays R1's letter to break its purpose.
- **Consolidate later.** Port the split, fold search in when 4.1 lands: dead clients at day one (DD-140's audit finding verbatim) and an origin/auth story left open through the 7.x track. Fails R1 for the whole interim.

## Tradeoffs

- **Positive:** one data origin (CSP `connect-src 'self'` holds for `/api`, proven in e2e), one bearer token on every data call (APC-06, 6.1), one wire format to keep parity with; the search slice is a thin client over an endpoint family, not a second stack.
- **Negative:** search is blocked on the server's 4.1 — the hold DD-140 and DD-143 already accepted; 7.4's client is specified from the Atlas source (052) as 4.1's spec lands, not guessed from the legacy's search-backend DTOs. A future data surface is an ADR event, not a pull request — the friction is the point, and the price of it.
- **Neutral / follow-ups:** the non-data surfaces today are Keycloak (cross-origin, whitelisted in the CSP — APC-05) and the OTel collector (same-origin `/otel` proxy, SHL-11); a future slice may add more, and this record does not stand in their way. The workspace's `EntitiesService` in `aurelius-atlas-data-access` is the FastAPI example's CRUD/SSE client — a template example, not a second data plane; it retires with the examples at 7.10 (DV-64, DD-019).
