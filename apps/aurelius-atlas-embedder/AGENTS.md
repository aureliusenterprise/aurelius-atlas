# aurelius-atlas-embedder

The embedding service of search by meaning (increment 11.2, ADR 059). This file covers wiring specific to this
app; workspace-wide rules, including the conversion workflow, live in the root `AGENTS.md`.

## Layout

- `aurelius_atlas_embedder/app.py` — the composition root: `create_app(settings, loader=load_model)` mounts
  the routers, installs the error shape, and loads the model in the start-up, before uvicorn accepts a
  connection (EMB-07, EMB-08). `loader` is injectable for the unit tests (DD-433).
- `aurelius_atlas_embedder/model.py` — `Model.embed` (prefix, tokenize, mean-pool over the attention mask,
  scale to length 1; EMB-03, EMB-04) and `load_model`, the only place that imports ONNX Runtime, by name
  (DD-433). The session and the tokenizer are protocols.
- `aurelius_atlas_embedder/schemas.py` — OpenAI's request and answer shapes, with `input_type` (EMB-01,
  EMB-02, EMB-06, DD-430); the limits `MAX_TEXTS` and `MAX_CHARACTERS` (EMB-05).
- `aurelius_atlas_embedder/errors.py` — refusals and invalid requests in OpenAI's error shape (EMB-05).
- `aurelius_atlas_embedder/routes/` — `embeddings.py` (`/v1/embeddings`, `/v1/models`) and `health.py`
  (`/liveness`, `/readiness`).
- `aurelius_atlas_embedder/settings.py` — `EmbedderSettings` (`AURELIUS_ATLAS_EMBEDDER_` prefix, EMB-09); the
  pinned `MODEL_ID` and `MODEL_REVISION`.
- `tests/` — unit tests on a fake session and tokenizer (`fakes.py`); no model, no ONNX Runtime.
- `e2e/` — the image with its real model over TLS, including the meaning check and the pinned files (EMB-10).

## Rules the app keeps

The EMB rules live in `apps/aurelius-atlas-embedder/specs/11-2-embedder/spec.md`; tests cite them with
`@pytest.mark.covers(..., rules=["EMB-NN"])` (ADR 056).

## Wiring Checklist

- `project.json` — only `serve`; `build`, `test`, `lint`, `typecheck`, `docker-*`, `certgen` and `e2e` are
  inferred by `tools/plugins/python.ts`. No `.env`: the app has no secrets.
- `pyproject.toml` — `onnxruntime` carries `python_version < '3.15'` (DD-433). Drop the marker once ONNX
  Runtime publishes 3.15 wheels.
- `Dockerfile` — Debian, not Alpine (DD-431): ONNX Runtime has no musl wheels. The `model` stage fetches the
  files with `ADD --checksum`; changing the model means a new revision, new checksums in the Dockerfile and in
  `e2e/test__aurelius_atlas_embedder_e2e.py`, and `MODEL_ID`/`MODEL_REVISION` in `settings.py`. The
  healthcheck is the readiness probe.
- `tls.json` — the certificate (`nx certgen`); its SANs cover the standalone stack's service name `embedder`.
- The standalone stack (`apps/aurelius-atlas-server/standalone/docker-compose.yaml`) runs it as `embedder`,
  with no published port (DD-432, EMB-11; `tests/test__standalone_embedder.py`).
- No Helm chart, no OTLP export and no token check yet: they come together, with the chart (DD-432).
- No `sonar-project.properties` yet: a Sonar key and token for the project come first.

## Removal

Remove `apps/aurelius-atlas-embedder`; its root `pyproject.toml` entries (member, dev group, uv source, the
pyright execution environment); the `embedder` service in the standalone compose file and its README
paragraph; `tests/test__standalone_embedder.py`; and the 11.2 roadmap row.
