# aurelius-atlas-data2model-client

The data2model extraction API contract and async client (8.4, DD-114, DD-115,
DD-116). This file covers wiring specific to this lib; workspace-wide rules
live in the root `AGENTS.md` and `libs/python/AGENTS.md`. See `README.md` for
what it is.

## Layout

- `aurelius_atlas_data2model_client/models.py` — the rules family and the
  extract request/response (git-moved from the 8.1 app, not forked)
- `aurelius_atlas_data2model_client/types.py` — the layout/shorthand
  vocabularies the rules reference
- `aurelius_atlas_data2model_client/client.py` — `Data2ModelClient`
  (`extract` / `with_token`), `Data2ModelClientError`

## Wiring Checklist

- Registered in root `pyproject.toml` (members, dev group, `uv.sources`).
- The app re-exports the models through `aurelius_atlas_data2model/rules.py`
  so its import paths stay; the lib is the single definition site.
- The extract route answers `JSONResponse(model_dump(mode="json",
by_alias=True))` — no `response_model` filtering; the wire stays exactly
  the legacy's (CL-50, parity compares parsed JSON exactly).

## Conventions

- No env vars (CL-01); the `httpx.AsyncClient` is provided externally (CL-02);
  bearer on every request
  (CL-03); `Data2ModelClientError` on >=400 with `status_code` (CL-04);
  transport failures propagate as `httpx` errors (CL-05).
- `LegacyStr` keeps the legacy's null-as-empty-string posture: the model
  serialises omitted strings as `""`.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-data2model-client/tests
```

## Removal

The data2model app's `rules.py`/`extract.py` and the lineage-model app's
extract call depend on it; remove those wirings first.
