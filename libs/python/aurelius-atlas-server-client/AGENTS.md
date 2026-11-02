# aurelius-atlas-server-client

The Atlas metadata API contract and async client (8.4, DD-203, DD-204).
This file covers wiring specific to this lib; workspace-wide rules live in the
root `AGENTS.md` and `libs/python/AGENTS.md`. See `README.md` for what it is.

## Layout

- `aurelius_atlas_server_client/models.py` — admin DTOs and `AtlasErrorInfo`
- `aurelius_atlas_server_client/lineage.py` — the `api/atlas/v2/lineage/{guid}`
  body models (`LineageInfo` et al., moved here from the 8.2 app by CL-12)
- `aurelius_atlas_server_client/client.py` — `AtlasClient` (`admin` / `types` /
  `search` / `lineage` / `with_token`, plus the `get_lineage` alias of
  `lineage.get`), `AtlasClientError`, `KIND_PATHS`;
  `search` mirrors `routes/discovery.py` (CL-13), GET parameters as query
  parameters with the Java defaults (false, 0) left out;
  `lineage` mirrors `routes/lineage.py` (CL-61..CL-63, 8.8)

## Wiring Checklist

- Registered in root `pyproject.toml` (members, dev group, `uv.sources`).
- Apps build the client in `create_app` — `AtlasClient(http, token)` over an
  `httpx2.AsyncClient` of their own, whose **pool they close** in the lifespan
  (the client exposes no close, DD-205); the token
  source is `str | Callable[[], str]` — a route forwarding the caller's token
  uses `with_token(token)` per request (shares the pool, closes nothing).
- The roots mirror the server's mounted prefixes, lineage included
  (`LINEAGE_ROOT = api/atlas/v2/lineage`, CL-60, DD-308). The 8.2 app's
  unit/scenario stubs and its e2e `fixture-atlas` answer that path.

## Conventions

- No env vars (CL-01); the `httpx2.AsyncClient` is provided externally (CL-02);
  bearer on every request (CL-03); `AtlasClientError` on >=400 with
  `status_code` and `.info` (CL-04);
  transport failures propagate as `httpx2` errors (CL-05).
- `routes/admin.py` / `routes/types.py` / `routes/discovery.py` of the server
  are the source of truth for paths — mirror changes here in the same PR
  (the server's `e2e/test__aurelius_atlas_server_search_e2e.py` proves the
  discovery paths against the container).

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-server-client/tests
```

## Removal

The lineage-model app (8.2) imports `AtlasClient`, `LineageInfo` and
`Direction` from here, and the lineage-model client lib imports `Direction`;
remove those wirings first.
