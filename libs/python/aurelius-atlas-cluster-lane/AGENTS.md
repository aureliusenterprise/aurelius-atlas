# aurelius-atlas-cluster-lane

The shared e2e cluster lane (10.5b, DD-282). This file covers wiring specific
to this lib; workspace-wide rules live in the root `AGENTS.md` and
`libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_cluster_lane/lane.py` — `lane_target`, the fail-fast gate,
  the Gateway/CA reads, the resolver shim (a `(host, port)` rewrite table;
  exact keys win over `.suffix` rules), `install_cluster_fixtures`, `mint_token`
- `aurelius_atlas_cluster_lane/forward.py` — `ServiceForward` /
  `forward_service` / `free_port` (CHT-104)
- `aurelius_atlas_cluster_lane/secrets.py` — `SecretReader` (CHT-103)
- `aurelius_atlas_cluster_lane/hosts.py` — `hosts_block`, the fenced
  `/etc/hosts` edit used by `install.sh hosts` (CHT-106)
- `tests/` — unit tests only: **no test here needs a cluster** (the lane's
  live proof is the suites' `e2e-cluster` targets)

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group,
  `uv.sources`). The dev group is what makes `uv run pytest` see it in every
  project — consumers import it in conftests, **not** in app `pyproject.toml`
  dependency lists (parity precedent).
- Deliberately not a pytest11 plugin: `install_cluster_fixtures(pytest, ...)`
  is an explicit opt-in so compose-mode pytest runs never autoload kubectl
  paths (CHT-103).
- Ruff: the package shells out to fixed `helm`/`kubectl`/`curl` arguments —
  `S603`/`S607` per-file-ignores in root `pyproject.toml`, same harness shape
  as the chart suite.

## Conventions

- The compose lane is the CI lane and the regression bar: a conftest refactor
  onto this lib must keep compose behaviour byte-identical, and the gate's
  fail-fast message keeps naming `install.sh up`.
- A cluster dial uses the Service's real name (the SAN-honest FQDN) over a
  `ServiceForward`; the dial URL carries the forward's own free port and the
  shim rewrites the host alone — a host+port rewrite is silently dropped by
  the async HTTP stack, so the URL's port is what gets connected to
  (CHT-104). The only sanctioned `127.0.0.1` dial is a baked-dashboard
  Playwright leg under `ignore_https_errors` (ADR 039) — `insecure=True`.
- The shim's registry is process-global; a session-scope fixture owns the
  install (autouse `_cluster_dns`). Never install it in a function-scope
  fixture.

## Removal

Removing the lane: delete the directory, remove it from root
`pyproject.toml` (members, dev group, uv.sources), revert the four e2e
conftests to standalone compose-only shapes, and delete the `e2e-cluster`
targets from the four project.json files.
