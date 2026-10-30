"""``python -m aurelius_atlas_server``: start the server with uvicorn."""

from typing import Any

import uvicorn

from aurelius_atlas_server.app import create_app
from aurelius_atlas_server.settings import ServerSettings


def uvicorn_options(settings: ServerSettings) -> dict[str, Any]:
    """The uvicorn options: address, port, TLS and proxy trust (SRV-03, SRV-06, SRV-10, DD-234, DD-238).

    The TLS pair is part of the options unconditionally: the settings refuse to construct without it,
    so a server that starts is an HTTPS server. ``forwarded_allow_ips`` declares which peers may rewrite
    the client address through ``X-Forwarded-For`` (SRV-10) — without it uvicorn trusts only the loopback,
    and behind a proxy every request looks like it came from the proxy.
    """
    certificate, key = settings.tls
    return {
        "host": settings.host,
        "port": settings.port,
        "log_level": settings.log_level,
        "ssl_certfile": str(certificate),
        "ssl_keyfile": str(key),
        "forwarded_allow_ips": settings.forwarded_allow_ips,
    }


def run() -> None:
    """Read the settings from the environment and serve until stopped (SRV-01)."""
    settings = ServerSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    uvicorn.run(create_app(settings), **uvicorn_options(settings))


if __name__ == "__main__":
    run()
