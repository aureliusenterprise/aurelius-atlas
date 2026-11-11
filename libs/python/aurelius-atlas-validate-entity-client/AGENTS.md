# aurelius-atlas-validate-entity-client

The validate-entity API contract and async client (8.4, DD-203, DD-204, DD-205;
CL-40 amended by 12.7 — the verdict models replace the card models).
This file covers wiring specific to this lib; workspace-wide rules live in the
root `AGENTS.md` and `libs/python/AGENTS.md`. See `README.md` for what it is.

## Layout

- `aurelius_atlas_validate_entity_client/models.py` — the verdict answer
  (`ValidationResponse` with its `GovernanceVerdict` and `UnreadRule` items,
  CL-40 as amended: `compliant` is a `StrictBool`, the camelCase aliases ride)
- `aurelius_atlas_validate_entity_client/client.py` — `ValidateEntityClient`
  (`validate` / `with_token`), `ValidateEntityClientError`

## Wiring Checklist

- Registered in root `pyproject.toml` (members, dev group, `uv.sources`).
- The app answers through `ValidationResponse` — the model is the app's own
  response contract, both sides of the wire from one source (CL-40). The 8.3
  card models retired with DV-67 (ADR 061, 12.7): a legacy string `compliant`
  flag no longer parses.

## Conventions

- No env vars (CL-01); the `httpx2.AsyncClient` is provided externally (CL-02);
  bearer on every request
  (CL-03); `ValidateEntityClientError` on >=400 with `status_code` (CL-04);
  transport failures propagate as `httpx2` errors (CL-05).
- Every model is `extra="forbid"` and frozen: the verdict document is exact,
  a field the app does not send is a validation error, not silence.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-validate-entity-client/tests
```

## Removal

The validate-entity app (8.3) depends on it; remove that wiring first.
