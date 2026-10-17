# aurelius-atlas-store-es

The Elasticsearch store library (DD-002, DD-005). This file covers wiring specific to this lib;
workspace-wide rules — including the scaffold recipe for Python libs — live in the root
`AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_store_es/` — `settings.py` (`StoreSettings`), `store.py` (`ElasticsearchStore`),
  `health.py` (`check_health`, `HealthReport`), `errors.py`
- `aurelius_atlas_store_es/testing/` — `fake.py` (`FakeClient`, no extra deps) and `container.py`
  (TLS-enabled Elasticsearch via testcontainers, `testing` extra) — DD-007
- `tests/` — unit tests against the fake, integration tests against the container

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group with `[testing]`, `uv.sources`).
- Rule ids (`STO-NN`) are specified in
  `docs/architecture/conversion/increments/0-2-elasticsearch-infrastructure.md`; every test names the
  rules it checks in its docstring until the `covers` marker exists (0.3).
- The container helper uses the same image tag as `dev/elasticsearch/docker-compose.yaml`; change both
  together.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-store-es/tests
uv run pyright libs/python/aurelius-atlas-store-es
```

## Conventions

- Settings come in as a `StoreSettings` object; never read environment variables here (STO-01).
- No option to disable certificate verification, ever (STO-02, DD-006).
- `check_health` must never raise (STO-06); new failure modes map to a `DOWN` report with a reason.
- Never put credentials into exceptions, log records or reports (STO-08).

## Removal

Not removable: it is the catalogue's only store (ADR 047).
