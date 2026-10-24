# aurelius-atlas-fastapi-example

Example FastAPI backend service. This file covers wiring specific to this app;
workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `aurelius_atlas_fastapi_example/` — the package (run with `uv run python -m aurelius_atlas_fastapi_example`)
    - `app.py` — FastAPI app factory and middleware wiring
    - `__main__.py` — uvicorn entry point
    - `globals.py` — process-wide singletons (settings, DB, clients)
    - `models.py` — pydantic models and `BaseSettings` (env-backed config)
    - `routes/` — routers, one module per resource
    - `providers/` — data access and external service clients
- `tests/` — unit tests (`test__*.py`, mirrors package layout, `conftest.py` fixtures)
- `e2e/` — pytest + testcontainers E2E tests with their own `docker-compose.yaml`

## Configuration

- Settings are a pydantic `BaseSettings` in `models.py`; every key comes from `.env`.
- When adding a setting: add it to the settings model, to `.env` (dev default),
  and run the encrypt `nx encrypt` target for this project.

## Wiring Checklist

When changing this app, check all of:

- `project.json` — `implicitDependencies` and `serve` `dependsOn` (Keycloak,
  Postgres, observability). Adding a dependency here changes what `nx serve` starts.
- `pyproject.toml` — workspace deps use `[tool.uv.sources]` with `workspace = true`;
  new libs must also be added to the root `pyproject.toml` dev group.
- `sonar-project.properties` — only touch if module paths change.
- `mkdocs.yaml` — API reference page lives at
  `docs/api-reference/apps/aurelius-atlas-fastapi-example.md`.
- `Dockerfile` and SBOM/vulnerability targets — keep in sync with new runtime deps.

## Commands

```bash
nx serve aurelius-atlas-fastapi-example        # starts Keycloak, Postgres, observability first
nx test aurelius-atlas-fastapi-example -c ci   # never without -c ci (watch mode hangs)
uv run pytest apps/aurelius-atlas-fastapi-example/tests   # fast unit run
nx e2e aurelius-atlas-fastapi-example          # builds docker image, runs testcontainers
nx lint aurelius-atlas-fastapi-example
```

Offline-safe: `uv run pytest`, `nx lint`, `nx typecheck`. Needs SOPS key: `nx test -c ci` (decrypt).
Needs Docker: `serve` (Keycloak/Postgres/observability), `e2e`.

## Conventions

- Routers stay thin; logic goes in `providers/`. Raise `HTTPException` in routes only.
- All DB access goes through `aurelius_atlas_sdk.postgresql` / SQLModel, never raw connections.
- Outbound calls use `pybreaker` circuit breakers (see `globals.py`) and `httpx2`.
- Responses use the generic `Envelope`/`PaginatedResponse` models in `models.py`.
- New routes need both a unit test in `tests/routes/` and coverage in `e2e/`.
- Custom OTel metrics go in `providers/metrics.py` and register through the
  native `metrics.get_meter()` (observable gauges) after `setup_telemetry()`
  in `app.py` (`register_sse_metric()`, DD-121). The SSE gauge exists because FastAPI's
  auto-instrumentation has no route label on `http_server.active_requests` and
  counts whole SSE stream lifetimes in the duration histogram; the FastAPI
  dashboard therefore excludes `/sse` from Request Duration and In-Flight
  (subtracts the gauge) and charts streams in their own row.

## Removal

This app is part of the spine. If a fork removes it, also remove: the frontend's
`implicitDependencies`/`dependsOn` reference, its `mkdocs.yaml` nav entry, the root
`pyproject.toml` uv member and dev-group entry, and `dev/keycloak` client config.
