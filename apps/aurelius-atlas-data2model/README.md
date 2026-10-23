# aurelius-atlas-data2model

The Aurelius Atlas data2model API: tabular data plus element/relation/view rules in,
an [archimate3](../../docs/architecture/conversion/increments/8-1-data2model-api.md)
model string out — the model-extraction API the legacy lineage graph drew on, ported
from the Aurelius `m4i-data2model` service
([ADR 055](../../docs/architecture/adr/055-the-lineage-chain-is-a-named-data-surface.md)).

Introduced by increment 8.1. The rules are pydantic models and the extraction is
plain Python — the port carries no pandas (DD-109) and no `m4i-analytics` (DV-15).
The code follows the workspace's example-app layout (DD-120): the collaborators
built by `providers/`, the endpoints in `routes/` (the extract route calls the
engine directly), and a thin composition root in `app.py`.

## Endpoints

| Endpoint        | Auth            | Answers                                                |
| --------------- | --------------- | ------------------------------------------------------ |
| `POST /extract` | Keycloak bearer | `{metadata: […], model: "<ar3 JSON string>"}` (DTM-01) |
| `GET /liveness` | –               | `204` while the app runs (the container healthcheck)   |

## Run

```bash
npx nx serve aurelius-atlas-data2model   # https://localhost:21001, dev Keycloak + collector up
npx nx test aurelius-atlas-data2model -c ci
npx nx e2e aurelius-atlas-data2model
```
