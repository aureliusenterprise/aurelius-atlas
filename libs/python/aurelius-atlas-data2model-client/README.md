# aurelius-atlas-data2model-client

The data2model extraction API as a contract and a client (8.4, DD-114,
DD-115, DD-116): the rules family the legacy chain evolved (AURELIUS-RULES),
the extraction request/response, and an async `Data2ModelClient` over `httpx2`.
The `aurelius-atlas-data2model` app imports its own contract from here — one
source of truth for both sides of the wire. This file covers wiring specific
to this lib; workspace-wide rules live in the root `AGENTS.md` and
`libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_data2model_client/models.py` — the rules family
  (`MappingEntry`, `ElementRule`, `RelationRule`, `ViewNodeRule`,
  `ViewEdgeRule`, `ViewRule`, `RulesDef`, `LegacyStr`), `ExtractionRequest`,
  `ExtractionResponse`, `MetadataEntry`
- `aurelius_atlas_data2model_client/types.py` — the shared vocabularies:
  `ELEMENT_TYPE_LAYERS`, `RELATIONSHIP_SHORTHANDS`, `LAYOUT_NAMES`
- `aurelius_atlas_data2model_client/client.py` — `Data2ModelClient`
  (`extract`, `with_token`), `Data2ModelClientError`, `TokenSource`

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`).
- The app owns the pool: build the `httpx2.AsyncClient` (base URL, TLS, timeout)
  and `Data2ModelClient(http, token)` in `create_app`, close the **pool** in the
  lifespan's shutdown — the client exposes no close of its own (DD-116). A
  `with_token(...)` wrapper shares the pool and closes nothing.
- The app's `rules.py` is a thin re-export of `models.py` — the rules schema
  changes land in the lib, not the app.
- The rules it keeps (CL-01..CL-05, CL-20, CL-21) are specified by the 8.4 spec
  (`docs/architecture/conversion/increments/8-4-api-client-libraries.md`).

## Conventions

- Libraries read no env vars: the app builds the `httpx2.AsyncClient` from its
  own settings (TLS, timeout) and passes it in with the token source (CL-01,
  DD-116). The request path is relative to its base URL, so the app's URL
  passes through as given — no trailing-slash trimming.
- The request serialises with `model_dump(mode="json", by_alias=True)` — the
  wire keys are the legacy's (CL-20); parity stays byte-comparable.
- A non-2xx answer raises `Data2ModelClientError` (CL-04); transport failures
  propagate as `httpx2` errors (CL-05).

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-data2model-client/tests
```

## Removal

The data2model app (8.1) and the lineage-model app (8.2, which POSTs extracts)
depend on it; removing it means rewiring them back to inline models first.
