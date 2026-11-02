# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-186. Entity details arrives as a routed skeleton; its data spine joins 2.3

- **Status:** Proposed
- **Increment:** 7.6
- **Date:** 2026-10-22

**Decision.** 7.6 ports the Aurelius details screen (`search/details/:guid`) as
the skeleton the data-free webapp can host today: the route contract, the header
shape (title, type-name line, the 7.13 `breadcrumbs`), the description box, the
properties accordion, and the side navigation — every part in its empty state,
fed by the bridge keys `search.details.*` already in the catalogue. No entity
fetch: `GET /v2/entity/guid/{guid}` is server 2.3 (planned), the type dispatch
is nine `m4i_*` governance layouts, and the lineage/quality cards post to
backends Aurelius Atlas will not have (DD-140). The wiring increment — the
resolver, the header data, the type components, lineage — is named in the spec
and lands when 2.3 does.

**Reason.** Every Aurelius details section reads one resolved entity; the
Aurelius `DetailsResolver` feeds a search stack that DD-140 deliberately left
unported. Shipping the fetch against a 404 is the speculative build DD-140
refuses, and shipping mock entity data is a UI promise the slice cannot keep —
the 7.5 seam (DD-143) again, one screen deeper. The skeleton is what is true
today: the URL is the screen's address, the chrome's strings are all keyed, the
7.13 components already render the trail and the rows, and the deep-link
contract (DET-07) is testable end to end with zero data.

**Alternatives.** A full port against `HttpTestingController` mocks (the e2e
stack runs the real server — the mocks evaporate at the first served test). A
stub server (a second source of truth the parity harness must then ignore).
Waiting for 2.3 entirely (the route, the layout, and the strings are real work
that 2.3 does not gate; the 7.5 precedent ports exactly this kind of slice).

**Consequences.** The webapp owns a details route that renders a provable
empty state; 2.3+7.6 is composition, not design — the resolver calls the
client method DET-03 builds, the header binds the DTO, the type components
join the shell. The nine `m4i_*` layouts stay deferred: Aurelius's own type
model, out of Aurelius Atlas's scope until its data exists (the slice table
names the wiring increment).

### DD-187. The entity client is built test-first against the Atlas wire format

- **Status:** Proposed
- **Increment:** 7.6
- **Date:** 2026-10-22

**Decision.** `AtlasEntitiesService.getEntityByGuid(guid)` lands in 7.6: the
DTOs are typed from the Apache Atlas 2.4.0 source (`AtlasEntity.java`,
`EntityREST.java`), cited at the type, and the specs are `HttpTestingController`
assertions on the request (path, headers, guid encoding) and the response
mapping. No screen calls it (DD-186's skeleton fetches nothing); the 2.3+7.6
wiring increment consumes it.

**Reason.** DD-140's rule is one method per server increment, "each method
lands testable against the real server." The entity-by-guid read is the
surface 2.3 implements, and its wire format is fixed by Atlas's source and
tests, not by this workspace — so the DTOs and the request shape are knowable
today, and a spec that asserts them is honest (it never claims a 200).
Building the client in the wiring increment makes that PR data + layout +
client at once; splitting it keeps 2.3+7.6 about the server round-trip.

**Alternatives.** Grow the client in 2.3+7.6 (the honest choice 7.3's pattern
allows — accepted as the fallback if the split adds review load). Port the
whole legacy `EntityAPIService` surface (create, update, bulk, relationships —
endpoints 2.4/3.x, unportable per DD-140's audit).

**Consequences.** The data-access lib gains one Atlas-native entity method,
the typedefs client's shape (APC-01 base url, one method per legacy
duplication, DD-140). When 2.3 lands, the e2e wiring scenario is the method's
first real 200; its specs keep asserting the request until then.

### DD-188. One API base: the client's URLs all ride the API_BASE_URL token

- **Status:** Accepted
- **Increment:** 7.6
- **Date:** 2026-10-22

**Decision.** ADR 054's rule, in client shape: every Aurelius Atlas **data**
request composes its URL from the injected `API_BASE_URL` token (the APC-01
rule, now carrying the consolidated-server decision), and the webapp ships no
second data-plane base URL, no hard-coded data host, and no search-backend
client. Non-data surfaces keep their own configuration — Keycloak's URL
(APC-05), the OTel exporter (SHL-11) — named at the deployment boundary, not
through the token. The served-app boundary holds the rule closed: the CSP
keeps `connect-src 'self'` for `/api`, widened only for Keycloak's origins,
and the e2e CSP scenario asserts the baseline.

**Reason.** The user's direction, 2026-10-22: "the legacy app had a split
between the app search api and apache atlas api. This new version consolidates
these into the server api... All requests can be expected to be made to the
server api," scoped the same day: "we may have other surfaces eventually but
this is the one that replaces app search and the apache atlas apis" — the
decision fixes the data plane's successor, and does not fence in identity,
telemetry, or future non-data surfaces. The audit (7.3, DD-140) found the
legacy split's two clients —
the Atlas REST set and the App Search stack (`/elastic`, `/gov_quality`,
`/data_quality`) — and ported only endpoints the server answers; the state
already matches the rule. Recording it turns an audit outcome into a contract
the search slice (7.4) cannot erode: when search lands, it lands as a server
endpoint family (4.1) behind the same token, not as a second stack.

**Alternatives.** Record nothing (true today, silent tomorrow — 7.4 is the
slice where a legacy-shaped search client would sneak back in). A purity-gate
grep for the legacy hosts (the CSP assertion is the served-app's proof, the
token is the code's; a grep bans strings, not shapes).

**Consequences.** DET-03's entity client composes from the token like the
typedefs client; 7.4's search client joins it, specified from the Atlas
source. The template example's `EntitiesService` (FastAPI CRUD/SSE, one SSE
stream) stays a retiring example (DD-019, 7.10), not a second API. Any future
non-server call site is an ADR event, not a pull request.
