"""Unit tests for the fenced /etc/hosts edit — a tmp file, never the machine's (CHT-106)."""

import pytest
from aurelius_atlas_cluster_lane.hosts import BEGIN, END, hosts_block

BASE = """127.0.0.1\tlocalhost
::1\tlocalhost
192.168.49.2\tminikube.upToDate.example
"""


_BOTH = {"atlas.atlas.test": "10.0.0.1", "keycloak.atlas.test": "10.0.0.1"}


@pytest.mark.covers("aurelius_atlas_cluster_lane.hosts.hosts_block", rules=["CHT-106"])
def test__first_insert_appends_the_block() -> None:
    """A hosts file with no fence gets the block appended, outside lines untouched."""
    out = hosts_block(BASE, _BOTH, hostname="devcontainer")
    assert out.startswith(BASE)  # nothing before the fence moved
    assert BEGIN in out
    assert END in out
    assert "10.0.0.1 atlas.atlas.test" in out
    assert "10.0.0.1 keycloak.atlas.test" in out


@pytest.mark.covers("aurelius_atlas_cluster_lane.hosts.hosts_block", rules=["CHT-106"])
def test__re_run_converges_on_the_new_ip_and_touches_nothing_else() -> None:
    """IP churn: the fenced block is replaced in place, everything outside survives verbatim."""
    new = {"atlas.atlas.test": "10.0.0.2", "keycloak.atlas.test": "10.0.0.2"}
    once = hosts_block(BASE, _BOTH, hostname="devcontainer")
    twice = hosts_block(once, new, hostname="devcontainer")
    assert twice.count(BEGIN) == 1
    assert twice.count(END) == 1
    assert "10.0.0.2 atlas.atlas.test" in twice
    assert "10.0.0.1" not in twice
    assert once[: once.index(BEGIN)] == twice[: twice.index(BEGIN)]
    # Re-running at the same IP is a fixed point (converges).
    assert hosts_block(twice, new, hostname="devcontainer") == twice


@pytest.mark.covers("aurelius_atlas_cluster_lane.hosts.hosts_block", rules=["CHT-106"])
def test__empty_entries_remove_the_block() -> None:
    """A cluster going down should not strand hosts: the fenced block goes away."""
    once = hosts_block(BASE, {"atlas.atlas.test": "10.0.0.1"}, hostname="devcontainer")
    assert BEGIN not in hosts_block(once, {}, hostname="devcontainer")
    assert hosts_block(BASE, {}, hostname="devcontainer") == BASE


@pytest.mark.covers("aurelius_atlas_cluster_lane.hosts.hosts_block", rules=["CHT-106"])
def test__the_blocks_own_hostname_line_is_never_shadowed() -> None:
    """On the minikube node itself, mapping the node's name to the Gateway breaks DNS."""
    with pytest.raises(ValueError, match="hostname"):
        hosts_block(BASE, {"minikube.upToDate.example": "10.0.0.1"}, hostname="minikube.upToDate.example")
