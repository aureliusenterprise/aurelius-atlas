from typing import Any

import uvicorn

from aurelius_fastapi_example import get_settings, main


def tls_options(cert_file: str, key_file: str) -> dict[str, Any]:
    """Return uvicorn TLS options when a certificate and key are configured.

    TLS is enabled by pointing AURELIUS_FASTAPI_TLS_CERT_FILE /
    AURELIUS_FASTAPI_TLS_KEY_FILE at a certificate and key; when unset the
    server stays plain HTTP (containerized setups terminate TLS at the proxy.
    Configuring exactly one of the two is a misconfiguration: it raises instead
    of silently falling back to plaintext (fail-closed), which would also leave
    the container's HTTPS healthcheck failing.

    Raises:
        ValueError: if only one of cert_file/key_file is set.
    """
    if bool(cert_file) != bool(key_file):
        message = (
            "AURELIUS_FASTAPI_TLS_CERT_FILE and AURELIUS_FASTAPI_TLS_KEY_FILE "
            "must both be set (or both unset) to configure TLS"
        )
        raise ValueError(message)
    if cert_file:
        return {"ssl_certfile": cert_file, "ssl_keyfile": key_file}
    return {}


def run() -> None:
    """Start the application server."""
    settings = get_settings()
    uvicorn.run(
        lambda: main(settings),
        factory=True,
        host=settings.host,
        port=settings.port,
        **tls_options(settings.tls_cert_file, settings.tls_key_file),
    )


if __name__ == "__main__":
    run()
