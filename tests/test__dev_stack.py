"""Dev-stack contract suite (CHT-101, 10.11).

The dev compose stacks publish their ports on the host for loopback tools;
the pentest's L2 half counted every one that binds ``0.0.0.0`` — on a shared
or CI host that is the LAN serving the store and the metrics DBs. The rule
is textual (compose is YAML + env interpolation, and no docker runs in this
suite): every ``ports:`` entry in the observability and store compose files
carries a loopback bind. In-network consumers (Grafana datasources, compose
DNS names, the collector's exporter endpoints) never touch the host publish,
which is why pinning all of them is zero-breakage. The Keycloak issuer and
the template Postgres publishes are named-but-deferred in the increment
spec — their e2e consumers dial the host-gateway address, so a pin needs a
compose-network rework, not one line.
"""

from __future__ import annotations

import pytest
import yaml
from conftest import WORKSPACE

DEV_COMPOSES = sorted(
    {p for stack in ("observability", "elasticsearch") for p in WORKSPACE.glob(f"dev/{stack}/docker-compose*.yaml")}
)

LOOPBACKS = {"127.0.0.1", "localhost"}


def _host_ip(publish: str) -> str | None:
    """The bind address of a compose publish entry (None when it floats).

    The shapes here are ``host:container`` (floats on 0.0.0.0) and
    ``ip:host:container``; the host part may be a ``${VAR}`` — interpolation
    never touches the leading address, so a textual split is honest.
    """
    parts = publish.removeprefix("[").split(":")
    return parts[0] if len(parts) >= 3 else None


@pytest.mark.covers(rules=["CHT-101"])
def test__dev_compose_publishes_are_loopback_pinned() -> None:
    """No dev-stack port binds every interface (CHT-101).

    Interpolated host ports (``${VAR}``) stay readable in the raw text — the
    files are scanned unparsed — so a host part must still be a literal
    loopback address.
    """
    assert DEV_COMPOSES, "the dev/* compose stacks moved; update this guard"
    offenders: list[str] = []
    for path in DEV_COMPOSES:
        docs = yaml.safe_load_all(path.read_text())
        for doc in docs:
            for service, spec in (doc or {}).get("services", {}).items():
                for publish in (spec or {}).get("ports", []):
                    text = str(publish)
                    if _host_ip(text) not in LOOPBACKS:
                        offenders.append(f"{path.relative_to(WORKSPACE)}:{service} -> {text}")
    assert not offenders, "unpinned dev publishes (prefix 127.0.0.1:):\n" + "\n".join(offenders)
