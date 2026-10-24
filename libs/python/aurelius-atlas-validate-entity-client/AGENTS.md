# aurelius-atlas-validate-entity-client

The validate-entity API contract and async client (8.4, DD-114, DD-115, DD-116).
This file covers wiring specific to this lib; workspace-wide rules live in the
root `AGENTS.md` and `libs/python/AGENTS.md`. See `README.md` for what it is.

## Layout

- `aurelius_atlas_validate_entity_client/models.py` — the validation card
  (`ValidationResponse` and its nested items, CL-40)
- `aurelius_atlas_validate_entity_client/client.py` — `ValidateEntityClient`
  (`validate` / `with_token`), `ValidateEntityClientError`

## Wiring Checklist

- Registered in root `pyproject.toml` (members, dev group, `uv.sources`).
- The app validates its mock card through `ValidationResponse` at import —
  the model is the app's own response contract (CL-40, CL-50).

## Conventions

- No env vars (CL-01); the `httpx2.AsyncClient` is provided externally (CL-02);
  bearer on every request
  (CL-03); `ValidateEntityClientError` on >=400 with `status_code` (CL-04);
  transport failures propagate as `httpx2` errors (CL-05).
- Every model is `extra="forbid"` and frozen: the card the screen renders is
  exact, a field the legacy does not send is a validation error, not silence.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-validate-entity-client/tests
```

## Removal

The validate-entity app (8.3) depends on it; remove that wiring first.
