# aurelius-atlas-lineage-model-client

The lineage-model API contract and async client (8.4, DD-203, DD-204, DD-205).
This file covers wiring specific to this lib; workspace-wide rules live in the
root `AGENTS.md` and `libs/python/AGENTS.md`. See `README.md` for what it is.

## Layout

- `aurelius_atlas_lineage_model_client/models.py` — `LineageModelParams`
  (the validated query), `LineageModelResponse` (model + metadata)
- `aurelius_atlas_lineage_model_client/client.py` — `LineageModelClient`
  (`get` / `with_token`), `LineageModelClientError`

## Wiring Checklist

- Registered in root `pyproject.toml` (members, dev group, `uv.sources`).
- `Direction` is imported from `aurelius_atlas_server_client.lineage` — do not
  redefine it here (single source of truth, CL-12).
- The app's route declares its query parameters from `LineageModelParams`'
  bounds (`DEFAULT_DEPTH`, `MIN_DEPTH`); the parameter model is
  `extra="forbid"` so an unknown query key is a validation error at the app.

## Conventions

- No env vars (CL-01); the `httpx2.AsyncClient` is provided externally (CL-02);
  bearer on every request
  (CL-03); `LineageModelClientError` on >=400 with `status_code` (CL-04);
  transport failures propagate as `httpx2` errors (CL-05).
- `get()` returns `None` for 204 (no lineage, CL-30), the response model for 200.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-lineage-model-client/tests
```

## Removal

The lineage-model app (8.2) depends on it; remove that wiring first.
