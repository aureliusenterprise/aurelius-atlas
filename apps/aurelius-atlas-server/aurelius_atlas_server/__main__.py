"""``python -m aurelius_atlas_server``: start the server with uvicorn."""

from typing import Any

import uvicorn

from aurelius_atlas_server.app import create_app
from aurelius_atlas_server.settings import ServerSettings


def uvicorn_options(settings: ServerSettings) -> dict[str, Any]:
    """The uvicorn options for the settings: address, port and, when configured, TLS (SRV-03)."""
    options: dict[str, Any] = {"host": settings.host, "port": settings.port, "log_level": settings.log_level}
    if settings.tls is not None:
        certificate, key = settings.tls
        options |= {"ssl_certfile": str(certificate), "ssl_keyfile": str(key)}
    return options


def run() -> None:
    """Read the settings from the environment and serve until stopped (SRV-01)."""
    settings = ServerSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    uvicorn.run(create_app(settings), **uvicorn_options(settings))


if __name__ == "__main__":
    run()
