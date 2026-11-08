# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-384. The aux API reaches the browser at `/lineage-model/`

- **Status:** Proposed
- **Increment:** 7.22a
- **Date:** 2026-11-07

**Decision.** The webapp's nginx serves the lineage-model API at the same-origin
path `/lineage-model/`, as a third location beside `/api/` and `/otel/`. The
client's default base URL is that path, and `/config.json` can replace it
(LDG-06, LDG-07).

**Reason.** The legacy has no base URL anywhere: `get-lineage-model.ts` calls
the relative path `lineage_model`, and the deployment proxy rewrites it to the
Flask app (`apps/atlas/proxy.conf.json` in development,
`k8s/charts/reverse-proxy/conf.d/atlas.yaml` in the cluster). 7-3 removed that
coupling for the Atlas API: the client composes the prefix from
`API_BASE_URL` and nothing else (APC-01, DD-139). The same rule applied to a
second backend needs one location and one optional key. TLS verification is not
optional here: the calls carry user bearer tokens, exactly the reason DD-142
gives for verifying the `/api/` upstream (LDG-06).

**Alternatives.** Keep the legacy path `lineage_model`. It loses: the webapp's
two existing locations are kebab (`/otel/`), and an underscore path is the
legacy's accident, not a contract (DV-142). Second, mount the aux API on the
gateway instead of the webapp's nginx. It loses: the gateway deliberately stays
coarse and does not duplicate the webapp's proxy (CHT-30, DD-285), and the
browser would then need a second origin in the CSP `connect-src` and in the
Keycloak allowed origins. Third, fold the aux route under `/api/` so no new
location is needed. It loses: `/api/` proxies to one upstream, and a prefix
collision on the Atlas server's own namespace is a worse cost than one location
block.

**Consequences.** The webapp chart gains the two upstream placeholders
(`_LINEAGE_MODEL_UPSTREAM`, `_LINEAGE_MODEL_UPSTREAM_NAME`) that deployment.yaml
resolves, mirroring the API pair (DD-294's URL shape). The CSP needs no change:
`connect-src 'self'` already covers a same-origin path. If a later slice adds
the data2model or validate-entity surface to the browser, each takes its own
location and its own key by the same rule.

### DD-385. The aux app accepts the browser client as an extra audience

- **Status:** Proposed
- **Increment:** 7.22a
- **Date:** 2026-11-07

**Decision.** The lineage-model app gains the setting
`AURELIUS_ATLAS_LINEAGE_MODEL_AUTH_EXTRA_AUDIENCES`; the dev, e2e, and chart
values set it to the browser client (`aurelius` in the dev realm, DD-300's
pairing unchanged). The app's own audience stays
`aurelius-atlas-lineage-model` (LDG-05, LM-08).

**Reason.** LM-08 verifies the caller's token against the app's audience, and
DV-74 states the intent: "browser tokens (azp `aurelius`) pass both". They pass
today only because the deployment sets `AUTH_AUDIENCE` to `aurelius`
(`settings.py`: "the dev deployment sets the webapp's `aurelius`, whose tokens
the chain forwards"), and the e2e mints its tokens for `aurelius` for the same
reason (`e2e/conftest.py`). That single setting cannot express both facts, so a
deployment that keeps its own service identity rejects the browser. The shared
library already supports the union of accepted values (`AuthConfig.extra_audiences`,
AUT-10), so the fix is a mapping, not a new check.

**Alternatives.** Set the app's audience to the browser client, as the dev
deployment does. It loses the service's own identity: a token minted for any
other public client of the realm would then pass, and the app's own client
becomes meaningless. Second, have the webapp mint a second token for the aux
audience. It loses: LM-04 forwards the caller's raw token to Atlas and data2model,
both of which the legacy and 8.2 accept from the browser client. A second token
would break the chain the app exists to guard.

**Consequences.** The aux app's spec test list gains one case (LDG-05's Python
test). `helm/atlas-lineage-model/values.yaml` gains the join beside the existing
`AUTH_AUDIENCE`. The other two aux apps keep their single audience: neither has
a browser caller today. If a later slice gives the browser a data2model surface,
that app gains the same join.

### DD-386. The empty lineage is a `null` answer, not an exception

- **Status:** Proposed
- **Increment:** 7.22a
- **Date:** 2026-11-07

**Decision.** `getLineageModel` answers `null` for the `204` of LM-05/LM-06
(LDG-03). Every other non-2xx status stays on the error channel with its parsed
body (LDG-04).

**Reason.** An entity without lineage is a normal state, not a failure: the
legacy details page shows a plain "no lineage model available" message for it
(`lineage-model.component.html`). The legacy reaches that state by swallowing
every error — `lineage-model.service.ts` catches anything and deletes the stored
model, so an outage and an empty graph look identical on screen. 7.19's failure
posture (the alert path) cannot render a distinction the client destroyed, so
the two channels separate here: absence is a value, a failure is an error.

**Alternatives.** Return an empty model object. It loses: LM-06 explicitly sends
no body, so an empty object would be an invention the parser then has to reject.
Second, keep the error channel for `204` and catch it in the component. It
loses: every caller re-implements the catch, and the 8.15 twin already shows the
better shape for a status with meaning — `SearchService.getSavedSearches` keeps
the server's `204` as a `null` body (DD-314).

**Consequences.** 7.22b's box renders three states from one signal: pending,
`null` (the message), and a model (the diagram). Because LDG-04 keeps failures
visible, 7.19's drawer and a retry affordance can be added to the box later
without a client change.

### DD-387. The aux client lives in `src/lib/aux/` with its own base-URL token

- **Status:** Proposed
- **Increment:** 7.22a
- **Date:** 2026-11-07

**Decision.** `LineageModelService` lands in
`libs/angular/aurelius-atlas-data-access/src/lib/aux/` and reads the new
`AUX_BASE_URL`-style token named for its own API (`LINEAGE_MODEL_BASE_URL`,
default `/lineage-model`). It does not read `API_BASE_URL`.

**Reason.** The lib's layout rule is one subfolder per backend contract, and
`src/lib/atlas/` is the Atlas surface — the `LineageService` that lives there is
the twin of `LineageREST` on the Atlas server (ALN-01..04). The aux APIs are
separate deployments with their own hosts, ports, and issuers' audiences
(ADR 055), so a client that composed its URL from `API_BASE_URL` would claim the
two backends share an origin. That is true in this deployment and false as a
rule: the legacy ran the API on `:7100` while Atlas ran on `:21000`. A token per
API also gives each its own `/config.json` key (LDG-07) without a naming
collision.

**Alternatives.** Put the client in `src/lib/atlas/` beside `LineageService`. It
loses: the two files differ only in their backend, so the folder would stop
carrying its meaning, and a reader cannot tell which lineage call goes where.
Second, compose `lineageModelBaseUrl` from `apiBaseUrl`. It loses the whole
point of DD-139: one key that happens to work for two services. Third, a new
library per aux API. It loses: three services, three packages, and no shared
model to justify the weight (the same call `8.15`/`8.20` make for the Atlas
routes).

**Consequences.** `src/index.ts` re-exports the service (the lib's rule:
consumers import the package root). The `204` handling, the always-sent query,
and the DTO field names are the Angular twin of
`libs/python/aurelius-atlas-lineage-model-client` (`LineageModelParams`,
`LineageModelResponse`, `None` for `204`), so the pair joins the coverage matrix
DD-217 opened: the row closes CL-30's pair. If a later slice ports the data2model
or validate-entity surface, its client joins this folder with its own token.

### DD-422. The standalone resolver points the lineage pair at the service name

- **Status:** Proposed
- **Increment:** 7.22a
- **Date:** 2026-11-08

**Decision.** The standalone stack's `resolve-nginx.sh` fills the two new
placeholders with `https://aurelius-atlas-lineage-model:21002` and
`aurelius-atlas-lineage-model`. The stack runs no lineage-model container, and
its `webapp/config.json` sets no `lineageModelBaseUrl`, so the browser never
calls the pair.

**Reason.** LDG-06 added the pair to the webapp's nginx template, and SWA-02
tests that the resolver covers every placeholder the template carries. The
resolver did not learn the pair in 7.22a, so its own fail-on-leftover guard
broke the standalone stack. The service-name value matches the chart's default
(`deployment.yaml` builds the same name and port from `lineageModel.port`).
An nginx variable `proxy_pass` resolves lazily, so a dead upstream fails one
request and never stops the container from serving.

**Alternatives.** Fill the pair with the server's own upstream. It loses: the
server does not serve `/lineage-model/` (it is an aux API, ADR 055), so every
diagram call would fail against a wrong peer. Second, keep the standalone copy
of the template free of the pair. It loses: the image ships one template, and
SWA-02 reads that one.

**Consequences.** The chart, dev, and standalone now each fill the pair, and
SWA-02 turns green again. A future increment that runs the aux API in the
standalone stack adds the service and its audience without a resolver change
beyond the value.
