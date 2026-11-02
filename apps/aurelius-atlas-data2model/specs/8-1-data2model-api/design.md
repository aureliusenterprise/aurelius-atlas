# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-198. The 8.x ports are pandas-free: pydantic rule models, plain row maps

- **Status:** Proposed
- **Increment:** 8.1
- **Date:** 2026-10-23

**Decision.** The data2model port (8.1) adds no pandas. The request's
`rules` parse as pydantic models (the app's public request contract,
validated at the boundary: unknown types, missing keys and dangling rule
references are 400 at parse time, DTM-11/DTM-12); the tabular `data` is a
plain `list[dict[str, Any]]` of row maps, and extraction, dedup, view
selection and layout are plain Python over that list. The same rule applies
to 8.2 (lineage-model) and 8.3 (validate-entity).

**Reason.** The legacy chain reaches pandas through `m4i-analytics`:
`DataFrame(data)` is the legacy representation of the request body, and the
DataFrame ops (`drop_duplicates`, `isin`, boolean masks) are the extraction
semantics the DTM rules state directly — the spec cites behaviour, not
pandas, and the browser contract is the response JSON, not the
representation. The workspace's spine is pydantic (FastAPI settings, model
validation; ADR 050's "only what the catalogue needs"), the user's stated
convention, and a pandas dependency buys nothing the DTM rules need: the
lineage chain's row counts are a lineage neighbourhood's edges, not a data
science corpus. One less native dependency in a dhi.io/alpine wheel set
(pandas' `numpy`/`pyarrow` transitives), and the app's typed surface is
the pydantic rule models, which FastAPI documents for free.

**Alternatives.** Port `m4i-analytics`'s DataFrame pipeline (refused —
DV-68 already refuses the library; its graphviz/bokeh tree arrives with
it). Pandas inside a thin native shell (refused — every DTM rule has a
five-line plain-Python form; pandas would be a dependency of a dozen
`drop_duplicates` calls). pydantic row models for `data` (refused — the
columns are the _caller's_ rule keys: a row model would be `model_config =
ConfigDict(extra="allow")` with declared fields for nothing; a row is a map,
the rules name its columns).

**Consequences.** The NaN semantics travel as null: a pandas NaN reaches the
legacy extractor through `read_json`-shaped payloads, and the JSON request
body can only carry it as `null` — the DTM rules state null-drop/null-empty
directly (the `'nan'`-string artefacts a NaN id produced in the legacy are
a legacy accident, recorded in 8.1's deviations, not a contract). The app's
pyproject gains `pydantic`/`fastapi` and no pandas; 8.2's flattening (12
columns, fixed keys) is the same shape and stays plain dicts.

### DD-199. App unit tests clear the injected `.env` prefix in an autouse fixture

- **Status:** Accepted
- **Increment:** 8.1
- **Date:** 2026-10-23

**Decision.** Every Python app's `tests/conftest.py` carries an autouse
fixture that deletes every environment variable starting with the app's
`ENV_PREFIX` before each test. Tests and fixtures then set exactly the
variables they mean.

**Reason.** Nx injects a project's `.env` into **every** task's environment
for that project, and pydantic-settings reads the environment for every
field a test does not pass explicitly — `model_validate` included. The dev
`.env` stores TLS material and directories as workspace-root-relative
paths, while `nx test` runs pytest with `cwd=projectRoot`, so the paths
do not resolve and every `FilePath` field fails validation: under
`nx test -c ci`, the server's suite reported 50 setup errors and
data2model's 12 — identical for both apps, invisible to a plain
`uv run pytest` from the workspace root, and invisible to CI, whose PR
gate selects tasks the `test`-affecting files do not touch. Clearing the
prefix is the smallest hermetic fix; the alternative — absolute paths in
`.env` — breaks the containers (the compose files resolve them against
the project dir) and `nx serve` (which runs from the workspace root, the
one cwd where the relative paths do resolve).

**Consequences.** Unit tests no longer read dev secrets, dev endpoints,
or dev certificates, in any working directory. The settings tests keep
testing environment reading — their `environment` fixture sets the
variables it needs after the clear. `e2e/` conftests keep loading the
real `.env` on purpose: those tests talk to the real dev stack.

### DD-209. data2model and validate-entity follow the example app's provider/route layout

**Context.** DD-207 and DD-208 settled the lineage-model app's shape: the
collaborators in `providers/`, the endpoints in `routes/` with the route
composing its own flow, a thin composition root in `app.py`. The two 8.x apps
built on the same foundation (DD-197) before that layout existed never
followed: both `aurelius-atlas-data2model/app.py` and
`aurelius-atlas-validate-entity/app.py` still define their routes inside
`create_app`, carry a private `_auth` builder, and inline the same ~35-line
`logfire.configure` block with its conditional dict-spread — `_auth` is
identical in all three apps, the telemetry block differs only by `NAME`.
**Decision.** Both apps move to the DD-207/DD-208 layout, layout only:

- Each app gains `globals.py` (NAME, LOGGER, its status constants) and the
  two providers, `providers/auth.py` (`build_auth`, the library's `http` seam
  open as lineage-model's) and `providers/telemetry.py` (`ingest_pipeline`,
  `configure_telemetry`) — the copy lineage-model already has.
- Each app gains `routes/health.py` (the anonymous `/liveness`, module-level
  so ADR 049 names it) and its endpoint module: `routes/extract.py`
  (`build_router(auth)`, the gated `POST /extract` calling the engine
  directly — the engine stays `extract.py`, the pure DTM-02..09 parser with
  its own tests) and `routes/validate.py` (`build_router(auth)`, the gated
  `POST /` answering the mock constant). The routes _are_ the use cases
  (DD-208): no new classes, no chain.
- `app.py` becomes the composition root: `create_app` builds the verifier,
  includes the routers, mounts the error contract, configures the telemetry.
  data2model's 400 handler stays at the root — the mapping is the app's
  contract, as lineage-model's handlers are (DD-207).
- `create_app(settings, auth=None)` keeps its injectable seam (DD-200..201)
  on both apps; the wire contract (paths, statuses, bodies, the DTM/VE rules)
  is untouched.

**Reason.** Three apps, one shape: the layout the example app proves, and a
review of data2model/validate-entity sees the same tangle DD-207 fixed —
routes, collaborators and telemetry in one function. Duplicating `_auth` and
the OTLP block per app is DD-196/DD-197's deliberate decision (the app owns
its export); duplicating them _inside_ one module, in `create_app`, is not
that decision — the providers hold them, one copy per app.
**Alternatives.** (a) Lift auth+telemetry into a shared lib — rejected: it
supersedes DD-196/DD-197 (per-app ingest clients, app-owned export), and
three copies of a 20-line factory is the accepted cost of that decision.
(b) Refactor data2model only — rejected: validate-entity carries the same
`create_app`-defined routes; one entry keeps the family uniform. (c) A
use-case class per route — rejected by DD-208 already.
**Consequences.** `test__app.py` on both apps keeps its covers targets
(`create_app` stays canonical); new provider/route test files name the new
public functions (ADR 049). The specs' design-log fields gain DD-209; no rule
id changes meaning. The e2e suites are untouched — they ride the wire.
