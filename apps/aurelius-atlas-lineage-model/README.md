# aurelius-atlas-lineage-model

The Aurelius Atlas lineage-model API: an entity guid in, the entity's lineage
graph fetched from the Atlas metadata API, flattened, and extracted through the
[data2model](../aurelius-atlas-data2model/README.md) API — the AR3 model string the
legacy lineage graph drew, ported from the Aurelius `m4i-lineage-model` service
([ADR 055](../../docs/architecture/adr/055-the-lineage-chain-is-a-named-data-surface.md)).

Introduced by increment 8.2. The app is a proxy with a flattener: it calls the
Atlas `v2/lineage` feed and the 8.1 data2model API, forwarding the caller's
bearer token to both, and answers the extraction verbatim
([spec](../../docs/architecture/conversion/increments/8-2-lineage-model-api.md)).
Each upstream is guarded by its own circuit breaker (increment 8.5, DV-60):
repeated outages open the circuit and the 502 arrives fast, without calling the
upstream, until a half-open trial closes it again
([spec](../../docs/architecture/conversion/increments/8-5-lineage-model-circuit-breakers.md)).
The code follows the workspace's example-app layout (DD-118, DD-119): the
collaborators built by `providers/`, the endpoints in `routes/` (the lineage
route composes the fetch → flatten → extract flow), and a thin composition
root in `app.py`.

## Endpoints

| Endpoint        | Auth            | Answers                                                                    |
| --------------- | --------------- | -------------------------------------------------------------------------- |
| `GET /`         | Keycloak bearer | the data2model answer, verbatim (`{metadata: […], model: "<ar3 string>"}`) |
| `GET /`         | Keycloak bearer | `204` when the guid has no lineage; `400`/`502` on upstream failures       |
| `GET /`         | Keycloak bearer | `502` fast, without the upstream call, while a circuit is open (8.5)       |
| `GET /liveness` | –               | `204` while the app runs (the container healthcheck)                       |

## Run

```bash
npx nx serve aurelius-atlas-lineage-model   # https://localhost:21002, dev Keycloak + collector up
npx nx test aurelius-atlas-lineage-model -c ci
npx nx e2e aurelius-atlas-lineage-model     # the chain: app + real data2model + fixture Atlas
```

The Atlas lineage feed is the server's (5.1, DV-52); until it lands, the e2e
chain points the app at a canned-file fixture Atlas (DD-111).
