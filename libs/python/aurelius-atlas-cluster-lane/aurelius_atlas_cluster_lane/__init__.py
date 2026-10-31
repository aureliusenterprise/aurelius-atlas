"""The e2e cluster lane: shared machinery for driving suites against the Helm umbrella.

The 10.5 POC (DD-280) proved one suite against the deployed umbrella and left the
lane machinery in that suite's conftest; 10.5b (DD-282) extracts it here so every
suite buys the lane instead of rebuilding it. The shapes:

- :func:`lane_target` — which deployment a suite drives (``ATLAS_E2E_TARGET``,
  default ``compose``: every existing invocation stays byte-identical).
- :func:`cluster_gate` / :func:`read_gateway_ip` / :func:`read_chart_ca` — the
  fail-fast gate on the live install, the Gateway address, and the chart CA
  (CHT-103).
- :func:`install_resolver_shim` — the process-local ``socket.getaddrinfo`` shim
  that maps cluster names onto loopback forwards while keeping the URL, SNI,
  and verified SAN honest (CHT-104).
- :class:`ServiceForward` — a ``kubectl port-forward`` of one Service to a free
  loopback port, registered with the shim while it runs (CHT-104).
- :func:`mint_token` — the realm password-grant mint both lanes share, at the
  lane's issuer origin.
- :func:`install_cluster_fixtures` — installs the session-scoped ``cluster`` and
  ``ca_file`` fixtures so a conftest names only what is *its* lane shape
  (CHT-103).
- :class:`SecretReader` — Secret keys read at run time from the release
  namespace (CHT-103).
- :func:`hosts_block` — the fenced ``/etc/hosts`` block for browser legs
  (CHT-106, used by ``tools/cluster/install.sh hosts``'s Python).

The library shells out to ``helm``/``kubectl`` (the user's own cluster
credentials), the same harness shape as the chart-contract suite. It is a
workspace dev-group member: e2e conftests import it, and a compose-mode run
never calls any of its cluster paths (CHT-103).
"""

from aurelius_atlas_cluster_lane.forward import ServiceForward, free_port
from aurelius_atlas_cluster_lane.hosts import hosts_block
from aurelius_atlas_cluster_lane.lane import (
    CA_SECRET,
    DEFAULT_DOMAIN,
    DEFAULT_NAMESPACE,
    DEFAULT_RELEASE,
    TARGET_ENV,
    Cluster,
    ca_file_fixture,
    clear_rewrite,
    cluster_fixture_dict,
    cluster_gate,
    install_cluster_fixtures,
    install_resolver_shim,
    lane_target,
    mint_token,
    read_chart_ca,
    read_gateway_ip,
    remove_resolver_shim,
    resolve_overrides,
    set_rewrite,
)
from aurelius_atlas_cluster_lane.secrets import SecretReader

__all__ = [
    "CA_SECRET",
    "DEFAULT_DOMAIN",
    "DEFAULT_NAMESPACE",
    "DEFAULT_RELEASE",
    "TARGET_ENV",
    "Cluster",
    "SecretReader",
    "ServiceForward",
    "ca_file_fixture",
    "clear_rewrite",
    "cluster_fixture_dict",
    "cluster_gate",
    "free_port",
    "hosts_block",
    "install_cluster_fixtures",
    "install_resolver_shim",
    "lane_target",
    "mint_token",
    "read_chart_ca",
    "read_gateway_ip",
    "remove_resolver_shim",
    "resolve_overrides",
    "set_rewrite",
]
