"""Unit tests for ServiceForward and free_port — no cluster needed (CHT-104).

``kubectl`` and ``curl`` are faked on PATH: the forward's command shape, its
shim registration, and its readiness polling are what the tests pin, not a
live port-forward.
"""

import os
import socket
import stat
from pathlib import Path

import pytest
from aurelius_atlas_cluster_lane.forward import ServiceForward, free_port
from aurelius_atlas_cluster_lane.lane import install_resolver_shim, resolve_overrides


def _fake_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, body: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    cli = bin_dir / name
    cli.write_text(f"#!/usr/bin/env bash\n{body}\n")
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


def test__free_port_hands_back_a_bindable_loopback_port() -> None:
    """The port is unbound at the moment it is handed out (the forward's first need)."""
    port = free_port()
    with socket.socket() as probe:  # bindable at the moment it is handed out
        probe.bind(("127.0.0.1", port))
    assert 1024 < port < 65536


def test__url_names_the_real_service_name_and_forward_port() -> None:
    """The dial URL is the Service's real name at the forward's free port (CHT-104).

    The hostname (the verified SAN) is the real FQDN; the port is the loopback
    port the Service is forwarded to, which the shim resolves from that name.
    """
    forward = ServiceForward(
        "atlas-data2model", 21001, "atlas-data2model.atlas.svc.cluster.local", probe_path="/liveness"
    )
    assert forward.url == f"https://atlas-data2model.atlas.svc.cluster.local:{forward.local_port}"


def test__starting_registers_the_host_and_stopping_removes_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The FQDN -> 127.0.0.1 host rewrite lives with the forward (CHT-104).

    Host-only (port kept from the URL): the async HTTP stack connects on the
    URL's own port, so the rewrite must not try to move the port.
    """
    _fake_cli(tmp_path, monkeypatch, "kubectl", 'printf "%s\\n" "$*" >> "$KL_ARGS"; exec sleep 30')
    _fake_cli(tmp_path, monkeypatch, "curl", "exit 0")
    monkeypatch.setenv("KL_ARGS", str(tmp_path / "kubectl-args"))
    ca = tmp_path / "ca.crt"
    ca.write_bytes(b"-----BEGIN CERTIFICATE-----\n")
    key = ("atlas-data2model.atlas.svc.cluster.local", None)
    with install_resolver_shim():
        assert key not in resolve_overrides()
        with (
            ServiceForward(
                "atlas-data2model",
                21001,
                "atlas-data2model.atlas.svc.cluster.local",
                probe_path="/liveness",
                ca_file=str(ca),
            ) as forward,
        ):
            assert resolve_overrides()[key] == ("127.0.0.1", None)
        assert key not in resolve_overrides()
    args = (tmp_path / "kubectl-args").read_text()
    assert args.strip() == f"-n atlas port-forward svc/atlas-data2model {forward.local_port}:21001"


def test__insecure_probe_carries_the_k_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The loopback browser dial (ADR 039): readiness curl must not verify (no SAN covers 127.0.0.1)."""
    _fake_cli(tmp_path, monkeypatch, "kubectl", "exec sleep 30")
    _fake_cli(tmp_path, monkeypatch, "curl", 'printf "%s\\n" "$*" >> "$CURL_ARGS"; exit 0')
    monkeypatch.setenv("CURL_ARGS", str(tmp_path / "curl-args"))
    with ServiceForward(
        "aurelius-atlas-server", 21000, "127.0.0.1", probe_path="/api/atlas/admin/liveness", insecure=True
    ):
        pass
    args = (tmp_path / "curl-args").read_text()
    assert "-k" in args.split()
    assert "https://127.0.0.1" in args


def test__honest_probe_carries_the_ca_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A SAN-honest FQDN dial over the forward: readiness verifies against the chart CA."""
    _fake_cli(tmp_path, monkeypatch, "kubectl", "exec sleep 30")
    _fake_cli(tmp_path, monkeypatch, "curl", 'printf "%s\\n" "$*" >> "$CURL_ARGS"; exit 0')
    monkeypatch.setenv("CURL_ARGS", str(tmp_path / "curl-args"))
    ca = tmp_path / "ca.crt"
    ca.write_bytes(b"-----BEGIN CERTIFICATE-----\n")
    with ServiceForward(
        "atlas-elasticsearch",
        9200,
        "atlas-elasticsearch.atlas.svc.cluster.local",
        probe_path="/_cluster/health",
        ca_file=str(ca),
    ) as forward:
        pass
    args = (tmp_path / "curl-args").read_text().split()
    assert "--cacert" in args
    assert "-k" not in args
    # The dial name stays the FQDN: the resolve spec pins it to the forward.
    assert "--resolve" in args
    assert f"atlas-elasticsearch.atlas.svc.cluster.local:{forward.local_port}:127.0.0.1" in args


def test__a_forward_that_never_becomes_ready_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A forward whose probe never passes raises, and its shim mapping leaves with it."""
    _fake_cli(tmp_path, monkeypatch, "kubectl", "exec sleep 30")
    _fake_cli(tmp_path, monkeypatch, "curl", "exit 7")
    ca = tmp_path / "ca.crt"
    ca.write_bytes(b"-----BEGIN CERTIFICATE-----\n")
    with (
        install_resolver_shim(),
        pytest.raises(RuntimeError, match="never became ready"),
        ServiceForward(
            "atlas-data2model",
            21001,
            "atlas-data2model.atlas.svc.cluster.local",
            probe_path="/liveness",
            ca_file=str(ca),
            ready_timeout=0.2,
        ),
    ):
        pass  # pragma: no cover - the context never opens
    assert ("atlas-data2model.atlas.svc.cluster.local", None) not in resolve_overrides()
    assert resolve_overrides() == {}  # the failed start leaves no mapping behind
