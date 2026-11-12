# aurelius-atlas-validate-entity

The Aurelius Atlas validate-entity API: an editor draft in, the governance verdicts out —
the validation endpoint the legacy editor called while a record was being edited, ported
from the Aurelius `m4i-validate-entity` service
([ADR 055](../../docs/architecture/adr/055-the-lineage-chain-is-a-named-data-surface.md)).

Introduced by increment 8.3 as the mock the legacy service was
([DV-67](../../docs/architecture/conversion/deviations.md)); made live by 12.7
([ADR 061](../../docs/architecture/adr/061-the-governance-banner-answers-live-verdicts.md),
[DV-153](../../docs/architecture/conversion/deviations.md)). The app reads the ACTIVE
governance rules (`m4i_gov_data_quality`) from the catalogue, runs each over the draft's
attributes with the 12.6 engine, and answers one boolean verdict per rule — the rule's own
guid, name, attribute, dimension, verdict, and message — plus the rules the vocabulary
cannot read
([spec](specs/12-7-governance-verdicts/spec.md)). The code follows the workspace's
example-app layout (DD-209): the collaborators built by `providers/`, the endpoints in
`routes/`, and a thin composition root in `app.py`.

## Endpoints

| Endpoint        | Auth            | Answers                                                                   |
| --------------- | --------------- | ------------------------------------------------------------------------- |
| `POST /`        | Keycloak bearer | `200` the draft's verdicts and unread rules; `400` a draft it cannot read |
| `GET /liveness` | –               | `204` while the app runs (the container healthcheck)                      |

The rules read signs as the app's **own** service identity (VEV-04), never the caller's,
and the catalogue leg travels one circuit breaker: an unreachable or refusing catalogue —
or a cluster without the realm join — answers `502`, never a no-rules answer (VEV-06).

## Run

```bash
npx nx serve aurelius-atlas-validate-entity   # https://localhost:21003, dev Keycloak + collector up
npx nx test aurelius-atlas-validate-entity -c ci
npx nx e2e aurelius-atlas-validate-entity     # the image + a real server, realm tokens, real TLS
```

The e2e suite stands a real Atlas server beside the app (8.2's chain pattern): it seeds
governance rules through the catalogue and reads them back as live verdicts. The `502`
case stays a unit proof on a closed pool (DD-200's seam), never a stopped container
(DD-223).
