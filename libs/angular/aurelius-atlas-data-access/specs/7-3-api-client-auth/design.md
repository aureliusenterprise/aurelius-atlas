# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-139. The client owns the base URL; the proxy forwards the prefix untouched

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The REST client composes every URL from the injected `API_BASE_URL` token
(`/api` from runtime `/config.json`), and the webapp's proxies — dev and e2e — forward
`/api` to the Atlas server with the prefix intact. The Aurelius mechanism (relative URLs
resolved against `<base href>`, prefix injected by the deployment proxy: dev
`proxy.conf.json` rewrites `/atlas` → `:21000/api/atlas`, k8s Apache `ProxyPass` rewrites
`/<ns>/atlas/atlas/` → `atlas:21000/api/atlas/`) is not ported.

**Reason.** The 7.0 audit asked how the legacy app reaches the server and found: nowhere
in the code — the coupling lives entirely in deployment. That is invisible to the compiler,
untestable against a stub, and the reason the legacy client cannot say which API it
speaks to. Aurelius Atlas inverts it: the client names its base URL from config (DD-130's
runtime-settings channel), the proxy is a dumb forwarder, and a deployment moves the API
by serving a `config.json`, not by editing proxy tables. The server's routes already carry
the `/api/atlas/...` prefix, so a rewriting proxy would double-strip it; forwarding
untouched is the composition that type-checks (`${apiBaseUrl}` + `/atlas/v2/...`).

**Alternatives.** Port the Aurelius split (relative URLs + rewriting proxy): keeps parity
with a deployment model this workspace does not share, and re-hides the coupling. Have the
browser call the server origin directly (`https://server:21000`): needs CORS policy and
per-deployment origins in the CSP, reopening the same-origin boundary ADR 039 closes.

**Consequences.** The webapp's dev proxy no longer points at the FastAPI example's
`:8000` (the copied line retargets at `:21000`); the example app keeps its own chain
until 7.10 retires it. The e2e nginx's `/api/` placeholder comment ("the Atlas API server
joins this proxy when 7.3 wires real data") is redeemed by DD-142.

### DD-140. The REST client ports the live surface; the search client is redesigned in 7.4

- **Status:** Proposed (the lineage/validate exclusion is superseded by
  [ADR 055](../../../../../docs/architecture/adr/055-the-lineage-chain-is-a-named-data-surface.md) —
  increments 8.x build those backends; the App Search exclusion stands)
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The ported client covers the endpoints the server implements today: the
typedefs of 1.6 (`/api/atlas/v2/types/**`) and the admin trio (`version`, `status`,
`session`). The legacy search stack — `AppSearchService`, the engine subclasses, the
`{provide: AppSearchService, useClass: AtlasEntitySearchService}` alias, ~300 lines of
App Search DTOs — is not ported in this slice. 7.4 designs the search client when browse
consumes it, against `/v2/search/basic` (increment 4.1), not against the App Search shape.

**Reason.** The audit found the Aurelius search posts to DuckDuckGo Enterprise App Search
engines (`/elastic`, `/gov_quality`, `/data_quality`) — a third-party search backend
Aurelius Atlas does not have and will not gain: search is Elasticsearch-native here
(ADR: the store). The server's Atlas-native search is increment 4.1, planned. Porting the
App Search DTOs now would ship typed structs for a wire format no server speaks, specs
asserting calls that answer 404, and a mapping layer 4.1 reworks anyway (DD-140's
consequence). The rest of the legacy surface (entity, glossary, relationship, lineage,
validate, dashboard) has the same property in smaller doses: endpoints 2.3+ have not
landed, and the lineage/validate/dashboard backends are separate services with no
Aurelius equivalent.

**Alternatives.** Port all 65 files now: a client that lies about the system, with dead
code at day one (the legacy app itself leaves half of it unused). Port search against the
legacy shape with an adapter: the adapter's shape is guesswork against an unbuilt
endpoint.

**Consequences.** The client grows one method-set per server increment — each method
lands testable against the real server, and the specs stay honest through 7.4–7.9. The
legacy's service+free-function duplication (e.g. `EntityAPIService.getEntityById` and
`get-entity-by-id/`) collapses to one method each as each set is ported.
