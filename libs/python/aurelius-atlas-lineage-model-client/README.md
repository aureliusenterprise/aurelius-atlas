# aurelius-atlas-lineage-model-client

The lineage-model API as a contract and a client (8.4, DD-114, DD-115,
DD-116): the query parameters of `GET /v2/lineage` and the model-document
response, plus an async `LineageModelClient` over `httpx2`. The
`aurelius-atlas-lineage-model` app
imports its own contract from here — one source of truth for both sides of the
wire. This file covers wiring specific to this lib; workspace-wide rules live
in the root `AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_lineage_model_client/models.py` — `LineageModelParams`
  (guid/depth/direction, `extra="forbid"`), `LineageModelResponse`,
  `DEFAULT_DEPTH`, `MIN_DEPTH`
- `aurelius_atlas_lineage_model_client/client.py` — `LineageModelClient`
  (`get`, `with_token`), `LineageModelClientError`, `TokenSource`

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`).
- Depends on `aurelius-atlas-server-client` for `Direction` — the direction
  vocabulary has one definition, never duplicated.
- The app owns the pool: build the `httpx2.AsyncClient` (base URL, TLS, timeout)
  and `LineageModelClient(http, token)` in `create_app`, close the **pool** in
  the lifespan's shutdown — the client exposes no close of its own (DD-116). A
  `with_token(...)` wrapper shares the pool and closes nothing.
- The rules it keeps (CL-01..CL-05, CL-30) are specified by the 8.4 spec
  (`docs/architecture/conversion/increments/8-4-api-client-libraries.md`).

## Conventions

- Libraries read no env vars: the app builds the `httpx2.AsyncClient` from its
  own settings (TLS, timeout) and passes it in with the token source (CL-01,
  DD-116). The request path is relative to its base URL, so the app's URL
  passes through as given — no trailing-slash trimming.
- A no-lineage answer is HTTP 204 — the client returns `None`, not a model
  (CL-30); the app's route maps that to its own 204.
- A non-2xx answer raises `LineageModelClientError` (CL-04); transport
  failures propagate as `httpx2` errors (CL-05).

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-lineage-model-client/tests
```

## Removal

The lineage-model app (8.2) depends on it; removing it means rewiring the app
back to inline models first.
