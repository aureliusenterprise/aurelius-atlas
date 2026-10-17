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
- `e2e/` — ESD-01 to ESD-06 against the dev store that `nx e2e` starts through the implicit dependency
  on `aurelius-atlas-dev-elasticsearch`; the persistence test runs `docker compose down`/`up` on it

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group with `[testing]`, `uv.sources`).
- Rule ids (`STO-NN`, `ESD-NN`) are specified in
  `docs/architecture/conversion/increments/0-2-elasticsearch-infrastructure.md`; every test names the
  functions and rules it checks with `@pytest.mark.covers` (ADR 049), and `aurelius-atlas-trace check`
  fails when a public function or rule is named by no test.
- The container helper uses the same image tag as `dev/elasticsearch/docker-compose.yaml`; change both
  together.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-store-es/tests
npx nx e2e aurelius-atlas-store-es    # starts dev/elasticsearch (and dev/observability) first
uv run pyright libs/python/aurelius-atlas-store-es
```

## Conventions

- Settings come in as a `StoreSettings` object; never read environment variables here (STO-01).
- No option to disable certificate verification, ever (STO-02, DD-006).
- `check_health` must never raise (STO-06); new failure modes map to a `DOWN` report with a reason.
- Never put credentials into exceptions, log records or reports (STO-08).

## Removal

Not removable: it is the catalogue's only store (ADR 047).
