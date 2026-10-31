# aurelius-atlas-cluster-lane

The shared e2e cluster machinery (10.5b, DD-282; single-lane per DD-283): the
pytest machinery for driving a suite against the Helm umbrella installed by
`tools/cluster/install.sh up`, extracted from the 10.5 POC's conftest (DD-280)
so each suite buys it instead of rebuilding it. A migrated suite has one
target — the cluster; its compose twin was migration scaffold and is retired
(DD-283).

A suite's conftest stays suite-aware, not lane-shaped: it decides _which_
services and clients its tests dial; this library owns _how_ the cluster is
driven —

- `install_cluster_fixtures(module)` — the session `cluster` gate
  (helm `deployed` or fail-fast naming `install.sh up`), the Gateway address,
  the chart CA Secret read, the resolver shim, and the `ca_file` fixture.
  `module` is the calling conftest (`sys.modules[__name__]`) — pytest collects
  a conftest's fixtures by scanning that module's namespace.
- `ServiceForward` — `kubectl port-forward` of a Service to a free loopback
  port; its dial URL names the real `<svc>.<ns>.svc.cluster.local` at that
  port and the `socket.getaddrinfo` shim rewrites the host alone, so the URL,
  SNI, and verified SAN stay honest (CHT-104).
- `mint_token()` — the realm password grant at the release's issuer origin.
- `SecretReader` — release Secret keys (passwords, CAs) read at run time.
- `hosts_block()` — the fenced `/etc/hosts` edit behind `install.sh hosts`
  (CHT-106, for browser legs that bypass the shim).

## Installation

Workspace dev-group member — e2e conftests import it; no app depends on it at
runtime. It is deliberately **not** a pytest11 plugin: a plain pytest run must
never autoload kubectl-shaped code paths.

## Usage

```python
import sys

from aurelius_atlas_cluster_lane import install_cluster_fixtures

# cluster / _cluster_dns / ca_file, registered on this conftest module:
install_cluster_fixtures(sys.modules[__name__])

@pytest.fixture(scope="session")
def app_url(_cluster_dns: None) -> Iterator[str]:
    with forward_service("atlas-data2model", 21001, host="atlas-data2model.atlas.svc.cluster.local", ...) as url:
        yield url
```

Run the library's own tests: `uv run pytest libs/python/aurelius-atlas-cluster-lane/tests`
(no cluster needed — they are unit tests). The machinery itself is exercised by
the suites' `nx e2e <project>` targets (precondition:
`tools/cluster/install.sh up`).
