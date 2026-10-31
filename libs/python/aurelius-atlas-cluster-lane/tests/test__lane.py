"""Unit tests for the lane gate, shim, and readers — no cluster needed (CHT-103/104).

The kubectl/helm reads are steered with fake CLIs on PATH (a per-test bin/
directory), so the real subprocess code paths run without a cluster.
"""

import base64
import os
import socket
import stat
from pathlib import Path

import pytest
from aurelius_atlas_cluster_lane import lane
from aurelius_atlas_cluster_lane.lane import (
    ca_file_fixture,
    clear_rewrite,
    cluster_gate,
    lane_target,
    read_gateway_ip,
    set_rewrite,
)
from aurelius_atlas_cluster_lane.secrets import SecretReader


def _fake_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, body: str) -> None:
    """Put a one-line fake CLI named ``name`` first on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    cli = bin_dir / name
    cli.write_text(f"#!/usr/bin/env bash\n{body}\n")
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.lane_target", rules=["CHT-103"])
def test__lane_target_defaults_to_compose(monkeypatch: pytest.MonkeyPatch) -> None:
    """No ATLAS_E2E_TARGET means compose: every existing invocation is unchanged."""
    monkeypatch.delenv("ATLAS_E2E_TARGET", raising=False)
    assert lane_target() == "compose"


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.lane_target", rules=["CHT-103"])
def test__lane_target_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """ATLAS_E2E_TARGET=cluster selects the cluster lane (CHT-103)."""
    monkeypatch.setenv("ATLAS_E2E_TARGET", "cluster")
    assert lane_target() == "cluster"


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.cluster_gate", rules=["CHT-103"])
def test__gate_fails_fast_naming_install_sh_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Absent release: the assert names install.sh up (CHT-53/103) — never a silent skip."""
    _fake_cli(tmp_path, monkeypatch, "helm", "exit 1")
    with pytest.raises(AssertionError, match=r"install\.sh up"):
        cluster_gate()


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.cluster_gate", rules=["CHT-103"])
def test__gate_passes_on_a_deployed_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A deployed release opens the lane — the gate never blocks a live cluster."""
    _fake_cli(tmp_path, monkeypatch, "helm", 'echo \'{"info":{"status":"deployed"}}\'')
    cluster_gate()


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.read_gateway_ip", rules=["CHT-103"])
def test__gateway_address_without_a_tunnel_address_fails_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No Gateway address: the failure names minikube tunnel, after polling out."""
    _fake_cli(tmp_path, monkeypatch, "kubectl", "exit 1")
    with pytest.raises(AssertionError, match="minikube tunnel"):
        read_gateway_ip(timeout=0.05, poll=0.01)


@pytest.mark.covers("aurelius_atlas_cluster_lane.secrets.SecretReader.read", rules=["CHT-103"])
def test__secret_reader_decodes_the_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Jsonpath output is base64; the reader hands back the secret (and raw bytes)."""
    payload = base64.b64encode(b"s3cr3t-pass").decode()
    _fake_cli(tmp_path, monkeypatch, "kubectl", f"echo -n {payload}")
    reader = SecretReader("atlas")
    assert reader.read("atlas-keycloak-users", "writer-password") == "s3cr3t-pass"
    assert reader.read_bytes("atlas-elasticsearch", "elastic-password") == b"s3cr3t-pass"


@pytest.mark.covers("aurelius_atlas_cluster_lane.secrets.SecretReader.read", rules=["CHT-103"])
def test__secret_reader_fails_loudly_on_a_missing_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unreadable Secret names itself — a lane without credentials is not a lane."""
    _fake_cli(tmp_path, monkeypatch, "kubectl", "echo 'no such secret' >&2; exit 1")
    with pytest.raises(AssertionError, match="unreadable"):
        SecretReader("atlas").read("nope", "nope")


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.install_resolver_shim", rules=["CHT-104"])
def test__shim_maps_the_domain_to_the_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every *.atlas.test name resolves to the Gateway, for str AND bytes hosts."""
    monkeypatch.setattr(lane, "_gateway_ip_cache", "10.9.8.7")
    with lane.install_resolver_shim():
        # The POC's rule is the suffix .atlas.test — the apex itself is not
        # mapped (byte-identical to the 10.5 conftest this library replaces).
        for host in ("atlas.atlas.test", "keycloak.atlas.test", "edge.atlas.test"):
            found = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            assert {entry[4][0] for entry in found} == {"10.9.8.7"}, host
        found = socket.getaddrinfo(b"atlas.atlas.test", 443, type=socket.SOCK_STREAM)
        assert {entry[4][0] for entry in found} == {"10.9.8.7"}


def _echo_resolver(host: object, port: object = None, **kwargs: object) -> list:  # noqa: ARG001 - resolver signature
    """A base resolver that never touches DNS: it echoes the (host, port) it receives."""
    name = host.decode() if isinstance(host, bytes) else str(host)
    return [(0, 0, 0, "", (name, port))]


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.install_resolver_shim", rules=["CHT-104"])
def test__shim_leaves_other_names_alone_and_restores_the_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unmapped names fall through to the wrapped resolver; exit restores it exactly."""
    monkeypatch.setattr(lane, "_gateway_ip_cache", "10.9.8.7")
    monkeypatch.setattr(socket, "getaddrinfo", _echo_resolver)  # the shim wraps THIS
    with lane.install_resolver_shim():
        assert socket.getaddrinfo is not _echo_resolver
        # An unmapped name falls through to the base resolver unchanged.
        found = socket.getaddrinfo("this.host.does-not-exist.invalid", 443)
        assert found[0][4] == ("this.host.does-not-exist.invalid", 443)
    assert socket.getaddrinfo is _echo_resolver  # restored on exit


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.install_resolver_shim", rules=["CHT-104"])
def test__shim_rewrites_the_host_and_port_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    """A registered (host, port) rewrites BOTH members; another port is not mapped."""
    monkeypatch.setattr(lane, "_gateway_ip_cache", "10.9.8.7")
    monkeypatch.setattr(socket, "getaddrinfo", _echo_resolver)  # the shim wraps THIS
    host = "atlas-elasticsearch.atlas.svc.cluster.local"
    with lane.install_resolver_shim():
        set_rewrite(host, 9200, ("127.0.0.1", 33111))
        try:
            for probe in (host, host.encode()):
                found = socket.getaddrinfo(probe, 9200)
                assert {(entry[4][0], entry[4][1]) for entry in found} == {("127.0.0.1", 33111)}
            # The same host at another port is not rewritten (the port is part of
            # the key): it falls through to the base resolver unchanged.
            found = socket.getaddrinfo(host, 9201)
            assert found[0][4] == (host, 9201)
        finally:
            clear_rewrite(host, 9200)


@pytest.mark.covers("aurelius_atlas_cluster_lane.lane.ca_file_fixture", rules=["CHT-103"])
def test__ca_file_fixture_branches_on_the_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cluster hands out the chart CA, compose the project's mkcert CA (CHT-103)."""
    certs = tmp_path / "certs"
    chart_ca = str(tmp_path / "chart-ca.crt")
    monkeypatch.setenv("ATLAS_E2E_TARGET", "cluster")
    assert ca_file_fixture({"ca_file": chart_ca}, certs) == chart_ca
    monkeypatch.delenv("ATLAS_E2E_TARGET")
    assert ca_file_fixture({}, certs) == str(certs / "ca.pem")
