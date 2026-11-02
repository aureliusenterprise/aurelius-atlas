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
  `AtlasSessionInfo`, `AtlasErrorInfo`, `DeleteType` (the admin shapes, the error
  body, and the delete-mode wire vocabulary — DD-311)
- `aurelius_atlas_server_client/lineage.py` — `LineageInfo`, `LineageRelation`,
  `EntityHeaderLite`, `Direction` (the `api/atlas/v2/lineage/{guid}` body, CL-12)
- `aurelius_atlas_server_client/client.py` — `AtlasClient` (`.admin`, `.types`,
  `.entity`, `.glossary`, `.relationship`, `.search`, `.lineage`, `get_lineage`,
  `with_token`), `AtlasClientError`, `TokenSource`, `GlossarySort` (DD-312).
  `.lineage`
  (CL-61..CL-63) answers the lineage feed of `routes/lineage.py`: `get`,
  `get_on_demand`, `get_by_unique_attributes`.
  `.entity` (CLE-01..CLE-12, 8.9) answers the 37 entity routes of
  `routes/entity.py`: reads by GUID and unique attributes, writes, deletes, the
  classification, business-metadata and label writes, audits and bulk headers.
  `.glossary` (CLG-01..CLG-09, 8.10) answers the 32 glossary routes of
  `routes/glossary.py`: glossaries, categories and terms (reads, writes, the
  partial updates, deletes), the term-assignment trio, the related reads, and
  the CSV/Excel import pair as bytes (DD-310). The paged reads send the
  server's `limit`/`offset`/`sort` with the defaults left out (CLG-02).
  `.relationship` (CLR-01..CLR-04, 8.11) answers the four routes of
  `routes/relationship.py`: `create`, `update`, `get` (with the
  `extendedInfo` flag), `delete`.
  `.admin` (CL-11 by 8.4, CLW-01..CLW-07 by 8.11) answers all 12 routes of
  `routes/admin.py`: the five reads plus `patches`, `purge`, the export/import
  ZIP pair as bytes (DD-310, the import's `request` part a form field per
  DD-313), `import_file`, and the task list with its repeated `guids`.
  `.search` (CL-13) answers the discovery routes: the basic POST/GET, attribute,
  fulltext, the quick POST/GET, and suggestions — bodies reused whole from
  `aurelius-atlas-model` (CL-10)

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`).
- The app owns the pool: build the `httpx2.AsyncClient` (base URL, TLS, timeout)
  and `AtlasClient(http, token)` in `create_app`, close the **pool** in the
  lifespan's shutdown — the client exposes no close of its own (DD-205). A
  `with_token(...)` wrapper shares the pool and closes nothing.
- The typedef bodies are `aurelius-atlas-model`'s, reused whole (CL-10) — never
  fork them here.
- The rules it keeps are specified per module: CL-01..CL-05, CL-10..CL-13 by the
  8.4 spec, CL-60..CL-65 by 8.8, CLE-01..CLE-12 by 8.9, CLG-01..CLG-09 by 8.10,
  CLR-01..CLR-04 and CLW-01..CLW-07 by 8.11
  (each under `libs/python/aurelius-atlas-server-client/specs/`).

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
