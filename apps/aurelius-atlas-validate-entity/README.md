# aurelius-atlas-validate-entity

The Aurelius Atlas validate-entity API: an entity in, the fixed governance-quality
document out — the validation endpoint the legacy editor called while a record was
being edited, ported from the Aurelius `m4i-validate-entity` service
([ADR 055](../../docs/architecture/adr/055-the-lineage-chain-is-a-named-data-surface.md)).

Introduced by increment 8.3. The legacy service **is a mock**
([DV-14](../../docs/architecture/conversion/deviations.md)): the body is never read
and the answer is a constant — the four governance cards the editor's panel renders.
The port keeps that browser contract verbatim, with the workspace's auth and
observability ([spec](../../docs/architecture/conversion/increments/8-3-validate-entity-api.md)).
The code follows the workspace's example-app layout (DD-120): the collaborators
built by `providers/`, the endpoints in `routes/`, and a thin composition root
in `app.py`.

## Endpoints

| Endpoint        | Auth            | Answers                                                           |
| --------------- | --------------- | ----------------------------------------------------------------- |
| `POST /`        | Keycloak bearer | `200` the mock document, for any body (malformed bodies included) |
| `GET /liveness` | –               | `204` while the app runs (the container healthcheck)              |

## Run

```bash
npx nx serve aurelius-atlas-validate-entity   # https://localhost:21003, dev Keycloak + collector up
npx nx test aurelius-atlas-validate-entity -c ci
npx nx e2e aurelius-atlas-validate-entity     # the image, realm tokens, real TLS
```

The app has no upstreams: unlike the [lineage-model](../aurelius-atlas-lineage-model/README.md)
chain (8.2), nothing is forwarded. Real governance validation is a future server rule
(DV-14); the app ships the mock, as the legacy did.
