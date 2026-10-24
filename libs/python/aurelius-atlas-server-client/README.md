# aurelius-atlas-server-client

The Atlas metadata API as a contract and a client (8.4, DD-203, DD-204, DD-205):
admin, typedef and lineage wire models and an async `AtlasClient` over
`httpx2`. The Python twin of `libs/angular/aurelius-atlas-data-access` — every
consumer of the server speaks through this library, and the lineage-model app
imports the lineage wire models from it (one source of truth). This file covers
wiring specific to this lib; workspace-wide rules live in the root `AGENTS.md`
and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_server_client/models.py` — `AtlasVersion`, `AtlasStatus`,
  `AtlasSessionInfo`, `AtlasErrorInfo` (the admin shapes and the error body)
- `aurelius_atlas_server_client/lineage.py` — `LineageInfo`, `LineageRelation`,
  `EntityHeaderLite`, `Direction` (the `v2/lineage/{guid}` body, CL-12)
- `aurelius_atlas_server_client/client.py` — `AtlasClient` (`.admin`, `.types`,
  `get_lineage`, `with_token`), `AtlasClientError`, `TokenSource`

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`).
- The app owns the pool: build the `httpx2.AsyncClient` (base URL, TLS, timeout)
  and `AtlasClient(http, token)` in `create_app`, close the **pool** in the
  lifespan's shutdown — the client exposes no close of its own (DD-205). A
  `with_token(...)` wrapper shares the pool and closes nothing.
- The typedef bodies are `aurelius-atlas-model`'s, reused whole (CL-10) — never
  fork them here.
- The rules it keeps (CL-01..CL-05, CL-10..CL-12) are specified by the 8.4 spec
  (`docs/architecture/conversion/increments/8-4-api-client-libraries.md`).

## Conventions

- Libraries read no env vars: the app builds the `httpx2.AsyncClient` from its
  own settings (TLS, timeout) and passes it in with the token source (CL-01,
  DD-205). Request paths are relative to its base URL, so the app's URL passes
  through as given — no trailing-slash trimming.
- The httpx2 client arrives from outside (CL-02): tests pass one built on a
  `httpx2.MockTransport`, no socket opens.
- A non-2xx answer raises `AtlasClientError` with the status and the parsed
  `{errorCode, errorMessage}` (CL-04); an unreachable upstream propagates as
  `httpx2`'s own error — mapping it to a status is the app's job (CL-05).

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-server-client/tests
```

## Removal

The lineage-model app (8.2) and the lineage-model client lib depend on it;
removing it means rewiring them back to inline models first.
