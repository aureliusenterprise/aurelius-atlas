"""The e2e cluster lane: shared machinery for driving suites against the Helm umbrella.

The 10.5 POC (DD-280) proved one suite against the deployed umbrella and left the
machinery in that suite's conftest; 10.5b (DD-282) extracts it here so every
suite buys it instead of rebuilding it, and DD-283 retired the dual-lane gate:
a migrated suite has one target, the Helm umbrella of ``tools/cluster/install.sh
up``. The shapes:

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
  ``ca_file`` fixtures so a conftest names only what is *its* suite shape
  (CHT-103).
- :class:`SecretReader` — Secret keys read at run time from the release
  namespace (CHT-103).
- :func:`hosts_block` — the fenced ``/etc/hosts`` block for browser legs
  (CHT-106, used by ``tools/cluster/install.sh hosts``'s Python).

The library shells out to ``helm``/``kubectl`` (the user's own cluster
credentials), the same harness shape as the chart-contract suite. It is a
workspace dev-group member: e2e conftests opt in explicitly, so a plain pytest
run never autoloads kubectl code (CHT-103).
"""

from aurelius_atlas_cluster_lane.forward import ServiceForward, free_port
from aurelius_atlas_cluster_lane.hosts import hosts_block
from aurelius_atlas_cluster_lane.lane import (
    CA_SECRET,
    DEFAULT_DOMAIN,
    DEFAULT_NAMESPACE,
    DEFAULT_RELEASE,
    Cluster,
    ca_file_fixture,
    clear_rewrite,
    cluster_fixture_dict,
    cluster_gate,
    install_cluster_fixtures,
    install_resolver_shim,
    mint_token,
    read_chart_ca,
    read_gateway_ip,
    remove_resolver_shim,
    resolve_overrides,
    set_rewrite,
)
from aurelius_atlas_cluster_lane.origins import admin_client, ensure_browser_origins
from aurelius_atlas_cluster_lane.secrets import SecretReader

__all__ = [
    "CA_SECRET",
    "DEFAULT_DOMAIN",
    "DEFAULT_NAMESPACE",
    "DEFAULT_RELEASE",
    "Cluster",
    "SecretReader",
    "ServiceForward",
    "admin_client",
    "ca_file_fixture",
    "clear_rewrite",
    "cluster_fixture_dict",
    "cluster_gate",
    "ensure_browser_origins",
    "free_port",
    "hosts_block",
    "install_cluster_fixtures",
    "install_resolver_shim",
    "mint_token",
    "read_chart_ca",
    "read_gateway_ip",
    "remove_resolver_shim",
    "resolve_overrides",
    "set_rewrite",
]
