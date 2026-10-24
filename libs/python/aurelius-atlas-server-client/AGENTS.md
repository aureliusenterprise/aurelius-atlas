# aurelius-atlas-server-client

The Atlas metadata API contract and async client (8.4, DD-114, DD-115).
This file covers wiring specific to this lib; workspace-wide rules live in the
root `AGENTS.md` and `libs/python/AGENTS.md`. See `README.md` for what it is.

## Layout

- `aurelius_atlas_server_client/models.py` — admin DTOs and `AtlasErrorInfo`
- `aurelius_atlas_server_client/lineage.py` — the `v2/lineage/{guid}` body
  models (`LineageInfo` et al., moved here from the 8.2 app by CL-12)
- `aurelius_atlas_server_client/client.py` — `AtlasClient` (`admin` / `types` /
  `get_lineage` / `with_token`), `AtlasClientError`, `KIND_PATHS`

## Wiring Checklist

- Registered in root `pyproject.toml` (members, dev group, `uv.sources`).
- Apps build the client in `create_app` — `AtlasClient(http, token)` over an
  `httpx2.AsyncClient` of their own, whose **pool they close** in the lifespan
  (the client exposes no close, DD-116); the token
  source is `str | Callable[[], str]` — a route forwarding the caller's token
  uses `with_token(token)` per request (shares the pool, closes nothing).
- The `get_lineage` server route lands with 5.1; the paths here already mirror
  it (`LINEAGE_ROOT`).

## Conventions

- No env vars (CL-01); the `httpx2.AsyncClient` is provided externally (CL-02);
  bearer on every request (CL-03); `AtlasClientError` on >=400 with
  `status_code` and `.info` (CL-04);
  transport failures propagate as `httpx2` errors (CL-05).
- `routes/admin.py` / `routes/types.py` of the server are the source of truth
  for paths — mirror changes here in the same PR.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-server-client/tests
```

## Removal

The lineage-model app (8.2) imports `AtlasClient`, `LineageInfo` and
`Direction` from here, and the lineage-model client lib imports `Direction`;
remove those wirings first.
