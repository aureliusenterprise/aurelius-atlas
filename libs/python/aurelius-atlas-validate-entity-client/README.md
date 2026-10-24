# aurelius-atlas-validate-entity-client

The validate-entity API as a contract and a client (8.4, DD-203, DD-204,
DD-205): the
governance validation card the screen renders and an async
`ValidateEntityClient` over `httpx2`. The `aurelius-atlas-validate-entity` app
imports its own response model from here — one source of truth for both sides
of the wire. This file covers wiring specific to this lib; workspace-wide rules
live in the root `AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_validate_entity_client/models.py` — `ValidationResponse`,
  `ValidationCard`, `GovQualityItem`, `GovQualityMeta`, `GovQualityValue`
  (all `extra="forbid"`, frozen — the card is exact, CL-40)
- `aurelius_atlas_validate_entity_client/client.py` — `ValidateEntityClient`
  (`validate`, `with_token`), `ValidateEntityClientError`, `TokenSource`

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`).
- The app owns the pool: build the `httpx2.AsyncClient` (base URL, TLS,
  timeout) and `ValidateEntityClient(http, token)` in
  `create_app`, close the **pool** in the lifespan's shutdown — the client
  exposes no close of its own (DD-205). A `with_token(...)`
  wrapper shares the pool and closes nothing.
- The rules it keeps (CL-01..CL-05, CL-40) are specified by the 8.4 spec
  (`docs/architecture/conversion/increments/8-4-api-client-libraries.md`).

## Conventions

- Libraries read no env vars: the app builds the `httpx2.AsyncClient` from its
  own settings (TLS, timeout) and passes it in with the token source (CL-01,
  DD-205). The request path is relative to its base URL, so the app's URL
  passes through as given — no trailing-slash trimming.
- `validate()` takes the entity as a plain mapping — the request has no
  schema of its own (the legacy posts the screen's object).
- A non-2xx answer raises `ValidateEntityClientError` (CL-04); transport
  failures propagate as `httpx2` errors (CL-05).

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-validate-entity-client/tests
```

## Removal

The validate-entity app (8.3) depends on it; removing it means rewiring the
app back to an inline model first.
